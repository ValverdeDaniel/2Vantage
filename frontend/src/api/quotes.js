// The Advisor (plan.md §7.7). Query keys: ['deal', id, 'advisor', 'lines'] · ['deal', id, 'advisor', line].
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import api from './client';
import { dealKey, invalidateDeal } from './deals';

export const advisorKey = (dealId, ...rest) => dealKey(dealId, 'advisor', ...rest);

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
    queryFn: async () => (await api.get(`deals/${dealId}/plans/`, { params: { line } })).data,
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

/** ({planId, changes}) — changes: any of carrier, name, plan_number, role, renews_id, replaces_ids, starred, notes, values */
export function useUpdatePlan(dealId) {
  return useAdvisorMutation(
    dealId,
    async ({ planId, changes }) => (await api.patch(`plans/${planId}/`, changes)).data,
  );
}

export function useDeletePlan(dealId) {
  return useAdvisorMutation(dealId, async (planId) => api.delete(`plans/${planId}/`));
}

export function useCreateRenewal(dealId) {
  return useAdvisorMutation(dealId, async (planId) => (await api.post(`plans/${planId}/renewal/`)).data);
}

export function useCopyPlan(dealId) {
  return useAdvisorMutation(dealId, async (planId) => (await api.post(`plans/${planId}/copy/`)).data);
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

export function useStar(dealId) {
  return useAdvisorMutation(
    dealId,
    async ({ planIds, starred }) => (await api.post(`deals/${dealId}/plans/star/`, { plan_ids: planIds, starred })).data,
  );
}

/** [{id, enrollment: {...}, on}] */
export function useSaveEnrollment(dealId) {
  return useAdvisorMutation(
    dealId,
    async (plans) => (await api.post(`deals/${dealId}/plans/enrollment/`, { plans })).data,
  );
}

export function useOrderPlans(dealId) {
  return useAdvisorMutation(dealId, async (body) => api.post(`deals/${dealId}/plans/order/`, body));
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
