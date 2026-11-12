// The Advisor (plan.md §7.8). Query keys: ['deal', id, 'advisor', 'lines'] · ['deal', id, 'advisor', line].
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import api from './client';
import { dealKey, invalidateDeal } from './deals';

export const advisorKey = (dealId, ...rest) => dealKey(dealId, 'advisor', ...rest);

/**
 * The comparison is compact (F.6): each cell carries only its flags, `{s: status, o: origin, d: document index,
 * m: mark}`, and the documents are listed once. The screens read `plan.status` and `plan.sources`, so they are
 * rebuilt here from the cells (display only; nothing is computed).
 */
export function expandComparison(data) {
  const documents = data.documents ?? [];
  return {
    ...data,
    plans: data.plans.map((plan) => {
      const status = {};
      const sources = {};
      Object.entries(plan.cells ?? {}).forEach(([key, cell]) => {
        if (cell.s) status[key] = cell.s;
        if (key in (plan.values ?? {})) {
          sources[key] = { origin: cell.o ?? 'typed', doc: documents[cell.d]?.id, mark: cell.m };
        }
      });
      return { ...plan, status, sources };
    }),
  };
}

export function useAdvisorLines(dealId) {
  return useQuery({
    queryKey: advisorKey(dealId, 'lines'),
    queryFn: async () => (await api.get(`deals/${dealId}/plans/lines/`)).data,
    staleTime: 0,
  });
}

export function useComparison(dealId, line) {
  return useQuery({
    queryKey: advisorKey(dealId, line),
    queryFn: async () => expandComparison((await api.get(`deals/${dealId}/plans/`, { params: { line } })).data),
    enabled: Boolean(line),
    staleTime: 0,
    placeholderData: (previous) => (previous?.line === line ? previous : undefined),
  });
}

/**
 * Every Advisor write refetches the Advisor (premiums, packages and the recommendation all move together) and,
 * when it can move the stage (sold), the deal header too. Proposal queries refetch on open (staleTime 0).
 */
function useAdvisorMutation(dealId, mutationFn, { header = false } = {}) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn,
    onSuccess: () => invalidateDeal(queryClient, dealId, { header }),
  });
}

export function useCreatePlan(dealId) {
  return useAdvisorMutation(dealId, async (body) => (await api.post(`deals/${dealId}/plans/`, body)).data);
}

const LINK_KEYS = ['role', 'renews_id', 'replaces_ids'];

/**
 * ({planId, changes}). PATCH takes only carrier, name, plan_number, client_name, notes, values and `expect` (F71);
 * a role and its links go through their own doors (F52, F53): `plans/role/` when the role changes (a plan already in
 * that role is left as it is), then `plans/links/` (which changes nothing when the role door already set them).
 */
export function useUpdatePlan(dealId) {
  return useAdvisorMutation(dealId, async ({ planId, changes }) => {
    const rest = Object.fromEntries(Object.entries(changes).filter(([key]) => !LINK_KEYS.includes(key)));
    let answer;
    if (changes.role) {
      const { role, renews_id: renewsId, replaces_ids: replacesIds } = changes;
      const links = role === 'renewal' ? { renews_id: renewsId } : { replaces_ids: replacesIds ?? [] };
      answer = (await api.post(`deals/${dealId}/plans/role/`, { plan_ids: [planId], role, ...links })).data;
      if (role !== 'current') {
        answer = (await api.post(`deals/${dealId}/plans/links/`, { plan_id: planId, ...links })).data;
      }
    }
    if (Object.keys(rest).length) answer = (await api.patch(`plans/${planId}/`, rest)).data;
    return answer;
  });
}

/** ({planIds, role, renewsId?, replacesIds?}) → {plans, activity_id}: Mark current, Remove current (F53). */
export function useSetRole(dealId) {
  return useAdvisorMutation(
    dealId,
    async ({ planIds, role, renewsId, replacesIds }) =>
      (
        await api.post(`deals/${dealId}/plans/role/`, {
          plan_ids: planIds,
          role,
          renews_id: renewsId,
          replaces_ids: replacesIds,
        })
      ).data,
  );
}

