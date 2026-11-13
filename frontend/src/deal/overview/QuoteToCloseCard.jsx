import { Link } from 'react-router';
import { formatDate } from '../../lib/format';
import { quoteRows, tabLink } from './gtm/gtmModel';

/**
 * Card 2, Quote to Close (plan.md §8.6; M62, M65; old Vantage 891f1b3 `PhaseCards.jsx`): the journey's Quote to Close
 * steps with the shell's own states, so the card and the stepper agree, each with the Overview's detail ("6 plans · 2 to
 * review · 1 missing" or "Waiting on carrier responses", "Proposal issued <date>"…), and Open comparison ▸ to the
 * Advisor. The client-selected step and the hand-off wait (M63, M64); Open hub ▸ is dropped (M66).
 */
export default function QuoteToCloseCard({ deal, rows, journey }) {
  return (
    <div className="bb-panel bnf-phase-card">
      <div className="bnf-phase-card-head">
        <div className="bb-panel-title">2 · Quote to Close</div>
      </div>
      <div className="bb-panel-sub">Quotes in, advisor shortlist, proposal out — through the sold hand-off.</div>
      {quoteRows(journey, rows).map((step) => (
        <div key={step.key} className="bnf-phase-step-row">
          <span className={`bnf-journey-step bnf-journey-step-${step.state}`}>
            <span className="bnf-journey-dot">{step.state === 'done' ? '✓' : ''}</span>
          </span>
          <span className="bnf-phase-step-label">{step.label}</span>
          {step.detail && (
            <span className="bnf-phase-step-detail">
              {step.detail}
              {step.at ? ` ${formatDate(step.at)}` : ''}
            </span>
          )}
        </div>
      ))}
      <div className="bnf-phase-card-foot">
        <Link className="btn btn-primary btn-sm" to={tabLink(deal.id, 'advisor')}>
          Open comparison ▸
        </Link>
      </div>
    </div>
  );
}
