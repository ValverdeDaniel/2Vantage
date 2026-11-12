import { useState } from 'react';
import { useDealActivity, useRevertActivity } from '../../api/deals';
import { errorText } from '../../lib/errors';
import { formatTime, formatUpdated } from '../../lib/format';
import { useToast } from '../../ui/useToast';
import { groupRows, groupSummary, rowIcon, WINDOW_MINUTES } from './historyGroups';

/*
 * The station's Change history (plan.md §8.16; E73, E74; the old ChangeHistoryCard): who changed what on this deal,
 * newest first, grouped by person into spans of at most 30 minutes, over the deal's Activity rows (no downloads or
 * views, §3.8). ↻ Refresh and "Show older ▾" page the feed; ↶ Revert puts one row back (a review's marks, a file's
 * kind, an edit) through POST activity/{id}/revert/, which refuses in words. Rows name files by their id's file, never
 * a file name in the log itself (§3.8). The old version rail and its diffs are dropped (E72).
 */

const KIND_ICON = { user: '✎', client: '👤', claude: '✦', system: '⚙' };

function spanLabel(start, end) {
  const a = formatTime(start);
  const b = formatTime(end);
  return a === b ? a : `${a}–${b}`;
}

function Line({ row, fileName }) {
  return (
    <span>
      <span className="hst-verb">{row.summary}</span>
      {row.document_id && fileName(row.document_id) && <span className="hst-muted"> · “{fileName(row.document_id)}”</span>}
      {row.reverted && (
        <span className="hst-muted">
          {' '}
          · reverted{row.reverted.by ? ` by ${row.reverted.by.name}` : ''} · {formatUpdated(row.reverted.at)}
        </span>
      )}
    </span>
  );
}

export default function HistoryCard({ dealId, fileName }) {
  const toast = useToast();
  const feed = useDealActivity(dealId);
  const revert = useRevertActivity(dealId);
  const [open, setOpen] = useState(() => new Set([0]));
  const rows = feed.data?.pages.flatMap((page) => page.results) ?? [];
  const groups = groupRows(rows);

  const toggle = (index) =>
    setOpen((now) => {
      const next = new Set(now);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });

  async function undo(row) {
    if (!window.confirm(`Revert: put back what “${row.summary}” changed?`)) return;
    try {
      await revert.mutateAsync(row.id);
      toast.success(`Reverted — ${row.summary}`);
    } catch (error) {
      toast.error(errorText(error));
    }
  }

  return (
    <section className="bb-panel hst-card" data-history-card>
      <div className="hst-head">
        <div>
          <div className="bb-panel-title">Change history</div>
          <div className="hst-sub">
            Who changed what on this deal, newest first. Each person’s changes within {WINDOW_MINUTES} minutes are
            grouped together.
          </div>
        </div>
        <button type="button" className="bnf-linklike" onClick={() => feed.refetch()} disabled={feed.isFetching}>
          {feed.isFetching ? 'Loading…' : '↻ Refresh'}
        </button>
      </div>
      {feed.isError && <div className="hst-empty">Could not load the history.</div>}
      {feed.isSuccess && !groups.length && (
        <div className="hst-empty">Nothing yet. Uploads, scans, edits and client answers appear here as they happen.</div>
      )}
      <ol className="hst-groups">
        {groups.map((group, index) => {
          const shown = open.has(index);
          return (
            <li key={`${group.end}-${group.items[0].id}`} className="hst-group">
              <button type="button" className="hst-group-head" aria-expanded={shown} onClick={() => toggle(index)}>
                <span className="hst-caret">{shown ? '▾' : '▸'}</span>
                <span className={`hst-who hst-who-${group.kind}`}>
                  {KIND_ICON[group.kind] || '·'} {group.actor || 'Unknown'}
                </span>
                <span className="hst-when">
                  {formatUpdated(group.end).replace(/ .*$/, '')} · {spanLabel(group.start, group.end)}
                </span>
                <span className="hst-summary">{groupSummary(group)}</span>
              </button>
              {shown && (
                <ul className="hst-items">
                  {group.items.map((row) => (
                    <li key={row.id} className="hst-item" data-activity={row.id}>
                      <span className="hst-time">{formatTime(row.at)}</span>
                      <span className="hst-icon">{rowIcon(row)}</span>
                      <span className="hst-text">
                        <Line row={row} fileName={fileName} />
                      </span>
                      {row.can_revert && !row.reverted && (
                        <button
                          type="button"
                          className="bnf-linklike hst-diff-btn"
                          disabled={revert.isPending}
                          onClick={() => undo(row)}
                          title="Put back exactly what this change changed"
                        >
                          {revert.isPending && revert.variables === row.id ? 'Reverting…' : '↶ Revert'}
                        </button>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </li>
          );
        })}
      </ol>
      {feed.hasNextPage && (
        <div className="hst-more">
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => feed.fetchNextPage()}
            disabled={feed.isFetchingNextPage}
          >
            Show older ▾
          </button>
        </div>
      )}
    </section>
  );
}
