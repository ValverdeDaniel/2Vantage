import { useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'react-router';
import { useClients } from '../../api/deals';
import { relationships, useMeta } from '../../api/meta';
import { errorStatus } from '../../lib/errors';
import Button from '../../ui/Button';
import cx from '../../ui/cx';
import EmptyState from '../../ui/EmptyState';
import InlineError from '../../ui/InlineError';
import Skeleton from '../../ui/Skeleton';
import Spinner from '../../ui/Spinner';
import TextInput from '../../ui/TextInput';
import ClientTable from './ClientTable';
import styles from './DashboardPage.module.css';
import NewClientDialog from './NewClientDialog';
import Pager from './Pager';

const PAGE_SIZE = 25;
const DEFAULT_ORDERING = '-last_activity';

// Typing updates the URL 250 ms after the last key; the box shows the URL's text otherwise (so Back restores it).
function SearchBox({ value, onCommit }) {
  const [draft, setDraft] = useState(null);
  const timer = useRef(null);
  useEffect(() => () => clearTimeout(timer.current), []);
  return (
    <TextInput
      type="search"
      className={styles.search}
      aria-label="Search clients"
      placeholder="Search clients…"
      value={draft ?? value}
      onChange={(event) => {
        const text = event.target.value;
        setDraft(text);
        clearTimeout(timer.current);
        timer.current = setTimeout(() => {
          onCommit(text);
          setDraft(null);
        }, 250);
      }}
    />
  );
}

/** Clients (plan.md §8.3): server-side search, type chips, two sort orders, 25 per page; the URL keeps it all. */
export default function DashboardPage() {
  const [params, setParams] = useSearchParams();
  const meta = useMeta();
  const [creating, setCreating] = useState(false);
  const types = relationships(meta.data);

  const q = params.get('q') || '';
  const relationship = types.some((t) => t.key === params.get('relationship')) ? params.get('relationship') : '';
  const ordering = params.get('ordering') === 'name' ? 'name' : DEFAULT_ORDERING;
  const page = Math.max(1, Number.parseInt(params.get('page'), 10) || 1);
  const clients = useClients({
    q: q.trim(),
    relationship,
    ordering: ordering === DEFAULT_ORDERING ? '' : ordering,
    page: page > 1 ? page : '',
  });

  useEffect(() => {
    document.title = 'Clients — 2Vantage';
  }, []);

  // Changes the URL; any change other than the page goes back to page 1. Defaults are left out of the URL.
  function update(changes, { replace = false } = {}) {
    setParams(
      (current) => {
        const next = new URLSearchParams(current);
        for (const [key, value] of Object.entries(changes)) {
          if (value === '' || value == null) next.delete(key);
          else next.set(key, String(value));
        }
        if (!('page' in changes)) next.delete('page');
        return next;
      },
      { replace },
    );
  }

  const newClientButton = (
    <Button variant="primary" onClick={() => setCreating(true)}>
      + New client
    </Button>
  );

  let body;
  if (clients.isPending) {
    body = <Skeleton lines={8} height="30px" label="Loading clients…" />;
  } else if (clients.isError && errorStatus(clients.error) === 404 && page > 1) {
    body = (
      <EmptyState title="This page is empty." action={<Button onClick={() => update({ page: '' })}>Go to page 1</Button>} />
    );
  } else if (clients.isError) {
    body = (
      <InlineError
        title="Could not load clients."
        error={clients.error}
        onRetry={() => clients.refetch()}
        retrying={clients.isFetching}
      />
    );
  } else if (clients.data.count === 0) {
    if (q.trim()) {
      body = (
        <EmptyState
          title={`No clients match "${q.trim()}".`}
          action={<Button onClick={() => update({ q: '' })}>Clear search</Button>}
        />
      );
    } else if (relationship) {
      const label = types.find((t) => t.key === relationship)?.label.toLowerCase();
      body = (
        <EmptyState
          title={`No ${label} clients.`}
          action={<Button onClick={() => update({ relationship: '' })}>Show all clients</Button>}
        />
      );
    } else {
      body = <EmptyState title="No clients yet." action={newClientButton} />;
    }
  } else {
    body = (
      <>
        <ClientTable
          rows={clients.data.results}
          meta={meta.data}
          ordering={ordering}
          onSort={(next) => update({ ordering: next === DEFAULT_ORDERING ? '' : next })}
        />
        <Pager page={page} count={clients.data.count} pageSize={PAGE_SIZE} onPage={(p) => update({ page: p > 1 ? p : '' })} />
      </>
    );
  }

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1>Clients</h1>
        {clients.isFetching && !clients.isPending && (
          <span className={styles.updating}>
            <Spinner size="sm" label="" /> Updating…
          </span>
        )}
        <div className={styles.headerAction}>{newClientButton}</div>
      </div>

      <div className={styles.toolbar}>
        <SearchBox value={q} onCommit={(text) => update({ q: text }, { replace: true })} />
        <div role="group" aria-label="Client type" className={styles.chips}>
          {[{ key: '', label: 'All' }, ...types].map((type) => (
            <button
              key={type.key || 'all'}
              type="button"
              aria-pressed={relationship === type.key}
              className={cx(styles.chip, relationship === type.key && styles.chipOn)}
              onClick={() => update({ relationship: type.key })}
            >
              {relationship === type.key && <span aria-hidden="true">✓ </span>}
              {type.label}
            </button>
          ))}
        </div>
      </div>

      {body}

      {creating && <NewClientDialog onClose={() => setCreating(false)} />}
    </div>
  );
}
