// The proposal builder and its pages (plan.md §7.12). Query keys: ['deal', id, 'proposal'] (the builder) and
// ['deal', id, 'proposal', 'pages', line, preset].
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
