import cx from '../../../ui/cx';
import { removeRule } from './boardConfig';
import BudgetHints from './BudgetHints';
import FilterControls from './FilterControls';
import FilterNotes from './FilterNotes';
import FinderBox from './FinderBox';
import RuleChips from './RuleChips';
import SavedBar from './SavedBar';

/*
 * The filter card (plan.md §8.14; F14–F28, F140; the old `bnf-advisor-filtercard`): above the board header, the state
 * that carries across line switches — how the quotes are narrowed. Its head holds the saved setups and "N active ·
 * Clear" (F26); then the Filters row (the finder with "Also matches", the budget, "Monthly total ≤ $", sliders, caps,
 * hides, switches and the amber notes); the carrier chips with two or more carriers (F23); and Claude's rule chips.
 */
export default function FilterCard({ meta, line, lineLabel, view, filters, currents, finderRef, onFind, onPickLine, onCounts }) {
  const { config, set, apply, clear } = view;
  const board = meta.board;
  const fields = Object.fromEntries((meta.plans?.fields ?? []).map((field) => [field.key, field]));
  const priced = config.budget_pct != null || config.sort.key === 'closest';
  return (
    <div className="bnf-advisor-filtercard">
      <div className="bnf-advisor-filtercard-head">
        <SavedBar line={line} lineLabel={lineLabel} current={config} onApply={apply} />
        {filters.active > 0 && (
          <span className="bnf-advisor-filterstate">
            <b>{filters.active}</b> active
            <button type="button" className="bnf-advisor-clear" onClick={clear} title="Reset every trigger and carrier chip">
              Clear
            </button>
          </span>
        )}
      </div>

      <div className="bnf-advisor-labelrow">
        <span className="bnf-advisor-views-label">Filters</span>
        <div className="bnf-advisor-filters">
          <FinderBox
            value={config.find}
            onChange={(find) => set({ find })}
            onEnter={onFind}
            others={filters.others}
            inputRef={finderRef}
            onPickLine={onPickLine}
          />
          <FilterControls board={board} line={line} config={config} set={set} filters={filters} currents={currents} />
          <BudgetHints board={board} line={line} config={config} set={set} currents={currents} />
          <FilterNotes
            unpriced={filters.unpriced}
            uncompared={filters.uncompared}
            noCurrent={priced && !currents}
            onCounts={onCounts}
          />
        </div>
      </div>

      {filters.carriers.length > 1 && (
        <div className="bnf-advisor-labelrow">
          <span className="bnf-advisor-views-label">Carriers</span>
          <div className="bnf-carrier-chips">
            {filters.carriers.map((carrier) => {
              const on = config.carriers.includes(carrier);
              return (
                <button
                  key={carrier}
                  type="button"
                  aria-pressed={on}
                  className={cx('bnf-carrier-chip', on && 'active')}
                  onClick={() =>
                    set((now) => ({
                      carriers: on ? now.carriers.filter((c) => c !== carrier) : [...now.carriers, carrier],
                    }))
                  }
                >
                  {carrier}
                </button>
              );
            })}
          </div>
        </div>
      )}

      <RuleChips
        rules={filters.rules}
        fields={fields}
        ops={board.rule_ops ?? []}
        lineLabel={lineLabel}
        onRemove={(rule) => set((now) => removeRule(now, rule))}
      />
    </div>
  );
}
