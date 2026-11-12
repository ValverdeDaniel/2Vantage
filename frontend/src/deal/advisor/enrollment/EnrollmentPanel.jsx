import CensusNotice from './CensusNotice';
import CountsCard from './CountsCard';
import SplitNotice from './SplitNotice';
import useCountsSave from './useCountsSave';

/*
 * What sits between the board's header and its table about enrollment (plan.md §8.14; F85, F88, F91): the split
 * notice and the census notice while the counts card is closed, and the card itself when it is open (the old
 * Advisor drew PlanCountsCard right there). `data` is the line's comparison; its `enrollment` block is the card's.
 */
export default function EnrollmentPanel({ dealId, meta, line, lineLabel, data, open, preselect, onOpen, onClose }) {
  const kit = useCountsSave(dealId, line, lineLabel);
  const block = data?.enrollment;
  if (!block) return null;
  if (open) {
    return (
      <CountsCard
        key={line}
        block={block}
        plans={data.plans}
        labels={meta.enrollment?.labels ?? {}}
        lineLabel={lineLabel}
        preselect={preselect}
        kit={kit}
        onClose={onClose}
      />
    );
  }
  return (
    <>
      <SplitNotice block={block} plans={data.plans} lineLabel={lineLabel} onSplit={onOpen} />
      <CensusNotice block={block} plans={data.plans} busy={kit.busy} onKeep={kit.keep} />
    </>
  );
}
