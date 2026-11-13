import { useEffect } from 'react';
import { Link, Navigate, useParams } from 'react-router';
import { useClient, useClientOverview } from '../../api/clientPage';
import { useMeta } from '../../api/meta';
import { errorStatus } from '../../lib/errors';
import ErrorBoundary from '../../ui/ErrorBoundary';
import InlineError from '../../ui/InlineError';
import Loading from '../../ui/Loading';
import { useDocWindowPresence } from '../../viewer/docWindowLink';
import ClientSidebar from './ClientSidebar';
import { clientPath, clientTabFor } from './clientTabs';
import ClientNotesTab from './notes/ClientNotesTab';
import ClientOverviewTab from './overview/ClientOverviewTab';

const TABS = { overview: ClientOverviewTab, notes: ClientNotesTab };
const LABELS = { overview: 'Overview', notes: 'Notes' };

function MissingClient() {
  return (
    <div className="bb-dash">
      <div className="bb-dash-header">
        <div>
          <div className="bb-title">This client does not exist.</div>
          <div className="bb-subtitle">The link may be wrong.</div>
        </div>
        <Link to="/?view=book" className="btn btn-primary bb-new-btn">
          Back to Clients
        </Link>
      </div>
    </div>
  );
}

/**
 * The client page (plan.md §8.5; CL13–CL23; old Vantage 891f1b3 `radar/ClientWorkspace.jsx`): the old client
 * workspace (`bb-workspace`) — its sidebar with the Plan year block, then one section at a time. The section is in the
 * path (`/clients/:clientId/:tab`); an unknown or unbuilt one opens the Overview. It reads deals' client detail and
 * the client's Overview, and says which client it is to a file's own window (E71). The page opens for every status
 * (§5.1), an archived client's too (M9).
 */
export default function ClientPage() {
  const { clientId, tab } = useParams();
  const validId = /^\d+$/.test(clientId || '');
  const client = useClient(validId ? clientId : null);
  const overview = useClientOverview(validId ? clientId : null);
  const meta = useMeta();
  const name = client.data?.name;
  // The client on screen, for a file's own window (E71): it covers itself once this tab leaves the client.
  useDocWindowPresence(name ? { key: `client:${clientId}`, name, dealId: null, year: '' } : null);

  useEffect(() => {
    if (name) document.title = `${name} — 2Vantage`;
  }, [name]);

  const shown = clientTabFor(tab);
  if (validId && shown !== tab) return <Navigate to={clientPath(clientId, shown)} replace />;
  if (!validId || (client.isError && errorStatus(client.error) === 404)) return <MissingClient />;
  const failed = [client, overview, meta].find((query) => query.isError);
  if (failed) {
    return (
      <InlineError
        title="Could not load this client."
        error={failed.error}
        onRetry={() => failed.refetch()}
        retrying={failed.isFetching}
      />
    );
  }
  if (client.isPending || overview.isPending || meta.isPending) return <Loading label="Loading the client…" />;

  const Tab = TABS[shown];
  return (
    <div className="bb-workspace">
      <ClientSidebar client={client.data} overview={overview.data} tab={shown} meta={meta.data} />
      <div className="bb-content">
        <section aria-label={LABELS[shown]}>
          <ErrorBoundary resetKey={shown}>
            <Tab client={client.data} overview={overview.data} meta={meta.data} />
          </ErrorBoundary>
        </section>
      </div>
    </div>
  );
}
