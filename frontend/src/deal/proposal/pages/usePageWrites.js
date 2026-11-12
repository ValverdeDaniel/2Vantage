import { useSetRecommended, useUpdatePlan } from '../../../api/quotes';
import { useOrderPlans, usePairPlans, usePutInSlot, useSetLinks, useStar } from '../../../api/quotesBoard';
import { errorText } from '../../../lib/errors';
import { useToast } from '../../../ui/useToast';

/*
 * What "What the client will see" writes, each through quotes' own door (plan.md §7.8; F43, F45, F46, F52, J5, J10–J13;
 * the old AdvisorTab's placeOnPage / moveOnPage / takeOffPage at 7385bb3): a pick (`plans/slot/` `at`), "＋ Add a plan"
 * (`beside`), the arrows (`plans/order/` passing the plans the pages do not show), "Replacing:" (`plans/links/`) and ✕
 * (`plans/star/`, and `recommend/` for a recommended plan, as the server's `remove` says); in the builder, "Our
 * recommendation" (`recommend/`, J52), ⋯ More's name on client documents (PATCH `client_name`, J14) and its "⧉ One
 * column with… · Split" (`plans/pair/`, J15; slice 33; ✕ on a pair takes both halves off). Every write refetches the
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
    rename: useUpdatePlan(dealId),
    pair: usePairPlans(dealId),
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
    recommend: (plan) =>
      doors.recommend.mutateAsync({ planId: plan.plan_id, recommended: !plan.recommended }).catch(failed),
    rename: (plan, name) =>
      doors.rename.mutateAsync({ planId: plan.plan_id, changes: { client_name: name } }).catch(failed),
    pairWith: (plan, otherId) =>
      doors.pair.mutateAsync({ firstId: plan.plan_id, secondId: otherId }).catch(failed),
    split: (plan) => doors.pair.mutateAsync({ planId: plan.plan_id, split: true }).catch(failed),
    takeOff: async (plan) => {
      const { unstar, unrecommend, star, also = [] } = plan.remove;
      try {
        if (unrecommend) await doors.recommend.mutateAsync({ planId: plan.plan_id, recommended: false });
        if (star.length) await doors.star.mutateAsync({ planIds: star, starred: true });
        else if (unstar || also.length) {
          await doors.star.mutateAsync({ planIds: [plan.plan_id, ...also], starred: false });
        }
      } catch (error) {
        failed(error);
      }
    },
  };
}
