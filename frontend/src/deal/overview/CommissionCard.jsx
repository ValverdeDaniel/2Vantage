import { Link } from 'react-router';
import { formatMoney } from '../../lib/format';
import SplitChips from '../../ui/SplitChips';

/**
 * The Overview's commission card (plan.md §8.6; M81; old Vantage 891f1b3 `CommissionSummaryCard.jsx`): what the deal
 * is expected to earn a year and on what basis, what was booked at the sale (holes, the house's share) as the viewer's
 * tier allows, who gets what as chips, the no-producer nudge, and Open Commission tab →, which owns the editing. All
 * of it is `commission.summary.card`, money rounded on the server. Received figures wait for the ledger (OQ6). The
 * client page mounts it with its own link (`to`, `linkLabel`: "Open Commissions tab →" to the client's tab; slice 68).
 */
export default function CommissionCard({ dealId, commission, meta, to = null, linkLabel = 'Open Commission tab →' }) {
  const roles = meta?.commission?.roles || [];
  const chips = (commission.chips || []).map((chip, index) => ({
    ...chip,
    party: index,
    role_label: roles.find((role) => role.key === chip.role)?.label || chip.role,
  }));
  const booking = commission.booking || {};
  const totals = booking.totals || {};
  const booked = booking.state === 'booked' && booking.record_count > 0;
  const expected = commission.expected;
  return (
    <div className="bb-panel bnf-ov-commission">
      <div className="bb-panel-title">Commission</div>
      <div className="bb-panel-sub">What this deal is worth and who gets what — edit on the Commission tab.</div>
      <div className="bnf-com-booked-line">
        <span>Expected annual revenue</span>
        <span className={`bb-mono ${expected != null ? 'bb-green' : 'bb-empty'}`}>
          {expected != null ? formatMoney(expected) : '—'}
        </span>
      </div>
      {commission.note && <div className="bb-drop-meta">{commission.note}</div>}
      {booked && booking.sees_ledger && (
        <div className="bnf-com-booked-line">
          <span>
            Booked at sale
            {totals.holes ? (
              <span className="bb-amber">
                {' '}
                · {totals.holes} hole{totals.holes === 1 ? '' : 's'}
              </span>
            ) : null}
          </span>
          <span className="bb-mono">
            {totals.expected != null ? formatMoney(totals.expected) : '—'}
            {totals.house != null ? <span className="bb-drop-meta"> · house {formatMoney(totals.house)}</span> : null}
          </span>
        </div>
      )}
      <div className="bnf-com-summary-people">
        <div className="bb-drop-meta">Who gets what</div>
        {chips.some((chip) => chip.role === 'primary') ? (
          <SplitChips shares={chips} showHouse={false} />
        ) : (
          <div className="bnf-com-nudge">No primary producer yet — set who is on the AOR letter on the Commission tab.</div>
        )}
      </div>
      <div className="bnf-com-actions">
        <Link className="btn btn-secondary btn-sm" to={to || `/deals/${dealId}/commission`}>
          {linkLabel}
        </Link>
      </div>
    </div>
  );
}
