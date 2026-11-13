import { useNavigate } from 'react-router';
import { relationshipLabel } from '../../api/meta';
import { formatDate, personName } from '../../lib/format';
import { ArchiveCell, ArchiveTh } from './ArchiveCells';
import { AccountCell, ClientSortTh, DealCell, DealTh } from './HomeCells';
import { ActionCell } from './QueueCells';

// "New client · since 03/01/2026" or "Existing client" (plan.md §8.3).
function statusLine(row, meta) {
  const label = relationshipLabel(meta, row.relationship);
  return row.client_since ? `${label} · since ${formatDate(row.client_since)}` : label;
}

/**
 * Clients (CL12): the old client book's table (ClientsDashboard.jsx at 891f1b3; bnf-clients-*), New and Existing
 * clients. Columns Client, Potential deal size, Owner, Next action (its deal's next step from the work feed, slice 61:
 * a won client's commission step, or "Sold"; I122 as changed by OQ101 c, OQ91), Deals and Archive (slice 38); the
 * Radar's Reminders column is not built. Each row is one client with its one deal (version 1), and opens the deal
 * until slice 67 brings the client page. `nextByDeal`: {deal id: its feed row}.
 */
export default function ClientsTable({ rows, meta, ordering, onSort, nextByDeal = {}, children }) {
  const navigate = useNavigate();
  return (
    <div className="bb-transfers-card">
      <div className="bb-transfers-head bnf-clients-head">
        <ClientSortTh ordering={ordering} onSort={onSort} />
        <DealTh />
        <div className="bnf-th-owner">Owner</div>
        <div className="bnf-th-action">Next action</div>
        <div className="bnf-th-cases">Deals</div>
        <ArchiveTh />
      </div>
      {children}
      {rows.map((row) => {
        const href = `/deals/${row.deal.id}`;
        return (
          <div key={row.id} className="bb-transfer-row bnf-clients-row" onClick={() => navigate(href)}>
            <AccountCell name={row.name} sub={statusLine(row, meta)} to={href} />
            <DealCell value={row.deal.deal_size} />
            <div className="bnf-th-owner bb-account-sub">{personName(row.owner, '—')}</div>
            <ActionCell row={nextByDeal[row.deal.id]} />
            <div className="bnf-th-cases bb-mono">{row.deal ? 1 : 0}</div>
            <ArchiveCell row={row} />
          </div>
        );
      })}
    </div>
  );
}
