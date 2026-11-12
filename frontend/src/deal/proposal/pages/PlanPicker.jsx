import { useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import cx from '../../../ui/cx';
import { blockedWhy, MAX_ROWS, pickerEntries, pickerNote } from './pickerRows';

/*
 * The drop-down behind a plan's name on "What the client will see" (plan.md §8.14; F45, F46, J8–J11; the old
 * PlanPicker.jsx at 7385bb3; D-221). Daniel, 2026-11-10: "select the plan by clicking the plan name and then a
 * searchable drop down appears. the starred and current should be clear ... but the user should be able to search for
 * any plan name by name."
 *
 * `spot` set: picking replaces the plan there (POST plans/slot/ `at`): the picked plan takes its place, its star and
 * the current plans it replaces, and the plan there takes the picked one's. No `spot`: "＋ Add a plan" (`beside`), with
 * its own "Replacing:" choice on a line with several current plans. The list, the greyed reasons and the note are
 * pickerRows.js; it opens in a layer on <body> under the clicked name, so no table's scrolling clips it.
 */

/** Under the anchor, kept on the screen: {top, left, width}. */
function placeUnder(anchor) {
  const rect = anchor?.getBoundingClientRect();
  if (!rect) return { top: 80, left: 8, width: 460 };
  const width = Math.min(460, window.innerWidth - 16);
  const left = Math.max(8, Math.min(rect.left, window.innerWidth - width - 8));
  const below = window.innerHeight - rect.bottom;
  const top = below > 320 || below > rect.top ? rect.bottom + 4 : Math.max(8, rect.top - 424);
  return { top, left, width };
}

function Marks({ plan, on, several, nothingStarred }) {
  const renewal = plan.chips.find((chip) => chip.key === 'renewal');
  const current = plan.chips.find((chip) => chip.key === 'current');
  const priced = plan.chips.find((chip) => chip.key === 'priced');
  return (
    <span className="bnf-pk-marks">
      {current && <span className="bnf-plan-chip bnf-chip-current">{current.text}</span>}
      {renewal && (
        <span className="bnf-plan-chip bnf-chip-renewal" title={renewal.title}>
          RENEWAL{several && renewal.of ? ` of ${renewal.of}` : ''}
        </span>
      )}
      {priced && (
        <span className="bnf-plan-chip bnf-chip-concession" title={priced.title}>
          {priced.title || priced.text}
        </span>
      )}
      {plan.kind !== 'current' && on && !nothingStarred && (
        <span className="bnf-pk-star" title="Starred: on the proposal">
          ★
        </span>
      )}
    </span>
  );
}

export default function PlanPicker({ payload, lineLabel, anchor, spot = null, places, forms, onChoose, onClose }) {
  const [query, setQuery] = useState('');
  const [active, setActive] = useState(0);
  const [beside, setBeside] = useState(payload.currents[0]?.id ?? null);
  const [place, setPlace] = useState(() => placeUnder(anchor));
  const boxRef = useRef(null);
  const listRef = useRef(null);
  const inputRef = useRef(null);
  const several = payload.several;

  useEffect(() => {
    const follow = () => setPlace(placeUnder(anchor));
    const away = (event) => {
      if (boxRef.current?.contains(event.target) || anchor?.contains(event.target)) return;
      onClose();
    };
    inputRef.current?.focus();
    window.addEventListener('scroll', follow, true);
    window.addEventListener('resize', follow);
    document.addEventListener('mousedown', away);
    return () => {
      window.removeEventListener('scroll', follow, true);
      window.removeEventListener('resize', follow);
      document.removeEventListener('mousedown', away);
    };
  }, [anchor, onClose]);

  const entries = useMemo(() => pickerEntries(payload, query, places, forms), [payload, query, places, forms]);
  const shown = entries.slice(0, MAX_ROWS);
  const at = Math.min(active, Math.max(0, shown.length - 1));
  const target = { spot, beside: several ? beside : null, payload };

  useEffect(() => {
    listRef.current?.querySelector('[aria-selected="true"]')?.scrollIntoView?.({ block: 'nearest' });
  }, [at]);

  const choose = (entry) => {
    if (!entry || blockedWhy(entry.plan, target)) return;
    onChoose(entry.plan, spot ? {} : { beside: several ? beside : null });
  };
  const onKeyDown = (event) => {
    const keys = {
      ArrowDown: () => setActive(Math.min(at + 1, shown.length - 1)),
      ArrowUp: () => setActive(Math.max(at - 1, 0)),
      Enter: () => choose(shown[at]),
      Escape: onClose,
    };
    if (!keys[event.key]) return;
    event.preventDefault();
    keys[event.key]();
  };

  const listId = `bnf-pk-list-${payload.line}`;
  const optionId = (plan) => `bnf-pk-${payload.line}-${plan.plan_id}`;
  const firstOff = shown.findIndex((entry) => !entry.on);
  const note = pickerNote({ spot, beside: several ? beside : null, payload, lineLabel });

  return createPortal(
    <div
      ref={boxRef}
      className="bnf-pk"
      style={place}
      role="dialog"
      aria-label={spot ? `Change ${spot.name}` : `Add a ${lineLabel} plan`}
    >
      <input
        ref={inputRef}
        type="text"
        className="bnf-pk-input"
        placeholder="Search every scanned plan by name, number or carrier…"
        role="combobox"
        aria-expanded="true"
        aria-controls={listId}
        aria-autocomplete="list"
        aria-activedescendant={shown[at] ? optionId(shown[at].plan) : undefined}
        value={query}
        onChange={(event) => {
          setQuery(event.target.value);
          setActive(0);
        }}
        onKeyDown={onKeyDown}
      />
      {!spot && several && (
        <label className="bnf-pk-replacing">
          <span>Replacing:</span>
          <select
            className="filter-select"
            value={beside ?? ''}
            onChange={(event) => setBeside(event.target.value ? Number(event.target.value) : null)}
          >
            {payload.currents.map((current) => (
              <option key={current.id} value={current.id}>
                Current {current.number} · {current.words} · {current.monthly || '—'}
              </option>
            ))}
            <option value="">No current plan (Other options)</option>
          </select>
        </label>
      )}
      <div className="bnf-pk-note">{note}</div>
      {shown.length ? (
        <div id={listId} ref={listRef} role="listbox" className="bnf-pk-list" aria-label={`${lineLabel} plans`}>
          {shown.map((entry, i) => {
            const { plan } = entry;
            const why = blockedWhy(plan, target);
            return [
              i === 0 && entry.on && (
                <div key="h-on" className="bnf-pk-section" role="presentation">
                  On the proposal
                </div>
              ),
              i === firstOff && (
                <div key="h-off" className="bnf-pk-section" role="presentation">
                  Other scanned quotes
                </div>
              ),
              <div
                key={plan.plan_id}
                id={optionId(plan)}
                role="option"
                aria-selected={i === at}
                aria-disabled={why ? true : undefined}
                className={cx('bnf-pk-row', i === at && 'is-active', why && 'is-blocked')}
                title={why || undefined}
                onMouseEnter={() => setActive(i)}
                // mousedown, not click: the search box keeps its focus.
                onMouseDown={(event) => {
                  event.preventDefault();
                  choose(entry);
                }}
              >
                <Marks plan={plan} on={entry.on} several={several} nothingStarred={payload.nothing_starred} />
                <span className="bnf-pk-name">
                  <span className="bnf-pk-carrier">{plan.carrier}</span>
                  <span>{plan.name}</span>
                  {why && <span className="bnf-pk-why">{why}</span>}
                </span>
                <span className="bnf-pk-figures">
                  <span className="bb-mono">{plan.monthly || '—'}</span>
                  {plan.change?.pct && (
                    <span className={cx('bnf-delta', plan.change.up ? 'bnf-delta-pos' : 'bnf-delta-neg')}>
                      {plan.change.pct}
                    </span>
                  )}
                  {plan.page && (
                    <span className="bnf-pk-page" title={`On page ${plan.page} now`}>
                      p.{plan.page}
                    </span>
                  )}
                </span>
              </div>,
            ];
          })}
          {entries.length > shown.length && (
            <div className="bnf-pk-more">{entries.length - shown.length} more — keep typing to narrow it</div>
          )}
        </div>
      ) : (
        <div className="bnf-pk-empty">No {lineLabel} plan matches.</div>
      )}
    </div>,
    document.body,
  );
}
