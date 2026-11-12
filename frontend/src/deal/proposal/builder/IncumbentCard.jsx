import { formatDate } from '../../../lib/format';
import BuilderCard from '../../shared/BuilderCard';

/*
 * A line kept as-is (plan.md §5.4, §8.14; J47, J52, B36; the old "On the proposal, not in the market" card at
 * 891f1b3): presented from the in-force arrangement, never sent out, so there is nothing to pick — its current plan is
 * the recommendation. Shows the current plans (or the intent's carrier and funding), the rate guarantee and renewal
 * date, and the EnrollmentStrip; "Edit intent ▸" goes to the intent card.
 */
export default function IncumbentCard({ line, card, strip, onEditIntent }) {
  const facts = line.incumbent;
  return (
    <BuilderCard
      guide="build-incumbent"
      title="On the proposal, not in the market"
      chips={<span className="bnf-state-chip bnf-state-guaranteed">guaranteed</span>}
      card={card}
    >
      <div className="bb-panel-sub">
        This line is presented from the in-force arrangement — it was deliberately not sent out for RFP, so there are no
        quotes to pick.
      </div>
      <div className="bnf-build-incumbent">
        {line.currents.length
          ? line.currents.map((plan) => (
              <div className="bnf-build-current" key={plan.id}>
                <span className="bnf-plan-chip bnf-chip-current">
                  CURRENT{line.currents.length > 1 ? ` ${plan.number}` : ''}
                </span>
                {plan.words}
                <b>{plan.monthly ? `${plan.monthly}/mo` : '—'}</b>
              </div>
            ))
          : facts && (
              <div className="bnf-build-current">
                <span className="bnf-plan-chip bnf-chip-current">IN FORCE</span>
                {facts.carrier || 'Carrier on file'}
                {facts.funding ? ` · ${facts.funding}` : ''}
              </div>
            )}
        {facts?.rate_guarantee_through && (
          <div className="bnf-build-incumbent-fact">
            Rate guaranteed through <b>{formatDate(facts.rate_guarantee_through)}</b>
          </div>
        )}
        {facts?.renewal_date && <div className="bnf-build-incumbent-fact">Renews {formatDate(facts.renewal_date)}</div>}
        {strip}
        <div className="bnf-build-incumbent-note">
          The client sees this section as their current coverage, and its current plan is the recommendation. To shop it
          after all — or drop it from the proposal — change the intent.{' '}
          <button type="button" className="bnf-override-link" onClick={onEditIntent}>
            Edit intent ▸
          </button>
        </div>
      </div>
    </BuilderCard>
  );
}
