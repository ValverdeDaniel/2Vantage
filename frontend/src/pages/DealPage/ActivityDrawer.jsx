import { useDealActivity, useRevertActivity } from '../../api/deals';
import { formatDate, formatDateTime, formatWhen } from '../../lib/format';
import Drawer from '../../ui/Drawer';
import InlineError from '../../ui/InlineError';
import Loading from '../../ui/Loading';

function When({ at }) {
  return (
    <time dateTime={at} title={formatDateTime(at)}>
      {formatWhen(at)}
    </time>
  );
}

// One row, in the old Overview activity feed's look (bnf-ov-event). "Revert this change" shows where the server says
// the row can be reverted (A34); a refusal (409) shows its sentence under the row, as the server wrote it.
function ActivityRow({ row, revert }) {
  const mine = revert.variables === row.id;
  return (
    <li className="bnf-cal-row bnf-ov-event">
      <div className="bnf-cal-date bb-mono">{formatDate(row.at)}</div>
      <div className={`bnf-cal-dot ${row.reverted ? 'bnf-ov-dot-warn' : 'bnf-ov-dot-info'}`} aria-hidden="true" />
      <div className="bnf-cal-main">
        <span className="bnf-cal-label">{row.summary}</span>
        <span className="bnf-agenda-detail">
          {row.actor} · <When at={row.at} />
        </span>
        {row.reverted && (
          <span className="bnf-agenda-detail">
            Reverted{row.reverted.by ? ` by ${row.reverted.by.name}` : ''} · <When at={row.reverted.at} />
          </span>
        )}
        {mine && revert.isError && <InlineError compact title="Not reverted." error={revert.error} />}
      </div>
      {row.can_revert ? (
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          disabled={revert.isPending}
          aria-busy={(mine && revert.isPending) || undefined}
          onClick={() => revert.mutate(row.id)}
        >
          Revert this change
        </button>
      ) : (
        <span />
      )}
    </li>
  );
}

// Mounted only while the drawer is open, so the log is fetched fresh on every open.
function ActivityList({ dealId }) {
  const activity = useDealActivity(dealId);
  const revert = useRevertActivity(dealId);
  if (activity.isPending) return <Loading label="Loading activity…" />;
  if (activity.isError) {
    return (
      <InlineError
        compact
        title="Could not load activity."
        error={activity.error}
        onRetry={() => activity.refetch()}
        retrying={activity.isFetching}
      />
    );
  }
  const rows = activity.data.pages.flatMap((page) => page.results);
  if (rows.length === 0) return <div className="bb-subtitle">Nothing has happened on this deal yet.</div>;
  return (
    <>
      <ol className="bnf-ov-timeline">
        {rows.map((row) => (
          <ActivityRow key={row.id} row={row} revert={revert} />
        ))}
      </ol>
      {activity.isFetchNextPageError && <InlineError compact title="Could not load more." error={activity.error} />}
      {activity.hasNextPage && (
        <button
          type="button"
          className="btn btn-secondary btn-sm bnf-ov-showall"
          disabled={activity.isFetchingNextPage}
          onClick={() => activity.fetchNextPage()}
        >
          Show more
        </button>
      )}
    </>
  );
}

/** Who changed what on this deal, newest first (GET deals/{id}/activity/), with Revert (POST activity/{id}/revert/). */
export default function ActivityDrawer({ dealId, open, onClose }) {
  return (
    <Drawer open={open} onClose={onClose} title="Activity" sub="Every touch on this deal, newest first.">
      <ActivityList dealId={dealId} />
    </Drawer>
  );
}
