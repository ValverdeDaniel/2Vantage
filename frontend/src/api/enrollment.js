// Typed enrollment (plan.md §5.5, §7.8; F85, F88, F90–F92): one door for a line's whole typed set. The comparison's
// `enrollment` block (api/quotes.js useComparison) is what the counts card reads.
import api from './client';
import { useAdvisorMutation } from './quotes';

/**
 * ({line, plans?: [{id, enrollment}], whole_line?, on?, census_names?: {planId: [texts]}, keep?}) → {line_enrollment,
 * plans, activity_id}. A part left out stays as it is; `plans` is the line's whole per-plan set (a plan left out loses
 * its counts); `keep` makes counts typed before the latest census import price again ("Keep my typed counts", F91).
 * An unchanged save answers activity_id null. Refetches the deal's Advisor.
 */
export function useSaveEnrollment(dealId) {
  return useAdvisorMutation(
    dealId,
    async (body) => (await api.post(`deals/${dealId}/plans/enrollment/`, body)).data,
  );
}
