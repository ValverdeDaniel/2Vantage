import { formatMoney } from '../../lib/format';
import Sparkline from './Sparkline';

// The home views' stat cards (A10, I82–I85, I124, I127; old CasesDashboard.jsx at 891f1b3), every number real: the
// counts come from the one feed, the money and the graph cards from the server (rule 5; OQ94). The cards ignore the
// filters, as the old ones did. While the feed loads, each reads "—".

const plural = (n, one) => `${n} ${one}${n === 1 ? '' : 's'}`;

/** Client responses (D-159; I85): the deals whose client sent something we have not handled. A click lifts them. */
export function ResponsesCard({ totals, loading, onShow }) {
  const words = [
    totals.questions && `${plural(totals.questions, 'unanswered question')}`,
    totals.answers && `${plural(totals.answers, 'answer')} to review`,
  ].filter(Boolean);
  return (
    <button
      type="button"
      className="bb-stat-card bnf-responses-card"
      title="Put the deals waiting on us at the top of the table"
      onClick={onShow}
    >
      <div className="bb-stat-label">Client responses</div>
      <div className={`bb-stat-value ${loading ? '' : totals.deals ? 'bb-rose' : 'bb-green'}`}>
        {loading ? '—' : totals.deals}
      </div>
      <div className="bb-stat-sub">
        {loading || !totals.deals ? 'Nothing from a client waiting on us' : words.join(' · ')}
      </div>
    </button>
  );
}

/** Prospects (I86, I124; OQ95): the open Prospect clients, their Potential deal size, and the responses card. */
export function ProspectCards({ cards, loading, responses, onShowResponses }) {
  const found = cards?.prospects;
  return (
    <div className="bnf-graph-row">
      <div className="bb-stat-card">
        <div className="bb-stat-label">Prospects</div>
        <div className="bb-stat-value">{loading || !found ? '—' : found.count}</div>
        <div className="bb-stat-sub">Open prospects, from intake to the sale</div>
      </div>
      <div className="bb-stat-card">
        <div className="bb-stat-label">Potential deal size</div>
        <div className="bb-stat-value">{loading || !found?.deal_size ? '—' : formatMoney(found.deal_size)}</div>
        <div className="bb-stat-sub">
          {!loading && found?.unsized > 0 ? `${found.unsized} without a size yet` : 'Across every open prospect'}
        </div>
      </div>
      <ResponsesCard totals={responses} loading={loading} onShow={onShowResponses} />
    </div>
  );
}

function GraphCard({ label, value, change, note, series, color }) {
  return (
    <div className="bnf-graph-card">
      <div className="bnf-graph-meta">
        <div className="bnf-graph-label">{label}</div>
        <div className="bnf-graph-value">{value}</div>
        {change != null && (
          <div className={`bnf-graph-change ${change >= 0 ? 'bb-green' : 'bb-rose'}`}>
            {change >= 0 ? '▲' : '▼'} {change >= 0 ? '+' : ''}
            {change}%<span className="bnf-graph-change-note">{note}</span>
          </div>
        )}
      </div>
      <Sparkline data={series} color={color} width={104} />
    </div>
  );
}

/** The Work queue (I82–I85): Overdue and Due this week over the mode's rows, the two graph cards, responses. */
export function QueueCards({ due, stats, loading, responses, onShowResponses }) {
  return (
    <div className="bnf-graph-row">
      <div className="bb-stat-card">
        <div className="bb-stat-label">Overdue</div>
        <div className={`bb-stat-value ${loading ? '' : due.overdue ? 'bb-rose' : 'bb-green'}`}>
          {loading ? '—' : due.overdue}
        </div>
      </div>
      <div className="bb-stat-card">
        <div className="bb-stat-label">Due this week</div>
        <div className={`bb-stat-value ${loading ? '' : due.week ? 'bb-amber' : 'bb-green'}`}>
          {loading ? '—' : due.week}
        </div>
      </div>
      <GraphCard
        label="Actions completed this week"
        value={stats ? stats.actions_week.total : 0}
        change={stats ? stats.actions_week.change_pct : null}
        note="vs last week"
        series={stats?.actions_week.series}
        color="#1f8a5b"
      />
      <GraphCard
        label="Total sales this month"
        value={stats ? formatMoney(stats.sales_month.total) : '—'}
        change={stats ? stats.sales_month.change_pct : null}
        note="vs last month"
        series={stats?.sales_month.series}
        color="#2e6fc7"
      />
      <ResponsesCard totals={responses} loading={loading} onShow={onShowResponses} />
    </div>
  );
}
