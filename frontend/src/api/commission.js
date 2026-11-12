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
 * can_save, needs_primary, parties}, basis: {revenue, employees, year}, preview}.
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
