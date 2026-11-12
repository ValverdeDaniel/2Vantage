import { useQueryClient } from '@tanstack/react-query';
import { useUpdateDocument, useUploadDocument } from '../../api/documents';
import { intakeKey, useAddCoverage, useConfirmIntent, useEditCoverage, useSetIntent } from '../../api/intake';
import { errorText } from '../../lib/errors';
import { useToast } from '../../ui/useToast';

/*
 * Every write of the Coverage & marketing intent card, one at a time (`busy`), with a toast in words on failure:
 * the intent door (the two controls, ×, select-all), Confirm and Reopen, the row's own facts (carrier, funding,
 * dates, note, guarantee: coverage's door, which creates the row on a line nobody has answered, as the old card did),
 * "＋ Add a line…", and the document chips' re-file, scope and upload (documents' doors).
 */
export default function useCoverageWrites(dealId) {
  const toast = useToast();
  const queryClient = useQueryClient();
  const intent = useSetIntent(dealId);
  const confirm = useConfirmIntent(dealId);
  const reopen = useConfirmIntent(dealId, { reopen: true });
  const add = useAddCoverage(dealId);
  const edit = useEditCoverage(dealId);
  const patchDoc = useUpdateDocument(dealId);
  const upload = useUploadDocument(dealId);
  const all = [intent, confirm, reopen, add, edit, patchDoc, upload];
  const busy = all.some((mutation) => mutation.isPending);

  const run = (mutation, value, fallback, done, after) => {
    if (busy) return;
    mutation.mutate(value, {
      onSuccess: () => {
        if (after) after();
        if (done) toast.success(done);
      },
      onError: (error) => toast.error(errorText(error, { fallback })),
    });
  };
  // A file's kind or lines move the chips: the card's counts come with the intake payload.
  const refreshCard = () => queryClient.invalidateQueries({ queryKey: intakeKey(dealId) });

  return {
    busy,
    setIntent: (row, patch) => run(intent, { line: row.line, ...patch }, 'Could not save that change.'),
    applyAll: (lines, patch) => lines.length && run(intent, { lines, ...patch }, 'Could not update those lines.'),
    patchLine: (row, patch) =>
      row.coverage_id
        ? run(edit, { id: row.coverage_id, changes: patch }, 'Could not save that change.')
        : run(add, { line: row.line, ...patch }, 'Could not save that change.'),
    addLine: (line) => run(add, { line, in_force: false }, 'Could not add that line.'),
    confirm: () => run(confirm, undefined, 'Could not confirm the coverage.', 'Coverage & intent confirmed'),
    reopen: () => run(reopen, undefined, 'Could not reopen the coverage.', 'Coverage confirmation cleared'),
    patchDocument: (documentId, changes) =>
      run(patchDoc, { documentId, changes }, 'Could not update that document.', null, refreshCard),
    uploadDocument: (line, kind, label, file) =>
      run(upload, { file, kind, lines: [line] }, 'Could not attach that file.', `${label} attached`, refreshCard),
  };
}
