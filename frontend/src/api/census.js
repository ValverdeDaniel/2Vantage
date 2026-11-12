// Census (plan.md §7.7). Query keys: ['deal', id, 'census'] (the page: summary, rollup, imports; staleTime 0, a deal
// tab) and ['deal', id, 'census', 'import', importId] (the mapping dialog: samples read from the file for that answer
// only, never stored). Writes refetch the census page; the dry run writes nothing and is not cached.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import api from './client';
import { dealKey, invalidateDeal } from './deals';
import { documentsKey } from './documents';

export const censusKey = (dealId) => dealKey(dealId, 'census');
export const importKey = (dealId, importId) => dealKey(dealId, 'census', 'import', Number(importId));

/** GET deals/{id}/census/ → {summary, rollup, derived, columns, imports, last_import_at, page, members}. */
export function useCensus(dealId) {
  return useQuery({
    queryKey: censusKey(dealId),
    // The roster grid is slice 41's; until then the tab reads the counts and one person (page_size=1).
    queryFn: async () => (await api.get(`deals/${dealId}/census/`, { params: { page_size: 1 } })).data,
    staleTime: 0,
  });
}

/** GET census/imports/{id}/ → the import with its samples, sheets and reformat (C14, C15). */
export function useCensusImport(dealId, importId) {
  return useQuery({
    queryKey: importKey(dealId, importId),
    queryFn: async () => (await api.get(`census/imports/${importId}/`)).data,
    enabled: Boolean(importId),
    staleTime: 0,
  });
}

/**
 * The import door: mutate({file}) uploads a census file through documents' one door (kind census), then proposes its
 * mapping; mutate({documentId}) maps a census file already on the deal. → the proposed import.
 */
export function useStartImport(dealId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ file, documentId }) => {
      let id = documentId;
      if (file) {
        const form = new FormData();
        form.append('file', file);
        form.append('kind', 'census');
        form.append('lines', JSON.stringify([]));
        id = (await api.post(`deals/${dealId}/documents/`, form)).data.id;
      }
      return (await api.post(`deals/${dealId}/census/imports/`, { document_id: id })).data;
    },
    onSuccess: (imp) => {
      queryClient.setQueryData(importKey(dealId, imp.id), imp);
      queryClient.invalidateQueries({
        queryKey: censusKey(dealId),
        exact: true,
      });
      queryClient.invalidateQueries({ queryKey: documentsKey(dealId) });
    },
  });
}

/** mutate(changes) — PATCH {sheet_name?, header_row?, first_data_row?, reformat?, mapping?: [{column, field}]}. */
export function useUpdateImport(dealId, importId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (changes) => (await api.patch(`census/imports/${importId}/`, changes)).data,
    onSuccess: (imp) => queryClient.setQueryData(importKey(dealId, importId), imp),
  });
}

/** POST census/imports/{id}/apply/?dry_run=1 → {added, changed, removed, kept, cells_changed, counts, masked_ssns}. */
export async function dryRun(importId) {
  return (await api.post(`census/imports/${importId}/apply/`, {}, { params: { dry_run: 1 } })).data;
}

/** mutate() — apply the import → {stats, summary, import, activity_id}; the roster and its counts move. */
export function useApplyImport(dealId, importId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => (await api.post(`census/imports/${importId}/apply/`)).data,
    onSuccess: () => invalidateDeal(queryClient, dealId),
  });
}

/** mutate() — set a proposed import aside; the roster is untouched. */
export function useDiscardImport(dealId, importId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => (await api.post(`census/imports/${importId}/discard/`)).data,
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: censusKey(dealId),
        exact: true,
      }),
  });
}
