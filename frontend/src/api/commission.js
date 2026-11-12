// Commission (plan.md §7.10; H3–H24, H95–H101, H106). Query keys: ['deal', id, 'commission'] (staleTime 0, a deal
// tab), ['client', id, 'commission'] for the client-scope split (slice 68 mounts it), ['commissions', area] for the
// /commissions page. Every write answers what the screen redraws, which the caller writes into the cache. The browser
// does no money math: the shares, dollars and house % all come from the server (rule 5).
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import api from './client';
import { dealKey } from './deals';

export const commissionKey = (dealId) => dealKey(dealId, 'commission');
export const clientSplitKey = (clientId) => ['client', Number(clientId), 'commission'];
export const PARTIES_KEY = ['commissions', 'parties'];
export const SETTINGS_KEY = ['commissions', 'settings'];

/**
 * GET deals/{id}/commission/ → {deal_id, client_id, client_name, rows: [{line, label, not_requested, in_force, rate,
 * effective, effective_label, source, source_label, basis: {key, label, plans, annual, employees, enrollment_source,
 * reason} | null, expected}], total, note, agency_default, year_number, split: {source, source_label, rows, scope,
 * can_save, needs_primary, parties}, basis: {revenue, employees, year}, preview, booking: {state none | unbooked |
 * booked, record_count, can_book, sees_ledger, and with a tier: records, totals, frozen, people, stale, disclosure}}.
 */
export function useDealCommission(dealId) {
  return useQuery({
    queryKey: commissionKey(dealId),
    queryFn: async () => (await api.get(`deals/${dealId}/commission/`)).data,
    staleTime: 0,
  });
}

/** PATCH deals/{id}/commission/ {rates: {line: Comp | ''}} → {changed, activity_id, …payload} (H5). */
export function useSetRate(dealId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (rates) => (await api.patch(`deals/${dealId}/commission/`, { rates })).data,
    // The RFP tab (which prints the rate, K29) refetches on mount: deal tabs use staleTime 0.
    onSuccess: (data) => queryClient.setQueryData(commissionKey(dealId), data),
  });
}

/**
 * The split editor's two calls for a deal (`scope: 'deal'`) or a client (H106): preview(rows, basis) → {preview};
 * save({scope, rows}) → {saved, activity_id, owner, …payload}. 400 {'rows.<i>.<field>' | 'rows.primary' |
 * 'rows.split_total': [sentence]}; 403 when the viewer may not save (OQ70).
 */
export function splitPaths({ dealId, clientId }) {
  const base = dealId ? `deals/${dealId}/commission/split/` : `clients/${clientId}/commission/split/`;
  return { save: base, preview: `${base}preview/` };
}

export async function previewSplit(target, rows, basis) {
  return (await api.post(splitPaths(target).preview, { rows, ...(basis || {}) })).data;
}

export function useSaveSplit(target) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body) => (await api.put(splitPaths(target).save, body)).data,
    onSuccess: (data) => {
      if (target.dealId) {
        queryClient.setQueryData(commissionKey(target.dealId), data);
        // The owner may have changed (H22), and the Activity drawer has a new row.
        queryClient.invalidateQueries({ queryKey: dealKey(target.dealId, 'header') });
        queryClient.invalidateQueries({ queryKey: dealKey(target.dealId, 'activity') });
      } else {
        queryClient.setQueryData(clientSplitKey(target.clientId), data);
      }
    },
  });
}

/** GET clients/{id}/commission/split/ → {client_id, client_name, split, basis, preview} (H106; the client page). */
export function useClientSplit(clientId) {
  return useQuery({
    queryKey: clientSplitKey(clientId),
    queryFn: async () => (await api.get(`clients/${clientId}/commission/split/`)).data,
    staleTime: 0,
  });
}

/** GET commissions/parties/?inactive=1 → {producers: [entry], partners: [entry], full} (H95–H98). */
export function useParties(inactive = false) {
  return useQuery({
    queryKey: [...PARTIES_KEY, inactive],
    queryFn: async () => (await api.get('commissions/parties/', { params: inactive ? { inactive: 1 } : {} })).data,
    staleTime: 0,
  });
}

/** mutate({id?, changes}): POST (no id: a new partner, or a login's Party with `user`) or PATCH (all tier). */
export function useSaveParty() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, changes }) =>
      (id ? await api.patch(`commissions/parties/${id}/`, changes) : await api.post('commissions/parties/', changes))
        .data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: PARTIES_KEY }),
  });
}

/** GET commissions/settings/ → {first_year_pct, renewal_pct, *_house_pct, confirmed, confirmed_by, confirmed_at,
 * default_commission, default_commission_label} (H100; all tier). */
export function useCommissionSettings() {
  return useQuery({
    queryKey: SETTINGS_KEY,
    queryFn: async () => (await api.get('commissions/settings/')).data,
    staleTime: 0,
  });
}

/** mutate({first_year_pct?, renewal_pct?, default_commission?, confirm?}) → the settings. */
export function useSaveSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body) => (await api.patch('commissions/settings/', body)).data,
    onSuccess: (data) => queryClient.setQueryData(SETTINGS_KEY, data),
  });
}

