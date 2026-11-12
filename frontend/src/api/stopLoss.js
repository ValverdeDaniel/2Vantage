// The Advisor's stop-loss analysis (plan.md §7.8 `plans/stop-loss/`, §8.14; F98–F107). Query key
// ['deal', id, 'advisor', 'stop-loss', without], staleTime 0, so a star or a value edit elsewhere on the Advisor
// refetches it. The laser what-if is `without` ("12:1,15:2", plan id : laser position): a parameter of the read, never
// stored (F104). The answer: {line, basis: {lives, months, source, words}, currents, current_id, columns: [{id,
// carrier, name, role, current, starred, recommended, sold, figures, vs, scored, what_if, terms}], ranks: {rank key:
// [option ids]}, punchline: {plan_id, carrier, name} | null, what_if, refusal}.
import { keepPreviousData, useQuery } from '@tanstack/react-query';
import api from './client';
import { advisorKey } from './quotes';

/** The analysis, with the lasers left out (`without`, already a string) applied by the server. */
export function useStopLoss(dealId, without = '') {
  return useQuery({
    queryKey: advisorKey(dealId, 'stop-loss', without),
    queryFn: async () =>
      (await api.get(`deals/${dealId}/plans/stop-loss/`, { params: without ? { without } : {} })).data,
    staleTime: 0,
    placeholderData: keepPreviousData,
  });
}

/** The five-tab workbook's address (J166; served by the proposals app), for `downloadFile`. */
export const stopLossWorkbookUrl = (dealId) => `deals/${dealId}/plans/stop-loss/workbook/`;
