import { useQueryClient } from '@tanstack/react-query';
import { useCallback } from 'react';
import { invalidateDeal } from '../../api/deals';
import { intakeKey, patchAnswers } from '../../api/intake';
import useWriteQueue from '../../grid/useWriteQueue';
import { withAnswer, withReply } from './formModel';

/*
 * The form's saves (plan.md §7.6, §8.21; B4): an answer shows at once on the copy on screen, then goes through the
 * per-answer write queue (src/grid/writeQueue.js: one request in flight per answer, the latest wins, each write
 * `expect`s the answer it replaces) as one PATCH deals/{id}/intake/. The reply carries the answers the server stored
 * and the form's state (hidden and needed questions, statuses, issues), laid over the copy at once; a refused answer
 * goes back to what was stored and its sentence stays under the row (`errorOf`) until it is written again. One
 * refetch per burst, header included (the target effective date is the deal's).
 */

/** The server's sentence for one refused answer (400 {answers: {key: sentence}}), else the queue's own words. */
function refusalFor(key, error) {
  const sentence = error?.response?.data?.answers?.[key];
  if (typeof sentence !== 'string') return error;
  return Object.assign(new Error(sentence), { response: { ...error.response, data: { detail: sentence } } });
}

export default function useAnswerWrites(dealId, { relay = false } = {}) {
  const queryClient = useQueryClient();
  const key = intakeKey(dealId);

  const show = useCallback(
    (answerKey, value) => queryClient.setQueryData(intakeKey(dealId), (data) => withAnswer(data, answerKey, value)),
    [queryClient, dealId],
  );

  const writes = useWriteQueue({
    send: async (answerKey, value, expect) => {
      let reply;
      try {
        reply = await patchAnswers(dealId, {
          answers: { [answerKey]: value },
          expect: { [answerKey]: expect ?? '' },
          ...(relay ? { relay: true } : {}),
        });
      } catch (error) {
        throw refusalFor(answerKey, error);
      }
      queryClient.setQueryData(key, (data) => withReply(data, reply));
      return queryClient.getQueryData(key)?.answers?.[answerKey] ?? '';
    },
    onFailed: (answerKey, saved) => show(answerKey, saved),
    onIdle: () => invalidateDeal(queryClient, dealId, { header: true }),
  });

  /** Save `text` for `answerKey`, whose stored answer was `base`. Resolves to the payload once the server has stored
   * it (null when it failed or a newer answer replaced it). */
  const { enqueue } = writes;
  const save = useCallback(
    (answerKey, text, base) => {
      show(answerKey, text);
      return enqueue(answerKey, text, base).then(
        (done) => (done ? queryClient.getQueryData(intakeKey(dealId)) : null),
        () => null,
      );
    },
    [enqueue, show, queryClient, dealId],
  );

  return { save, errorOf: writes.errorOf, settle: writes.settle };
}
