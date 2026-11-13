import { errorStatus } from '../../lib/errors';
import InlineError from '../../ui/InlineError';
import ClientsTable from './ClientsTable';
import { pageWords } from './homeParams';
import Pager from './Pager';

// The empty words (plan.md §8.3, which rewords the old book's for the client status).
const EMPTY = 'No clients yet — a prospect becomes a client when a plan is marked sold, or with Convert to client.';
const NO_MATCH = 'Nothing matches these filters.';

/** One page of Clients (25), with its empty words, the pager, and Try again when the page fails to load. Prospects and
 *  the Work queue list the work feed instead (FeedView, slice 61). */
export default function ClientList({ list, meta, page, filtered, ordering, onChange, nextByDeal }) {
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
  const sort = (next) => onChange({ ordering: next });
  return (
    <>
      <ClientsTable rows={results} meta={meta} ordering={ordering} onSort={sort} nextByDeal={nextByDeal}>
        {results.length === 0 && <div className="empty-state">{filtered ? NO_MATCH : EMPTY}</div>}
      </ClientsTable>
      <Pager words={pageWords(page, count)} onPage={(next) => onChange({ page: next })} />
    </>
  );
}
