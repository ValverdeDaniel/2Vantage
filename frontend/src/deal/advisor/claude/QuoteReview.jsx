import ChangeList from './ChangeList';
import { otherItems, planItems } from './changeSet';
import PlanDiff from './PlanDiff';

/*
 * The quote reader's body for the staged review card (plan.md §10.5; D28, D31): the plans in the file's order, then
 * the printed counts and lines to add. The generic card (deal/claude/ReviewCard) holds the ticks, the places of the
 * "Which current plan?" columns and the buttons; `onOpen(doc, page)` shows a value's page in the file.
 */
export default function QuoteReview({ changeSet, meta, picked, onToggle, places, onPlace, onOpen }) {
  const plans = planItems(changeSet);
  return (
    <>
      {plans.length > 0 ? (
        <PlanDiff
          items={plans}
          meta={meta}
          picked={picked}
          onToggle={onToggle}
          places={places}
          onPlace={onPlace}
          onOpen={onOpen}
        />
      ) : (
        <div className="bb-subtitle bb-mt">This read found no plan.</div>
      )}
      <ChangeList items={otherItems(changeSet)} kept={changeSet.kept} picked={picked} onToggle={onToggle} />
    </>
  );
}
