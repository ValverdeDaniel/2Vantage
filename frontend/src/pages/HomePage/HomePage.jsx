import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router';
import { useClients } from '../../api/deals';
import { clientStatuses, creatableStatuses, PROSPECT, useMeta } from '../../api/meta';
import InlineError from '../../ui/InlineError';
import Loading from '../../ui/Loading';
import ClientList from './ClientList';
import HomeHeader from './HomeHeader';
import { changeHome, listQuery, readHome, viewParams } from './homeParams';
import HomeSearch from './HomeSearch';
import NewClientDialog from './NewClientDialog';
import ViewBar from './ViewBar';

/**
 * The Benefits home (plan.md §8.3; CasesDashboard.jsx at 891f1b3): the eyebrow, each view's header and stat card, the
 * view pill, the search and the list. Prospects (bare /, OQ95) lists Prospect clients; Clients (?view=book) lists New
 * and Existing clients with their chips (OQ101 c). Search runs on the server; the URL keeps the search and filters.
 */
export default function HomePage() {
  const [params, setParams] = useSearchParams();
  const meta = useMeta();
  const [creating, setCreating] = useState(null); // the status the New client dialog starts with
  const state = readHome(params);
  const statuses = clientStatuses(meta.data);
  const query = listQuery(state, { prospect: PROSPECT, statuses: statuses.map((s) => s.key) });
  const enabled = Boolean(meta.data);
  const list = useClients(query, { enabled });
  // The stat card counts the whole view, whatever the search or chip says.
  const everyone = useClients(
    { relationship: state.view === 'book' ? statuses.map((s) => s.key).join(',') : PROSPECT },
    { enabled, placeholderData: undefined },
  );

  useEffect(() => {
    document.title = `${state.view === 'book' ? 'Clients' : 'Prospects'} — 2Vantage`;
  }, [state.view]);

  const update = (changes, options) => setParams((current) => changeHome(current, changes), options);
  const existing = creatableStatuses(meta.data).find((s) => s.key !== PROSPECT)?.key;
  const navigate = useNavigate();
  // ＋ New deal opens the New deal page with its two mode cards (A14; slice 20); Clients' ＋ New client, the dialog.
  const startCreating = () => (state.view === 'book' ? setCreating(existing) : navigate('/deals/new'));

  let body;
  if (meta.isError) {
    body = <InlineError title="Could not load the lists." error={meta.error} onRetry={() => meta.refetch()} />;
  } else if (!meta.data || list.isPending) {
    body = <Loading />;
  } else {
    body = (
      <ClientList
        view={state.view}
        list={list}
        meta={meta.data}
        page={state.page}
        filtered={Boolean(state.q.trim() || state.status)}
        ordering={state.ordering}
        onChange={update}
      />
    );
  }

  return (
    <div className="bb-dash">
      <div className="bnf-benefits-topbar">
        <div className="bb-eyebrow">Benefits</div>
      </div>
      <HomeHeader view={state.view} count={everyone.data?.count} onCreate={startCreating} />
      <ViewBar
        view={state.view}
        onView={(view) => setParams(viewParams(view), { replace: true })}
        refreshing={list.isFetching && !list.isPending}
        failed={list.isError && Boolean(list.data)}
        onRetry={() => list.refetch()}
      />
      <HomeSearch
        key={state.view}
        view={state.view}
        q={state.q}
        status={state.status}
        statuses={statuses}
        onChange={update}
      />
      {body}
      {creating !== null && <NewClientDialog status={creating} onClose={() => setCreating(null)} />}
    </div>
  );
}
