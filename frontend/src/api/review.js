// Review & requests (plan.md §7.13; Part L). Query keys ['deal', id, 'review', area] (staleTime 0, a deal tab). Every
// write answers the request row it changed; the hooks put it into the Board's cache and refetch the Board, since a
// write can move a request in or out of the Waiting lane and change the pills' counts.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import api from './client';
import { dealKey } from './deals';

export const reviewKey = (dealId, ...rest) => dealKey(dealId, 'review', ...rest);

/**
 * GET deals/{id}/review/board/ → {deal_id, asks_closed: sentence | null, counts: {to_send, to_review, waiting,
 * questions}, readiness: {pct, state}, lanes: {waiting: [request]}, in_progress: [{link_id, request_id, name,
 * last_saved_at}]}. request = {id, created_at, created_by, message, asks: [words], sections, state, first_sent_at,
 * answered_at, answered_by, closed_at, closed_by, close_reason, close_reason_label, expiring, soonest_days,
 * recipients: [person]}; person = {link_id, contact_id, name, email, role, security, blank, path (/portal/<token>,
 * or null once it can never open again), sent, sent_at, opened, opened_at, last_opened_at, opens, submitted_at,
 * last_saved_at, expires_at, ceiling_at, days_left, expired, revoked, revoked_at, revoked_by, covered, state,
 * in_progress, can_extend, can_restore}. Writes nothing.
 */
export function useReviewBoard(dealId) {
  return useQuery({
    queryKey: reviewKey(dealId, 'board'),
    queryFn: async () => (await api.get(`deals/${dealId}/review/board/`)).data,
    staleTime: 0,
  });
}

/** The client's contacts, for "Who gets it" (deals' door, §7.3): {contacts: [contact], primary_id}. */
export function useClientContacts(dealId, clientId) {
  return useQuery({
    queryKey: reviewKey(dealId, 'contacts'),
    queryFn: async () => (await api.get(`clients/${clientId}/contacts/`)).data,
    staleTime: 0,
    enabled: Boolean(clientId),
  });
}

/**
 * POST deals/{id}/review/requests/?dry_run=1 — the builder's live floor (L40); writes nothing. body as createRequest
 * → {floor: {level, because: [words]}, security, people, asks: [words]}. 400 {field: [sentence]}; 409 {detail}.
 */
export async function planRequest(dealId, body) {
  return (await api.post(`deals/${dealId}/review/requests/`, body, { params: { dry_run: 1 } })).data;
}

/**
 * mutate(body) — POST deals/{id}/review/requests/ (L40, L55): body {people: [{contact_id} | {name, email?}], asks:
 * {intake?, census?, questionnaires?, documents?}, message?, security?: link | pin, expires_on?: YYYY-MM-DD, blank?}
 * → 201 {request, links: [{link_id, name, email, path, pin (shown this once), security, expires_at}], activity_id}.
 */
export function useCreateRequest(dealId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body) => (await api.post(`deals/${dealId}/review/requests/`, body)).data,
    onSettled: () => queryClient.invalidateQueries({ queryKey: reviewKey(dealId, 'board') }),
  });
}

function withRequest(queryClient, dealId, request) {
  queryClient.setQueryData(reviewKey(dealId, 'board'), (board) => {
    if (!board) return board;
    const waiting = board.lanes.waiting.map((row) => (row.id === request.id ? request : row));
    return { ...board, lanes: { ...board.lanes, waiting } };
  });
}

/**
 * mutate({linkId, action, copied?}) — PATCH links/{id}/ (L8, L60, L64, L71): action mark_sent | unsend | extend |
 * revoke | restore | new_pin → {link: person, request, changed, activity_id, pin? (new_pin, this once)}. 409 {detail}.
 */
export function useLinkAction(dealId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ linkId, ...body }) => (await api.patch(`links/${linkId}/`, body)).data,
    onSuccess: (answer) => withRequest(queryClient, dealId, answer.request),
    onSettled: () => queryClient.invalidateQueries({ queryKey: reviewKey(dealId, 'board') }),
  });
}

/** mutate({requestId, reason}) — POST deals/{id}/review/requests/{rid}/close/ (L70) → {request, changed, activity_id}. */
export function useCloseRequest(dealId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ requestId, reason }) =>
      (await api.post(`deals/${dealId}/review/requests/${requestId}/close/`, { reason })).data,
    onSettled: () => queryClient.invalidateQueries({ queryKey: reviewKey(dealId, 'board') }),
  });
}
