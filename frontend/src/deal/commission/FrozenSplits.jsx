import { Link } from 'react-router';
import { formatMoney } from '../../lib/format';

/*
 * Who gets what as the sale froze it (plan.md §8.13; H23; 891f1b3 `overview/SplitsPanel.jsx`'s frozen view, its
 * words and classes): once the deal is booked the editor gives way to the booked shares, per line when the lines'
 * shares differ, with "Edit them in Commissions". The own tier sees its own share only (H102). Server figures only.
 */
export default function FrozenSplits({ dealId, frozen, title = 'Producers & splits' }) {
  const perLine = frozen.length > 1;
  return (
    <div className="bb-panel bnf-com-splits" data-guide="overview-splits">
      <div className="bb-panel-title">{title}</div>
      <div className="bb-panel-sub">Who gets what — frozen when the deal sold.</div>
      <div className="bnf-com-source">
        <span className="bb-badge bb-badge-green">booked — splits frozen</span>
      </div>
      <div className="bnf-com-splitlist" data-guide="splits-frozen">
        {frozen.map((group) => (
          <div key={group.line || 'all'}>
            {perLine && (
              <div className="bb-drop-meta" style={{ marginTop: 6 }}>
                {group.line_label}
              </div>
            )}
            {group.shares.map((share) => (
              <div key={`${share.role}-${share.party ?? 'house'}`} className="bnf-com-booked-line">
                <span>
                  <span className={`bnf-com-kind bnf-com-role-${share.role}`}>{share.role_label}</span>{' '}
                  {share.role === 'house' ? '' : share.name}
                </span>
                <span>
                  {share.pct_label}
                  {share.amount != null ? <strong> · {formatMoney(share.amount)}</strong> : ''}
                </span>
              </div>
            ))}
          </div>
        ))}
        <div className="bb-drop-meta" style={{ marginTop: 6 }}>
          Shares of agency revenue. Edit them in <Link to={`/commissions?deal=${dealId}`}>Commissions</Link>.
        </div>
      </div>
    </div>
  );
}
