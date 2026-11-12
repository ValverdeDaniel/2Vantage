import { Suspense, useEffect } from 'react';
import { Link, Navigate, useParams } from 'react-router';
import { useDeal } from '../../api/deals';
import { useMeta } from '../../api/meta';
import { claudeRoom, WorkWithClaude } from '../../deal/claude';
import { errorStatus } from '../../lib/errors';
import { dealPresence, useDocWindowPresence } from '../../viewer/docWindowLink';
import ErrorBoundary from '../../ui/ErrorBoundary';
import InlineError from '../../ui/InlineError';
import Loading from '../../ui/Loading';
import BookingSlot from './BookingSlot';
import DealHeader from './DealHeader';
import DealSidebar from './DealSidebar';
import { tabFor, tabLabel } from './nav';
import { BUILT_TABS, TAB_COMPONENTS } from './tabs';
import useWarmTabs from './useWarmTabs';

function MissingDeal() {
  return (
    <div className="bb-dash">
      <div className="bb-dash-header">
        <div>
          <div className="bb-title">This deal does not exist.</div>
          <div className="bb-subtitle">It may have been deleted, or the link may be wrong.</div>
        </div>
        <Link to="/" className="btn btn-primary bb-new-btn">
          Back to Benefits
        </Link>
      </div>
    </div>
  );
}

/**
 * DealShell (A20, A21, A26; plan.md §8.4): the old deal workspace (`bb-workspace`) with its sidebar, then the header
 * strip and the open tab. The tab is in the path; only its code and data load, switching tabs never reloads the
 * header, and each tab has its own error boundary, so a failing tab leaves the sidebar and the other tabs working.
 */
export default function DealPage() {
  const { dealId, tab } = useParams();
  const validId = /^\d+$/.test(dealId || '');
  const header = useDeal(validId ? dealId : null);
  const meta = useMeta();
  const clientName = header.data?.client.name;
  // The client on screen, for a file's own window (E71): it covers itself when this tab leaves the client.
  useDocWindowPresence(dealPresence(header.data));
  useWarmTabs(header.data?.id); // the RFP payload, once the browser is idle (K3)

  useEffect(() => {
    if (clientName) document.title = `${clientName} — 2Vantage`;
  }, [clientName]);

  const shown = tabFor(tab, BUILT_TABS);
  if (validId && shown !== tab) return <Navigate to={`/deals/${dealId}/${shown}`} replace />;
  if (!validId || (header.isError && errorStatus(header.error) === 404)) return <MissingDeal />;
  if (header.isError || meta.isError) {
    const failed = header.isError ? header : meta;
    return (
      <InlineError
        title="Could not load this deal."
        error={failed.error}
        onRetry={() => failed.refetch()}
        retrying={failed.isFetching}
      />
    );
  }
  if (header.isPending || meta.isPending) return <Loading label="Loading the deal…" />;

  const deal = header.data;
  const Tab = TAB_COMPONENTS[shown];
  const label = tabLabel(shown);
  return (
    <div className={`bb-workspace${claudeRoom(shown) ? ' bnf-wwc-room' : ''}`}>
      <DealSidebar deal={deal} tab={shown} />
      <div className="bb-content">
        <DealHeader key={deal.id} deal={deal} meta={meta.data} />
        <WorkWithClaude deal={deal} tab={shown} />
        <BookingSlot deal={deal} />
        <section aria-label={label} className="bnf-claude-section">
          <ErrorBoundary resetKey={shown}>
            <Suspense fallback={<Loading label={`Loading the ${label}…`} />}>
              <Tab deal={deal} />
            </Suspense>
          </ErrorBoundary>
        </section>
      </div>
    </div>
  );
}
