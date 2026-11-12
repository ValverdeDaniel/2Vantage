import { formatDate } from '../../../lib/format';

/*
 * A plan's head on the station's Grid (plan.md §8.16; E40; the old DocumentsTab plan head): CURRENT, RENEWAL (the
 * renewal of which plan, on hover), SOLD ✓, ★ FIT with the star's reason and date on hover, and ⚠ N — the values from
 * this file to look at again (potential errors, E50) — then the carrier and the plan's name. The words are the old
 * app's; nothing here is decided in the browser.
 */
export default function PlanHead({ plan, issues, renewsName }) {
  const star = plan.star;
  const starTitle = [star?.reason, star?.at ? `starred ${formatDate(star.at)}` : ''].filter(Boolean).join(' — ');
  return (
    <div className="bnf-plan-head">
      <div>
        {plan.role === 'current' && <span className="bnf-plan-chip bnf-chip-current">CURRENT</span>}
        {plan.role === 'renewal' && (
          <span className="bnf-plan-chip bnf-chip-renewal" title={renewsName ? `The renewal of ${renewsName}` : undefined}>
            RENEWAL
          </span>
        )}
        {plan.sold && <span className="bnf-plan-chip bnf-chip-sold">SOLD ✓</span>}
        {plan.starred && (
          <span className="bnf-plan-chip bnf-chip-shortlist" title={starTitle || undefined}>
            ★ FIT
          </span>
        )}
        {issues > 0 && (
          <span
            className="bnf-plan-chip gs-plan-flag"
            title={`${issues} value${issues === 1 ? '' : 's'} from this file to look at again`}
          >
            ⚠ {issues}
          </span>
        )}
        <div className="bnf-plan-carrier">{plan.carrier}</div>
        <div className="bnf-plan-name">{plan.name}</div>
      </div>
    </div>
  );
}
