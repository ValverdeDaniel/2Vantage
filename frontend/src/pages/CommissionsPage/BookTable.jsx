import { Link } from 'react-router';
import { formatDate, formatMoney } from '../../lib/format';
import SplitChips from '../../ui/SplitChips';

/*
 * The Book's table (H50, H51; 891f1b3 `commissions/BookTab.jsx` GroupRows, its words and classes): client (with its
 * year), line, carrier, effective, premium, rate, expected, house (the all tier's), who gets what and status; a row
 * click opens its drawer. "Group by client" puts a head row with the client's sums (the server's) over its rows. The
 * Received and Gap columns wait with the ledger (OQ6), as the tiles' do.
 */
const STATUS_TONE = {
  booked: 'bb-badge-green',
  active: 'bb-badge-green',
  renewed: 'bb-badge-gray',
  void: 'bb-badge-gray',
};

function groupRows(rows) {
  const groups = new Map();
  rows.forEach((row) => {
    if (!groups.has(row.client_id)) groups.set(row.client_id, { key: row.client_id, name: row.client_name, rows: [] });
    groups.get(row.client_id).rows.push(row);
  });
  return [...groups.values()];
}

export default function BookTable({ rows, sums = {}, grouped, isAll, openId, onOpen }) {
  const groups = grouped ? groupRows(rows) : [{ key: 'all', rows }];
  return (
    <div className="bb-transfers-card" data-guide="book-table">
      <table className="bnf-com-table">
        <thead>
          <tr>
            <th>Client</th>
            <th>Line</th>
            <th>Carrier</th>
            <th>Effective</th>
            <th className="bnf-com-num">Premium</th>
            <th>Rate</th>
            <th className="bnf-com-num">Expected</th>
            {isAll && <th className="bnf-com-num">House</th>}
            <th>Who gets what</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {groups.map((group) => (
            <Group
              key={group.key}
              group={group}
              sums={sums[group.key]}
              grouped={grouped}
              isAll={isAll}
              openId={openId}
              onOpen={onOpen}
            />
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Group({ group, sums, grouped, isAll, openId, onOpen }) {
  const count = group.rows.length;
  return (
    <>
      {grouped && (
        <tr className="bnf-com-grouphead">
          <td colSpan={isAll ? 10 : 9}>
            {group.name}
            <span className="bb-drop-meta">
              {' '}
              · {count} line{count === 1 ? '' : 's'}
            </span>
            <span className="bnf-com-groupsum">
              expected <strong className="bb-green">{formatMoney(sums?.expected, { empty: '—' })}</strong>
              {isAll ? (
                <>
                  {' · '}house <strong>{formatMoney(sums?.house, { empty: '—' })}</strong>
                </>
              ) : null}
            </span>
          </td>
        </tr>
      )}
      {group.rows.map((row) => (
        <tr
          key={row.id}
          className={`bnf-com-clickable ${openId === row.id ? 'active' : ''} ${grouped ? 'bnf-com-grouped' : ''}`}
          onClick={() => onOpen(openId === row.id ? null : row.id)}
        >
          <td>
            {grouped ? null : row.deal_id ? (
              <Link to={`/deals/${row.deal_id}/commission`} onClick={(event) => event.stopPropagation()}>
                {row.client_name}
              </Link>
            ) : (
              row.client_name
            )}
            <span className="bb-drop-meta"> · {row.year_number ? `yr ${row.year_number}` : 'renewal'}</span>
          </td>
          <td>{row.line_label}</td>
          <td>{row.carrier || '—'}</td>
          <td>{row.effective_date ? formatDate(row.effective_date) : '—'}</td>
          <td className={`bnf-com-num ${row.premium_annual == null ? 'bnf-com-hole' : ''}`}>
            {row.premium_annual != null ? formatMoney(row.premium_annual) : 'not known'}
          </td>
          <td className={row.holes.includes('rate') ? 'bnf-com-hole' : ''}>
            {row.rate_label || 'not set'}
            {row.sources.rate === 'agency' ? <span className="bb-drop-meta"> (agency default)</span> : null}
          </td>
          <td className={`bnf-com-num ${row.expected == null ? 'bnf-com-hole' : 'bb-green'}`}>
            {row.expected != null ? formatMoney(row.expected) : '—'}
          </td>
          {isAll && (
            <td className="bnf-com-num">{row.house_share != null ? formatMoney(row.house_share) : '—'}</td>
          )}
          <td>
            <SplitChips shares={row.shares} showHouse={false} />
          </td>
          <td>
            <span className={`bb-badge ${STATUS_TONE[row.status] || 'bb-badge-amber'}`}>{row.status_label}</span>
          </td>
        </tr>
      ))}
    </>
  );
}
