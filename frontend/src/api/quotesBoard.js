// The board's marks and arrangement (plan.md §7.8): stars, the shortlist, roles and links, the order, slots, and
// removing or moving plans. Every undoable write answers its `activity_id`; Undo is POST activity/{id}/revert/.
import api from './client';
import { useAdvisorMutation } from './quotes';

/** ({planIds, starred}) → {plans, activity_id}; past 16 columns a line answers 409 with the sentence (F50, F58). */
export function useStar(dealId) {
  return useAdvisorMutation(
    dealId,
    async ({ planIds, starred }) => (await api.post(`deals/${dealId}/plans/star/`, { plan_ids: planIds, starred })).data,
  );
}

/** (line) → {plans, activity_id}: every star on that line comes off (F55). */
export function useClearShortlist(dealId) {
  return useAdvisorMutation(
    dealId,
    async (line) => (await api.post(`deals/${dealId}/plans/shortlist/clear/`, { line })).data,
  );
}

/** ({planIds, role}) → {plans, activity_id}: Mark current, Remove current (F53). */
export function useSetRole(dealId) {
  return useAdvisorMutation(
    dealId,
    async ({ planIds, role }) => (await api.post(`deals/${dealId}/plans/role/`, { plan_ids: planIds, role })).data,
  );
}

/** ({planId, replacesIds} | {planId, renewsId}) → {plans, activity_id}: "Replacing:" (F52). */
export function useSetLinks(dealId) {
  return useAdvisorMutation(dealId, async ({ planId, replacesIds, renewsId }) => {
    const body = renewsId !== undefined ? { renews_id: renewsId } : { replaces_ids: replacesIds ?? [] };
    return (await api.post(`deals/${dealId}/plans/links/`, { plan_id: planId, ...body })).data;
  });
}

/**
 * The order door (F43–F48, OQ13): {line, move: {plan_id, step, among?}} | {line, swap: [a, b]} | {line, reset: true}
 * → {line, order, activity_id}; a step out of its group answers 409 with the reason. Stop-loss included.
 */
export function useOrderPlans(dealId) {
  return useAdvisorMutation(dealId, async (body) => (await api.post(`deals/${dealId}/plans/order/`, body)).data);
}

/** ({line, planId, at} | {line, planId, beside?}) → {line, plans, order, activity_id}: a pick on Pages (F45, F46). */
export function usePutInSlot(dealId) {
  return useAdvisorMutation(
    dealId,
    async ({ line, planId, at, beside }) =>
      (await api.post(`deals/${dealId}/plans/slot/`, { line, plan_id: planId, at, beside })).data,
  );
}

/**
 * (planId | [planIds]) → {removed, kept: [{id, name, reason}], note, plans, activity_id}: a soft delete (F60); Undo
 * (Revert of `activity_id`) restores them. Sold plans stay and are named in `note`; when every plan named is sold the
 * door answers 409 with that sentence.
 */
export function useDeletePlans(dealId) {
  return useAdvisorMutation(
    dealId,
    async (planIds) => (await api.post(`deals/${dealId}/plans/delete/`, { plan_ids: [].concat(planIds) })).data,
  );
}

/** (line) → the same shape: every quoted plan on the line goes; current and sold plans stay (F61). */
export function useClearLine(dealId) {
  return useAdvisorMutation(dealId, async (line) => (await api.post(`deals/${dealId}/plans/clear/`, { line })).data);
}

/** ({planIds, line}) → {line, plans, activity_id}: moved with the same ids; refusals are 409 sentences (F59). */
export function useMoveLine(dealId) {
  return useAdvisorMutation(
    dealId,
    async ({ planIds, line }) =>
      (await api.post(`deals/${dealId}/plans/move-line/`, { plan_ids: planIds, line })).data,
  );
}

/**
 * Two plans printed as one column (D-219, J15; slice 33): ({firstId, secondId}) pairs them, the column keeping the
 * first's id, place and number; ({planId, split: true}) takes the pair holding it apart. → {plans, activity_id};
 * refusals (another carrier, another kind, already paired) are 409 sentences.
 */
export function usePairPlans(dealId) {
  return useAdvisorMutation(dealId, async ({ firstId, secondId, planId, split }) => {
    const body = split ? { plan_ids: [planId], split: true } : { plan_ids: [firstId, secondId] };
    return (await api.post(`deals/${dealId}/plans/pair/`, body)).data;
  });
}
