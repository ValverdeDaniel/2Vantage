import { useNavigate } from 'react-router';
import { stageLabel } from '../../../api/meta';
import { formatDate, formatMoney } from '../../../lib/format';
import { historyChips } from './clientView';

// G116's chips (old ArtifactChips.jsx): buttons inside the row, each opening that section of the deal page. A chip
// stops the row's own click, so it opens the census rather than the deal's Overview.
function Chips({ row }) {
  const navigate = useNavigate();
  const chips = historyChips(row);
  if (!chips.length) return null;
  return (
    <span className="bnf-cw-artifacts">
      {chips.map((chip) => (
        <button
          key={chip.key}
          type="button"
          className={`bnf-cw-artifact ${chip.done ? 'bnf-cw-artifact-done' : ''}`}
          title={chip.title}
          onClick={(event) => {
            event.stopPropagation();
            navigate(`/deals/${row.deal_id}/${chip.tab}`);
          }}
        >
          {chip.label}
          {chip.count ? <span className="bb-mono"> {chip.count}</span> : null}
        </button>
      ))}
    </span>
  );
}

/**
 * History (plan.md §8.5; CL22, G116; old ClientOverviewTab.jsx's History card at 891f1b3): one row per deal, newest
 * first — its year, "Deal · <carriers sold>", in flight or its stage and when it sold, its artifact chips, and what it
 * is expected to earn — the row opening the deal. The old "All cases & history →" waits with the Deals & history tab
 * (CL27).
 */
export default function HistoryCard({ history, meta }) {
  const navigate = useNavigate();
  return (
    <div className="bb-panel">
      <div className="bb-panel-title">History</div>
      <div className="bb-panel-sub">
        Every deal with this client, newest first. Each deal&apos;s intake, census and questionnaires are one click away.
      </div>
      {history.length === 0 && <div className="bb-drop-meta">No deals yet.</div>}
      <div className="bnf-cw-history">
        {history.map((row) => (
          // A div, not a link: the chips are buttons, and a button inside an anchor is invalid and swallows clicks.
          <div
            key={row.deal_id}
            role="link"
            tabIndex={0}
            className={`bnf-cw-history-row ${row.current ? 'bnf-cw-history-current' : ''}`}
            title="Open this deal"
            onClick={() => navigate(`/deals/${row.deal_id}/overview`)}
            onKeyDown={(event) => event.key === 'Enter' && navigate(`/deals/${row.deal_id}/overview`)}
          >
            <span className="bnf-cw-history-year bb-mono">{row.year || '—'}</span>
            <span className="bnf-cw-history-main">
              <span className="bnf-cw-history-title">
                Deal
                {row.sold?.carriers.length ? ` · ${row.sold.carriers.join(', ')}` : ''}
              </span>
              <span className="bnf-cw-history-sub">
                {row.current ? 'in flight' : stageLabel(meta, row.stage)}
                {row.sold?.at ? ` · sold ${formatDate(row.sold.at)}` : ''}
              </span>
              <Chips row={row} />
            </span>
            <span className={`bnf-cw-history-amt bb-mono ${row.expected != null ? 'bb-green' : 'bb-empty'}`}>
              {row.expected != null ? formatMoney(row.expected) : ''}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
