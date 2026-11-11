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
