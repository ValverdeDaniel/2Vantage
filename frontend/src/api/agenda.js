// Agenda (plan.md §7.15; I.6): the deal's steps, marks and tasks. Query key: ['deal', id, 'agenda'] (staleTime 0, a
// deal tab). Every write invalidates only the agenda, the shell's journey, the Overview, the activity and the Work
// queue (I8, ch. 13), never the Advisor's queries; the tab redraws from its own refetch. From slice 61: the shell's
// one read ['deal', id, 'journey'], and the home page's feed ['work-queue', include] and stats ['work-queue-stats'].
// From slice 68 the client page's Agenda writes through the same doors and names its client, whose page (['client', id,
// …]: its Agenda, rollup, tile and activity) then refetches too.
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import api from './client';
import { clientKey } from './clientPage';
import { dealKey } from './deals';

export const agendaKey = (dealId) => dealKey(dealId, 'agenda');
export const journeyKey = (dealId) => dealKey(dealId, 'journey');
export const WORK_QUEUE_KEY = ['work-queue'];
export const QUEUE_STATS_KEY = ['work-queue-stats'];

/**
 * GET deals/{id}/journey/ → {deal_id, today, next_step, waiting, journey: {modules: [{key, label, pct, steps: [{key,
 * label, tab, state: done | current | todo}]}], complete}, progress, badges, meters, ready}: the sidebar's badges,
 * meters and ready chip and the stepper (A21, A23, A24). `invalidateDeal` refetches it after a tab's write.
 */
export function useJourney(dealId) {
  return useQuery({
    queryKey: journeyKey(dealId),
    queryFn: async () => (await api.get(`deals/${dealId}/journey/`)).data,
    staleTime: 0,
    enabled: Boolean(dealId),
  });
}

/**
 * GET work-queue/ → {today, rows, owners, client_names, cards: {prospects: {count, deal_size, unsized}}}: every live
 * deal's row, open tasks and nudges (agenda/queue/feed.py). `closed` asks for finished and lost deals' rows too (I80).
 * Kept on screen while a newer copy loads, as the old home's cache did (I89).
 */
export function useWorkQueue({ closed = false, enabled = true } = {}) {
  return useQuery({
    queryKey: [...WORK_QUEUE_KEY, closed ? 'closed' : 'open'],
    queryFn: async () => (await api.get('work-queue/', { params: closed ? { include: 'closed' } : {} })).data,
    staleTime: 0,
    placeholderData: keepPreviousData,
    enabled,
  });
}

/** GET work-queue/stats/ → {actions_week, sales_month}, each {total, change_pct, series} (I83, I84, I127). */
export function useQueueStats({ enabled = true } = {}) {
  return useQuery({
    queryKey: QUEUE_STATS_KEY,
    queryFn: async () => (await api.get('work-queue/stats/')).data,
    staleTime: 0,
    enabled,
  });
}

/**
 * GET deals/{id}/agenda/ → {today, deal_id, lost, finished, next_step, waiting, journey, progress, rows}. A row is a
 * step, a task or a nudge: {id, kind, key, label, section, date, severity, link, also?, chip, can: {…}, …}.
 */
export function useAgenda(dealId) {
  return useQuery({
    queryKey: agendaKey(dealId),
    queryFn: async () => (await api.get(`deals/${dealId}/agenda/`)).data,
    staleTime: 0,
  });
}

function settle(queryClient, dealId, clientId) {
  const id = Number(dealId);
  for (const area of ['agenda', 'journey', 'overview', 'activity']) {
    queryClient.invalidateQueries({ queryKey: dealKey(id, area) });
  }
  queryClient.invalidateQueries({ queryKey: WORK_QUEUE_KEY });
  if (clientId) queryClient.invalidateQueries({ queryKey: clientKey(clientId) });
}

/**
 * The Agenda's writes, each one request and one transaction (I.5 bug 8): {later, doneAnyway, clearMark, followUp,
 * addTask, updateTask, deleteTask, nudge}. Each is a mutateAsync; a refusal throws the API's 400/409 with its sentence.
 * `nudge` is Later ({linkId, kind: 'later', until, note}) or ✓ ({linkId, kind: 'done'}) on a nudge row, which the
 * server hands to review's set_nudge / finish_nudge (I37) → {nudge: row | null}. `clientId`: the client page writing
 * (slice 68), whose queries refetch after each write too.
 */
export function useAgendaWrites(dealId, { clientId } = {}) {
  const queryClient = useQueryClient();
  const write = (call) => ({ mutationFn: call, onSuccess: () => settle(queryClient, dealId, clientId) });
  const marks = `deals/${dealId}/agenda/marks/`;
  const later = useMutation(
    write(async ({ stepKey, until, note }) => (await api.post(marks, { step_key: stepKey, kind: 'later', until, note }))
      .data),
  );
  const doneAnyway = useMutation(
    write(async ({ stepKey }) => (await api.post(marks, { step_key: stepKey, kind: 'done' })).data),
  );
  const clearMark = useMutation(
    write(async ({ stepKey }) => (await api.delete(`${marks}${encodeURIComponent(stepKey)}/`)).data),
  );
  const followUp = useMutation(
    write(
      async ({ stepKey, kind, body }) =>
        (await api.post(`deals/${dealId}/agenda/follow-ups/`, { step_key: stepKey, kind, body })).data,
    ),
  );
  const addTask = useMutation(write(async (body) => (await api.post(`deals/${dealId}/tasks/`, body)).data));
  const updateTask = useMutation(
    write(async ({ taskId, ...changes }) => (await api.patch(`tasks/${taskId}/`, changes)).data),
  );
  const deleteTask = useMutation(write(async ({ taskId }) => (await api.delete(`tasks/${taskId}/`)).data));
  const nudge = useMutation(
    write(async ({ linkId, ...body }) => (await api.post(`deals/${dealId}/agenda/nudges/${linkId}/`, body)).data),
  );
  return { later, doneAnyway, clearMark, followUp, addTask, updateTask, deleteTask, nudge };
}
