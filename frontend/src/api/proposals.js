// The proposal builder and its pages (plan.md §7.12). Query keys: ['deal', id, 'proposal'] (the builder) and
// ['deal', id, 'proposal', 'pages', line, preset]; the Export viewer's previews ['proposal-preview', id, file, tab,
// files stamp, firm stamp] (slice 28), outside ['deal', id] so a deal write does not rebuild them: their stamps do.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import api from './client';
import { dealKey, invalidateDeal } from './deals';

export const proposalKey = (dealId) => dealKey(dealId, 'proposal');

/**
 * The builder (J.6.5): {config, marks: {done, total, stored}, lines: [{line, label, state, chip, off, done, rate_basis,
 * currents, incumbent, quotes, starred, presented_ids, pages, room, recommendation: {covered, missing, needs_pick,
 * plans, groups, sold, renewals, keepable}, reasons, enrollment, spec, rows, card_stats, card_stats_standard,
 * preset}], ready: {ok, missing, sentence, draft}, checks: [{code, level, line, line_label, text, fix}], issues}.
 * Every deal write refetches it (invalidateDeal), so a star or a pick shows here at once.
 */
export function useProposal(dealId) {
  return useQuery({
    queryKey: proposalKey(dealId),
    queryFn: async () => (await api.get(`deals/${dealId}/proposal/`)).data,
    staleTime: 0,
  });
}

/**
 * ({path: value}) → {changed, cleared, activity_id}: merged by path on the server (J20), which also takes the mark off
 * the card that owns each changed path (J19). One path at a time from the builder; refetches the deal.
 */
export function useSetConfig(dealId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (changes) => (await api.patch(`deals/${dealId}/proposal/`, changes)).data,
    onSuccess: () => invalidateDeal(queryClient, dealId),
  });
}

/** ({card, line?, done}) → {card, line, stamp, activity_id}: a card marked completed, or its mark taken off (J18). */
export function useSetMark(dealId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body) => (await api.post(`deals/${dealId}/proposal/marks/`, body)).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: proposalKey(dealId), exact: true }),
  });
}

/**
 * "What the client will see" (slice 14; F37–F39, J49): one line's proposal page by page as the PowerPoint prints it.
 * `preset` is the Advisor's Columns tab, which picks the rows, or the builder's
 * Key rows (`key`). → {line, label, per_page, cap, room, nothing_starred,
 * several, off, quotes, currents, presented_ids, pages, plans (each column's facts and words), rows (formatted cells
 * by plan id), others (the plans off the proposal, for the picker), landing, full_words}. Every quotes write
 * refetches it (invalidateDeal); the previous line's pages stay on screen while the same line refetches.
 */
export function usePages(dealId, line, preset) {
  return useQuery({
    queryKey: dealKey(dealId, 'proposal', 'pages', line, preset),
    queryFn: async () => (await api.get(`deals/${dealId}/proposal/pages/`, { params: { line, preset } })).data,
    enabled: Boolean(line),
    staleTime: 0,
    placeholderData: (previous) => (previous?.line === line ? previous : undefined),
  });
}

export const previewKey = (dealId, file, tab, stamps) => [
  'proposal-preview',
  Number(dealId),
  file,
  tab || '',
  stamps?.files ?? '',
  stamps?.firm ?? '',
];

/**
 * The Export viewer's copy of one file (plan.md §7.12; J107, F3): `GET deals/{id}/proposal/preview/?file=&tab=`,
 * built by the server from the downloads' own builders and never stored. Keyed on the file, the tab and the builder's
 * `stamps` (the caller settles them first), so it builds only when something a client file prints may have changed:
 * staleTime Infinity, no retry, no refetch on focus or mount; a superseded build is aborted (the signal). Enabled only
 * while its file is on screen and nothing is saving (the caller's `enabled`). Until a copy for this key arrives, the
 * last copy of the same file stays on screen (`isPlaceholderData`), from this view or an earlier visit.
 * → workbook: {file, built_at, draft, opens_on, tabs: [{title, counts, capped}], tab: {…}} · deck (slice 30; one copy
 * behind the PowerPoint, PDF and Paper views): {file, built_at, style, draft, slides: [{n, title, kind, line, continued,
 * notes, chart, fit}], paper: {scale, sheet, as_is, inner}, pdf (base64)} · 409 {detail}.
 */
export function usePreview(dealId, { file, tab, stamps, enabled }) {
  const queryClient = useQueryClient();
  return useQuery({
    queryKey: previewKey(dealId, file, tab, stamps),
    queryFn: async ({ signal }) =>
      (await api.get(`deals/${dealId}/proposal/preview/`, { params: { file, tab: tab || undefined }, signal })).data,
    enabled: Boolean(enabled && stamps),
    staleTime: Infinity,
    gcTime: 5 * 60 * 1000,
    retry: false,
    refetchOnWindowFocus: false,
    refetchOnMount: false,
    refetchOnReconnect: false,
    placeholderData: (previous) => previous ?? lastPreview(queryClient, dealId, file),
  });
}

/** The newest copy of `file` built for this deal under any key, or undefined (a failed build keeps it on screen). */
export function lastPreview(queryClient, dealId, file) {
  const found = queryClient
    .getQueryCache()
    .findAll({ queryKey: ['proposal-preview', Number(dealId), file] })
    .filter((query) => query.state.data)
    .sort((a, b) => b.state.dataUpdatedAt - a.state.dataUpdatedAt);
  return found[0]?.state.data;
}
