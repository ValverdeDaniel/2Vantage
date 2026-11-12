import { useParams } from 'react-router';
import { useIntake } from '../../../api/intake';
import { setTotalCap } from './boardConfig';
import { budgetStep, clientBudget, dollars, totalCapOf } from './clientBudget';

/*
 * The client's budget hints on the filter card (plan.md §8.14; F139; OQ51 default): "Client target $X/mo · Apply" and
 * "Client accepts up to N% · Apply", from the intake's Goals answers (clientBudget.js holds the rules). Nothing is
 * prefilled: Apply sets this line's total cap, or the budget step, and the hint stays. Reads the intake the Intake tab
 * reads (one query, ['deal', id, 'intake']); shows nothing while the client has given no budget.
 */
export default function BudgetHints({ board, line, config, set, currents }) {
  const { dealId } = useParams();
  const intake = useIntake(dealId);
  const { target, increase } = clientBudget(intake.data?.answers);
  if (target === null && increase === null) return null;
  const step = budgetStep(board.budget, increase);
  const capped = target !== null && totalCapOf(config, line) === target;
  const stepped = step !== null && config.budget_pct === step.value;
  return (
    <>
      {target !== null && (
        <span className="bb-drop-meta" title="The Monthly Budget Target on the intake's Goals card">
          Client target {dollars(target)}/mo
          {!capped && (
            <>
              {' · '}
              <button
                type="button"
                className="bnf-override-link"
                title={`Show only the plans whose monthly total is at most ${dollars(target)} on this line`}
                onClick={() => set((now) => setTotalCap(now, line, target))}
              >
                Apply
              </button>
            </>
          )}
        </span>
      )}
      {increase !== null && (
        <span className="bb-drop-meta" title="The Acceptable Increase on the intake's Goals card">
          Client accepts up to {increase}%
          {step && !stepped && (
            <>
              {' · '}
              <button
                type="button"
                className="bnf-override-link"
                disabled={!currents}
                title={
                  currents
                    ? `Sets the budget to “${step.label}”, the nearest step inside what the client accepts`
                    : 'Set a current plan with rates to enable the budget trigger'
                }
                onClick={() => set({ budget_pct: step.value })}
              >
                Apply
              </button>
            </>
          )}
        </span>
      )}
    </>
  );
}
