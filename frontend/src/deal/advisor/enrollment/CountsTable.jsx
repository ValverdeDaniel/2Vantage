import { badKeys, totalOf } from './countsModel';

/*
 * The counts card's table (the old PlanCountsCard's `bnf-pc-table`; F85, F88, F92): one row per picked plan, and the
 * whole-line row first where the card offers it. The inputs follow the line's rate basis (tiers, lives or volume);
 * the Total column says "Enter at least one person" until a row has someone.
 */
function Cells({ keys, labels, label, row, onChange, placeholder }) {
  const bad = badKeys(row, keys);
  return keys.map((key) => (
    <td key={key}>
      <input
        type="text"
        inputMode={key === 'volume' ? 'decimal' : 'numeric'}
        value={row[key] ?? ''}
        placeholder={placeholder?.[key] ? String(placeholder[key]) : '0'}
        aria-label={`${label}: ${labels[key] ?? key}`}
        aria-invalid={bad.includes(key) || undefined}
        onChange={(event) => onChange(key, event.target.value)}
      />
    </td>
  ));
}

function Total({ row, keys }) {
  const total = totalOf(row, keys);
  return (
    <td className={`bnf-pc-total${total ? '' : ' is-empty'}`}>
      {total ? total.toLocaleString('en-US') : 'Enter at least one person'}
    </td>
  );
}

export default function CountsTable({ keys, labels, plans, rows, onCount, figure, onFigure, note, split }) {
  return (
    <table className="bnf-pc-table">
      <thead>
        <tr>
          <th scope="col">Plan</th>
          {keys.map((key) => (
            <th key={key} scope="col" title={labels[key]}>
              {keys.length > 1 ? key : labels[key]}
            </th>
          ))}
          <th scope="col">Total</th>
        </tr>
      </thead>
      <tbody>
        {figure && (
          <tr data-plan-counts="line">
            <th scope="row">
              Whole line
              <span className="bnf-pc-note">Prices every plan without counts of its own.</span>
            </th>
            <Cells keys={keys} labels={labels} label="Whole line" row={figure} onChange={onFigure} />
            <Total row={figure} keys={keys} />
          </tr>
        )}
        {plans.map((plan) => {
          const label = `${plan.carrier} · ${plan.name}${plan.role === 'current' ? ' (current)' : ''}`;
          const row = rows[plan.id] ?? {};
          return (
            <tr key={plan.id} data-plan-counts={plan.id}>
              <th scope="row">
                {label}
                {note(plan) && <span className="bnf-pc-note">{note(plan)}</span>}
              </th>
              <Cells
                keys={keys}
                labels={labels}
                label={label}
                row={row}
                placeholder={plan.role === 'current' ? split : null}
                onChange={(key, value) => onCount(plan.id, key, value)}
              />
              <Total row={row} keys={keys} />
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
