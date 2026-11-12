import { useQueryClient } from '@tanstack/react-query';
import { useUploadDocument } from '../../api/documents';
import { intakeKey, useChecklistItem } from '../../api/intake';
import { errorText } from '../../lib/errors';
import { useToast } from '../../ui/useToast';

/*
 * The checklist card's writes (plan.md §7.6; B27), one at a time (`busy`), with a toast in words on failure: the "On
 * file" / "Confirmed" tick, the requirement (Not needed, Still needed ▸ with the client's note, Undo) — both through
 * intake's checklist door, whose answer lands the card and the ready state at once — and ⬆ Attach, a file of the
 * item's kind through documents' one door (the card's state then comes with the intake payload). Saves stay quiet;
 * an upload says so.
 */
export default function useChecklistWrites(dealId) {
  const toast = useToast();
  const queryClient = useQueryClient();
  const item = useChecklistItem(dealId);
  const upload = useUploadDocument(dealId);
  const busy = item.isPending || upload.isPending;
  const failed = (fallback) => ({ onError: (error) => toast.error(errorText(error, { fallback })) });

  return {
    busy,
    tick: (key, checked) => item.mutate({ item: key, checked }, failed('Could not save that tick.')),
    requirement: (key, requirement, clientNote = '') =>
      item.mutate({ item: key, requirement, client_note: clientNote }, failed('Could not change that item.')),
    attach: (kind, label, file) =>
      upload.mutate(
        { file, kind },
        {
          onSuccess: () => {
            toast.success(`${label} attached`);
            queryClient.invalidateQueries({ queryKey: intakeKey(dealId) });
          },
          ...failed('Could not attach that file.'),
        },
      ),
  };
}
