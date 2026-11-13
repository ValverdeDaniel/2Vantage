// Agenda (plan.md §7.15; I.6): the deal's steps, marks and tasks. Query key: ['deal', id, 'agenda'] (staleTime 0, a
// deal tab). Every write invalidates only the agenda, the Overview, the activity and the Work queue (I8, ch. 13), never
// the Advisor's queries; the tab redraws from its own refetch.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import api from './client';
import { dealKey } from './deals';

export const agendaKey = (dealId) => dealKey(dealId, 'agenda');

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

function settle(queryClient, dealId) {
  const id = Number(dealId);
  for (const area of ['agenda', 'overview', 'activity']) {
    queryClient.invalidateQueries({ queryKey: dealKey(id, area) });
  }
  queryClient.invalidateQueries({ queryKey: ['work-queue'] });
}

/**
 * The Agenda's writes, each one request and one transaction (I.5 bug 8): {later, doneAnyway, clearMark, followUp,
 * addTask, updateTask, deleteTask}. Each is a mutateAsync; a refusal throws the API's 400/409 with its sentence.
 */
export function useAgendaWrites(dealId) {
  const queryClient = useQueryClient();
  const write = (call) => ({ mutationFn: call, onSuccess: () => settle(queryClient, dealId) });
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
  return { later, doneAnyway, clearMark, followUp, addTask, updateTask, deleteTask };
}
