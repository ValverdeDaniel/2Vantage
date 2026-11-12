import { useQueryClient } from '@tanstack/react-query';
import { useCallback } from 'react';
import { advisorKey, patchPlan, refreshAdvisor } from '../../../api/quotes';
import useUndoStack from '../../../grid/useUndoStack';
import useWriteQueue, { refusalText } from '../../../grid/useWriteQueue';
import { undoWrite } from '../../../grid/undoStack';
import { useToast } from '../../../ui/useToast';

/*
 * The board's cell writes in ✎ Edit (plan.md §8.21; F70, F71, J74; O.6 #33). A typed value shows at once in the
 * cached comparison, then goes through the per-cell queue as one PATCH plans/{id}/ {values, expect}: `expect` is the
 * value the person saw, so a value someone else changed meanwhile is never written over (409, its sentence on the
 * cell). Each stored write is one undo step; Ctrl+Z or ↶ Undo writes the earlier value expecting the stored one, and
 * the server refuses it when the cell changed since. One refetch per burst, when the queue has settled.
 * Cells are "<plan id>|<field key>", whatever the orientation.
 */

const cellOf = (planId, key) => `${planId}|${key}`;
function split(cell) {
  const at = cell.indexOf('|');
  return [Number(cell.slice(0, at)), cell.slice(at + 1)];
}

export default function useCellWrites(dealId, session) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const undo = useUndoStack(session);

  // Every cached comparison of the deal that holds the plan (the line's board).
  const show = useCallback(
    (planId, key, value) => {
      queryClient.setQueriesData({ queryKey: advisorKey(dealId) }, (data) =>
        data?.plans?.some((plan) => plan.id === planId)
          ? {
              ...data,
              plans: data.plans.map((plan) =>
                plan.id === planId ? { ...plan, values: { ...plan.values, [key]: value ?? '' } } : plan,
              ),
            }
          : data,
      );
    },
    [queryClient, dealId],
  );

  const writes = useWriteQueue({
    send: async (cell, value, expect) => {
      const [planId, key] = split(cell);
      const answer = await patchPlan(planId, { values: { [key]: value }, expect: { [key]: expect ?? '' } });
      const stored = answer.values?.[key] ?? '';
      show(planId, key, stored);
      return stored;
    },
    onFailed: (cell, saved) => {
      const [planId, key] = split(cell);
      show(planId, key, saved);
    },
    onIdle: () => refreshAdvisor(queryClient, dealId),
  });

  /** A committed edit: `base` is the value the editor opened with. */
  const commit = useCallback(
    (planId, key, text, base) => {
      const value = String(text ?? '').trim();
      const cell = cellOf(planId, key);
      show(planId, key, value);
      writes
        .enqueue(cell, value, base ?? '')
        .then((done) => {
          if (done && done.before !== done.after) undo.push({ cell, before: done.before, after: done.after });
        })
        .catch(() => {}); // the message is on the cell
    },
    [writes, show, undo],
  );

  /** Ctrl+Z and ↶ Undo: the newest step back, or a refusal in words. Returns the cell it went to, or null. */
  const undoLast = useCallback(() => {
    const entry = undo.take();
    if (!entry) return null;
    const { cell, value, expect } = undoWrite(entry);
    const [planId, key] = split(cell);
    show(planId, key, value);
    writes.enqueue(cell, value, expect).catch((error) => toast.error(refusalText(error)));
    return { planId, key };
  }, [undo, writes, show, toast]);

  return {
    commit,
    undo: undoLast,
    canUndo: undo.canUndo,
    settle: writes.settle,
    errorOf: writes.errorOf,
  };
}
