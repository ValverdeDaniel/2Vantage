import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router';
import { useQueueStats, useWorkQueue } from '../../api/agenda';
import InlineError from '../../ui/InlineError';
import Loading from '../../ui/Loading';
import HomeHeader from './HomeHeader';
import {
  dueCards,
  filterProspects,
  filterQueue,
  isHeld,
  isProspectRow,
  NO_FILTERS,
  onePerClient,
  queueView,
  responsesFirst,
  responseTotals,
  nextSort,
  sortRows,
} from './homeRows';
import ProspectsTable from './ProspectsTable';
import QueueFilters from './QueueFilters';
import { ProspectCards, QueueCards } from './StatCards';
import ViewBar from './ViewBar';
import WorkQueueTable from './WorkQueueTable';

const NO_ROWS = [];
// "Responses first" (D-159) is an order, not a filter: remembered per browser, off until someone turns it on (I79).
const RESPONSES_FIRST_KEY = 'vantage.benefits.responsesFirst';

function readResponsesFirst() {
  try {
    return window.localStorage.getItem(RESPONSES_FIRST_KEY) === '1';
  } catch {
    return false;
  }
}

const EMPTY = {
  prospects: 'No new business in flight — start one with “New deal”.',
  queue: 'Nothing in the queue — start one with “New deal”.',
};
const NO_MATCH = 'Nothing matches these filters.';

/**
 * Prospects (the landing view; I86, CL11) and the Work queue (`?view=queue`; I70–I85) over the one work feed (old
 * CasesDashboard.jsx at 891f1b3): the header and its cards, the view pill, the filters (kept while switching between
 * the two, as the old values were), and the table. Finished and lost deals are fetched only when the Sold or Lost stage
 * or a client search asks (I80). The feed refetches on every visit and stays on screen behind the Refreshing… chip.
 */
export default function FeedView({ view, steps, onSteps, meta, onView }) {
  const navigate = useNavigate();
  const [filters, setFilters] = useState(NO_FILTERS);
  const [showLater, setShowLater] = useState(false);
  const [lift, setLiftState] = useState(readResponsesFirst);
  const [sort, setSort] = useState({ key: 'due', dir: 'asc' });
  const isQueue = view === 'queue';
  const closed = filters.stage === 'sold' || filters.stage === 'lost' || Boolean(filters.selectedClient);
  const feed = useWorkQueue({ closed });
  const stats = useQueueStats({ enabled: isQueue });
  const items = feed.data?.rows || NO_ROWS;
  const today = feed.data?.today || '';
  const buckets = meta.agenda?.queue?.due;
  const loading = !feed.data;

  const setLift = (on) => {
    setLiftState(on);
    try {
      window.localStorage.setItem(RESPONSES_FIRST_KEY, on ? '1' : '0');
    } catch {
      /* private mode: the toggle still works for this visit */
    }
  };
  const showResponses = () => {
    setLift(true);
    document.querySelector('.bb-transfers-card')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  const filteredQueue = useMemo(() => filterQueue(items, filters, buckets), [items, filters, buckets]);
  const rows = useMemo(() => {
    if (!isQueue) return onePerClient(filterProspects(items, filters, buckets));
    return queueView(filteredQueue, { steps, showLater, today });
  }, [isQueue, items, filters, buckets, filteredQueue, steps, showLater, today]);
  const heldCount = useMemo(
    () => queueView(filteredQueue, { steps, showLater: true, today }).filter((row) => isHeld(row, today)).length,
    [filteredQueue, steps, today],
  );
  const sorted = useMemo(() => {
    const byColumn = sortRows(rows, sort);
    return lift ? responsesFirst(byColumn) : byColumn;
  }, [rows, sort, lift]);

  // The cards count what is open, whatever the filters say (I82, I85).
  const open = items.filter((row) => row.kind === 'deal' && !row.finished && !row.lost);
  const responses = responseTotals(isQueue ? open : open.filter(isProspectRow));
  const due = dueCards(queueView(items, { steps, today }), buckets);
  const clientNames = useMemo(() => {
    const source = isQueue ? items : items.filter(isProspectRow);
    return [...new Set(source.map((row) => row.client_name))].sort((a, b) => a.localeCompare(b));
  }, [items, isQueue]);
  const filtered =
    filters.due !== 'all' || filters.owner !== 'all' || filters.stage !== 'all' || filters.selectedClient;
  const anyOpen = isQueue ? items.length > 0 : open.some(isProspectRow);

  const cards = isQueue ? (
    <QueueCards due={due} stats={stats.data} loading={loading} responses={responses} onShowResponses={showResponses} />
  ) : (
    <ProspectCards cards={feed.data?.cards} loading={loading} responses={responses} onShowResponses={showResponses} />
  );

  let body;
  if (feed.isError && !feed.data) {
    body = <InlineError title="Could not load the list." error={feed.error} onRetry={() => feed.refetch()} />;
  } else if (loading) {
    body = <Loading />;
  } else {
    const emptyText = anyOpen || filtered ? NO_MATCH : EMPTY[view];
    const tableProps = { rows: sorted, meta, sort, onSort: (key) => setSort(nextSort(sort, key)), emptyText };
    body = (
      <>
        <QueueFilters
          mode={view}
          meta={meta}
          filters={filters}
          onChange={(patch) => setFilters((current) => ({ ...current, ...patch }))}
          onClear={() => setFilters(NO_FILTERS)}
          owners={feed.data.owners}
          clientNames={clientNames}
          liftResponses={lift}
          onLiftResponses={setLift}
          waitingCount={responses.deals}
        />
        {isQueue ? (
          <WorkQueueTable {...tableProps} mode={{ steps, onSteps, showLater, onShowLater: setShowLater, heldCount }} />
        ) : (
          <ProspectsTable {...tableProps} />
        )}
      </>
    );
  }

  return (
    <>
      <HomeHeader view={view} onCreate={() => navigate('/deals/new')}>
        {cards}
      </HomeHeader>
      <ViewBar
        view={view}
        onView={onView}
        refreshing={feed.isFetching && Boolean(feed.data)}
        failed={feed.isError && Boolean(feed.data)}
        onRetry={() => feed.refetch()}
      />
      {body}
    </>
  );
}
