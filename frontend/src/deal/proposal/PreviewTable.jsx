import cx from '../../ui/cx';
import styles from './ProposalTab.module.css';

function Summary({ summary }) {
  return (
    <section className={styles.summary} aria-label="Summary">
      <h4>Our recommendation</h4>
      {summary.today_annual && <p>Today: {summary.today_annual} a year</p>}
      {summary.groups.map((group, index) => (
        <div key={group.current || index} className={styles.summaryGroup}>
          {group.current && <p className={styles.summaryCurrent}>In place of {group.current}:</p>}
          {group.options.length ? (
            <ul>
              {group.options.map((option) => (
                <li key={option.plan_id}>
                  {option.label && <strong>{option.label} </strong>}
                  {option.carrier} {option.name} — {option.annual}
                  {option.change && ` (${option.change}, ${option.change_pct})`}
                  {option.note && <span className={styles.muted}> {option.note}</span>}
                </li>
              ))}
            </ul>
          ) : (
            <p className={styles.blocker}>
              <span aria-hidden="true">⚠ </span>Nothing recommended yet
            </p>
          )}
        </div>
      ))}
      {summary.packages.length > 0 && (
        <ul>
          {summary.packages.map((row) => (
            <li key={row.key}>
              {row.label}: {row.annual}
              {row.change && ` (${row.change}, ${row.change_pct})`}
            </li>
          ))}
        </ul>
      )}
      {summary.reasons && <p className={styles.reasons}>{summary.reasons}</p>}
    </section>
  );
}

/** Exactly the rows and figures the client workbook will print (plan.md §7.9, §9.4). Display only. */
export default function PreviewTable({ preview }) {
  const columns = preview.columns;
  const head = [
    ['Option', (c) => c.option],
    ['Recommended', (c) => (c.recommended ? 'RECOMMENDED' : '')],
    ['Carrier', (c) => c.carrier],
    ['Plan', (c) => c.plan],
  ];
  return (
    <div className={styles.previewWrap}>
      <Summary summary={preview.summary} />
      <div className={styles.previewScroll}>
        <table className={styles.preview}>
          <thead>
            {head.map(([label, cell]) => (
              <tr key={label}>
                <th scope="row">{label}</th>
                {columns.map((column) => (
                  <th scope="col" key={column.plan_id} className={styles[column.role]}>
                    {cell(column)}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {preview.design_rows.map((row) => (
              <tr key={row.label}>
                <th scope="row">{row.label}</th>
                {row.cells.map((cell, index) => (
                  <td key={columns[index].plan_id}>{cell}</td>
                ))}
              </tr>
            ))}
          </tbody>
          <tbody className={styles.costs}>
            {preview.cost_rows.map((row) => (
              <tr key={row.label} className={cx(row.kind === 'total' && styles.total)}>
                <th scope="row">{row.label}</th>
                {row.cells.map((cell, index) => (
                  <td key={columns[index].plan_id} className={cx(row.kind === 'input' && styles.inputCell)}>
                    {cell}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {preview.packages.length > 0 && (
        <table className={styles.packages}>
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
                <td>{row.monthly}</td>
                <td>{row.annual}</td>
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
