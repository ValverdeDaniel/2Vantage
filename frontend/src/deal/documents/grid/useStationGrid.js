import { useMemo } from 'react';
import { gridFind, onlyMatches } from './gridFind';
import { buildStationGrid, filterGrid } from './stationModel';
import useStationComparisons from './useStationComparisons';

/*
 * The station's Grid as the panel holds it (plan.md §8.16; E36–E41, E50, E60–E64): the comparisons and the finder's
 * index (useStationComparisons), the model for the files in scope, what the plan filters leave (`filtered`), Find's
 * hits over that (`found`) and what "Only matches" leaves on screen (`shown`). Each step is memoised, so typing in
 * Find rebuilds only the hits. The index also gives the List's rows their plan's carrier, for nicknames (OQ14).
 */
export default function useStationGrid({ dealId, plansMeta, scopeIds, enabled, terms, only, filters }) {
  const data = useStationComparisons(dealId, enabled);
  const ids = scopeIds.join(',');
  const model = useMemo(
    () => buildStationGrid({ comparisons: data.comparisons, meta: plansMeta, scopeIds: new Set(scopeIds) }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [data.comparisons, plansMeta, ids],
  );
  const { errorsOnly, rowsOnly } = filters;
  const filtered = useMemo(() => filterGrid(model, { errorsOnly, rowsOnly }), [model, errorsOnly, rowsOnly]);
  const found = useMemo(() => gridFind(model, filtered, terms, data.index), [model, filtered, terms, data.index]);
  const shown = useMemo(() => (only ? onlyMatches(filtered, found) : filtered), [only, filtered, found]);
  return { data, model, filtered, found, shown };
}
