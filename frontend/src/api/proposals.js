// The Proposal tab (plan.md §7.9). Query key: ['deal', id, 'proposal'].
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import api from './client';
import { dealKey, invalidateDeal } from './deals';

export const proposalKey = (dealId) => dealKey(dealId, 'proposal');

export function useProposal(dealId) {
  return useQuery({
    queryKey: proposalKey(dealId),
    queryFn: async () => (await api.get(`deals/${dealId}/proposal/`)).data,
    staleTime: 0,
  });
}

/** ({title?, notes?, lines?: {line: [ids]}, reasons?: {line: text}}) → the whole proposal payload */
export function useSaveProposal(dealId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (changes) => (await api.put(`deals/${dealId}/proposal/`, changes)).data,
    onSuccess: (data) => {
      queryClient.setQueryData(proposalKey(dealId), data);
      invalidateDeal(queryClient, dealId);
    },
  });
}

/**
 * "What the client will see" (slice 14; F37–F39, J49): one line's proposal page by page as the PowerPoint prints it.
 * `preset` is the Advisor's Columns tab, which picks the rows. → {line, label, per_page, cap, room, nothing_starred,
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
