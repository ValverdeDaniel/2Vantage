import { formatDate, formatMoney } from '../../../lib/format';
import { agendaTile, effectiveTile } from './clientView';

/**
 * The client's tiles (plan.md §8.5; CL18; old ClientOverviewTab.jsx's `bb-metric-row` at 891f1b3): Effective (days to
 * or since the deal's effective date), Agenda (overdue, soon or clear over its open items) and Expected revenue (the
 * Commission tab's figure, rounded on the server in whole dollars). Received waits for the ledger (OQ6).
 */
export default function ClientTiles({ tiles }) {
  const effective = effectiveTile(tiles.effective);
  const agenda = agendaTile(tiles.agenda);
  const revenue = tiles.expected_revenue;
  return (
    <div className="bb-metric-row">
      <div className="bb-stat-card">
        <div className="bb-stat-label">Effective</div>
        <div className={`bb-stat-value ${effective.tone}`}>{effective.value}</div>
        {tiles.effective && <div className="bb-drop-meta">{formatDate(tiles.effective.date)}</div>}
      </div>
      <div className="bb-stat-card">
        <div className="bb-stat-label">Agenda</div>
        <div className={`bb-stat-value ${agenda.tone}`}>{agenda.value}</div>
        <div className="bb-drop-meta">{agenda.total} on the agenda</div>
      </div>
      <div className="bb-stat-card">
        <div className="bb-stat-label">Expected revenue</div>
        <div className={`bb-stat-value ${revenue != null ? 'bb-green' : 'bb-empty'}`}>
          {revenue != null ? formatMoney(revenue) : '—'}
        </div>
      </div>
    </div>
  );
}
