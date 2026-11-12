// Census (plan.md §7.7). Query keys: ['deal', id, 'census', 'page', {page, page_size, show, q}] (the census page:
// summary, rollup, imports and one page of the roster; staleTime 0, a deal tab) and ['deal', id, 'census', 'import',
// importId] (the mapping dialog: samples read from the file for that answer only, never stored). Writes refetch the
// census pages (`refreshCensus`); the dry run writes nothing and is not cached.
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import api from './client';
import { dealKey, invalidateDeal } from './deals';
import { documentsKey } from './documents';

export const censusKey = (dealId) => dealKey(dealId, 'census');
export const censusPagesKey = (dealId) => dealKey(dealId, 'census', 'page');
export const importKey = (dealId, importId) => dealKey(dealId, 'census', 'import', Number(importId));

export const PAGE_SIZE = 100;

/** Refetch every census page of the deal (not the open mapping dialog). */
export function refreshCensus(queryClient, dealId) {
  return queryClient.invalidateQueries({ queryKey: censusPagesKey(dealId) });
}

/**
 * GET deals/{id}/census/ → {summary, rollup, derived, columns, imports, last_import_at, page, members, review, cobra}.
 * `page`, `show` (all · issues · missing) and `q` (a first or last name) pick the roster page; the counts are the
 * whole census. The page on screen stays while the next one loads.
 */
export function useCensus(dealId, { page = 1, pageSize = PAGE_SIZE, show = 'all', q = '' } = {}) {
  const params = { page, page_size: pageSize, show, q };
  return useQuery({
    queryKey: [...censusPagesKey(dealId), params],
    queryFn: async () => (await api.get(`deals/${dealId}/census/`, { params })).data,
    staleTime: 0,
    placeholderData: keepPreviousData,
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
      refreshCensus(queryClient, dealId);
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
    onSuccess: () => refreshCensus(queryClient, dealId),
  });
}

// ---- the roster grid (slice 41) ---------------------------------------------------------------------------------

/**
 * PATCH census/members/{id}/ {values: {key: text}, expect?: {key: seen}, relay?} → {member, changed, summary, review,
 * activity_id}: the changed person and their issues only (C6); 409 {detail, keys} when a cell changed since.
 */
export async function patchMember(memberId, body) {
  return (await api.patch(`census/members/${memberId}/`, body)).data;
}

/** POST deals/{id}/census/members/ {kind, employee_id?, values?, relay?} → 201 {member, summary, review, activity_id}. */
export async function addMember(dealId, body) {
  return (await api.post(`deals/${dealId}/census/members/`, body)).data;
}

/** DELETE census/members/{id}/ → 204: a soft removal, an employee's dependents too. */
export async function removeMember(memberId) {
  await api.delete(`census/members/${memberId}/`);
}

/** POST deals/{id}/census/clear/ {confirm: true} → 204: everyone removed, softly. */
export async function clearRoster(dealId) {
  await api.post(`deals/${dealId}/census/clear/`, { confirm: true });
}

/**
 * POST deals/{id}/census/marks/ {action, refs?: ["census:<member id>:<key>"]} → {action, changed, activity_id, cells:
 * [{ref, review}], review}. With no refs: every open warning on the roster (for clear, every mark).
 */
export async function postCensusMarks(dealId, body) {
  return (await api.post(`deals/${dealId}/census/marks/`, body)).data;
}

/** GET deals/{id}/census/missing/ → {refs, count}: every required blank on the roster, whatever page is shown. */
export async function getMissing(dealId) {
  return (await api.get(`deals/${dealId}/census/missing/`)).data;
}

/** The census template (§9.1: prefilled when the roster has people) and the census export (§9.2). */
export const censusTemplatePath = (dealId) => `deals/${dealId}/census/template/`;
export const censusExportPath = (dealId) => `deals/${dealId}/census/export/`;
