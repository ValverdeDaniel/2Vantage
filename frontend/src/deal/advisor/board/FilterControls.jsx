import { formatMoney } from '../../../lib/format';
import { setTotalCap } from './boardConfig';
import NumberFilter from './NumberFilter';

/*
 * The filter card's controls after the finder (plan.md §8.14; F18–F22; the old `bnf-advisor-filters`): the budget
 * select (each plan's change against what it replaces, F18), "Monthly total ≤ $" (this line's total rule, F19), the
 * line's sliders in steps of 50 between its quotes' values (an "at least" slider for an annual maximum or a frame
 * allowance, F20), the dollar caps (F21), the hides and the three switches (F22). Lists and words of the budget,
 * sliders, caps and hides come from /api/meta/ `board`.
 */

function Slider({ slider, onChange }) {
  const { bounds, value, op, label } = slider;
  const atMost = op === '<=';
  const loose = bounds ? (atMost ? bounds.max : bounds.min) : 0;
  let shown = 'n/a';
  if (bounds) shown = value == null ? 'Any' : `${atMost ? '≤' : '≥'} ${formatMoney(value)}`;
  return (
    <div className="bnf-filter-slider" title={bounds ? '' : 'Not enough data in this column to filter'}>
      <span className="bnf-filter-slider-label">
        {label} <b>{shown}</b>
      </span>
      <input
        type="range"
        aria-label={label}
        min={bounds ? bounds.min : 0}
        max={bounds ? bounds.max : 100}
        step={50}
        value={bounds ? (value ?? loose) : 0}
        disabled={!bounds}
        onChange={(event) => {
          const next = Number(event.target.value);
          onChange(next === loose ? null : next); // the loose end is "Any": a blank shows again
        }}
      />
    </div>
  );
}

function Check({ checked, onChange, title, children }) {
  return (
    <label className="bnf-filter-check" title={title || undefined}>
      <input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} />
      {children}
    </label>
  );
}

export default function FilterControls({ board, line, config, set, filters, currents }) {
  const hide = new Set(config.hide);
  const toggleHide = (key, on) => set({ hide: board.hides.map((h) => h.key).filter((k) => (k === key ? on : hide.has(k))) });
  return (
    <>
      <select
        className="filter-select"
        aria-label="Budget"
        value={config.budget_pct ?? ''}
        disabled={!currents && config.budget_pct == null}
        title={currents ? 'Each quote against the plan it replaces' : 'Set a current plan with rates to enable the budget trigger'}
        onChange={(event) => set({ budget_pct: event.target.value === '' ? null : Number(event.target.value) })}
      >
        {board.budget.map((rung) => (
          <option key={rung.value ?? 'any'} value={rung.value ?? ''}>
            {rung.label}
          </option>
        ))}
      </select>
      <NumberFilter
        label="Monthly total ≤ $"
        title="Only the plans whose monthly total is at most this, on this line; a plan with no price yet is named, not hidden silently"
        value={filters.rules.totalCap?.value ?? null}
        onChange={(value) => set((now) => setTotalCap(now, line, value))}
      />
      {filters.sliders.map((slider) => (
        <Slider
          key={slider.key}
          slider={slider}
          onChange={(value) =>
            set((now) => {
              const sliders = { ...now.sliders };
              if (value == null) delete sliders[slider.key];
              else sliders[slider.key] = value;
              return { sliders };
            })
          }
        />
      ))}
      {filters.caps.map((cap) => (
        <NumberFilter key={cap.key} label={cap.label} title={cap.title} value={config[cap.key]} onChange={(value) => set({ [cap.key]: value })} />
      ))}
      {board.hides.map((option) => (
        <Check key={option.key} checked={hide.has(option.key)} title={option.title} onChange={(on) => toggleHide(option.key, on)}>
          {option.label}
        </Check>
      ))}
      <Check checked={config.starred_only} title="Only the shortlisted plans — the ones being seriously considered" onChange={(on) => set({ starred_only: on })}>
        ★ Starred only
      </Check>
      <Check checked={config.needs_check} title="Only the plans with a value someone flagged as needing checking" onChange={(on) => set({ needs_check: on })}>
        ⚑ Needs checking
      </Check>
      <Check
        checked={config.to_review}
        title="Only the quotes with an AI value still to review: unsure reads nobody approved or ignored, and anything flagged"
        onChange={(on) => set({ to_review: on })}
      >
        ⚠ To review
      </Check>
    </>
  );
}
