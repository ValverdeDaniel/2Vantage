import { errorStatus } from '../../lib/errors';
import InlineError from '../../ui/InlineError';
import ClientsTable from './ClientsTable';
import { pageWords } from './homeParams';
import Pager from './Pager';
import ProspectsTable from './ProspectsTable';

// The empty words (I125; plan.md §8.3), unchanged from the old home but for Clients, which §8.3 rewords.
const EMPTY = {
  prospects: 'No new business in flight — start one with “New deal”.',
  book: 'No clients yet — a prospect becomes a client when a plan is marked sold, or with Convert to client.',
};
const NO_MATCH = 'Nothing matches these filters.';

/** One page of the view's rows (25), with its empty words, the pager, and Try again when the page fails to load. */
export default function ClientList({ view, list, meta, page, filtered, ordering, onChange }) {
  if (list.isError && errorStatus(list.error) === 404 && page > 1) {
    return (
      <div className="empty-state">
        This page is empty.{' '}
        <button type="button" className="bnf-archived-link" onClick={() => onChange({ page: 1 })}>
          Go to page 1
        </button>
      </div>
    );
  }
  if (list.isError && !list.data) {
    return (
      <InlineError
        title="Could not load the list."
        error={list.error}
        onRetry={() => list.refetch()}
        retrying={list.isFetching}
      />
    );
  }

  const { results, count } = list.data;
  const Table = view === 'book' ? ClientsTable : ProspectsTable;
  const sort = (next) => onChange({ ordering: next });
  return (
    <>
      <Table rows={results} meta={meta} ordering={ordering} onSort={sort}>
        {results.length === 0 && <div className="empty-state">{filtered ? NO_MATCH : EMPTY[view]}</div>}
      </Table>
      <Pager words={pageWords(page, count)} onPage={(next) => onChange({ page: next })} />
    </>
  );
}
