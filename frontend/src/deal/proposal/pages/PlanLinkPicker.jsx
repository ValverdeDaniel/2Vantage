import { useState } from 'react';
import cx from '../../../ui/cx';

/*
 * "Replacing: [current plan ▾]" under a column, on a line with two or more current plans (plan.md §5.4, §8.14; F52,
 * J12; the old PlanLinkPicker.jsx at 7385bb3; D-174): which plan this quote replaces, so its change, its group and its
 * page follow. Daniel, 2026-11-10: "where it says vs, write replacing:". "Several…" makes a consolidation: tick the
 * current plans it replaces together (three plans become two, §5.4); a consolidation reads "Several: Current 2 + 3"
 * and "Several…" edits it. Saves through `plans/links/` (quotes' one door), which refuses in words.
 */

const PICK = 'several-pick';
const SEVERAL = 'several';

export default function PlanLinkPicker({ plan, currents, disabled, onChange }) {
  const ids = plan.replacing.ids;
  const [ticked, setTicked] = useState(null); // the "Several…" checklist while open: [current ids]
  const numberOf = (id) => currents.find((current) => current.id === id)?.number;
  const several = ids.length > 1;
  const value = several ? SEVERAL : (ids[0] ?? '');
  const linked = currents.find((current) => current.id === ids[0]);

  const pick = (raw) => {
    if (raw === PICK) setTicked(ids);
    else if (raw !== SEVERAL) onChange(plan, raw ? [Number(raw)] : []);
  };
  const tick = (id, on) => setTicked((now) => (on ? [...now, id] : now.filter((other) => other !== id)));

  return (
    <>
      <label className={cx('bnf-link-picker', !ids.length && 'bnf-link-picker-open')}>
        <span>Replacing:</span>
        <select
          className="filter-select"
          value={value}
          disabled={disabled}
          title={
            several
              ? 'A consolidation: one plan in place of several current plans'
              : linked
                ? linked.words
                : 'Not linked: pick the current plan this quote replaces'
          }
          aria-label={`Which current plan ${plan.name} replaces`}
          onChange={(event) => pick(event.target.value)}
        >
          <option value="">Pick a current plan</option>
          {currents.map((current) => (
            <option key={current.id} value={current.id}>
              Current {current.number} · {current.monthly || '—'}
            </option>
          ))}
          {several && (
            <option value={SEVERAL}>Several: Current {ids.map(numberOf).filter(Boolean).join(' + ')}</option>
          )}
          <option value={PICK}>Several…</option>
        </select>
      </label>
      {ticked && (
        <div className="bnf-pg-menu-body" role="group" aria-label={`The current plans ${plan.name} replaces`}>
          {currents.map((current) => (
            <label key={current.id} className="bnf-output-check">
              <input
                type="checkbox"
                checked={ticked.includes(current.id)}
                onChange={(event) => tick(current.id, event.target.checked)}
              />
              Current {current.number} · {current.words}
            </label>
          ))}
          <span className="bnf-count-actions">
            <button
              type="button"
              className="btn btn-primary btn-sm"
              disabled={disabled || ticked.length < 2}
              title={ticked.length < 2 ? 'Tick two or more: a consolidation replaces several current plans' : undefined}
              onClick={() => {
                onChange(plan, ticked);
                setTicked(null);
              }}
            >
              Replace these {ticked.length}
            </button>
            <button type="button" className="btn btn-secondary btn-sm" onClick={() => setTicked(null)}>
              Cancel
            </button>
          </span>
        </div>
      )}
    </>
  );
}
