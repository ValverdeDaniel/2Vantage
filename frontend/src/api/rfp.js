// The RFP tab (plan.md §7.11; K.6). Query key ['deal', id, 'rfp'] (staleTime 0, a deal tab). Its writes answer the
// blocks they redraw, which the tab writes into the cache (deal/rfp/useRfpWrites.js); intake's doors refetch it with
// the rest of the deal (invalidateDeal).
import { useQuery } from '@tanstack/react-query';
import api from './client';
import { dealKey } from './deals';

export const rfpKey = (dealId) => dealKey(dealId, 'rfp');

async function getRfp(dealId) {
  return (await api.get(`deals/${dealId}/rfp/`)).data;
}

/**
 * GET deals/{id}/rfp/ → {deal_id, client_name, request: {route, route_default, route_stored, carriers, other_carriers,
 * funding, funding_default, due_date, notes}, carriers: [{key, name, group, selected, eligible, reason, lines,
 * line_labels, census_format, on_form, note}], done: {card: {by, by_id, at}}, band: {key, label, count, source,
 * estimate, from}, enrollment: {intake, census, advisor, differ, warning}, lines: [{key, label}], commission: {text,
 * breakdown, source}, census: {has_roster, employees, dependents, readiness_pct, errors}}. A GET makes no row.
 */
export function useRfp(dealId) {
  return useQuery({ queryKey: rfpKey(dealId), queryFn: () => getRfp(dealId), staleTime: 0 });
}

/** The deal workspace's warm-up (K3): fetched once the browser is idle, so the tab's first click is instant. */
export function prefetchRfp(queryClient, dealId) {
  return queryClient.prefetchQuery({ queryKey: rfpKey(dealId), queryFn: () => getRfp(dealId), staleTime: 0 });
}

/**
 * PATCH deals/{id}/rfp/ — the request's settings (K20–K27). body: {route?: warner | direct | null, carriers?: {add,
 * remove}, funding?: {add, remove} | null, other_carriers?, due_date? (YYYY-MM-DD | ''), notes?} → {changed, cleared:
 * [card], activity_id, request, carriers, done}. 400 {field: [sentence]}.
 */
export async function patchRfp(dealId, body) {
  return (await api.patch(`deals/${dealId}/rfp/`, body)).data;
}

/** POST deals/{id}/rfp/done/ {card, done} → {done: {card: {by, by_id, at}}, activity_id} (K9). */
export async function markRfpCard(dealId, body) {
  return (await api.post(`deals/${dealId}/rfp/done/`, body)).data;
}
