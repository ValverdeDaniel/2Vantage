import ChangeList from './ChangeList';
import { otherItems, planItems } from './changeSet';
import PlanDiff from './PlanDiff';

/*
 * The quote reader's body for the staged review card (plan.md §10.5; D28, D31): the plans in the file's order, then
 * the printed counts and lines to add. The generic card (deal/claude/ReviewCard) holds the ticks and the buttons.
 */
export default function QuoteReview({ changeSet, meta, picked, onToggle }) {
  const plans = planItems(changeSet);
  return (
    <>
      {plans.length > 0 ? (
        <PlanDiff items={plans} meta={meta} picked={picked} onToggle={onToggle} />
      ) : (
        <div className="bb-subtitle bb-mt">This read found no plan.</div>
      )}
      <ChangeList items={otherItems(changeSet)} kept={changeSet.kept} picked={picked} onToggle={onToggle} />
    </>
  );
}
