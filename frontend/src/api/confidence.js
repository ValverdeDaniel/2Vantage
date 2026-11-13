// The Overview's data confidence (plan.md §7.13, §8.6; M83–M93; M.6; slice 64). Query key ['deal', id, 'confidence'],
// a sibling of the Overview's own (staleTime 0, as every deal tab): reviewing a value refetches it and the deal's
// activity, never the rest of the Overview. Undo is the deals' revert (`useRevertActivity`), which refetches the deal.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import api from './client';
import { dealKey } from './deals';

export const confidenceKey = (dealId) => dealKey(dealId, 'confidence');

/**
 * GET deals/{id}/confidence/ → {deal_id, cells: {scanned, corrected, typed, from_client, pending}, filled, confirmed:
 * {total, by_person, by_recheck, pct}, warnings: {low, to_review, check, ignored}, documents: [{id, name, kind,
 * values, confirmed, to_review, check, ignored, headline: {label, tone}}], documents_more, ignored | check: {rows:
 * [{ref, owner, where, label, value (null for member data), tab, form, doc: {id, name} | null, by, at}], more},
 * recheck: {values, last: {job_id, status, scanned, waiting, resolution, error, at, counts: {checked, agreed, differ,
 * not_found}, differences: [{label, old, new, doc, page}]} | null}}.
 */
export function useConfidence(dealId) {
  return useQuery({
    queryKey: confidenceKey(dealId),
    queryFn: async () => (await api.get(`deals/${dealId}/confidence/`)).data,
    staleTime: 0,
  });
}

/**
 * mutate({action: approve | ignore | check | clear, documentId} | {action, refs}) → {action, changed: {owner: n},
 * count, activity_id}: one file's values, or the values named, on every owner in one transaction (M88–M91). Refetches
 * the confidence, the deal's activity and Claude's state (its flag count).
 */
export function useReviewMarks(dealId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ action, documentId, refs }) =>
      (
        await api.post(`deals/${dealId}/review/marks/`, {
          action,
          ...(documentId ? { document_id: documentId } : {}),
          ...(refs ? { refs } : {}),
        })
      ).data,
    onSettled: () =>
      ['confidence', 'activity', 'ai'].forEach((area) =>
        queryClient.invalidateQueries({ queryKey: dealKey(dealId, area) }),
      ),
  });
}
