import { createElement, useState } from 'react';
import { useReviewMarks } from '../../../api/confidence';
import { useRevertActivity } from '../../../api/deals';
import { errorText } from '../../../lib/errors';
import { useToast } from '../../../ui/useToast';
import { restoredCount, undoneText } from '../../../valuereview/reviewWords';
import { markToast } from './confidenceWords';

/*
 * The data confidence's one door for reviews (plan.md §8.6; M88–M91; the old DataConfidence's `confirmDoc`, `reviewDoc`,
 * `reviewOne` and `undoAllIgnored`): every button posts review's marks across owners, so each is one Activity row
 * whose toast offers Undo (its revert, `activity/{id}/revert/`; refused in words when the values changed since).
 * `run(key, body, where)` names what runs in `busy` (a file's id with its action, a row's ref, 'undo-all'), so only
 * that button says it is working and the rest wait.
 */
function UndoNote({ text, onUndo }) {
  return createElement(
    'span',
    null,
    text,
    ' · ',
    createElement('button', { type: 'button', className: 'bnf-linklike', onClick: onUndo }, 'Undo'),
  );
}

export default function useConfidenceMarks(dealId) {
  const toast = useToast();
  const mark = useReviewMarks(dealId);
  const revert = useRevertActivity(dealId);
  const [busy, setBusy] = useState('');

  function undo(activityId) {
    revert.mutate(activityId, {
      onSuccess: (answer) => toast.success(undoneText(restoredCount(answer.changes))),
      onError: (error) => toast.error(errorText(error, { fallback: 'Could not undo that review.' })),
    });
  }

  async function run(key, body, where = '') {
    if (busy) return;
    setBusy(key);
    try {
      const answer = await mark.mutateAsync(body);
      const text = markToast(body.action, answer.count, where);
      if (answer.activity_id) {
        toast.success(createElement(UndoNote, { text, onUndo: () => undo(answer.activity_id) }), { duration: 10000 });
      } else {
        toast.info(text);
      }
    } catch (error) {
      toast.error(errorText(error, { fallback: 'Could not save the review.' }));
    } finally {
      setBusy('');
    }
  }

  return { busy: busy || (revert.isPending ? 'undo' : ''), run };
}
