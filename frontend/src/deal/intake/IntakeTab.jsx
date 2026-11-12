import { useRef, useState } from 'react';
import { useSearchParams } from 'react-router';
import { useIntake } from '../../api/intake';
import { useMeta } from '../../api/meta';
import InlineError from '../../ui/InlineError';
import Loading from '../../ui/Loading';
import ReviewBulkBar from '../../valuereview/ReviewBulkBar';
import { isBlank } from '../shared/fieldValue';
import CoverageIntentCard from './CoverageIntentCard';
import CurrentCoverageCard from './CurrentCoverageCard';
import { allRows, missingKeys } from './formModel';
import FromClientToggle from '../shared/FromClientToggle';
import IntakeNotes from './IntakeNotes';
import IntakeSelectBar from './IntakeSelectBar';
import IntakeViews from './IntakeViews';
import LinesToQuote from './LinesToQuote';
import QuestionCard from './QuestionCard';
import useAnswerMarks from './useAnswerMarks';
import useIntakeForm from './useIntakeForm';
import { viewOf } from './views';

/*
 * The Intake tab (plan.md §8.9; Part B), in the old tab's frame and order (891f1b3 `IntakeTab.jsx`, `bb-tab-page`): the
 * view pills (B36), the head with "These came from the client" and ☑ Select fields (B10), the select bar or the
 * review bar (B10, B11), the banners (B9), the Coverage & marketing intent card (B16–B24, slice 11), then the cards
 * grid: the four question cards (B1–B8; slice 39), Current coverage (B14) and Lines to quote (B32). Contacts, the
 * checklist, the BOR, the ready badge and Mark as marketed join in slice 40; ✦ Work with Claude with its drawer
 * (slice 20); ＋ Ask with the request tray (slice 56).
 */
export default function IntakeTab({ deal }) {
  const meta = useMeta().data;
  const intake = useIntake(deal.id);
  const [params, setParams] = useSearchParams();
  const view = viewOf(params);
  const [relay, setRelay] = useState(false);
  const [picked, setPicked] = useState(null); // a Set while ☑ Select fields is on, else null
  const pageRef = useRef(null);
  const marks = useAnswerMarks(deal.id);
  const form = useIntakeForm({
    dealId: deal.id,
    formMeta: meta?.intake?.form,
    data: intake.data,
    enabled: view === 'form' && !picked,
    relay,
    rootRef: pageRef,
  });

  if (intake.isPending || !meta) return <Loading label="Loading the intake…" />;
  if (intake.isError) return <InlineError title="Intake" error={intake.error} onRetry={() => intake.refetch()} />;

  const pick = (next) => {
    const nextParams = new URLSearchParams(params);
    if (next === 'form') nextParams.delete('view');
    else nextParams.set('view', next);
    setParams(nextParams, { replace: true });
  };

  const toggle = (key) =>
    setPicked((now) => {
      const next = new Set(now);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  const rowProps = (row) => ({
    ...form.rowProps(row),
    select: picked ? { picked: picked.has(row.key), onToggle: () => toggle(row.key) } : null,
  });
  const tickedAnswers = picked ? allRows(form.sections).filter((row) => picked.has(row.key) && !isBlank(row.value)) : [];
  const review = intake.data.review ?? { open: 0 };

  return (
    <div className="bb-tab-page" ref={pageRef}>
      <IntakeViews view={view} onPick={pick} />
      <div className="bnf-intake-head">
        <div>
          <div className="bb-tab-title">Intake</div>
          <div className="bb-subtitle">Collect once — every answer feeds the proposal, census, and hand-off.</div>
        </div>
        <div className="bnf-intake-head-actions">
          {!picked && <FromClientToggle checked={relay} onChange={setRelay} />}
          {!picked && (
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              title="Pick specific fields to approve, or to ask the client about"
              onClick={() => setPicked(new Set())}
            >
              ☑ Select fields
            </button>
          )}
        </div>
      </div>
      {picked && (
        <IntakeSelectBar
          count={picked.size}
          answered={tickedAnswers.length}
          busy={marks.busy}
          onAllMissing={() => setPicked(new Set(missingKeys(form.sections)))}
          onMark={(action) =>
            marks.run(action, tickedAnswers.map((row) => row.key), 'the selected questions').then((done) => done && setPicked(null))
          }
          onCancel={() => setPicked(null)}
        />
      )}
      {!picked && review.open > 0 && (
        <ReviewBulkBar counts={review} target="this intake's answers" busy={marks.busy} onAction={(action) => marks.run(action, null, 'this intake')} />
      )}
      <IntakeNotes sections={form.sections} notes={intake.data.notes} />
      <CoverageIntentCard deal={deal} meta={meta} intent={intake.data.intent} />
      <div className="bnf-intake-grid">
        {form.sections.map((section) => (
          <QuestionCard key={section.key} section={section} rowProps={rowProps} />
        ))}
        <CurrentCoverageCard deal={deal} meta={meta} coverage={intake.data.coverage} />
        <LinesToQuote deal={deal} meta={meta} />
      </div>
    </div>
  );
}
