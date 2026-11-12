import { formatDate } from '../../../lib/format';
import { arrowsFor, canMove } from './boardOrder';
import { complianceFailures, complianceText, complianceTitle, planChips, pricedKind, requiresText } from './chips';
import OrderArrows from './OrderArrows';
import PlanActions from './PlanActions';
import ReplacingPicker from './ReplacingPicker';

/*
 * The Plan cell (plan.md §8.14; F43, F44, F52, F62; the old AdvisorTab's `carrier` column): its chips, the arrows
 * while the board reads in the client's order (▲▼ down the rows, ◀▶ transposed; OQ13: on every line), the carrier
 * and name with the compliance chip, the star's reason, "Replacing:", and under a priced version what must sell and
 * when it was priced. The ⋯ menu keeps 2V's plan actions until their slices place them (F134).
 */
export default function PlanCell({ plan, board, ui }) {
  const { order, currents } = board;
  const failures = complianceFailures(plan, ui.compliance);
  const requires = requiresText(plan, ui.namesById);
  const priced = pricedKind(plan);
  const arrows = board.inProposal && canMove(plan, order) ? arrowsFor(plan, ui.shownIds, order) : null;
  const chips = planChips(plan, { currents, supersededIds: ui.supersededIds });
  return (
    <>
      <div className="bnf-plan-head">
        <div>
          {chips.map((chip) => (
            <span key={chip.key} className={chip.className} title={chip.title || undefined}>
              {chip.text}
            </span>
          ))}
          {plan.sold && <span className="bnf-plan-chip bnf-chip-sold">SOLD ✓</span>}
        </div>
        <PlanActions plan={plan} actions={ui.actions} plans={board.plans} />
      </div>
      {arrows && (
        <div className="bnf-advisor-order">
          <OrderArrows
            name={plan.name}
            axis={ui.axis}
            first={arrows.first}
            last={arrows.last}
            busy={ui.ordering}
            onMove={(step) => ui.actions.move(plan, step, arrows.among)}
          />
        </div>
      )}
      <div className="bnf-plan-carrier">{plan.carrier}</div>
      <div className="bnf-plan-name">
        {plan.name}
        {failures.length > 0 && (
          <span className="bnf-plan-chip bnf-chip-noncompliant" title={complianceTitle(failures)}>
            {complianceText(failures)}
          </span>
        )}
      </div>
      {plan.starred && plan.star?.reason && <div className="bnf-shortlist-reason">{plan.star.reason}</div>}
      <ReplacingPicker plan={plan} currents={currents} busy={ui.linking} onChange={ui.actions.link} />
      {requires && <div className="bnf-conc-requires">requires {requires}</div>}
      {priced && plan.derived?.at && <div className="bnf-conc-updated">updated {formatDate(plan.derived.at)}</div>}
    </>
  );
}