// ---- Booking, the Book and By person (slice 49; H25–H58, H68, H108, H120) ------------------------------------------
export const BOOK_KEY = ['commissions', 'book'];
export const PEOPLE_KEY = ['commissions', 'people'];
const recordKey = (id) => ['commissions', 'record', Number(id)];

/** After any booking or record write: the Book, By person, the record and the deal's tab read again. */
function refreshLedger(queryClient, dealId) {
  queryClient.invalidateQueries({ queryKey: ['commissions'] });
  if (dealId) {
    queryClient.invalidateQueries({ queryKey: commissionKey(dealId) });
    queryClient.invalidateQueries({ queryKey: dealKey(dealId, 'activity') });
  }
}

/** POST deals/{id}/commission/book/ → {booked, changed, activity_id, …payload}: Book now, Update, Rebook (all tier). */
export function useBookDeal(dealId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => (await api.post(`deals/${dealId}/commission/book/`)).data,
    onSuccess: (data) => {
      queryClient.setQueryData(commissionKey(dealId), data);
      refreshLedger(queryClient, dealId);
    },
  });
}

/** The CAA disclosure's path (H108; all tier); 409 {detail} when nothing is booked on medical, dental or vision. */
export const disclosurePath = (dealId) => `deals/${dealId}/commission/disclosure.pdf`;
export const BOOK_EXPORT_PATH = 'commissions/records/export/';
export const PEOPLE_EXPORT_PATH = 'commissions/people/export/';

/** Drops the blank filters, so the query key and the request carry only what is asked. */
export function cleanFilters(filters) {
  return Object.fromEntries(Object.entries(filters || {}).filter(([, value]) => value !== '' && value != null));
}

/**
 * GET commissions/records/ ?q, client, deal, party, record, status, year → {rows: [record], capped, cap, totals:
 * {records, live, expected, holes, house?, pool?, next_12}, years}. record = {id, client_id, client_name, deal_id,
 * line, line_label, carrier, plan_label, effective_date, term_end, year_number, year_label, status, status_label,
 * premium_annual, rate, rate_label, employees, sources, expected, house_share, shares: [{party, key, name, kind, role,
 * role_label, share, pct, pct_label, amount}], typed_shares, reason, holes, notes, booked_at, booked_by, updated_by}.
 */
export function useRecords(filters, { enabled = true } = {}) {
  const params = cleanFilters(filters);
  return useQuery({
    queryKey: [...BOOK_KEY, params],
    queryFn: async () => (await api.get('commissions/records/', { params })).data,
    staleTime: 0,
    enabled,
    placeholderData: (previous) => previous,
  });
}

/** GET commissions/records/{id}/ → {record, history: [activity row + changes]} (history: the all tier's, H57). */
export function useRecord(id) {
  return useQuery({
    queryKey: recordKey(id),
    queryFn: async () => (await api.get(`commissions/records/${id}/`)).data,
    staleTime: 0,
    enabled: Boolean(id),
  });
}

function useRecordWrite(request) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: request,
    onSuccess: (data) => refreshLedger(queryClient, data?.record?.deal_id),
  });
}

/** mutate({id, changes}) → PATCH: the facts and notes (H54, H56; all tier). */
export function useEditRecord() {
  return useRecordWrite(async ({ id, changes }) => (await api.patch(`commissions/records/${id}/`, changes)).data);
}

/** mutate({id, shares: [{party, role, pct}] | null, reason}) → PUT …/shares/ (H55; all tier). */
export function useSetShares() {
  return useRecordWrite(
    async ({ id, shares, reason }) => (await api.put(`commissions/records/${id}/shares/`, { shares, reason })).data,
  );
}

/** mutate(id) → POST …/rebook/ (H36; all tier). */
export function useRebookRecord() {
  return useRecordWrite(async (id) => (await api.post(`commissions/records/${id}/rebook/`)).data);
}

/** mutate({client | client_name + relationship, line, …facts}) → 201 {record, activity_id} (H58; all tier). */
export function useAddToBook() {
  return useRecordWrite(async (body) => (await api.post('commissions/records/', body)).data);
}

/** GET commissions/people/ ?year → {rows: [{key, party, name, kind, records, expected, share_of_book}], years}. */
export function usePeople(year) {
  const params = cleanFilters({ year });
  return useQuery({
    queryKey: [...PEOPLE_KEY, params],
    queryFn: async () => (await api.get('commissions/people/', { params })).data,
    staleTime: 0,
    placeholderData: (previous) => previous,
  });
}

/** GET commissions/people/{party id | 'house'}/ ?year → {rows: [record + mine]} (H68's drill-down). */
export function usePersonRecords(key, year) {
  const params = cleanFilters({ year });
  return useQuery({
    queryKey: [...PEOPLE_KEY, String(key), params],
    queryFn: async () => (await api.get(`commissions/people/${key}/`, { params })).data,
    staleTime: 0,
    enabled: key != null,
  });
}

/** GET commissions/clients/ ?q → [{id, name, relationship, archived}]: Add to book's client search (all tier). */
export function useClientPick(q) {
  return useQuery({
    queryKey: ['commissions', 'clients', q],
    queryFn: async () => (await api.get('commissions/clients/', { params: { q } })).data,
    enabled: q.trim().length > 1,
    staleTime: 30_000,
  });
}
