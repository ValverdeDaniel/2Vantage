import { useQueries } from '@tanstack/react-query';
import { useMemo, useState } from 'react';
import { comparisonQuery, useAdvisorLines, useFindIndex } from '../../../api/quotes';

/*
 * What the station's Grid reads (plan.md §8.16; E36, E62): the Advisor's own cached comparison of every line that has
 * plans, so a Grid opened from the Advisor draws at once and a review's marks, written into those caches (E53), show
 * on both; and the finder's index (`plans/find/`), whose texts and carrier key a plan's head answers to in Find (E62,
 * E64). Only while the Grid is shown (`enabled`). → {comparisons (deal line order), index: Map(id → entry), pending,
 * error, refetch}.
 */
export default function useStationComparisons(dealId, enabled) {
  const lines = useAdvisorLines(dealId);
  const keys = useMemo(
    () => (lines.data ?? []).filter((row) => row.current + row.renewal + row.alternate > 0).map((row) => row.line),
    [lines.data],
  );
  const results = useQueries({
    queries: keys.map((line) => ({ ...comparisonQuery(dealId, line), enabled, refetchOnWindowFocus: false })),
  });
  const finder = useFindIndex(dealId);
  // A new list only when a line's data changed, so the grid's model is not rebuilt on every render.
  const datas = results.map((result) => result.data);
  const [kept, setKept] = useState(datas);
  if (datas.length !== kept.length || datas.some((data, at) => data !== kept[at])) setKept(datas);
  const comparisons = useMemo(() => kept.filter(Boolean), [kept]);
  const index = useMemo(
    () => new Map((finder.data?.plans ?? []).map((entry) => [entry.id, entry])),
    [finder.data],
  );
  const error = lines.error || results.find((result) => result.error)?.error || null;
  return {
    comparisons,
    index,
    pending: lines.isPending || results.some((result) => result.isPending && result.fetchStatus !== 'idle'),
    error,
    refetch: () => {
      lines.refetch();
      for (const result of results) result.refetch();
    },
  };
}