/** ({planId, replacesIds} | {planId, renewsId}) → {plans, activity_id}: "Replacing:" and "Several…" (F52). */
export function useSetLinks(dealId) {
  return useAdvisorMutation(dealId, async ({ planId, replacesIds, renewsId }) => {
    const body = renewsId !== undefined ? { renews_id: renewsId } : { replaces_ids: replacesIds ?? [] };
    return (await api.post(`deals/${dealId}/plans/links/`, { plan_id: planId, ...body })).data;
  });
}

/**
 * (planId | [planIds]) → {removed, kept: [{id, name, reason}], note, plans, activity_id}: a soft delete (F60); Revert of
 * its Activity row restores the plans. Sold plans stay and are named in `note`; when every plan named is sold the
 * door answers 409 with that sentence.
 */
export function useDeletePlan(dealId) {
  return useAdvisorMutation(
    dealId,
    async (planIds) =>
      (await api.post(`deals/${dealId}/plans/delete/`, { plan_ids: [].concat(planIds) })).data,
  );
}

export function useCreateRenewal(dealId) {
  return useAdvisorMutation(dealId, async (planId) => (await api.post(`plans/${planId}/renewal/`)).data);
}

/** (planId | {planId, name}) → the copy: Duplicate, keeping the rates (F81); unnamed, it is "<name> — copy". */
export function useCopyPlan(dealId) {
  return useAdvisorMutation(dealId, async (arg) => {
    const { planId, name } = typeof arg === 'object' ? arg : { planId: arg };
    return (await api.post(`plans/${planId}/copy/`, name ? { name } : {})).data;
  });
}

export function useSetSold(dealId) {
  return useAdvisorMutation(
    dealId,
    async ({ planId, sold }) => (await api.post(`plans/${planId}/sold/`, { sold })).data,
    { header: true },
  );
}

export function useSetRecommended(dealId) {
  return useAdvisorMutation(
    dealId,
    async ({ planId, recommended }) => (await api.post(`plans/${planId}/recommend/`, { recommended })).data,
  );
}

/** ({planIds, starred}) → {plans, activity_id}; past 16 columns a line answers 409 with the sentence (F50). */
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

/** [{id, enrollment: {...}, on}] */
export function useSaveEnrollment(dealId) {
  return useAdvisorMutation(
    dealId,
    async (plans) => (await api.post(`deals/${dealId}/plans/enrollment/`, { plans })).data,
  );
}

/**
 * The order door (F43–F48): {line, move: {plan_id, step, among?}} | {line, swap: [a, b]} | {line, reset: true}
 * → {line, order, activity_id}; a step out of its group answers 409 with the reason.
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

export function useCreatePackage(dealId) {
  return useAdvisorMutation(dealId, async (body) => (await api.post(`deals/${dealId}/plans/packages/`, body)).data);
}

export function useUpdatePackage(dealId) {
  return useAdvisorMutation(
    dealId,
    async ({ packageId, changes }) => (await api.patch(`packages/${packageId}/`, changes)).data,
  );
}

export function useDeletePackage(dealId) {
  return useAdvisorMutation(dealId, async (packageId) => api.delete(`packages/${packageId}/`));
}

export function templateUrl(dealId, line) {
  return `deals/${dealId}/plans/template/${line ? `?line=${encodeURIComponent(line)}` : ''}`;
}

/** ({file, dryRun}) → {create, update, cells_changed, errors}; a refused import answers 400 with the same shape. */
export function useImportTemplate(dealId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ file, dryRun }) => {
      const form = new FormData();
      form.append('file', file);
      try {
        const { data } = await api.post(`deals/${dealId}/plans/import/`, form, {
          params: dryRun ? { dry_run: 1 } : undefined,
        });
        return data;
      } catch (error) {
        if (error?.response?.status === 400 && Array.isArray(error.response.data?.errors)) return error.response.data;
        throw error;
      }
    },
    onSuccess: (data, { dryRun }) => {
      if (!dryRun && !data.errors?.length) invalidateDeal(queryClient, dealId);
    },
  });
}
