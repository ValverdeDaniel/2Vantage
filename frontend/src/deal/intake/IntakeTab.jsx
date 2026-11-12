import { useIntake } from '../../api/intake';
import { useMeta } from '../../api/meta';
import InlineError from '../../ui/InlineError';
import Loading from '../../ui/Loading';
import CoverageIntentCard from './CoverageIntentCard';
import CurrentCoverageCard from './CurrentCoverageCard';
import LinesToQuote from './LinesToQuote';

/*
 * The Intake tab (plan.md §8.9; Part B), in the old tab's frame (891f1b3 `IntakeTab.jsx`, `bb-tab-page`). Slice 11
 * builds the Coverage & marketing intent card (B16–B24) above the cards grid, and in the grid the Current coverage
 * subcards (B14) and the Lines to quote chips (B32). The view pills, the four question cards and the Enter/Tab flow
 * come in slice 39; contacts, the checklist, the BOR, the ready badge and Mark as marketed in slice 40.
 */
export default function IntakeTab({ deal }) {
  const meta = useMeta().data;
  const intake = useIntake(deal.id);
  if (intake.isPending) return <Loading label="Loading the intake…" />;
  if (intake.isError) return <InlineError title="Intake" error={intake.error} onRetry={() => intake.refetch()} />;
  return (
    <div className="bb-tab-page">
      <div className="bnf-intake-head">
        <div>
          <div className="bb-tab-title">Intake</div>
          <div className="bb-subtitle">Collect once — every answer feeds the proposal, census, and hand-off.</div>
        </div>
      </div>
      <CoverageIntentCard deal={deal} meta={meta} intent={intake.data.intent} />
      <div className="bnf-intake-grid">
        <CurrentCoverageCard deal={deal} meta={meta} coverage={intake.data.coverage} />
        <LinesToQuote deal={deal} meta={meta} />
      </div>
    </div>
  );
}
