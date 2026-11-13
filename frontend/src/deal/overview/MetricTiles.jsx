import { formatAgo, formatMoney } from '../../lib/format';

/**
 * The four tiles (M35–M38; old `bb-metric-row` at 891f1b3): Intake complete (the journey's Intake meter, intake's
 * answered over needed), Plans quoted (renewals and alternates not removed), Last contact ("just now", "3h ago",
 * "2d ago") and Expected revenue (the Commission tab's figure, rounded on the server in whole dollars, half up).
 */
export default function MetricTiles({ tiles, journey }) {
  const intake = journey?.meters?.intake;
  const contact = tiles.last_contact_at;
  const revenue = tiles.expected_revenue;
  return (
    <div className="bb-metric-row">
      <div className="bb-stat-card">
        <div className="bb-stat-label">Intake complete</div>
        <div className="bb-stat-value">{intake ?? 0}%</div>
      </div>
      <div className="bb-stat-card">
        <div className="bb-stat-label">Plans quoted</div>
        <div className="bb-stat-value">{tiles.plans_quoted}</div>
      </div>
      <div className="bb-stat-card">
        <div className="bb-stat-label">Last contact</div>
        <div className={`bb-stat-value ${contact ? '' : 'bb-empty'}`}>{contact ? formatAgo(contact) : '—'}</div>
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
