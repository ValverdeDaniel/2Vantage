import { useEffect, useImperativeHandle, useRef, useState } from 'react';
import cx from '../ui/cx';
import { HotkeyLegend, ReviewDone } from './HotkeyLegend';
import { listShown } from './listFind';
import ReviewListRow from './ReviewListRow';

/*
 * A file's values, worst first, beside the file (plan.md §8.16, §10.7; E56–E58, D121, D122, D124; the old
 * FileReviewList). The owner buckets, orders, counts and pages on the server (200 a page, "Show more"); this draws:
 * - the bucket chips, each with its open count and its words on hover (E57: "N done" counts what a person dealt with);
 * - the bulk bar: exactly the rows shown (named, with their count) take ✓ Approve, Ignore or ⚑ Needs checking, one
 *   undoable action (E58), and "Check this file" runs the locator (E59);
 * - the keys' legend with the last action and its ↶ Undo (E54, D124);
 * - the rows: a click or ↑/↓ (J/K) selects, never moving the file; F, Enter or a double-click opens the value in the
 *   file; A, I, C and U come from the tab's keys through `act` (ref). After an action the selection keeps its place.
 * - Find (E63, D127): `find` = {hits (refs, in this order), current, only, nonce, words} marks the loaded rows that
 *   match; a step selects the current one, and "Only matches" lists just those, so the bulk bar acts on them.
 * - Review mode (D-201, E65): a click opens the value in the file at once and the arrows follow a beat later
 *   (`onFollow`); the List has no editor, so E or a double-click hands the value to the Grid (`onEdit`).
 */
