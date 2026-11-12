import { useIntake } from '../../../api/intake';
import { CoverageIntentCard } from '../../intake';
import CompletedMark from '../../shared/CompletedMark';

/*
 * Coverage & marketing intent on the builder (plan.md §8.14; J46): the final check on WHICH lines the client sees —
 * the same card the Intake tab mounts, its third door (one intent, one writer, one confirmation). A line it leaves off,
 * or never mentions, prints on no client document. The builder owns its open state and its completed mark; an intent
 * or coverage edit takes the mark off on the server (intake's `coverage_changed`), as the old `afterIntentEdit` did.
 * It counts toward "n of N completed" once its inputs have loaded, as the old card did.
 */
export default function CoverageCard({ dealId, meta, card }) {
  const intake = useIntake(dealId);
  if (!intake.data) return null;
  return (
    <div data-guide="build-coverage">
      <CoverageIntentCard
        deal={{ id: Number(dealId) }}
        meta={meta}
        intent={intake.data.intent}
        open={card.open}
        onToggleOpen={card.onToggleOpen}
        mark={<CompletedMark done={card.done} busy={card.busy} onToggleDone={card.onToggleDone} />}
      />
    </div>
  );
}
