import { useSaveEnrollment } from '../../../api/enrollment';
import { useSetIntent } from '../../../api/intake';
import { useSetConfig, useSetMark } from '../../../api/proposals';
import { useSetRecommended } from '../../../api/quotes';
import { useOrderPlans } from '../../../api/quotesBoard';
import { errorText } from '../../../lib/errors';
import { useToast } from '../../../ui/useToast';

/*
 * What the builder writes (plan.md §7.12, §8.14; J18–J20, J30, J31, J48, J55): one config path at a time, merged on
 * the server, which takes the mark off the card that owns it (J19, J20); a card's mark; and, through their own apps'
 * doors, "Recommend the renewal for every plan" (quotes' recommend, one plan after another), "Back to the default
 * order", the EnrollmentStrip's line figure (quotes' enrollment door) and "Put it on" (intake's intent door). Each
 * refetches the deal; a refusal shows the server's sentence. Downloads, when they come, wait on useIsMutating().
 */
export default function useBuilderWrites(dealId) {
  const toast = useToast();
  const doors = {
    config: useSetConfig(dealId),
    mark: useSetMark(dealId),
    recommend: useSetRecommended(dealId),
    order: useOrderPlans(dealId),
    enrollment: useSaveEnrollment(dealId),
    intent: useSetIntent(dealId),
  };
  const failed = (error) => {
    toast.error(errorText(error));
    return null;
  };
  return {
    busy: Object.values(doors).some((door) => door.isPending),
    setPath: (path, value) => doors.config.mutateAsync({ [path]: value }).catch(failed),
    mark: (card, done) => doors.mark.mutateAsync({ card: card.key, line: card.line ?? '', done }).catch(failed),
    recommendAll: async (planIds) => {
      try {
        for (const planId of planIds) await doors.recommend.mutateAsync({ planId, recommended: true });
      } catch (error) {
        failed(error);
      }
    },
    resetOrder: (line) => doors.order.mutateAsync({ line, reset: true }).catch(failed),
    saveEnrollment: (line, figures) => doors.enrollment.mutateAsync({ line, whole_line: figures }).catch(failed),
    putOn: (line, hasToday) =>
      doors.intent.mutateAsync({ line, this_year: 'market', has_today: hasToday }).catch(failed),
  };
}
