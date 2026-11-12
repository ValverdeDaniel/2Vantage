import { useQueryClient } from '@tanstack/react-query';
import { useCallback } from 'react';
import { censusPagesKey, patchMember } from '../../api/census';
import { invalidateDeal } from '../../api/deals';
import useUndoStack from '../../grid/useUndoStack';
import useWriteQueue, { refusalText } from '../../grid/useWriteQueue';
import { undoWrite } from '../../grid/undoStack';
import { useToast } from '../../ui/useToast';
import { cellOf, splitCell, withAnswer, withValue } from './rosterModel';

/*
 * The roster's cell writes in ✎ Edit (plan.md §7.7, §8.21; C5, C6, F70, F71; O.6 #33): a typed value shows at once on
 * the cached page, then goes through the per-cell queue as one PATCH census/members/{id}/ {values, expect, relay?}.
 * `expect` is the value the person saw, so a cell someone else changed meanwhile is never written over (409, its
 * sentence on the cell). The answer is the changed person and their issues only (C6), laid over the page; one refetch
 * per burst, when the queue has settled, re-reads every other person's underline (a duplicate SSN, a dependent's
 * tier). Each stored write is one undo step; Ctrl+Z or ↶ Undo writes the earlier value expecting the stored one.
 * Cells are "<member id>|<key>". `relay` is "These came from the client" (C4).
 */

/** The server's sentence for one refused cell (400 {values: {key: sentence}}), else the error as it came. */
function refusalFor(key, error) {
  const values = error?.response?.data?.values;
  const sentence = Array.isArray(values) ? values[0] : values?.[key];
  if (typeof sentence !== 'string') return error;
  return Object.assign(new Error(sentence), { response: { ...error.response, data: { detail: sentence } } });
}

export default function useRosterWrites(dealId, session, { relay = false } = {}) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const undo = useUndoStack(session);

  const show = useCallback(
    (memberId, key, value) =>
      queryClient.setQueriesData({ queryKey: censusPagesKey(dealId) }, (page) => withValue(page, memberId, key, value)),
    [queryClient, dealId],
  );

  const writes = useWriteQueue({
    send: async (cell, value, expect) => {
      const [memberId, key] = splitCell(cell);
      let answer;
      try {
        answer = await patchMember(memberId, {
          values: { [key]: value },
          expect: { [key]: expect ?? '' },
          ...(relay ? { relay: true } : {}),
        });
      } catch (error) {
        throw refusalFor(key, error);
      }
      queryClient.setQueriesData({ queryKey: censusPagesKey(dealId) }, (page) => withAnswer(page, answer));
      return answer.member.values[key] ?? '';
    },
    onFailed: (cell, saved) => {
      const [memberId, key] = splitCell(cell);
      show(memberId, key, saved);
    },
    onIdle: () => invalidateDeal(queryClient, dealId),
  });

  /** A committed edit: `base` is the text the editor opened with. */
  const commit = useCallback(
    (memberId, key, text, base) => {
      const value = String(text ?? '').trim();
      const cell = cellOf(memberId, key);
      show(memberId, key, value);
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
    const [memberId, key] = splitCell(cell);
    show(memberId, key, value);
    writes.enqueue(cell, value, expect).catch((error) => toast.error(refusalText(error)));
    return { memberId, key };
  }, [undo, writes, show, toast]);

  return { commit, undo: undoLast, canUndo: undo.canUndo, settle: writes.settle, errorOf: writes.errorOf };
}