export default function ReviewList({
  ref,
  rows,
  head,
  buckets,
  filter,
  onFilter,
  scopeWords,
  valueOf,
  fileOf,
  activeRef,
  onOpen,
  onMark,
  onMarkOne,
  busy,
  done,
  onUndo,
  undoing,
  more,
  check,
  recheck = null,
  find = null,
  review = false,
  onFollow = null,
  onEdit = null,
}) {
  const listRef = useRef(null);
  // The selected row follows its value while it is listed; once an action moves it out of the filter, the selection
  // keeps its place in the list, so nothing jumps under the reader.
  const hits = find?.hits ?? [];
  const visible = listShown(rows, hits, find?.only);
  const matched = new Set(hits);
  const [pick, setPick] = useState({ ref: null, place: -1 });
  // Find's step (or its first match, as the words settle) selects that row.
  const findSig = find?.current ? `${find.current}~${find.nonce}` : '';
  const [seenFind, setSeenFind] = useState('');
  if (findSig !== seenFind) {
    setSeenFind(findSig);
    const place = visible.findIndex((row) => row.ref === find?.current);
    if (place >= 0) setPick({ ref: find.current, place });
  }
  const found = visible.findIndex((row) => row.ref === pick.ref);
  const at = found >= 0 ? found : pick.place >= 0 && visible.length ? Math.min(pick.place, visible.length - 1) : -1;
  const selected = at >= 0 ? visible[at].ref : null;
  const choose = (index) => setPick({ ref: visible[index].ref, place: index });
  const byKey = Object.fromEntries(buckets.map((bucket) => [bucket.key, bucket]));
  const counts = head?.counts ?? {};
  const all = head?.all ?? { open: 0, done: 0 };

  useEffect(() => {
    listRef.current?.querySelector('.bnf-frl-row.is-active')?.scrollIntoView?.({ block: 'nearest' });
  }, [selected, find?.nonce]);

  const move = (step) => {
    if (!visible.length) return;
    const next = at < 0 ? 0 : Math.min(visible.length - 1, Math.max(0, at + step));
    choose(next);
    if (review) onFollow?.(visible[next]);
  };

  useImperativeHandle(
    ref,
    () => ({
      /** A key from the tab: 'approve' | 'ignore' | 'check' | 'clear' | 'find'. False when nothing is selected. */
      act(action) {
        const row = at >= 0 ? visible[at] : null;
        if (!row) return false;
        if (action === 'find') onOpen(row);
        else if (action === 'edit') onEdit?.(row);
        else onMarkOne(action, row);
        return true;
      },
      focus: () => listRef.current?.focus(),
    }),
    [at, visible, onOpen, onEdit, onMarkOne],
  );

  const onKeyDown = (event) => {
    if (event.target !== listRef.current || event.metaKey || event.ctrlKey || event.altKey) return;
    const key = event.key;
    if (key === 'ArrowDown' || key === 'j' || key === 'ArrowUp' || key === 'k') {
      event.preventDefault();
      event.stopPropagation();
      move(key === 'ArrowDown' || key === 'j' ? 1 : -1);
    } else if (key === 'Enter' && at >= 0) {
      event.preventDefault();
      event.stopPropagation();
      onOpen(visible[at]);
    }
  };

  const narrowed = visible !== rows;
  const inBucket = filter ? ` in ${byKey[filter]?.label}` : '';
  const shownWord = narrowed
    ? `Matching “${find?.words ?? ''}”${inBucket}`
    : filter
      ? byKey[filter]?.label
      : `Every value from ${scopeWords}`;
  const total = head?.total ?? rows.length;
  const unchecked = counts.unchecked?.open ?? 0;
  return (
    <div className="bnf-frl" data-review-list>
      <div className="bnf-frl-filters" role="toolbar" aria-label="Filter these values">
        <button type="button" className={cx('bnf-frl-chip', !filter && 'is-on')} onClick={() => onFilter('')}>
          All <b>{all.open + all.done}</b>
          {all.done > 0 && ` · ✓ ${all.done} done`}
        </button>
        {buckets
          .filter((bucket) => counts[bucket.key])
          .map((bucket) => (
            <button
              key={bucket.key}
              type="button"
              title={`${bucket.help}${counts[bucket.key].done ? ` (${counts[bucket.key].done} done)` : ''}`}
              className={cx('bnf-frl-chip', `bnf-frl-tone-${bucket.tone}`, filter === bucket.key && 'is-on')}
              data-bucket={bucket.key}
              onClick={() => onFilter(bucket.key)}
            >
              {bucket.label} <b>{counts[bucket.key].open}</b>
            </button>
          ))}
      </div>
      <div className="bnf-frl-bulk">
        <span className="bnf-frl-bulk-what">
          {shownWord}: {narrowed ? visible.length : rows.length < total ? `${rows.length} of ${total} shown` : total}
        </span>
        <button
          type="button"
          className="btn btn-sm btn-secondary"
          disabled={Boolean(busy) || !visible.length}
          onClick={() => onMark('approve', visible)}
          title="Approve exactly the values listed: you looked, and they are right"
        >
          {busy === 'approve' ? 'Approving…' : `✓ Approve ${visible.length}`}
        </button>
        <button
          type="button"
          className="btn btn-sm btn-secondary"
          disabled={Boolean(busy) || !visible.length}
          onClick={() => onMark('ignore', visible)}
          title="Ignore the AI's warning on exactly the values listed"
        >
          {busy === 'ignore' ? 'Saving…' : 'Ignore'}
        </button>
        <button
          type="button"
          className="btn btn-sm btn-secondary"
          disabled={Boolean(busy) || !visible.length}
          onClick={() => onMark('check', visible)}
          title="Flag exactly the values listed for someone to check"
        >
          {busy === 'check' ? 'Saving…' : '⚑ Needs checking'}
        </button>
        {recheck && head?.warnings?.open > 0 && (
          <button
            type="button"
            className="btn btn-sm btn-secondary bnf-review-btn-claude"
            disabled={Boolean(busy) || recheck.busy}
            onClick={recheck.run}
            title="Claude re-reads just the flagged values against their pages and proposes approvals and fixes for you to apply"
          >
            ✦ Ask Claude to re-check {head.warnings.open}
          </button>
        )}
        {check && (
          <button
            type="button"
            className="btn btn-sm btn-secondary"
            disabled={check.busy}
            onClick={check.run}
            title="Look for every value in the file again, in code: no AI, no cost"
            data-check-file
          >
            {check.busy ? 'Checking…' : unchecked ? `${check.label} (${unchecked} not checked)` : check.label}
          </button>
        )}
      </div>
      <div className="gs-legend-row">
        <ReviewDone done={done} onUndo={onUndo} undoing={undoing} />
        <HotkeyLegend list review={review} />
      </div>
      {visible.length ? (
        <div
          ref={listRef}
          className="bnf-frl-list"
          role="listbox"
          tabIndex={0}
          aria-label="Values read from this file. Arrow keys move; A approves, I ignores, C flags, U clears, F shows it in the file."
          aria-activedescendant={at >= 0 ? `frl-${visible[at].ref}` : undefined}
          onKeyDown={onKeyDown}
        >
          {visible.map((row, index) => (
            <ReviewListRow
              key={row.ref}
              row={row}
              bucket={byKey[row.bucket]}
              value={valueOf(row)}
              file={fileOf(row)}
              selected={row.ref === selected}
              open={row.ref === activeRef}
              found={matched.has(row.ref)}
              current={row.ref === find?.current}
              review={review}
              onClick={(event) => {
                choose(index);
                listRef.current?.focus();
                if (review && event.detail < 2) onOpen(row);
              }}
              onDoubleClick={() => (review ? onEdit?.(row) : onOpen(row))}
            />
          ))}
          {more?.has && !narrowed && (
            <button type="button" className="bnf-linklike bnf-frl-more" disabled={more.loading} onClick={more.load}>
              {more.loading ? 'Loading…' : `Show ${Math.min(more.pageSize, total - rows.length)} more of ${total - rows.length}`}
            </button>
          )}
        </div>
      ) : (
        <div className="bb-subtitle bb-mt">No values from {scopeWords} in this view.</div>
      )}
    </div>
  );
}
