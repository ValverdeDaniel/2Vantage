// The Advisor's plans (plan.md §7.8). Query keys: ['deal', id, 'advisor', 'lines'] · ['deal', id, 'advisor', line].
// The board's marks and arrangement (stars, roles, links, order, delete, clear, move) are in quotesBoard.js.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import api from './client';
import { dealKey, invalidateDeal } from './deals';

export const advisorKey = (dealId, ...rest) => dealKey(dealId, 'advisor', ...rest);

/** [{line, label, requested, current, renewal, alternate, starred, recommended, recommendation_covered, columns,
 *  room, sold_plans}] in the deal's line order (F5). */
export function useAdvisorLines(dealId) {
  return useQuery({
    queryKey: advisorKey(dealId, 'lines'),
    queryFn: async () => (await api.get(`deals/${dealId}/plans/lines/`)).data,
    staleTime: 0,
  });
}

/**
 * One line's comparison, as the server sends it (F.6, C23): {line, rate_basis, groups, plans, documents, room,
 * packages, member_packages, recommendation, warnings}, the plans in `order.layout`'s order, each with its compact
 * `cells` ({key: {s: status, o: origin, d: index into documents, m: mark}}), `premium`, `change`, `facts`,
 * `closeness`, `presented` and `base_ids`. A value's full source comes on ↗ (plans/{id}/source/).
 */
export function useComparison(dealId, line) {
  return useQuery({
    queryKey: advisorKey(dealId, line),
    queryFn: async () => (await api.get(`deals/${dealId}/plans/`, { params: { line } })).data,
    enabled: Boolean(line),
    staleTime: 0,
    placeholderData: (previous) => (previous?.line === line ? previous : undefined),
  });
}

/** Refetch the Advisor's own queries (the board after a burst of cell writes; F71). */
export function refreshAdvisor(queryClient, dealId) {
  return queryClient.invalidateQueries({ queryKey: advisorKey(dealId) });
}

/** Write one plan value into the cached comparison at once (a typed cell, or its restore after a failure). */
export function setCachedValue(queryClient, dealId, line, planId, key, value) {
  queryClient.setQueryData(advisorKey(dealId, line), (data) =>
    data
      ? {
          ...data,
          plans: data.plans.map((plan) =>
            plan.id === planId ? { ...plan, values: { ...plan.values, [key]: value ?? '' } } : plan,
          ),
        }
      : data,
  );
}

/**
 * PATCH plans/{id}/ (F71, J74): only carrier, name, plan_number, client_name, notes and values, with `expect` (the
 * values the person last saw; a stored value that differs answers 409 naming the keys). → plan + activity_id.
 */
export async function patchPlan(planId, body) {
  return (await api.patch(`plans/${planId}/`, body)).data;
}

/**
 * Every other Advisor write refetches the deal's queries (premiums, packages and the recommendation move together)
 * and, when it can move the stage (sold), the deal header too. Proposal queries refetch on open (staleTime 0).
 */
export function useAdvisorMutation(dealId, mutationFn, { header = false } = {}) {
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
 * ({planId, changes}) for the plan dialog: details through PATCH; a role and its links through their own doors
 * (F52, F53): `plans/role/` when the role changes, then `plans/links/`.
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
    if (Object.keys(rest).length) answer = await patchPlan(planId, rest);
    return answer;
  });
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

/** ({planId, recommended}); any plan may be recommended (OQ37: on a current plan it reads "Keep this plan"). */
export function useSetRecommended(dealId) {
  return useAdvisorMutation(
    dealId,
    async ({ planId, recommended }) => (await api.post(`plans/${planId}/recommend/`, { recommended })).data,
  );
}

/** [{id, enrollment: {...}, on}] */
export function useSaveEnrollment(dealId) {
  return useAdvisorMutation(
    dealId,
    async (plans) => (await api.post(`deals/${dealId}/plans/enrollment/`, { plans })).data,
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

/**
 * ⤓ Export (F93, J167): the board as it stands, as Excel. `plans` are the ids in the order drawn, `columns` the
 * column keys in theirs, `orientation` 'rows' or 'cols'; the server works out every figure again.
 */
export function boardExport(dealId, { line, plans, columns, orientation }) {
  return {
    url: `deals/${dealId}/plans/board-export/`,
    params: { line, plans: plans.join(','), columns: columns.join(','), orientation },
  };
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
