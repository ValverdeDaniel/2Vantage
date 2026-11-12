import { useMemo } from 'react';
import { useQuotedTable } from '../../../api/asQuoted';
import { buildAsQuoted } from './asQuotedModel';
import { gridFind, onlyMatches } from './gridFind';
import { filterGrid } from './stationModel';
import useStationComparisons from './useStationComparisons';

/*
 * One scanned quote's printed table as a grid (plan.md §8.14, §8.16; D66, E42, F42; slice 21): the server's table
 * (`plans/as-quoted/`) over the Advisor's cached comparisons (useStationComparisons), in the station Grid's shape, so
 * StationGrid draws it with the station's filters, Find (`found`, `shown`), picks, marks and ✎ Edit. → the same
 * {data, model, filtered, found, shown} as useStationGrid, plus `table` (the server's answer).
 */
export default function useAsQuotedGrid({ dealId, plansMeta, documentId, line, enabled, terms, only, filters }) {
  const data = useStationComparisons(dealId, enabled);
  const table = useQuotedTable(dealId, documentId, line, { enabled });
  const model = useMemo(
    () => buildAsQuoted({ table: table.data, comparisons: data.comparisons, meta: plansMeta }),
    [table.data, data.comparisons, plansMeta],
  );
  const { errorsOnly, rowsOnly } = filters;
  const filtered = useMemo(() => filterGrid(model, { errorsOnly, rowsOnly }), [model, errorsOnly, rowsOnly]);
  const found = useMemo(() => gridFind(model, filtered, terms, data.index), [model, filtered, terms, data.index]);
  const shown = useMemo(() => (only ? onlyMatches(filtered, found) : filtered), [only, filtered, found]);
  return {
    data: {
      ...data,
      pending: data.pending || (enabled && table.isPending),
      error: data.error || table.error || null,
      refetch: () => {
        data.refetch();
        table.refetch();
      },
    },
    model,
    filtered,
    found,
    shown,
    table: table.data ?? null,
  };
}
