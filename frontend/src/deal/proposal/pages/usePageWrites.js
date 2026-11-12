import { useSetRecommended } from '../../../api/quotes';
import { useOrderPlans, usePutInSlot, useSetLinks, useStar } from '../../../api/quotesBoard';
import { errorText } from '../../../lib/errors';
import { useToast } from '../../../ui/useToast';

/*
 * What "What the client will see" writes, each through quotes' own door (plan.md §7.8; F43, F45, F46, F52, J5, J10–J13;
 * the old AdvisorTab's placeOnPage / moveOnPage / takeOffPage at 7385bb3): a pick (`plans/slot/` `at`), "＋ Add a plan"
 * (`beside`), the arrows (`plans/order/` passing the plans the pages do not show), "Replacing:" (`plans/links/`) and ✕
 * (`plans/star/`, and `recommend/` for a recommended plan, as the server's `remove` says). Every write refetches the
 * deal's queries, the pages among them; a refusal shows the server's sentence.
 */
export default function usePageWrites(dealId, line, payload) {
  const toast = useToast();
  const doors = {
    slot: usePutInSlot(dealId),
    order: useOrderPlans(dealId),
    links: useSetLinks(dealId),
    star: useStar(dealId),
    recommend: useSetRecommended(dealId),
  };
  const failed = (error) => {
    toast.error(errorText(error));
    return null;
  };
  return {
    busy: Object.values(doors).some((door) => door.isPending),
    pick: (plan, spot) => doors.slot.mutateAsync({ line, planId: plan.plan_id, at: spot.plan_id }).catch(failed),
    add: (plan, beside) =>
      doors.slot.mutateAsync({ line, planId: plan.plan_id, beside: beside ?? undefined }).catch(failed),
    move: (plan, step) =>
      doors.order
        .mutateAsync({ line, move: { plan_id: plan.plan_id, step, among: payload?.presented_ids ?? [] } })
        .catch(failed),
    link: (plan, replacesIds) => doors.links.mutateAsync({ planId: plan.plan_id, replacesIds }).catch(failed),
    takeOff: async (plan) => {
      const { unstar, unrecommend, star } = plan.remove;
      try {
        if (unrecommend) await doors.recommend.mutateAsync({ planId: plan.plan_id, recommended: false });
        if (star.length) await doors.star.mutateAsync({ planIds: star, starred: true });
        else if (unstar) await doors.star.mutateAsync({ planIds: [plan.plan_id], starred: false });
      } catch (error) {
        failed(error);
      }
    },
  };
}
