import cx from '../../../ui/cx';

/*
 * The stop-loss board's controls (plan.md §8.14; F102; the old StopLossAnalysis.jsx at 891f1b3): Rank by, PEPM or
 * Annual only, Contract terms and Hide options we can't score — the four a saved setting keeps (F29) — and Reset
 * lasers, shown while the what-if leaves a laser out (never saved, F104). The rank keys come from /api/meta/.
 */
export default function StopLossControls({ rankKeys, controls, onControls, whatIf, onReset }) {
  const set = (patch) => onControls({ ...controls, ...patch });
  return (
    <div className="bnf-advisor-filters bnf-sl-controls">
      <label className="bnf-filter-check">
        Rank by
        <select className="filter-select" value={controls.rank_by} onChange={(e) => set({ rank_by: e.target.value })}>
          {rankKeys.map((key) => (
            <option key={key.key} value={key.key}>
              {key.label}
            </option>
          ))}
        </select>
      </label>
      <span className="bnf-sl-seg">
        <button
          type="button"
          className={cx(!controls.annual_mode && 'bnf-sl-seg-on')}
          aria-pressed={!controls.annual_mode}
          onClick={() => set({ annual_mode: false })}
        >
          PEPM
        </button>
        <button
          type="button"
          className={cx(controls.annual_mode && 'bnf-sl-seg-on')}
          aria-pressed={controls.annual_mode}
          onClick={() => set({ annual_mode: true })}
        >
          Annual only
        </button>
      </span>
      <label className="bnf-filter-check">
        <input type="checkbox" checked={controls.show_terms} onChange={(e) => set({ show_terms: e.target.checked })} />
        Contract terms
      </label>
      <label className="bnf-filter-check">
        <input
          type="checkbox"
          checked={controls.hide_unscored}
          onChange={(e) => set({ hide_unscored: e.target.checked })}
        />
        Hide options we can&rsquo;t score
      </label>
      {whatIf && (
        <button type="button" className="btn btn-secondary btn-sm" onClick={onReset}>
          Reset lasers
        </button>
      )}
    </div>
  );
}
