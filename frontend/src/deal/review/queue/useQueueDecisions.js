import { useState } from 'react';
import { patchMember } from '../../../api/census';
import { useInvalidateDeal } from '../../../api/deals';
import { patchAnswers } from '../../../api/intake';
import { useDecide } from '../../../api/review';
import { errorText } from '../../../lib/errors';
import { useToast } from '../../../ui/useToast';
import { approvedWords, cellOf, DECIDED } from './queueWords';

/*
 * Every write the review queue makes (L16, L17, L43, C28; old 891f1b3 `CensusClientReview.jsx` onDecide, acceptAll),
 * each through the endpoint that owns it: A approves through review (`approve/`, the owner lands it with origin
 * client), U "Keep ours" is review's reject, E "Correct" is the owner's own typed write (intake's answers, the census
 * cell), which closes the client's answer as replaced; ↶ Undo takes an approval back (`undo/`). `decided` is this
 * visit's record of it, by ref, for the queue's marks; a decision reads every deal query again (useDecide).
 */
export default function useQueueDecisions(dealId) {
  const toast = useToast();
  const decide = useDecide(dealId);
  const invalidate = useInvalidateDeal();
  const [decided, setDecided] = useState({});
  const [busyId, setBusyId] = useState(null);

  // The row itself rides along (`item`, and where it stood, `index`), so it stays in the list once a read drops it.
  const mark = (item, status, extra = {}) =>
    setDecided((now) => ({ ...now, [item.id]: { status, ...DECIDED[status], item, index: item.index ?? 0, ...extra } }));

  async function correct(item, value) {
    const cell = cellOf(item.ref);
    if (cell.surface === 'census') await patchMember(cell.memberId, { values: { [cell.column]: value } });
    else await patchAnswers(dealId, { answers: { [cell.key]: value } });
  }

  async function onDecide(item, { action, value }) {
    setBusyId(item.id);
    try {
      if (action === 'approve') {
        await decide.mutateAsync({ door: 'approve', refs: [item.ref] });
        mark(item, 'approved');
      } else if (action === 'clear') {
        await decide.mutateAsync({ door: 'reject', refs: [item.ref] });
        mark(item, 'kept');
      } else if (action === 'correct') {
        await correct(item, value);
        invalidate(dealId);
        mark(item, 'corrected', { value });
      } else {
        return false;
      }
      return true;
    } catch (error) {
      toast.error(errorText(error));
      return false;
    } finally {
      setBusyId(null);
    }
  }

  async function undo(item) {
    setBusyId(item.id);
    try {
      await decide.mutateAsync({ door: 'undo', refs: [item.ref] });
      mark(item, 'undone');
    } catch (error) {
      toast.error(errorText(error));
    } finally {
      setBusyId(null);
    }
  }

  async function approveAll(refs) {
    if (!refs?.length) return false;
    try {
      const answer = await decide.mutateAsync({ door: 'approve', refs });
      toast.success(approvedWords(answer.approved.length));
      return true;
    } catch (error) {
      toast.error(errorText(error));
      return false;
    }
  }

  return { decided, busyId, onDecide, undo, approveAll, busy: decide.isPending };
}
