import { Fragment } from 'react';
import { formatMoney } from '../../../lib/format';
import { bands, DELTA_ROWS, money, termText } from './stopLossModel';

/*
 * ③ Option comparison (plan.md §8.14; F103; the old StopLossAnalysis.jsx at 891f1b3): transposed like the grid and
 * the sheet, the in-force contracts first, then the options in the verdict's order. Every figure and every difference
 * against the one in-force contract is the server's (F103: none worked out here). PEPM or Annual only picks the rows.
 */
function Delta({ value }) {
  if (value == null) return <span>—</span>;
  if (value === 0) return <span className="bnf-delta">Same</span>;
  return (
    <span className={`bnf-delta ${value > 0 ? 'bnf-delta-pos' : 'bnf-delta-neg'}`}>
      {formatMoney(value, { signed: true })}
    </span>
  );
}

function Group({ title, span }) {
  return (
    <tr className="bnf-group-row">
      <td colSpan={span}>{title}</td>
    </tr>
  );
}

function Row({ label, columns, render, className, strong, mono = true }) {
  return (
    <tr className={className}>
      <td className="bnf-benefit-col">{strong ? <strong>{label}</strong> : label}</td>
      {columns.map((column) => (
        <td key={column.id} className={`bnf-cell bnf-computed${mono ? ' bb-mono' : ''}`}>
          {render(column)}
        </td>
      ))}
    </tr>
  );
}

export default function OptionTable({ columns, best, controls, fields, terms }) {
  const span = columns.length + 1;
  return (
    <div className="bb-grid-card">
      <div className="bb-grid-scroll">
        <table className="bnf-sl-table">
          <thead>
            <tr>
              <th className="bnf-benefit-col">Variable</th>
              {columns.map((column) => (
                <th
                  key={column.id}
                  className={[
                    column.current ? 'bnf-plan-col-current' : '',
                    !column.current && best && column.id === best.id ? 'bnf-sl-col-best' : '',
                  ]
                    .filter(Boolean)
                    .join(' ')}
                >
                  {column.current && <span className="bnf-plan-chip bnf-chip-current">CURRENT</span>}
                  <div className="bnf-plan-carrier">{column.carrier || '—'}</div>
                  <div className="bnf-plan-name">{column.name}</div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {controls.show_terms && (
              <>
                <Group title="Contract terms" span={span} />
                <Row
                  label="Specific deductible (per person)"
                  columns={columns}
                  render={(column) => money(column.figures.spec_deductible)}
                />
                {terms.map((term) => (
                  <Row
                    key={term.key}
                    label={term.label}
                    columns={columns}
                    mono={false}
                    render={(column) => termText(fields, term.key, column)}
                  />
                ))}
              </>
            )}
            {bands(controls.annual_mode).map(([title, rows]) => (
              <Fragment key={title}>
                <Group title={title} span={span} />
                {rows.map((row) => (
                  <Row
                    key={row.key}
                    label={row.label}
                    columns={columns}
                    render={(column) => row.show(column.figures[row.key])}
                  />
                ))}
              </Fragment>
            ))}
            <Group title="Annual cost comparison" span={span} />
            <Row
              label="Projected cost (SL + admin + expected claims)"
              columns={columns}
              render={(column) => money(column.figures.projected_cost)}
            />
            <Row
              className="bnf-sl-verdict-row"
              label="Maximum annual liability"
              strong
              columns={columns}
              render={(column) => (
                <>
                  <strong>{money(column.figures.max_annual_liability)}</strong>
                  {column.what_if && <span className="bnf-flag-chip">what-if</span>}
                </>
              )}
            />
            {DELTA_ROWS.map(([label, key]) => (
              <Row
                key={key}
                className="bnf-sl-delta-row"
                label={label}
                columns={columns}
                render={(column) => <Delta value={column.vs?.[key] ?? null} />}
              />
            ))}
          </tbody>
        </table>
      </div>
      <div className="bnf-sl-note">Negative numbers mean the proposal is lower than the current contract.</div>
    </div>
  );
}
