// Client archive and the Archived page (plan.md §7.3; A13, A18, M6–M9, M103–M105). Query key: ['archived'].
// Clients and deals themselves are in api/deals.js.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import api from './client';
import { CLIENTS_KEY, dealKey } from './deals';

export const ARCHIVED_KEY = ['archived'];

/** {archived: true | false} → {client_id, archived: {at, by} | null}. Archive hides the client and its deal from
 *  every list; Restore brings them back. Nothing is deleted. */
export async function archiveClient(clientId, archived) {
  const { data } = await api.post(`clients/${clientId}/archive/`, { archived });
  return data;
}

/** [{id, name, relationship, client_since, archived: {at, by}, deal: {id, stage, effective_date} | null, deal_count}] */
export async function listArchived() {
  const { data } = await api.get('archived/');
  return data;
}

/** The Archived page's rows, latest archived first. */
export function useArchived() {
  return useQuery({ queryKey: ARCHIVED_KEY, queryFn: listArchived, staleTime: 0 });
}

/**
 * mutate({clientId, archived, dealId?}) — Archive or Restore from any screen. Afterwards the home lists and the
 * Archived page refetch, and the open deal's header (when `dealId` is given) shows or drops its banner at once.
 */
export function useArchiveClient() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ clientId, archived }) => archiveClient(clientId, archived),
    onSuccess: (block, { dealId }) => {
      if (dealId == null) return;
      queryClient.setQueryData(dealKey(dealId, 'header'), (header) =>
        header ? { ...header, archived: block.archived } : header,
      );
      queryClient.invalidateQueries({ queryKey: dealKey(dealId, 'activity') });
      queryClient.invalidateQueries({ queryKey: dealKey(dealId, 'client') });
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: CLIENTS_KEY });
      queryClient.invalidateQueries({ queryKey: ARCHIVED_KEY });
      queryClient.invalidateQueries({ queryKey: ['work-queue'] }); // the home feed (slice 61); its row leaves
    },
  });
}
