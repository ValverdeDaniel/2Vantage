import cx from '../../../ui/cx';

/*
 * The table card's own toolbar (plan.md §8.14; F31, F32, F34, F36; the old `bnf-advisor-tablebar`): the column
 * presets from `/api/meta/`, the sort select (Proposal order, the default; Sort by column; Closest to current), ⇄
 * Transpose (kept per browser, refused above the limit with its tooltip) and, transposed with sizes of your own,
 * ↺ Reset sizes. ▦ Pages joins with slice 14.
 */
export default function TableBar({ board, preset, onPreset, sort, onSort, transpose, sizes, currents }) {
  const presets = board?.presets ?? [];
  const sorts = board?.sorts ?? [];
  const special = sort.key === 'proposal' || sort.key === 'closest';
  const sortTitle =
    sort.key === 'proposal'
      ? 'The client’s order, the one the proposal and every document use: the arrows in each Plan cell move a plan. Nothing sorts on its own.'
      : currents > 1
        ? 'Order the quotes by similarity to the nearest current plan across this line’s key numbers'
        : currents
          ? 'Order the quotes by similarity to the current plan across this line’s key numbers'
          : 'Set a current plan on this line to enable closest-to-current';
  return (
    <div className="bnf-advisor-tablebar">
      <span className="bnf-advisor-views-label">Columns</span>
      <div className="bnf-preset-tabs" role="group" aria-label="Columns">
        {presets.map((tab) => (
          <button
            key={tab.key}
            type="button"
            aria-pressed={preset === tab.key}
            className={cx('bnf-preset-tab', preset === tab.key && 'active')}
            onClick={() => onPreset(tab.key)}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <span className="bnf-advisor-tablebar-right">
        <select
          className="filter-select"
          aria-label="Order"
          value={special ? sort.key : ''}
          title={sortTitle}
          onChange={(event) => {
            const next = event.target.value;
            onSort(next ? { key: next, dir: 1 } : { key: 'total', dir: 1 });
          }}
        >
          {sorts.map((option) => (
            <option key={option.key} value={option.key}>
              {option.label}
            </option>
          ))}
        </select>
        <button
          type="button"
          className="bnf-preset-tab bnf-transpose-btn"
          aria-pressed={transpose.shown === 'cols'}
          disabled={transpose.blocked}
          title={
            transpose.blocked
              ? `Transpose shows up to ${transpose.max} plans; ${transpose.count} are on screen.`
              : transpose.shown === 'rows'
                ? 'Flip to plans-as-columns (the proposal grid’s shape)'
                : 'Flip back to plans-as-rows (the horizontal board)'
          }
          onClick={() => transpose.pick(transpose.shown === 'rows' ? 'cols' : 'rows')}
        >
          ⇄ Transpose
        </button>
        {transpose.shown === 'cols' && sizes.custom && (
          <button
            type="button"
            className="bnf-preset-tab"
            title="Plan columns back to five across and every row back to three lines (your sizes, in this browser)"
            onClick={sizes.reset}
          >
            ↺ Reset sizes
          </button>
        )}
      </span>
    </div>
  );
}
