import { useDealActivity } from '../../api/deals';
import { formatDateTime, formatWhen } from '../../lib/format';
import Button from '../../ui/Button';
import Drawer from '../../ui/Drawer';
import EmptyState from '../../ui/EmptyState';
import InlineError from '../../ui/InlineError';
import Skeleton from '../../ui/Skeleton';
import styles from './ActivityDrawer.module.css';

// Mounted only while the drawer is open, so the log is fetched fresh on every open.
function ActivityList({ dealId }) {
  const activity = useDealActivity(dealId);
  if (activity.isPending) return <Skeleton lines={6} height="32px" label="Loading activity…" />;
  if (activity.isError) {
    return (
      <InlineError
        title="Could not load activity."
        error={activity.error}
        onRetry={() => activity.refetch()}
        retrying={activity.isFetching}
      />
    );
  }
  const rows = activity.data.pages.flatMap((page) => page.results);
  if (rows.length === 0) {
    return (
      <EmptyState compact title="No activity yet.">
        Changes to this deal will be listed here.
      </EmptyState>
    );
  }
  return (
    <>
      <ol className={styles.list}>
        {rows.map((row) => (
          <li key={row.id} className={styles.item}>
            <p className={styles.summary}>{row.summary}</p>
            <p className={styles.meta}>
              {row.actor} ·{' '}
              <time dateTime={row.at} title={formatDateTime(row.at)}>
                {formatWhen(row.at)}
              </time>
            </p>
          </li>
        ))}
      </ol>
      {activity.isFetchNextPageError && (
        <InlineError compact title="Could not load more." error={activity.error} />
      )}
      {activity.hasNextPage && (
        <Button
          size="sm"
          className={styles.more}
          onClick={() => activity.fetchNextPage()}
          busy={activity.isFetchingNextPage}
        >
          Show more
        </Button>
      )}
    </>
  );
}

/** Who changed what on this deal, newest first (GET deals/{id}/activity/). */
export default function ActivityDrawer({ dealId, open, onClose }) {
  return (
    <Drawer open={open} onClose={onClose} title="Activity">
      <ActivityList dealId={dealId} />
    </Drawer>
  );
}
