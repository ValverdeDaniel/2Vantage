import { Link } from 'react-router';
import { stageLabel } from '../../../api/meta';
import { formatDate } from '../../../lib/format';
import JourneyStepper from '../../DealPage/JourneyStepper';

function Step({ state, label, detail }) {
  return (
    <div className="bnf-phase-step-row">
      <span className={`bnf-journey-step bnf-journey-step-${state}`}>
        <span className="bnf-journey-dot">{state === 'done' ? '✓' : ''}</span>
      </span>
      <span className="bnf-phase-step-label">{label}</span>
      <span className="bnf-phase-step-detail">{detail}</span>
    </div>
  );
}

/**
 * The Deal card (plan.md §8.5; CL19; old ClientOverviewTab.jsx's Renewal card at 891f1b3): the deal in flight's stage,
 * "The <year> deal — effective <date>.", the compact journey stepper, the next step, "Intake x% · Census y% · Proposal
 * z% · N plans quoted" (the shell's meters; Hand-off is dropped, A23), "Open the deal →" (at its next step) and
 * "Commission tab". With none in flight: the newest sale, or "Nothing sold on the record yet." Start renewal and the
 * carrier's offer wait with renewals (H104, CL27).
 */
export default function DealCard({ overview, journey, meta }) {
  const { current, last_sold: sold } = overview;
  if (!current) {
    return (
      <div className="bb-panel bnf-phase-card">
        <div className="bnf-phase-card-head">
          <div className="bb-panel-title">Deal</div>
        </div>
        <div className="bb-panel-sub">No deal in flight.</div>
        {sold ? (
          <Step
            state="done"
            label={`${sold.year} sold${sold.carriers.length ? ` — ${sold.carriers.join(', ')}` : ''}`}
            detail={sold.at ? formatDate(sold.at) : ''}
          />
        ) : (
          <div className="bb-drop-meta">Nothing sold on the record yet.</div>
        )}
      </div>
    );
  }
  const meters = journey?.meters;
  const next = journey?.next_step;
  const plans = current.plans_quoted;
  return (
    <div className="bb-panel bnf-phase-card">
      <div className="bnf-phase-card-head">
        <div className="bb-panel-title">Deal</div>
        <span className="bb-stage-pill bnf-ov-stage">{stageLabel(meta, current.stage)}</span>
      </div>
      <div className="bb-panel-sub">
        The {current.year} deal — effective {current.effective_date ? formatDate(current.effective_date) : '—'}.
      </div>
      <JourneyStepper deal={{ id: current.deal_id }} tab="client-overview" compact />
      {next?.label && <Step state="current" label={next.label} detail="next step" />}
      {meters && (
        <div className="bnf-phase-step-row">
          <span className="bnf-phase-step-detail">
            Intake {meters.intake}% · Census {meters.census}% · Proposal {meters.proposal}%
            {plans ? ` · ${plans} plan${plans === 1 ? '' : 's'} quoted` : ''}
          </span>
        </div>
      )}
      <div className="bnf-phase-card-foot">
        <Link className="btn btn-primary btn-sm" to={next?.link || `/deals/${current.deal_id}/overview`}>
          Open the deal →
        </Link>
        <Link className="btn btn-secondary btn-sm" to={`/deals/${current.deal_id}/commission`}>
          Commission tab
        </Link>
      </div>
    </div>
  );
}
