import { useState } from 'react';
import { useCensus } from '../../api/census';
import InlineError from '../../ui/InlineError';
import Roster from './Roster';

/*
 * The roster beside a census file on Documents (plan.md §8.16; E43, D130; OQ97's default: the full roster, not only
 * the review list; slice 65): the Census tab's own grid, paged on the server, with ✎ Edit, ☑ Select cells, the
 * review bar, the line chips and the pager. A cell's ↗ opens it where the file prints it, in the viewer above. The
 * COBRA tick, the import door and the counts the pricing reads stay on the Census tab (Roster's `beside`). An empty
 * roster says so in the old station's words.
 */
export default function RosterBeside({ deal, meta }) {
  const [page, setPage] = useState(1);
  const census = useCensus(deal.id, { page });
  if (census.isPending) return <div className="bb-subtitle bb-mt">Loading the census…</div>;
  if (census.isError) {
    return <InlineError compact title="Could not load the census." error={census.error} onRetry={() => census.refetch()} />;
  }
  const { summary } = census.data;
  if (summary.employees + summary.dependents === 0) {
    return (
      <div className="bb-subtitle bb-mt">No census roster yet — map this file from the Census tab to build the grid.</div>
    );
  }
  return (
    <div className="bb-mt" data-roster-beside>
      <div className="bb-subtitle">
        {summary.employees} employees · {summary.dependents} dependents · the whole roster, as on the Census tab. ↗ on a
        cell shows it in the file.
      </div>
      <Roster
        deal={deal}
        meta={meta}
        census={census.data}
        onPage={setPage}
        onReview={() => {}}
        refetch={() => census.refetch()}
        beside
      />
    </div>
  );
}
