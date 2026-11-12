import { useEffect, useImperativeHandle, useRef, useState } from 'react';
import cx from '../ui/cx';
import { HotkeyLegend, ReviewDone } from './HotkeyLegend';
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
}) {
  const listRef = useRef(null);
  // The selected row follows its value while it is listed; once an action moves it out of the filter, the selection
  // keeps its place in the list, so nothing jumps under the reader.
  const [pick, setPick] = useState({ ref: null, place: -1 });
  const found = rows.findIndex((row) => row.ref === pick.ref);
  const at = found >= 0 ? found : pick.place >= 0 && rows.length ? Math.min(pick.place, rows.length - 1) : -1;
  const selected = at >= 0 ? rows[at].ref : null;
  const choose = (index) => setPick({ ref: rows[index].ref, place: index });
  const byKey = Object.fromEntries(buckets.map((bucket) => [bucket.key, bucket]));
  const counts = head?.counts ?? {};
  const all = head?.all ?? { open: 0, done: 0 };

  useEffect(() => {
    listRef.current?.querySelector('.bnf-frl-row.is-active')?.scrollIntoView?.({ block: 'nearest' });
  }, [selected]);

  const move = (step) => {
    if (!rows.length) return;
    choose(at < 0 ? 0 : Math.min(rows.length - 1, Math.max(0, at + step)));
  };

  useImperativeHandle(
    ref,
    () => ({
      /** A key from the tab: 'approve' | 'ignore' | 'check' | 'clear' | 'find'. False when nothing is selected. */
      act(action) {
        const row = at >= 0 ? rows[at] : null;
        if (!row) return false;
        if (action === 'find') onOpen(row);
        else onMarkOne(action, row);
        return true;
      },
      focus: () => listRef.current?.focus(),
    }),
    [at, rows, onOpen, onMarkOne],
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
      onOpen(rows[at]);
    }
  };

  const shownWord = filter ? byKey[filter]?.label : `Every value from ${scopeWords}`;
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
          {shownWord}: {rows.length < total ? `${rows.length} of ${total} shown` : total}
        </span>
        <button
          type="button"
          className="btn btn-sm btn-secondary"
          disabled={Boolean(busy) || !rows.length}
          onClick={() => onMark('approve', rows)}
          title="Approve exactly the values listed: you looked, and they are right"
        >
          {busy === 'approve' ? 'Approving…' : `✓ Approve ${rows.length}`}
        </button>
        <button
          type="button"
          className="btn btn-sm btn-secondary"
          disabled={Boolean(busy) || !rows.length}
          onClick={() => onMark('ignore', rows)}
          title="Ignore the AI's warning on exactly the values listed"
        >
          {busy === 'ignore' ? 'Saving…' : 'Ignore'}
        </button>
        <button
          type="button"
          className="btn btn-sm btn-secondary"
          disabled={Boolean(busy) || !rows.length}
          onClick={() => onMark('check', rows)}
          title="Flag exactly the values listed for someone to check"
        >
          {busy === 'check' ? 'Saving…' : '⚑ Needs checking'}
        </button>
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
        <HotkeyLegend list />
      </div>
      {rows.length ? (
        <div
          ref={listRef}
          className="bnf-frl-list"
          role="listbox"
          tabIndex={0}
          aria-label="Values read from this file. Arrow keys move; A approves, I ignores, C flags, U clears, F shows it in the file."
          aria-activedescendant={at >= 0 ? `frl-${rows[at].ref}` : undefined}
          onKeyDown={onKeyDown}
        >
          {rows.map((row, index) => (
            <ReviewListRow
              key={row.ref}
              row={row}
              bucket={byKey[row.bucket]}
              value={valueOf(row)}
              file={fileOf(row)}
              selected={row.ref === selected}
              open={row.ref === activeRef}
              onClick={() => {
                choose(index);
                listRef.current?.focus();
              }}
              onDoubleClick={() => onOpen(row)}
            />
          ))}
          {more?.has && (
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
