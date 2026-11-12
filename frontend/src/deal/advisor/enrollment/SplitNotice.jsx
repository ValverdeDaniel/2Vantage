import { countsText, namesOf } from './countsModel';

/*
 * The split (plan.md §5.5 step 5; F88, OQ20): once a line has two or more current plans, a figure typed for the whole
 * line would spread everyone across every plan, so it stops pricing them. This names the plans that lost their price
 * and opens the counts card on the split; the quotes that replace no current plan yet ask what they replace (their
 * "Replacing:" picker on the board). The old `bnf-tiersource-note bnf-tiersource-none`, ComparisonGrid's warning.
 */
export default function SplitNotice({ block, plans, lineLabel, onSplit }) {
  const split = block?.split;
  if (!split) return null;
  const currents = plans.filter((plan) => plan.role === 'current').length;
  const lost = split.lost.length;
  return (
    <div className="bnf-tiersource-note bnf-tiersource-none" role="status">
      <span>
        ⚠ {namesOf(plans, split.lost)} {lost === 1 ? 'has' : 'have'} no price: {lineLabel} has {currents} current plans,
        so {split.figure ? `its counts for the whole line (${countsText(split.figure, block.keys)})` : 'one figure'} cannot
        price them. Type each current plan&apos;s own counts.
        {split.unlinked.length > 0 &&
          ` ${split.unlinked.length} ${split.unlinked.length === 1 ? 'quote replaces' : 'quotes replace'} no current plan yet — pick under “Replacing:”.`}
      </span>
      <button type="button" className="bnf-tiersource-link" onClick={onSplit}>
        Split the counts →
      </button>
    </div>
  );
}
