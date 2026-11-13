// Clients and deals (plan.md §7.3). Query keys: ['clients', params] · ['deal', dealId, '<area>', …] · ['users'].
import { keepPreviousData, useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import api from './client';

// ---- keys ------------------------------------------------------------------------------------------------------

/** ['deal', 31, area, ...rest]. Deal ids in keys are always numbers (route params arrive as strings). */
export function dealKey(dealId, ...rest) {
  return ['deal', Number(dealId), ...rest];
}

export const CLIENTS_KEY = ['clients'];
export const USERS_KEY = ['users'];
const HEADER = 'header';

/**
 * After anything that changes a deal: refetch every ['deal', id, …] query except the header (which the caller has
 * just written), and the dashboard rows. Tabs call this after their own writes when the header may change
 * (e.g. marking a plan sold moves the stage): pass {header: true}.
 */
export function invalidateDeal(queryClient, dealId, { header = false } = {}) {
  const id = Number(dealId);
  queryClient.invalidateQueries({
    queryKey: ['deal', id],
    predicate: (query) => header || query.queryKey[2] !== HEADER,
  });
  queryClient.invalidateQueries({ queryKey: CLIENTS_KEY });
}

/** `const invalidate = useInvalidateDeal(); invalidate(deal.id, {header: true})` */
export function useInvalidateDeal() {
  const queryClient = useQueryClient();
  return (dealId, options) => invalidateDeal(queryClient, dealId, options);
}

// ---- plain calls -----------------------------------------------------------------------------------------------

function clean(params) {
  return Object.fromEntries(Object.entries(params || {}).filter(([, value]) => value !== '' && value != null));
}

export async function listClients(params) {
  const { data } = await api.get('clients/', { params: clean(params) });
  return data;
}

/** {name, relationship? (prospect, the default, or existing_client), effective_date?, owner_id?} → {client, deal} */
export async function createClient(body) {
  const { data } = await api.post('clients/', body);
  return data;
}

/** A new deal's lines to quote, through intake's intent door, their one writer (B17; slice 11) → requested_lines. */
async function shopLines(dealId, lines) {
  const { data } = await api.post(`deals/${dealId}/intake/intent/`, { lines, shop: true });
  return data.requested_lines;
}

export async function getClient(clientId) {
  const { data } = await api.get(`clients/${clientId}/`);
  return data;
}

/** {name, owner_id, notes} (any subset) → client. The status has its own door: setClientStatus. */
export async function updateClient(clientId, changes) {
  const { data } = await api.patch(`clients/${clientId}/`, changes);
  return data;
}

/** {to: 'new_client' | 'prospect' | 'existing_client'} → client detail. A refused move is a 409 whose `detail` is
 *  its sentence ("A plan is marked sold — un-sell it first."). */
export async function setClientStatus(clientId, to) {
  const { data } = await api.post(`clients/${clientId}/status/`, { to });
  return data;
}

export async function getDeal(dealId) {
  const { data } = await api.get(`deals/${dealId}/`);
  return data;
}

/** {effective_date, stage (intake|quoting|proposal), owner_id} (any subset) → deal header. The lines to quote have
 *  their own door: api/intake.js useSetIntent. */
export async function updateDeal(dealId, changes) {
  const { data } = await api.patch(`deals/${dealId}/`, changes);
  return data;
}

export async function markLost(dealId, reason) {
  const { data } = await api.post(`deals/${dealId}/lost/`, { reason });
  return data;
}

export async function reopenDeal(dealId) {
  const { data } = await api.post(`deals/${dealId}/reopen/`);
  return data;
}

export async function listActivity(dealId, page = 1) {
  const { data } = await api.get(`deals/${dealId}/activity/`, { params: { page } });
  return data;
}

/** Puts back the earlier values of one Activity row → {activity_id, reverted_id, deal_id, summary, changes}.
 *  A refusal is a 409 whose `detail` is the sentence to show (already undone, a later write, a sold plan…). */
export async function revertActivity(activityId) {
  const { data } = await api.post(`activity/${activityId}/revert/`);
  return data;
}

export async function listUsers() {
  const { data } = await api.get('users/');
  return data;
}

export async function getAgency() {
  const { data } = await api.get('agency/');
  return data;
}

// ---- queries ---------------------------------------------------------------------------------------------------

/** Dashboard rows. params: {q, relationship, stage, owner, ordering, page}. Keeps the previous page on screen. */
export function useClients(params, options = {}) {
  const cleaned = clean(params);
  return useQuery({
    queryKey: [...CLIENTS_KEY, cleaned],
    queryFn: () => listClients(cleaned),
    placeholderData: keepPreviousData,
    ...options,
  });
}

/** The deal header, key ['deal', id, 'header']. Shared by the deal page and every tab (tabs get it as a prop). */
export function useDeal(dealId) {
  return useQuery({ queryKey: dealKey(dealId, HEADER), queryFn: () => getDeal(dealId), enabled: Boolean(dealId) });
}

/** Paged activity, newest first: data.pages[n].results; fetchNextPage() for "Show more". */
export function useDealActivity(dealId, { enabled = true } = {}) {
  return useInfiniteQuery({
    queryKey: dealKey(dealId, 'activity'),
    queryFn: ({ pageParam }) => listActivity(dealId, pageParam),
    initialPageParam: 1,
    getNextPageParam: (last, pages) => (last.next ? pages.length + 1 : undefined),
    staleTime: 0,
    enabled,
  });
}

/** Active users [{id, name}] for owner pickers. */
export function useUsers() {
  return useQuery({ queryKey: USERS_KEY, queryFn: listUsers, staleTime: 5 * 60 * 1000 });
}

export function useAgency() {
  return useQuery({ queryKey: ['agency'], queryFn: getAgency, staleTime: 5 * 60 * 1000 });
}

// ---- mutations -------------------------------------------------------------------------------------------------

const OPTIMISTIC_FIELDS = ['effective_date', 'stage'];

function optimisticHeader(queryClient, previous, changes) {
  const next = { ...previous };
  for (const field of OPTIMISTIC_FIELDS) if (field in changes) next[field] = changes[field];
  if ('owner_id' in changes) {
    const users = queryClient.getQueryData(USERS_KEY) || [];
    next.owner = changes.owner_id == null ? null : users.find((u) => u.id === changes.owner_id) || previous.owner;
  }
  return next;
}

// Writes the returned header into the cache (unless a newer header write is still in flight), then refreshes the
// rest of the deal. With `optimistic`, the header changes at once and rolls back on error.
function useHeaderMutation(dealId, mutationFn, { optimistic = false } = {}) {
  const queryClient = useQueryClient();
  const key = dealKey(dealId, HEADER);
  return useMutation({
    mutationKey: key,
    mutationFn,
    onMutate: optimistic
      ? async (changes) => {
          await queryClient.cancelQueries({ queryKey: key });
          const previous = queryClient.getQueryData(key);
          if (previous) queryClient.setQueryData(key, optimisticHeader(queryClient, previous, changes));
          return { previous };
        }
      : undefined,
    onError: (_error, _vars, context) => {
      if (context?.previous) queryClient.setQueryData(key, context.previous);
      queryClient.invalidateQueries({ queryKey: key });
    },
    onSuccess: (header) => {
      if (queryClient.isMutating({ mutationKey: key }) <= 1) queryClient.setQueryData(key, header);
    },
    onSettled: () => invalidateDeal(queryClient, dealId),
  });
}

/** mutate({effective_date | stage | owner_id}) — optimistic. */
export function useUpdateDeal(dealId) {
  return useHeaderMutation(dealId, (changes) => updateDeal(dealId, changes), { optimistic: true });
}

/**
 * mutate(activityId) — Revert in the Activity drawer (A34) and, later, the Undo toasts (E54). Afterwards every
 * query of the deal refetches, the header included: a revert can touch any tab. Refusals reach `error` (409).
 */
export function useRevertActivity(dealId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: revertActivity,
    onSettled: () => invalidateDeal(queryClient, dealId, { header: true }),
  });
}

