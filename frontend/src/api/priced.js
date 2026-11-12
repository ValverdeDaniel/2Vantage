// Priced versions (plan.md §7.8; F76–F84): a dry run that previews, then the commit. The dry run writes nothing, so it
// is a plain request (no cache, no invalidation); the commits refetch the deal's queries like every Advisor write.
import api from './client';
import { patchPlan, useAdvisorMutation } from './quotes';

function url(dealId, editId) {
  return editId ? `plans/${editId}/priced/` : `deals/${dealId}/plans/priced/`;
}

/**
 * ({dealId, editId, body, signal}) → {dry_run: true, drafts: [{original_id, name, label, derived, starred, changes,
 * premium, change, part_of, credit, enrollment_used, enrollment_source}], warning}. A refusal answers 409 and a bad
 * request 400, each with the sentence in `detail`.
 */
export async function previewPriced({ dealId, editId, body, signal }) {
  return (await api.post(url(dealId, editId), { ...body, dry_run: true }, { signal })).data;
}

/** ({editId?, body}) → {drafts, plans, warning, activity_id}: the versions written (✎ re-prices `editId`). */
export function useCommitPriced(dealId) {
  return useAdvisorMutation(dealId, async ({ editId, body }) => (await api.post(url(dealId, editId), body)).data);
}

/** ({planId, bundling}): whether a quote's rates already include the bundling discount ('', 'unbundled', 'included'). */
export function useSetBundling(dealId) {
  return useAdvisorMutation(dealId, async ({ planId, bundling }) => patchPlan(planId, { bundling }));
}
