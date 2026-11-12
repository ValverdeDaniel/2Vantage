// The RFP tab (plan.md §7.11; K.6). Query key ['deal', id, 'rfp'] (staleTime 0, a deal tab). Its writes answer the
// blocks they redraw, which the tab writes into the cache (deal/rfp/useRfpWrites.js); intake's doors refetch it with
// the rest of the deal (invalidateDeal).
import { useQuery } from '@tanstack/react-query';
import { downloadFile } from '../lib/download';
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
 * breakdown, source}, census: {has_roster, employees, dependents, readiness_pct, errors}, packet: {count, members,
 * sections: [{key, title}], notices: [{kind, title, text}], rows: [{key, section, title, label, sub, file_format,
 * include, default_include, deliberate, packet_eligible, available, reason, hint, required_by, for_fallback, rows,
 * max_rows, capped, lens, phi, …}]}, drafts: {route, rows: [{key, label, name, to, cc, subject, body,
 * attachment_keys, attachments, size, sent: {on, shown, by} | null, changed: [sentence]}], sent_count, total,
 * sent_earlier: [{key, label, on, shown, by}], any_sent}, checks_stamp}. A GET makes no row.
 */
export function useRfp(dealId) {
  return useQuery({ queryKey: rfpKey(dealId), queryFn: () => getRfp(dealId), staleTime: 0 });
}

/** The deal workspace's warm-up (K3): fetched once the browser is idle, so the tab's first click is instant. */
export function prefetchRfp(queryClient, dealId) {
  return queryClient.prefetchQuery({ queryKey: rfpKey(dealId), queryFn: () => getRfp(dealId), staleTime: 0 });
}

/**
 * PATCH deals/{id}/rfp/ — the request's settings (K20–K27) and the packet's ticks (K35). body: {route?: warner |
 * direct | null, carriers?: {add, remove}, funding?: {add, remove} | null, other_carriers?, due_date? (YYYY-MM-DD |
 * ''), notes?, include?: {file key: true | false | null} | 'reset'} → {changed, cleared: [card], activity_id, request,
 * carriers, packet, done}. 400 {field: [sentence]}.
 */
export async function patchRfp(dealId, body) {
  return (await api.patch(`deals/${dealId}/rfp/`, body)).data;
}

/** POST deals/{id}/rfp/done/ {card, done} → {done: {card: {by, by_id, at}}, activity_id} (K9). */
export async function markRfpCard(dealId, body) {
  return (await api.post(`deals/${dealId}/rfp/done/`, body)).data;
}

// ---- the check, the files and the sends (slice 46) ----------------------------------------------------------------

/** GET deals/{id}/rfp/check/?file=<key> → {key, label, ok, problems: [{code, text, count, fix, where?, people?}], ack}
 * for a row of the one key space, 'packet' or 'draft-<key>' (K69). */
export async function fetchRfpCheck(dealId, key) {
  return (await api.get(`deals/${dealId}/rfp/check/`, { params: { file: key } })).data;
}

/** GET deals/{id}/rfp/checks/ → {checks_stamp, cards: {key: {status ready|problems|unsigned, count}}, deal}: the
 * packet grid's pills (K52), asked again only when the page's `checks_stamp` moves (staleTime Infinity). */
export function useRfpChecks(dealId, stamp) {
  return useQuery({
    queryKey: dealKey(dealId, 'rfp', 'checks', stamp),
    queryFn: async () => (await api.get(`deals/${dealId}/rfp/checks/`)).data,
    staleTime: Infinity,
    enabled: Boolean(stamp),
  });
}

/** Any RFP file under the server's name; with `ack`, a check that changed since answers 409 {detail, report} (K70). */
export function downloadRfpFile(dealId, key, ack) {
  return downloadFile(`deals/${dealId}/rfp/files/${key}/`, { params: ack ? { ack } : undefined });
}

/** POST deals/{id}/rfp/drafts/{key}/sent/ {sent} → {drafts, done, stage, activity_id} (K64–K68, K120). */
export async function markDraftSent(dealId, key, sent) {
  return (await api.post(`deals/${dealId}/rfp/drafts/${key}/sent/`, { sent })).data;
}

// ---- the carrier census files and the lens (slice 45) ------------------------------------------------------------

/** GET deals/{id}/rfp/files/{key}/: a census file of the one key space (census-warner … census-angle-csv). */
export const rfpFilePath = (dealId, key) => `deals/${dealId}/rfp/files/${key}/`;

/**
 * GET deals/{id}/rfp/files/{key}/look/?sheet=&start= → the built file as sheet windows (the document viewer's shape:
 * {sheets, sheet, start, window, total_rows, cols, col_letters, rows, format}) with {file, warnings}; logged (K82).
 */
export async function fetchRfpLook(dealId, key, params = {}) {
  return (await api.get(`deals/${dealId}/rfp/files/${key}/look/`, { params })).data;
}

export const rfpFormatsKey = (dealId) => dealKey(dealId, 'rfp', 'formats');

/**
 * GET deals/{id}/rfp/formats/ → {formats: [{key, kind, label, carrier, file_formats, rows, columns, gaps, max_rows,
 * capped, in_packet, required_by, to_fix}], default_key}: the Export readiness cards and lens chips (K79, K80).
 */
export function useRfpFormats(dealId, enabled = true) {
  return useQuery({
    queryKey: rfpFormatsKey(dealId),
    queryFn: async () => (await api.get(`deals/${dealId}/rfp/formats/`)).data,
    staleTime: 0,
    enabled,
  });
}

/**
 * GET deals/{id}/rfp/formats/{key}/?rows= → one format: {key, label, carrier, version, file_formats, sheet, geometry,
 * columns: [{letter, header, fills: {kind, text, field}, carrier_required, filled, total, expected, blank,
 * required_blanks, translation, rules}], gaps, gap_notes, not_sent, warnings, max_rows, capped, in_packet, required_by,
 * preview: {headers, letters, rows, total_rows, missing_cells}, filled_pct, needs, gap_items, gap_total, notes}.
 */
export function useRfpFormat(dealId, key, rows = 50) {
  return useQuery({
    queryKey: [...rfpFormatsKey(dealId), key, rows],
    queryFn: async () => (await api.get(`deals/${dealId}/rfp/formats/${key}/`, { params: { rows } })).data,
    staleTime: 0,
    enabled: Boolean(key),
  });
}
