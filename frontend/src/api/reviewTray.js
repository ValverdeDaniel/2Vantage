// The request tray, notes and the request page (plan.md §7.13; L22, L29, L33, L49–L54; B12; slice 56). Query keys
// ['deal', id, 'review', area] (staleTime 0, a deal tab). The tray is one read the whole deal page shares — the bar,
// its snippet, the request page's cart and every "＋ Ask" button (L54) — so asking on one tab shows on the next. A
// write answers the tray it left; the hooks put that in the cache and read the Board, the request page and the queues
// again, since an ask moves their counts.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import api from './client';
import { reviewKey } from './review';

export const trayKey = (dealId) => reviewKey(dealId, 'tray');

function refreshReview(queryClient, dealId, tray) {
  if (tray) queryClient.setQueryData(trayKey(dealId), tray);
  ['board', 'request', 'queue'].forEach((area) => queryClient.invalidateQueries({ queryKey: reviewKey(dealId, area) }));
}

/**
 * GET deals/{id}/review/tray/ → {count, asks_closed, items: [{id, ref, surface, kind, title, text, at, by, target:
 * {key, request_id, names, expires_at, days_left} | null, why, gone, named}], links: [{key, request_id, created_at,
 * names, people: [{link_id, name, security, sent_at, opened, last_opened_at, submitted_at, expires_at, days_left,
 * expires_if_sent}]}], needs_new: [id], out: {ref: first asked}}. Writes nothing.
 */
export function useTray(dealId, enabled = true) {
  return useQuery({
    queryKey: trayKey(dealId),
    queryFn: async () => (await api.get(`deals/${dealId}/review/tray/`)).data,
    staleTime: 0,
    enabled: Boolean(dealId) && enabled,
  });
}

/**
 * mutateAsync({refs, kind?: ask | sendback, text?, request_id?, skip_out?} | {census: {columns, scope}}) — POST
 * deals/{id}/review/tray/ (L51, L54; B12) → {tray, added, activity_id}. 400 {refs | columns: [sentence]}; 409 {detail}.
 */
export function useTrayAsk(dealId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body) => (await api.post(`deals/${dealId}/review/tray/`, body)).data,
    onSuccess: (answer) => refreshReview(queryClient, dealId, answer.tray),
  });
}

/** mutateAsync(ids) — POST deals/{id}/review/tray/remove/ {ids} → {removed, tray} (L50, L51). */
export function useTrayRemove(dealId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (ids) => (await api.post(`deals/${dealId}/review/tray/remove/`, { ids })).data,
    onSuccess: (answer) => refreshReview(queryClient, dealId, answer.tray),
  });
}

/**
 * mutateAsync({ids?, request_id?, new?: {people, security?, expires_on?, message?, blank?}}) — POST
 * deals/{id}/review/tray/send/ (L53) → {sent, targets: [{key, request_id, names, items, links}], waiting: [id], whys:
 * {id: sentence}, dropped, tray, request?, links? (a new link's, with its PIN this once)}. 409 {detail}.
 */
export function useTraySend(dealId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body) => (await api.post(`deals/${dealId}/review/tray/send/`, body || {})).data,
    onSuccess: (answer) => refreshReview(queryClient, dealId, answer.tray),
  });
}

/**
 * mutateAsync(body) — POST deals/{id}/review/notes/ (L22): {kind: note, ref, text, audience: team | client} or
 * {kind: reply, question_id, text} → {note, activity_id}; {kind: ask | sendback, ref, text?} → {tray, activity_id}.
 * note = {id, ref, kind, audience, text, by, who, at, sent_at, resolved_at, from_client, link_id, request_id}.
 */
export function useNote(dealId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body) => (await api.post(`deals/${dealId}/review/notes/`, body)).data,
    onSuccess: (answer) => refreshReview(queryClient, dealId, answer.tray),
  });
}

/** mutateAsync(noteId) — PATCH deals/{id}/review/notes/{nid}/ {action: resolve} → {note, activity_id}. */
export function useResolveNote(dealId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (noteId) => (await api.patch(`deals/${dealId}/review/notes/${noteId}/`, { action: 'resolve' })).data,
    onSuccess: () => refreshReview(queryClient, dealId, null),
  });
}

/**
 * GET deals/{id}/review/request/?pane=intake|census|documents (L24–L29, L33) → {pane, asks_closed, panes: [{key, label,
 * waiting, in_cart}], people: [{link_id, request_id, name, security, sent, opens, days_left, expired, revoked,
 * submitted_at, path}], counts: {all, question, in_cart, answered, asked, on_file, missing}, items: [{ref, label,
 * section, needed, value, status, asked_at, draft_id, notes}], columns? (census: [{key, label, group, required, blank,
 * required_blank, in_cart, asked, on_link, answered, questions}]), census_file?, threads: {ref: [note]}, seen_at, new,
 * target (with `requestId`, the Ask card's request, slice 57: {request_id, names, link_ids, asks, security, message,
 * parts, on_link: [ref], drafted: {ref: draft id}})}.
 */
export function useRequestPage(dealId, pane, requestId = null) {
  return useQuery({
    queryKey: reviewKey(dealId, 'request', pane, requestId || ''),
    queryFn: async () =>
      (await api.get(`deals/${dealId}/review/request/`, { params: { pane, ...(requestId ? { request: requestId } : {}) } }))
        .data,
    staleTime: 0,
    placeholderData: (previous) => previous,
  });
}

/** POST deals/{id}/review/seen/ — this person's last look at the deal's threads (L33); fire and forget. */
export async function markSeen(dealId, at) {
  return (await api.post(`deals/${dealId}/review/seen/`, at ? { at } : {})).data;
}
