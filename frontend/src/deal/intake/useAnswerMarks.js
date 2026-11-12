import { useQueryClient } from '@tanstack/react-query';
import { createElement, useState } from 'react';
import { intakeKey, postMarks } from '../../api/intake';
import { revertActivity } from '../../api/deals';
import { errorText } from '../../lib/errors';
import { useToast } from '../../ui/useToast';
import { reviewToast } from '../../valuereview/reviewWords';

/*
 * Review marks on the form's answers (plan.md §10.7; B10, B11; E48, E54): ✓ Approve, Ignore and ⚑ Needs checking on
 * the ticked answers (`refs`) or, from the review bar, on every open warning the form counts. The reply's marks,
 * statuses and counts land on the copy on screen at once; the toast offers ↶ Undo, which reverts the one `marked`
 * Activity row. `busy` names the action in flight.
 */
export default function useAnswerMarks(dealId) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const [busy, setBusy] = useState('');

  function adopt(reply) {
    queryClient.setQueryData(intakeKey(dealId), (data) =>
      data
        ? { ...data, sources: { ...data.sources, ...reply.sources }, status: reply.status, review: reply.review }
        : data,
    );
  }

  async function undo(activityId) {
    try {
      await revertActivity(activityId);
      toast.success('Undone');
    } catch (error) {
      toast.error(errorText(error));
    }
    queryClient.invalidateQueries({ queryKey: intakeKey(dealId) });
  }

  /** Mark `keys` (or, with none, every open warning on the form); resolves true once marked. */
  async function run(action, keys = null, where = '') {
    if (busy) return false;
    setBusy(action);
    try {
      const reply = await postMarks(dealId, { action, ...(keys ? { refs: keys.map((key) => `intake:${key}`) } : {}) });
      adopt(reply);
      const words = reviewToast(action, reply.changed, where).replace(/\bvalue(s?)\b/, 'answer$1');
      if (!reply.activity_id) toast.info(words);
      else {
        const button = createElement(
          'button',
          { type: 'button', className: 'bnf-linklike', onClick: () => undo(reply.activity_id) },
          'Undo',
        );
        toast.success(createElement('span', null, words, ' · ', button), { duration: 10000 });
      }
      return true;
    } catch (error) {
      toast.error(errorText(error));
      return false;
    } finally {
      setBusy('');
    }
  }

  return { run, busy };
}
