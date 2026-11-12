import { useNavigate } from 'react-router';
import { stageLabel } from '../../api/meta';
import { stagePillClass } from '../../lib/dealLook';
import { formatDate, personName, toDate } from '../../lib/format';
import { ArchiveCell, ArchiveTh } from './ArchiveCells';
import { AccountCell, ClientSortTh, DealCell, DealTh } from './HomeCells';

function startOfToday() {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return today;
}

/**
 * Prospects (CL11): I86's table (NewClientsTable.jsx at 891f1b3; bnf-nc-*), one row per Prospect client with its deal.
 * Due is the effective date, red once past. Until slice 61 brings the work feed, Next action and Client response are
 * empty, and the stage has no readiness bar. Archive hides the client and its deal (I126). A row opens the deal.
 */
export default function ProspectsTable({ rows, meta, ordering, onSort, children }) {
  const navigate = useNavigate();
  const today = startOfToday();
  return (
    <div className="bb-transfers-card">
      <div className="bb-transfers-head bnf-nc-head">
        <ClientSortTh ordering={ordering} onSort={onSort} />
        <DealTh />
        <div className="bnf-th-action">Next action</div>
        <div className="bnf-th-response">Client response</div>
        <div className="bnf-wq-th-extra">Stage</div>
        <div className="bb-th-date">Due</div>
        <div className="bnf-th-owner">Owner</div>
        <ArchiveTh />
      </div>
      {children}
      {rows.map((row) => {
        const href = `/deals/${row.deal.id}`;
        const due = toDate(row.deal.effective_date);
        return (
          <div key={row.id} className="bb-transfer-row bnf-nc-row" onClick={() => navigate(href)}>
            <AccountCell name={row.name} sub="New business" to={href} />
            <DealCell value={row.deal.deal_size} />
            <div className="bnf-th-action" />
            <div className="bnf-th-response bb-account-sub">—</div>
            <div className="bnf-wq-th-extra">
              <div className="bnf-wq-stagecell">
                <span className={stagePillClass(row.deal.stage)}>{stageLabel(meta, row.deal.stage)}</span>
              </div>
            </div>
            <div className={due && due < today ? 'bb-th-date bb-mono bnf-wq-overdue' : 'bb-th-date bb-mono'}>
              {formatDate(row.deal.effective_date, '—')}
            </div>
            <div className="bnf-th-owner bb-account-sub">{personName(row.owner, '—')}</div>
            <ArchiveCell row={row} />
          </div>
        );
      })}
    </div>
  );
}
