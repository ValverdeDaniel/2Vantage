// The printed tables of a deal's scanned quotes (plan.md §7.8, O.3.5; F42, E42; slice 21), for the Advisor's
// "As quoted" and Documents' "As in the file". Read only; under the Advisor's keys, so a landed read, an Undo and a
// value typed anywhere refetch them: ['deal', id, 'advisor', 'as-quoted'] · […, 'as-quoted', document, line].
import { useQuery } from '@tanstack/react-query';
import api from './client';
import { advisorKey } from './quotes';

const PATH = (dealId) => `deals/${dealId}/plans/as-quoted/`;

/** [{document, line, line_label, label, where, page_label, plans, rows, written_at}]: one entry per printed table on
 *  a file not removed, files in upload order. */
export function useQuotedFiles(dealId, { enabled = true } = {}) {
  return useQuery({
    queryKey: advisorKey(dealId, 'as-quoted'),
    queryFn: async () => (await api.get(PATH(dealId))).data.files,
    enabled: Boolean(dealId) && enabled,
    staleTime: 0,
  });
}

/** One table: {document, line, line_label, label, kind, where, page_label, written_at, job, columns: [{col, plan,
 *  head}], left_out, rows: [{label, keys, printed?}]}; `printed` has one cell per column (none for PHI kinds). */
export function useQuotedTable(dealId, documentId, line, { enabled = true } = {}) {
  return useQuery({
    queryKey: advisorKey(dealId, 'as-quoted', Number(documentId), line || ''),
    queryFn: async () => (await api.get(PATH(dealId), { params: { document: documentId, line } })).data,
    enabled: Boolean(dealId && documentId) && enabled,
    staleTime: 0,
  });
}
