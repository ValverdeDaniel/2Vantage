// Intake (plan.md §7.6). Query key ['deal', id, 'intake'] (staleTime 0, a deal tab). The intent door answers the card
// and the rows as they now stand and the lines to quote, so the intake cache and the deal header's lines follow at
// once; the coverage rows' doors answer the row, so the intake query refetches after them.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import api from './client';
import { dealKey, invalidateDeal } from './deals';

export const intakeKey = (dealId) => dealKey(dealId, 'intake');

/** GET deals/{id}/intake/ → {answers, sources, hidden, coverage: [row], intent: card}. */
export function useIntake(dealId) {
  return useQuery({
    queryKey: intakeKey(dealId),
    queryFn: async () => (await api.get(`deals/${dealId}/intake/`)).data,
    staleTime: 0,
  });
}

/**
 * POST deals/{id}/intake/intent/ — the one writer of the lines to quote (B17, B32). body: {line | lines,
 * has_today?, this_year? (market | keep | off), shop?, remove?} → {intent, coverage, requested_lines, activity_id}.
 */
export async function postIntent(dealId, body) {
  return (await api.post(`deals/${dealId}/intake/intent/`, body)).data;
}

// The answer of an intent door into the caches: the intake payload's card and rows, the header's lines; then the rest
// of the deal (the Advisor's line tabs read the intent).
function adoptIntent(queryClient, dealId, answer) {
  queryClient.setQueryData(intakeKey(dealId), (current) =>
    current ? { ...current, intent: answer.intent, coverage: answer.coverage } : current,
  );
  queryClient.setQueryData(dealKey(dealId, 'header'), (header) =>
    header ? { ...header, requested_lines: answer.requested_lines } : header,
  );
  invalidateDeal(queryClient, dealId);
}

/** mutate(body) — a gesture of the coverage card, the Lines-to-quote chips or the header's Lines picker. */
export function useSetIntent(dealId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body) => postIntent(dealId, body),
    onSuccess: (answer) => adoptIntent(queryClient, dealId, answer),
  });
}

/** mutate() — Confirm coverage & intent (or Confirm again); with {reopen: true}, Reopen (B20). */
export function useConfirmIntent(dealId, { reopen = false } = {}) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => (await api.post(`deals/${dealId}/intake/intent/${reopen ? 'reopen' : 'confirm'}/`)).data,
    onSuccess: (answer) => adoptIntent(queryClient, dealId, answer),
  });
}

function useCoverageWrite(dealId, mutationFn) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn,
    onSettled: () => invalidateDeal(queryClient, dealId),
  });
}

/** mutate({line, carrier?, funding?, in_force?, …}) → the new row (B14's ＋ Add coverage line, B19's ＋ Add a line…). */
export function useAddCoverage(dealId) {
  return useCoverageWrite(dealId, async (body) => (await api.post(`deals/${dealId}/coverage/`, body)).data);
}

/** mutate({id, changes}) → the row. Carrier and funding answer 400 once the line has current plans (§6.5). */
export function useEditCoverage(dealId) {
  return useCoverageWrite(dealId, async ({ id, changes }) => (await api.patch(`coverage/${id}/`, changes)).data);
}

/** mutate(id) — the subcard's ×; the line stays on the lines to quote (the card's × is the intent's `remove`). */
export function useRemoveCoverage(dealId) {
  return useCoverageWrite(dealId, async (id) => (await api.delete(`coverage/${id}/`)).data);
}
