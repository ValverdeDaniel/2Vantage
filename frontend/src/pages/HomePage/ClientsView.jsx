import { useMemo, useState } from 'react';
import { useWorkQueue } from '../../api/agenda';
import { useClients } from '../../api/deals';
import { clientStatuses, creatableStatuses, PROSPECT } from '../../api/meta';
import InlineError from '../../ui/InlineError';
import Loading from '../../ui/Loading';
import ClientList from './ClientList';
import HomeHeader from './HomeHeader';
import { changeHome, listQuery } from './homeParams';
import HomeSearch from './HomeSearch';
import NewClientDialog from './NewClientDialog';
import ViewBar from './ViewBar';

/**
 * Clients (`?view=book`; CL12, A13; plan.md §8.3): New and Existing clients in the old book's look, searched on the
 * server 250 ms after typing stops, with the Status chips, 25 rows a page and the URL keeping it all. Next action is
 * each client's deal's next step from the work feed (slice 61), finished deals included, so a won client shows its
 * commission step, or "Sold" (I122 as changed by OQ101 c; OQ91). ＋ New client opens the dialog preset to Existing.
 */
export default function ClientsView({ state, meta, setParams, onView }) {
  const [creating, setCreating] = useState(null);
  const statuses = clientStatuses(meta.data);
  const enabled = Boolean(meta.data);
  const list = useClients(listQuery(state, { prospect: PROSPECT, statuses: statuses.map((s) => s.key) }), { enabled });
  // The stat card counts the whole view, whatever the search or chip says.
  const everyone = useClients(
    { relationship: statuses.map((s) => s.key).join(',') },
    { enabled, placeholderData: undefined },
  );
  const feed = useWorkQueue({ closed: true, enabled });
  const nextByDeal = useMemo(() => {
    const found = {};
    (feed.data?.rows || []).forEach((row) => {
      if (row.kind === 'deal') found[row.deal_id] = row;
    });
    return found;
  }, [feed.data]);
  const update = (changes, options) => setParams((current) => changeHome(current, changes), options);
  const existing = creatableStatuses(meta.data).find((s) => s.key !== PROSPECT)?.key;

  let body;
  if (meta.isError) {
    body = <InlineError title="Could not load the lists." error={meta.error} onRetry={() => meta.refetch()} />;
  } else if (!meta.data || list.isPending) {
    body = <Loading />;
  } else {
    body = (
      <ClientList
        list={list}
        meta={meta.data}
        page={state.page}
        filtered={Boolean(state.q.trim() || state.status)}
        ordering={state.ordering}
        onChange={update}
        nextByDeal={nextByDeal}
      />
    );
  }

  return (
    <>
      <HomeHeader view="book" count={everyone.data?.count} onCreate={() => setCreating(existing)} />
      <ViewBar
        view="book"
        onView={onView}
        refreshing={list.isFetching && !list.isPending}
        failed={list.isError && Boolean(list.data)}
        onRetry={() => list.refetch()}
      />
      <HomeSearch view="book" q={state.q} status={state.status} statuses={statuses} onChange={update} />
      {body}
      {creating !== null && <NewClientDialog status={creating} onClose={() => setCreating(null)} />}
    </>
  );
}
