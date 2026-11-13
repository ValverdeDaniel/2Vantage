// The client page (plan.md §7.3, §7.15, §7.16, §8.5; slices 67–68). Query keys ['client', id] (deals' client detail),
// ['client', id, 'overview'], ['client', id, 'activity'] (the Timeline's feed) and ['client', id, 'agenda'] (slice 68;
// its writes are the deals' own doors, `useAgendaWrites(dealId, {clientId})`), each staleTime 0 like a deal tab.
// The page writes nothing of its own: the client's name and brief go through deals' PATCH, the status through the
// status door, the main contact through the contact's PATCH and archive through deals' archive door (rule 6). After
// a write every client query refetches, and the deal the page works in, whose header shows the client too.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import api from './client';
import { ARCHIVED_KEY, archiveClient } from './clients';
import { CLIENTS_KEY, getClient, invalidateDeal, setClientStatus, updateClient } from './deals';

/** ['client', 12, ...rest]: client ids in keys are numbers (route params arrive as strings). */
export function clientKey(clientId, ...rest) {
  return ['client', Number(clientId), ...rest];
}

/** The Timeline's key over `clients/{id}/activity/` (`Timeline {path, queryKey}`, slice 63). */
export const clientFeedKey = (clientId) => clientKey(clientId, 'activity');

/** GET clients/{id}/ → {id, name, relationship, client_since, owner, notes, archived, deals, contacts, primary_id,
 *  moves: [{to, label, allowed, sentence}]}. */
export function useClient(clientId) {
  return useQuery({
    queryKey: clientKey(clientId),
    queryFn: () => getClient(clientId),
    staleTime: 0,
    enabled: Boolean(clientId),
  });
}

/**
 * GET clients/{id}/overview/ → {client_id, deal_id (the deal the page works in), current: {deal_id, year, stage,
 * effective_date, type, type_label, plans_quoted} | null, last_sold: {deal_id, year, carriers, at} | null, convert:
 * {allowed, sentence} | null, facts: {deal_id, legal_name, fein, sic_code, situs_state, employees: {value, from,
 * from_label, estimate}, funding: {value, from}} | null, tiles: {effective: {date, days} | null, agenda: {overdue,
 * soon, total}, expected_revenue}, in_force: {kind, rows}, commission (the deal's commission card) | null, history:
 * [{deal_id, year, stage, current, effective_date, sold, expected, chips: {intake, census, forms, documents}}]}.
 */
export function useClientOverview(clientId) {
  return useQuery({
    queryKey: clientKey(clientId, 'overview'),
    queryFn: async () => (await api.get(`clients/${clientId}/overview/`)).data,
    staleTime: 0,
    enabled: Boolean(clientId),
  });
}

/**
 * GET clients/{id}/agenda/ → {today, counts: {overdue, soon, total}, deals: [{deal: {id, stage, effective_date, link},
 * next_step, waiting, rows}]}: one panel per deal still being worked, each with the rows its own Agenda shows (CL24).
 */
export function useClientAgenda(clientId) {
  return useQuery({
    queryKey: clientKey(clientId, 'agenda'),
    queryFn: async () => (await api.get(`clients/${clientId}/agenda/`)).data,
    staleTime: 0,
    enabled: Boolean(clientId),
  });
}

function settle(queryClient, clientId, dealId) {
  queryClient.invalidateQueries({ queryKey: clientKey(clientId) });
  queryClient.invalidateQueries({ queryKey: CLIENTS_KEY });
  queryClient.invalidateQueries({ queryKey: ['work-queue'] });
  if (dealId) invalidateDeal(queryClient, dealId, { header: true });
}

/**
 * The page's writes, each through its owner's door: {update ({name} | {notes}: PATCH clients/{id}/), setStatus (to:
 * POST clients/{id}/status/, a 409 carries the refusal's sentence), setPrimary (contactId: PATCH contacts/{id}/
 * {is_primary: true}), archive (archived: POST clients/{id}/archive/)}. `dealId` is the deal the page works in.
 */
export function useClientWrites(clientId, dealId) {
  const queryClient = useQueryClient();
  const write = (mutationFn, after) => ({
    mutationFn,
    onSettled: () => {
      settle(queryClient, clientId, dealId);
      after?.();
    },
  });
  const update = useMutation(write((changes) => updateClient(clientId, changes)));
  const setStatus = useMutation(write((to) => setClientStatus(clientId, to)));
  const setPrimary = useMutation(
    write(async (contactId) => (await api.patch(`contacts/${contactId}/`, { is_primary: true })).data),
  );
  const archive = useMutation(
    write(
      (archived) => archiveClient(clientId, archived),
      () => queryClient.invalidateQueries({ queryKey: ARCHIVED_KEY }),
    ),
  );
  return { update, setStatus, setPrimary, archive };
}
