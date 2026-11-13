import { useNavigate } from 'react-router';
import { ArchiveCell, ArchiveTh } from './ArchiveCells';
import { DealCell, DealTh } from './HomeCells';
import { archiveRow, TYPE_BADGES } from './homeRows';
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

// The sub-line under each row's name (old WorkQueueTable's SUB).
const SUB = { deal: 'Deal', step: 'Deal step', task: 'Task', nudge: 'Task' };

/** Next step / All open steps (I74) and "Show N held until later" (I75); the old plan-my-day hint waits with AG3. */
function ModeBar({ steps, onSteps, showLater, onShowLater, heldCount }) {
  const tab = (on, label, title) => (
    <button
      type="button"
      role="tab"
      aria-selected={steps === on}
      className={steps === on ? 'bnf-viewtab bnf-viewtab-on' : 'bnf-viewtab'}
      title={title}
      onClick={() => onSteps(on)}
    >
      {label}
    </button>
  );
  return (
    <div className="bnf-wq-modebar">
      <div className="bnf-viewtabs bnf-wq-modes" role="tablist" aria-label="What the queue lists">
        {tab(false, 'Next step', "Each deal's one next step, with tasks")}
        {tab(true, 'All open steps', 'Every step a deal can take now (never one waiting on a step before it)')}
      </div>
      {heldCount > 0 && (
        <label className="bnf-wq-later-toggle" title="Rows someone put off until a later day">
          <input type="checkbox" checked={showLater} onChange={(event) => onShowLater(event.target.checked)} />
          Show {heldCount} held until later
        </label>
      )}
    </div>
  );
}

/**
 * The Work queue (I70–I82; old WorkQueueTable.jsx at 891f1b3): every open thing to do, one row each — each deal's next
 * step (or every open step), hand tasks and nudges — soonest due first unless a column is sorted. The pick column, its
 * select-all and the tray wait with Plan my day (I91, AG3; OQ8). A row opens its action; the name opens the deal; the
 * chip opens the action too; the Client response chips open Review & requests.
 */
export default function WorkQueueTable({ rows, meta, sort, onSort, emptyText, mode }) {
  const navigate = useNavigate();
  const typeLabel = (key) => (meta.deal_types || []).find((item) => item.key === key)?.label || key;
  return (
    <>
      <ModeBar {...mode} />
      <div className="bb-transfers-card">
        <div className="bb-transfers-head bnf-wq-head">
          <SortTh className="bb-th-account" sortKey="client" sort={sort} onSort={onSort}>
            Client
          </SortTh>
          <DealTh sort={sort} onSort={onSort} />
          <div className="bnf-wq-th-type">Type</div>
          <div className="bnf-th-action">Next action</div>
          <SortTh className="bnf-th-response" sortKey="response" sort={sort} onSort={onSort} title={RESPONSE_TITLE}>
            Client response
          </SortTh>
          <div className="bnf-wq-th-extra">Stage / category</div>
          <SortTh className="bb-th-date" sortKey="due" sort={sort} onSort={onSort}>
            Due
          </SortTh>
          <div className="bnf-th-owner">Owner</div>
          <ArchiveTh />
        </div>
        {rows.length === 0 && <div className="empty-state">{emptyText}</div>}
        {rows.map((row) => (
          <div key={row.id} className="bb-transfer-row bnf-wq-row" onClick={() => navigate(row.link)}>
            <RowAccountCell row={row} sub={SUB[row.kind] || 'Deal'} />
            <DealCell value={row.deal_size} />
            <div className="bnf-wq-th-type">
              <span className={`bb-badge ${TYPE_BADGES[row.type] || TYPE_BADGES.new_business}`}>
                {typeLabel(row.type)}
              </span>
            </div>
            <ActionCell row={row} />
            <ResponseCell row={row} />
            <StageCell row={row} meta={meta} />
            <DueCell row={row} />
            <OwnerCell row={row} />
            {row.kind === 'deal' ? <ArchiveCell row={archiveRow(row)} /> : <div className="bnf-th-archive" />}
          </div>
        ))}
      </div>
    </>
  );
}
