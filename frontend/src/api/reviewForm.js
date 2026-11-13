// Review & requests, slice 57 (plan.md §7.13; L30, L34–L42, L45–L48, L72; B37; C27, C28, C30): the Ask card and its
// dry run, the link settings card, People & links, their form in the middle, edit mode and the sections' boards. Query
// keys ['deal', id, 'review', area] (staleTime 0, a deal tab). A write reads the Board, the request page, the tray and
// the sections again, since each moves their counts.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import api from './client';
import { invalidateDeal } from './deals';
import { reviewKey } from './review';

function refresh(queryClient, dealId) {
  ['board', 'request', 'tray', 'requests', 'section', 'blanks'].forEach((area) =>
    queryClient.invalidateQueries({ queryKey: reviewKey(dealId, area) }),
  );
}

/** GET deals/{id}/review/requests/ → {requests: [request row]}: People & links, every link ever made (L38). */
export function useRequests(dealId, enabled = true) {
  return useQuery({
    queryKey: reviewKey(dealId, 'requests'),
    queryFn: async () => (await api.get(`deals/${dealId}/review/requests/`)).data,
    staleTime: 0,
    enabled: Boolean(dealId) && enabled,
  });
}

/**
 * POST deals/{id}/review/requests/{rid}/form/?dry_run=1 (L42) — body {ids?, off?: {refs, columns, parts}, on?: {intake,
 * census, columns, census_file, documents_missing, blocks}, security?, message?, settings?: {linkId: {blank?,
 * expires_on?, nudge_on?}}} → {asks, adds, offs, floor: {level, because}, level, owed, refused, warnings, numbers}.
 * Writes nothing.
 */
export async function planForm(dealId, requestId, body) {
  return (await api.post(`deals/${dealId}/review/requests/${requestId}/form/`, body, { params: { dry_run: 1 } })).data;
}

/**
 * mutateAsync({requestId, ...body}) — POST …/requests/{rid}/form/ (Update link) → {request, changed, pins: [{link_id,
 * name, pin (this once)}], sent, closed, activity_id}. 409 {detail} or {detail, needs_level}.
 */
export function useUpdateForm(dealId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ requestId, ...body }) =>
      (await api.post(`deals/${dealId}/review/requests/${requestId}/form/`, body)).data,
    onSettled: () => refresh(queryClient, dealId),
  });
}

/** mutateAsync({requestId, people}) — POST …/requests/{rid}/people/ (L72) → {request, links: [made], activity_id}. */
export function useGiveAccess(dealId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ requestId, people }) =>
      (await api.post(`deals/${dealId}/review/requests/${requestId}/people/`, { people })).data,
    onSettled: () => refresh(queryClient, dealId),
  });
}

/**
 * POST deals/{id}/review/preview/ (L30) — {request_id, link_id?, ids?, off?, on?, blank?, message?} for an open link, or
 * {asks, blank?, message?} for a new one → {page (the portal payload, preview: true), why, new_refs}. Writes nothing.
 */
export function usePreviewForm(dealId, body, enabled = true) {
  const key = JSON.stringify(body || {});
  return useQuery({
    queryKey: reviewKey(dealId, 'preview', key),
    queryFn: async () => (await api.post(`deals/${dealId}/review/preview/`, JSON.parse(key))).data,
    staleTime: 0,
    enabled: Boolean(dealId) && enabled && Boolean(body),
    placeholderData: (previous) => previous,
  });
}

/** mutateAsync({answers: {ref: value}, origin: typed | relay}) — POST …/review/enter/ (L35) → {saved, activity_ids}. */
export function useEnter(dealId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body) => (await api.post(`deals/${dealId}/review/enter/`, body)).data,
    onSettled: () => invalidateDeal(queryClient, dealId),
  });
}

/**
 * GET …/review/census-blanks/?required= (L35) → {people: [{id, title, kind, cells: [{ref, column, label, type, choices,
 * required}]}], total, shown, truncated}.
 */
export function useCensusBlanks(dealId, required, enabled = true) {
  return useQuery({
    queryKey: reviewKey(dealId, 'blanks', required),
    queryFn: async () =>
      (await api.get(`deals/${dealId}/review/census-blanks/`, { params: required ? { required: 1 } : {} })).data,
    staleTime: 0,
    enabled: Boolean(dealId) && enabled,
  });
}

/**
 * GET …/review/section/?surface=intake|census (B37; C27, C30) → the Intake board {rows, documents, counts,
 * asks_closed} or the Census board {columns, people, employees, dependents, file_hint, asks_closed}.
 */
export function useSection(dealId, surface, enabled = true) {
  return useQuery({
    queryKey: reviewKey(dealId, 'section', surface),
    queryFn: async () => (await api.get(`deals/${dealId}/review/section/`, { params: { surface } })).data,
    staleTime: 0,
    enabled: Boolean(dealId && surface) && enabled,
  });
}

/** GET …/review/section/?surface=census&column= (C28) → {column, people: [{member_id, ref, title, value, …}]}. */
export function useColumnDrill(dealId, column) {
  return useQuery({
    queryKey: reviewKey(dealId, 'section', 'drill', column),
    queryFn: async () =>
      (await api.get(`deals/${dealId}/review/section/`, { params: { surface: 'census', column } })).data,
    staleTime: 0,
    enabled: Boolean(dealId && column),
  });
}

/**
 * mutateAsync({surface, rules}) — POST …/review/rules/ (B37, C27; OQ17): intake {key: {state, note?}}, census {column:
 * auto | required | waived} → {changed, activity_id, board}. A rule moves readiness, so every deal query reads again.
 */
export function useSetRules(dealId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body) => (await api.post(`deals/${dealId}/review/rules/`, body)).data,
    onSuccess: (answer, body) => queryClient.setQueryData(reviewKey(dealId, 'section', body.surface), answer.board),
    onSettled: () => invalidateDeal(queryClient, dealId),
  });
}
