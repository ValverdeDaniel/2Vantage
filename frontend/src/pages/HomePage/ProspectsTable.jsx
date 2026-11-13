import { useNavigate } from 'react-router';
import { ArchiveCell, ArchiveTh } from './ArchiveCells';
import { DealCell, DealTh } from './HomeCells';
import { archiveRow } from './homeRows';
import {
  ActionCell,
  DueCell,
  OwnerCell,
  RESPONSE_TITLE,
  ResponseCell,
  RowAccountCell,
  SortTh,
  StageCell,
} from './QueueCells';

/**
 * Prospects (CL11; I86's table, old NewClientsTable.jsx at 891f1b3; bnf-nc-*), on the work feed from slice 61: one row
 * per Prospect client (`homeRows.onePerClient`) with its next action, client response, stage and progress, due (the
 * effective date, red once past) and owner; every other thing it needs is on the Work queue. A sale moves the client
 * to Clients at once (I122 as changed by OQ101 c). The row opens its next action; the name opens the deal.
 */
export default function ProspectsTable({ rows, meta, sort, onSort, emptyText }) {
  const navigate = useNavigate();
  return (
    <div className="bb-transfers-card">
      <div className="bb-transfers-head bnf-nc-head">
        <SortTh className="bb-th-account" sortKey="client" sort={sort} onSort={onSort}>
          Client
        </SortTh>
        <DealTh sort={sort} onSort={onSort} />
        <div className="bnf-th-action">Next action</div>
        <SortTh className="bnf-th-response" sortKey="response" sort={sort} onSort={onSort} title={RESPONSE_TITLE}>
          Client response
        </SortTh>
        <div className="bnf-wq-th-extra">Stage</div>
        <SortTh className="bb-th-date" sortKey="due" sort={sort} onSort={onSort}>
          Due
        </SortTh>
        <div className="bnf-th-owner">Owner</div>
        <ArchiveTh />
      </div>
      {rows.length === 0 && <div className="empty-state">{emptyText}</div>}
      {rows.map((row) => (
        <div key={row.client_id} className="bb-transfer-row bnf-nc-row" onClick={() => navigate(row.link)}>
          <RowAccountCell row={row} sub={row.dealCount > 1 ? `${row.dealCount} new-business deals` : 'New business'} />
          <DealCell value={row.deal_size} />
          <ActionCell row={row} />
          <ResponseCell row={row} />
          <StageCell row={row} meta={meta} />
          <DueCell row={row} />
          <OwnerCell row={row} />
          <ArchiveCell row={archiveRow(row)} />
        </div>
      ))}
    </div>
  );
}
