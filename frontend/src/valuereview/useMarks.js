import { useState } from 'react';
import { useMarkPlans, useUndoReview } from '../api/planReview';
import { errorText } from '../lib/errors';
import { useToast } from '../ui/useToast';
import { confirmWords, restoredCount, reviewToast, undoneText } from './reviewWords';

/*
 * One door for every review of plan values (plan.md §10.7; E48, E52–E54, E58, F63, F65, F67): the station's strip,
 * List and keys and the Advisor's flags chip and strip all mark through it, so each action is one Activity row with
 * its ↶ Undo. `run(action, target, {where, fromKey, count})` posts `target` ({refs} | {plan_ids} | {document_ids});
 * a key that would act on more than 25 values asks first (D126). `last` is what the last action did, until Undo or the
 * next one; `undo()` reverts it, and says how many values came back and how many changed since (E54).
 */
export default function useMarks(dealId, { toastDone = true } = {}) {
  const toast = useToast();
  const mark = useMarkPlans(dealId);
  const undoer = useUndoReview(dealId);
  const [last, setLast] = useState(null); // {action, changed, activityId}

  async function run(action, target, { where = '', fromKey = false, count = 0 } = {}) {
    if (mark.isPending) return null;
    const question = confirmWords(action, count, { fromKey });
    if (question && !window.confirm(question)) return null;
    try {
      const answer = await mark.mutateAsync({ action, ...target });
      setLast(answer.changed ? { action, changed: answer.changed, activityId: answer.activity_id } : null);
      if (toastDone || !answer.changed) toast.info(reviewToast(action, answer.changed, where));
      return answer;
    } catch (error) {
      toast.error(errorText(error));
      return null;
    }
  }

  async function undo(done = last) {
    if (!done?.activityId || undoer.isPending) return;
    try {
      const answer = await undoer.mutateAsync(done.activityId);
      const restored = restoredCount(answer.changes);
      toast.success(undoneText(restored, Math.max(0, done.changed - restored)));
    } catch (error) {
      toast.error(errorText(error));
    } finally {
      setLast((now) => (now?.activityId === done.activityId ? null : now));
    }
  }

  return {
    run,
    undo,
    last,
    forget: () => setLast(null),
    busy: mark.isPending ? mark.variables?.action || 'busy' : '',
    undoing: undoer.isPending,
  };
}