/** mutate(reason) */
export function useMarkLost(dealId) {
  return useHeaderMutation(dealId, (reason) => markLost(dealId, reason));
}

/** mutate() */
export function useReopenDeal(dealId) {
  return useHeaderMutation(dealId, () => reopenDeal(dealId));
}

// The header's copy of the client follows a client write at once.
function setHeaderClient(queryClient, deal, client) {
  queryClient.setQueryData(dealKey(deal.id, HEADER), (header) =>
    header
      ? {
          ...header,
          client: {
            ...header.client,
            name: client.name,
            relationship: client.relationship,
            client_since: client.client_since,
          },
        }
      : header,
  );
}

/** mutate(to) — Convert to client, Back to prospect, or a status fix (plan.md §5.1). A 409 reaches `error`. */
export function useSetClientStatus(deal) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (to) => setClientStatus(deal.client.id, to),
    onSuccess: (client) => {
      queryClient.setQueryData(dealKey(deal.id, 'client'), client);
      setHeaderClient(queryClient, deal, client);
    },
    onSettled: () => invalidateDeal(queryClient, deal.id),
  });
}

/** mutate({name, relationship (prospect | existing_client), effective_date, requested_lines, owner_id}) → {client, deal}.
 *  The client and its deal first, then its lines to quote through intake's intent door (§8.3; B17). */
export function useCreateClient() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ requested_lines: lines = [], ...body }) => {
      const created = await createClient(body);
      if (!lines.length) return created;
      return { ...created, deal: { ...created.deal, requested_lines: await shopLines(created.deal.id, lines) } };
    },
    onSuccess: ({ deal }) => {
      queryClient.setQueryData(dealKey(deal.id, HEADER), deal);
      queryClient.invalidateQueries({ queryKey: CLIENTS_KEY });
    },
  });
}
