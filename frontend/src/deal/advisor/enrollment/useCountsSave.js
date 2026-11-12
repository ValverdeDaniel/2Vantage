import { createElement } from 'react';
import { useRevertActivity } from '../../../api/deals';
import { useSaveEnrollment } from '../../../api/enrollment';
import { errorText } from '../../../lib/errors';
import { useToast } from '../../../ui/useToast';
import UndoNote from '../board/UndoNote';

/*
 * The counts card's writes (plan.md §5.5; F85, F88, F90, F91): Save, the switch and "Keep my typed counts", each one
 * POST to the line's typed-set door, worded in the old card's toasts with Undo through the row it wrote. An unchanged
 * save answers no row: "Nothing changed". A refusal or a 400 keeps the card open with the server's sentence.
 */
export default function useCountsSave(dealId, line, lineLabel) {
  const toast = useToast();
  const door = useSaveEnrollment(dealId);
  const revert = useRevertActivity(dealId);

  const said = (text, answer) => {
    const id = answer?.activity_id;
    if (!id) {
      toast.success('Nothing changed');
      return answer;
    }
    const onUndo = () =>
      revert
        .mutateAsync(id)
        .then(() => toast.success('Undone'))
        .catch((error) => toast.error(errorText(error)));
    toast.success(createElement(UndoNote, { text, onUndo }), { duration: 10000 });
    return answer;
  };

  return {
    busy: door.isPending,
    error: door.error,
    reset: door.reset,
    save: (body, words) => door.mutateAsync({ line, ...body }).then((answer) => said(words, answer)),
    flip: (on) =>
      door
        .mutateAsync({ line, on })
        .then((answer) =>
          said(
            on
              ? `Summary tiers on: typed counts price ${lineLabel}`
              : `Summary tiers off: ${lineLabel} prices on the census (counts kept)`,
            answer,
          ),
        ),
    keep: () =>
      door
        .mutateAsync({ line, keep: true })
        .then((answer) => said(`Your typed counts price ${lineLabel} again`, answer))
        .catch((error) => toast.error(errorText(error))),
  };
}
