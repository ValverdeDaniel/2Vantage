// Documents (plan.md §7.4; E.6). Query keys: ['deal', id, 'documents'] and ['deal', id, 'documents', 'removed'];
// ['value-source', ref] for one value's source on ↗. Documents' writes refetch only the documents lists (E53), never
// the whole deal; a removed or restored file also refetches the deal's header (its counts move).
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import api from './client';
import { dealKey } from './deals';

export const documentsKey = (dealId) => dealKey(dealId, 'documents');
export const removedKey = (dealId) => dealKey(dealId, 'documents', 'removed');

export function useDocuments(dealId) {
  return useQuery({
    queryKey: documentsKey(dealId),
    queryFn: async () => (await api.get(`deals/${dealId}/documents/`)).data,
    staleTime: 0,
  });
}

/** "Show removed files (N)" (E16): the deal's archived files. */
export function useRemovedDocuments(dealId) {
  return useQuery({
    queryKey: removedKey(dealId),
    queryFn: async () => (await api.get(`deals/${dealId}/documents/`, { params: { archived: 1 } })).data,
    staleTime: 0,
  });
}

function useDocumentsWrite(dealId, mutationFn) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: documentsKey(dealId) }),
  });
}

/** ({file, kind, role, carrier, lines, label}) → document. One file per request (E7). */
export function useUploadDocument(dealId) {
  return useDocumentsWrite(dealId, async ({ file, lines = [], ...meta }) => {
    const form = new FormData();
    form.append('file', file);
    Object.entries(meta).forEach(([key, value]) => value != null && form.append(key, value));
    form.append('lines', JSON.stringify(lines));
    return (await api.post(`deals/${dealId}/documents/`, form)).data;
  });
}

/** ({documentId, changes}) → document. An unchanged PATCH writes nothing (E14). */
export function useUpdateDocument(dealId) {
  return useDocumentsWrite(
    dealId,
    async ({ documentId, changes }) => (await api.patch(`documents/${documentId}/`, changes)).data,
  );
}

/** Remove (archive) or Restore one file (E15, E16): (documentId) → document. */
export function useArchiveDocument(dealId, { restore = false } = {}) {
  return useDocumentsWrite(
    dealId,
    async (documentId) => (await api.post(`documents/${documentId}/${restore ? 'restore' : 'archive'}/`)).data,
  );
}

export function downloadUrl(documentId, { inline = false } = {}) {
  return `documents/${documentId}/download/${inline ? '?inline=1' : ''}`;
}

/** The file as the viewer fetches it: same origin, so the session goes with it (E17). */
export function inlineUrl(documentId) {
  return `/api/${downloadUrl(documentId, { inline: true })}`;
}

/** One window of a sheet (E27): {sheet, start, cell, look}. */
export async function fetchSheet(documentId, params) {
  return (await api.get(`documents/${documentId}/sheet/`, { params })).data;
}

/** Where a value is in a sheet, posted in the body, never the URL (E28): {value, line, hint} → {sheet, cell, state}. */
export async function findInSheet(documentId, body) {
  return (await api.post(`documents/${documentId}/sheet/find/`, body)).data;
}

/*
 * A value's full source, for ↗ (E18): served by the value's owner (O.3.1). `ref` is "plan:<id>:<key>" (quotes),
 * "census:<member id>:<key>" (census) or "intake:<key>" (intake, the deal's own form; slice 65). → {value, label, hint,
 * what, source: {doc, page, cell, line, loc, ...}}. The questionnaire's refs join with its slice.
 */
const OWNERS = {
  plan: { url: (id) => `plans/${id}/source/` },
  census: { url: (id) => `census/members/${id}/source/` },
  intake: { url: (_id, dealId) => `deals/${dealId}/intake/source/`, ofDeal: true },
};

export function parseRef(ref) {
  const [owner, ...rest] = String(ref || '').split(':');
  const spec = OWNERS[owner];
  if (!spec) return null;
  if (spec.ofDeal) {
    const key = rest.join(':');
    return key ? { owner, id: null, key } : null;
  }
  const [id, ...more] = rest;
  const key = more.join(':');
  return /^\d+$/.test(id || '') && key ? { owner, id: Number(id), key } : null;
}

export function useValueSource(ref, dealId) {
  const parsed = parseRef(ref);
  return useQuery({
    queryKey: ['value-source', ref, dealId],
    queryFn: async () => {
      const url = OWNERS[parsed.owner].url(parsed.id, dealId);
      return (await api.get(url, { params: { key: parsed.key } })).data;
    },
    enabled: Boolean(parsed),
    staleTime: 0,
    // A refusal (4xx) is the answer; a dropped connection or a server error is asked again, twice.
    retry: (count, error) => count < 2 && !(error?.response?.status < 500),
  });
}
