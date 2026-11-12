import cx from '../../ui/cx';

function Summary({ summary }) {
  return (
    <section className="bnf-build-panel" aria-label="Summary">
      <div className="bnf-present-head">Our recommendation</div>
      {summary.today_annual && <div className="bnf-packet-note">Today: {summary.today_annual} a year</div>}
      {summary.groups.map((group, index) => (
        <div key={group.current || index} className="bnf-packet-note">
          {group.current && <div>In place of {group.current}:</div>}
          {group.options.length ? (
            <ul>
              {group.options.map((option) => (
                <li key={option.plan_id}>
                  {option.label && <strong>{option.label} </strong>}
                  {option.carrier} {option.name} — {option.annual}
                  {option.change && ` (${option.change}, ${option.change_pct})`}
                  {option.note && <span className="bb-drop-meta"> {option.note}</span>}
                </li>
              ))}
            </ul>
          ) : (
            <div className="bnf-pp-rec-status is-open">⚠ Nothing recommended yet</div>
          )}
        </div>
      ))}
      {summary.packages.length > 0 && (
        <ul className="bnf-packet-note">
          {summary.packages.map((row) => (
            <li key={row.key}>
              {row.label}: {row.annual}
              {row.change && ` (${row.change}, ${row.change_pct})`}
            </li>
          ))}
        </ul>
      )}
      {summary.reasons && <div className="bnf-packet-note">{summary.reasons}</div>}
    </section>
  );
}

/**
 * Exactly the rows and figures the client workbook will print (plan.md §7.9, §9.4), in the old grid's table
 * (`bnf-compare-table`, plans as columns). Display only.
 */
export default function PreviewTable({ preview }) {
  const columns = preview.columns;
  const head = [
    ['Option', (c) => c.option],
    ['Recommended', (c) => (c.recommended ? 'RECOMMENDED' : '')],
    ['Carrier', (c) => c.carrier],
    ['Plan', (c) => c.plan],
  ];
  const current = (column) => column.role === 'current' && 'bnf-plan-col-current';
  return (
    <div className="bnf-build-panel">
      <Summary summary={preview.summary} />
      <div className="bb-grid-card">
        <div className="bb-grid-scroll gk-grid">
          <table className="bnf-compare-table">
            <thead>
              {head.map(([label, cell]) => (
                <tr key={label}>
                  <th scope="row" className="bnf-benefit-col">
                    {label}
                  </th>
                  {columns.map((column) => (
                    <th scope="col" key={column.plan_id} className={cx(current(column))}>
                      {cell(column)}
                    </th>
                  ))}
                </tr>
              ))}
            </thead>
            <tbody>
              {preview.design_rows.map((row) => (
                <tr key={row.label}>
                  <th scope="row" className="bnf-benefit-col">
                    {row.label}
                  </th>
                  {row.cells.map((cell, index) => (
                    <td key={columns[index].plan_id} className={cx(current(columns[index]))}>
                      {cell}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
            <tbody>
              {preview.cost_rows.map((row) => (
                <tr key={row.label} className="bnf-computed-row">
                  <th scope="row" className="bnf-benefit-col">
                    {row.kind === 'total' ? <strong>{row.label}</strong> : row.label}
                  </th>
                  {row.cells.map((cell, index) => (
                    <td
                      key={columns[index].plan_id}
                      className={cx(row.kind !== 'input' && 'bnf-cell bnf-computed', current(columns[index]))}
                    >
                      {cell}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      {preview.packages.length > 0 && (
        <table className="bnf-archived-table">
          <thead>
            <tr>
              <th scope="col">Package</th>
              <th scope="col">Plans</th>
              <th scope="col">Monthly</th>
              <th scope="col">Annual</th>
              <th scope="col">Change $</th>
              <th scope="col">Change %</th>
            </tr>
          </thead>
          <tbody>
            {preview.packages.map((row) => (
              <tr key={row.key}>
                <th scope="row">{row.label}</th>
                <td>{row.plans}</td>
                <td className="bb-mono">{row.monthly}</td>
                <td className="bb-mono">{row.annual}</td>
                <td>{row.change || row.note}</td>
                <td>{row.change_pct}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
