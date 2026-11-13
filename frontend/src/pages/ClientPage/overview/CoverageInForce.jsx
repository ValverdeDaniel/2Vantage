import { labelOf } from '../../../api/meta';
import { formatDate, formatMoney } from '../../../lib/format';

const SUBS = {
  sold: 'What the client has today — the plans sold on its deal, with the premium a month and what the carrier pays us on each.',
  current: 'What the client has today — the coverage in force its Intake records, with the in-force commission.',
};

function Empty() {
  return <span className="bb-empty">—</span>;
}

/**
 * Coverage in force (plan.md §8.5; CL20, H106; old ClientOverviewTab.jsx's `bnf-cw-table` at 891f1b3): for a client,
 * the sold plans per line, with the premium a month of the line's Sold package and the commission the Commission tab
 * applies (its rate and what it earns a year); before a sale, the current coverage with its in-force commission. Renews
 * is the server's: the current coverage on the deal's effective date, the sold plans a year after. Every figure
 * arrives from the server, rounded there (rule 5).
 */
export default function CoverageInForce({ block, meta }) {
  const rows = block.rows || [];
  return (
    <div className="bb-panel">
      <div className="bb-panel-title">Coverage in force</div>
      <div className="bb-panel-sub">{SUBS[block.kind] || SUBS.current}</div>
      {rows.length === 0 && (
        <div className="bb-drop-meta">No coverage lines recorded yet — they are entered on a deal&apos;s Intake tab.</div>
      )}
      {rows.length > 0 && (
        <div className="bnf-cw-table-wrap">
          <table className="bnf-cw-table">
            <thead>
              <tr>
                <th>Line</th>
                <th>Carrier</th>
                <th>Funding</th>
                <th className="bnf-cw-num">Premium / mo</th>
                <th>In-force commission</th>
                <th>Renews</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.line}>
                  <td>
                    <strong>{row.label}</strong>
                    {row.plan ? <span className="bb-drop-meta"> · {row.plan}</span> : null}
                  </td>
                  <td>{row.carrier || <Empty />}</td>
                  <td>{row.funding ? labelOf(meta?.funding, row.funding) : <Empty />}</td>
                  <td className="bnf-cw-num bb-mono">
                    {row.premium_month != null ? formatMoney(row.premium_month) : '—'}
                  </td>
                  <td>
                    {row.commission || <span className="bb-empty">not known</span>}
                    {row.expected != null ? <span className="bb-drop-meta"> · {formatMoney(row.expected)}/yr</span> : null}
                  </td>
                  <td>{row.renews ? formatDate(row.renews) : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
