import { useState } from 'react';
import { useFeed } from '../../../api/overview';
import { formatDate, formatDateTime } from '../../../lib/format';
import InlineError from '../../../ui/InlineError';
import Loading from '../../../ui/Loading';
import { activityLook } from './activityLook';

const SHOWN = 8; // rows before "Show all N" (old COLLAPSED)

function Event({ row }) {
  const look = activityLook(row.area, row.action, row.actor_kind === 'client');
  return (
    <div className="bnf-cal-row bnf-ov-event">
      <div className="bnf-cal-date bb-mono" title={formatDateTime(row.at)}>
        {formatDate(row.at)}
      </div>
      <div className={`bnf-cal-dot bnf-ov-dot-${look.tone}`} aria-hidden="true" />
      <div className="bnf-cal-main">
        <span className="bnf-cal-label">
          <span className="bnf-ov-event-icon" aria-hidden="true">
            {look.icon}
          </span>
          {row.summary}
        </span>
        {row.detail && <span className="bnf-agenda-detail">{row.detail}</span>}
      </div>
      {row.actor && <span className="bb-drop-meta bnf-ov-actor">{row.actor}</span>}
    </div>
  );
}

/**
 * The Timeline (plan.md §8.6; M70, M71; old Vantage 891f1b3 `ActivityFeed.jsx`): the Activity card — its title and
 * sub, whatever the page puts above the rows (`children`: the Overview's outreach strip and "Who we've asked"), then
 * every touch, newest first, with its tone, icon, words, detail and who: eight at first, Show all N, then Show more a
 * page (25) at a time, and Show less. Shared: the deal's Overview mounts it with `dealId`; another page passes `path`
 * and `queryKey` for a feed of the same shape (the client page's, slice 67) and its own words.
 */
export default function Timeline({
  dealId,
  path,
  queryKey,
  title = 'Activity',
  sub = 'Every touch on this deal, newest first.',
  emptyText = 'Nothing has happened on this deal yet.',
  children = null,
}) {
  const [expanded, setExpanded] = useState(false);
  const feed = useFeed({ dealId, path, queryKey });
  const pages = feed.data?.pages || [];
  const rows = pages.flatMap((page) => page.results);
  const total = pages[0]?.count ?? 0;
  const shown = expanded ? rows : rows.slice(0, SHOWN);

  return (
    <div className="bb-panel bnf-ov-activity">
      <div className="bb-panel-title">{title}</div>
      <div className="bb-panel-sub">{sub}</div>
      {children}
      {feed.isPending && <Loading label="Loading activity…" />}
      {feed.isError && (
        <InlineError compact title="Could not load activity." error={feed.error} onRetry={() => feed.refetch()} />
      )}
      {feed.isSuccess && rows.length === 0 && <div className="bb-subtitle">{emptyText}</div>}
      <div className="bnf-ov-timeline">
        {shown.map((row) => (
          <Event key={row.id} row={row} />
        ))}
      </div>
      {expanded && feed.hasNextPage && (
        <button
          type="button"
          className="bnf-override-link bnf-ov-showall"
          disabled={feed.isFetchingNextPage}
          onClick={() => feed.fetchNextPage()}
        >
          Show more
        </button>
      )}
      {total > SHOWN && (
        <button type="button" className="bnf-override-link bnf-ov-showall" onClick={() => setExpanded(!expanded)}>
          {expanded ? 'Show less' : `Show all ${total}`}
        </button>
      )}
    </div>
  );
}
