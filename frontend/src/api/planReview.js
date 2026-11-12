// Reviewing plan values (plan.md §7.8, §10.7; E48, E53, E54, E56, F63–F67). Query keys: ['deal', id, 'review', 'plans',
// files, bucket] for the station's List. A review's answer is written into the Advisor's cached comparisons at once
// (cells and counts), the List refetches its own pages, and nothing else of the deal moves (E53: no invalidateDeal).
import { useInfiniteQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { patchComparison } from '../valuereview/marksCache';
import api from './client';
import { dealKey, revertActivity } from './deals';
import { advisorKey } from './quotes';

export const reviewKey = (dealId, ...rest) => dealKey(dealId, 'review', ...rest);

/**
 * The List's rows for these files (`documentIds`, or every file when empty), worst first, 200 a page, in one bucket or
 * all: pages of {rows, page, pages, total, counts: {bucket: {open, done}}, all, warnings: {open, check, unflagged},
 * quality: {high, low, missing}, headline: {label, tone}}. `fetchNextPage()` is "Show more".
 */
export function usePlanSources(dealId, { documentIds = [], bucket = '', enabled = true } = {}) {
  const files = documentIds.join(',');
  return useInfiniteQuery({
    queryKey: reviewKey(dealId, 'plans', files, bucket),
    queryFn: async ({ pageParam }) =>
      (
        await api.get(`deals/${dealId}/plans/sources/`, {
          params: { ...(files ? { documents: files } : {}), ...(bucket ? { bucket } : {}), page: pageParam },
        })
      ).data,
    initialPageParam: 1,
    getNextPageParam: (last) => (last.page < last.pages ? last.page + 1 : undefined),
    staleTime: 0,
    refetchOnWindowFocus: false, // a heavy station query (O.4)
    placeholderData: (previous) => previous,
    enabled,
  });
}

function settle(queryClient, dealId, answer) {
  queryClient.setQueriesData({ queryKey: advisorKey(dealId) }, (data) =>
    data?.groups && Array.isArray(data.plans) ? patchComparison(data, answer) : data,
  );
  if (answer?.truncated) queryClient.invalidateQueries({ queryKey: advisorKey(dealId) });
  queryClient.invalidateQueries({ queryKey: reviewKey(dealId) });
  queryClient.invalidateQueries({ queryKey: dealKey(dealId, 'activity') });
}

/**
 * mutate({action: 'approve' | 'ignore' | 'check' | 'clear', refs?, plan_ids?, document_ids?}) → {action, changed,
 * activity_id, truncated, values: [{ref, plan_id, key, cell, mark, confirmed, open, potential, dealt, bucket}], plans:
 * [{id, flags, incomplete}]}. `refs` ("plan:41:rate_ee") name exactly those values; plans and files take only their
 * open warnings (for clear, their marks). Bad targets answer 400 with a sentence.
 */
export function useMarkPlans(dealId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body) => (await api.post(`deals/${dealId}/plans/marks/`, body)).data,
    onSuccess: (answer) => settle(queryClient, dealId, answer),
  });
}

/**
 * mutate(activityId) — ↶ Undo of one review (E54): its Activity row reverted; the values changed since stay as they
 * are, and when none can go back the server refuses (409) naming them. The board and the List refetch.
 */
export function useUndoReview(dealId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: revertActivity,
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: advisorKey(dealId) });
      queryClient.invalidateQueries({ queryKey: reviewKey(dealId) });
      queryClient.invalidateQueries({ queryKey: dealKey(dealId, 'activity') });
    },
  });
}
