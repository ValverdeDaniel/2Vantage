import { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router';
import { useJourney } from '../../api/agenda';

// The dots' glyphs (old JourneyStepper.jsx at 891f1b3). No step is ever "skipped" (M40): a milestone a quote-first
// deal went past reads to do, so the old "–" never draws.
const GLYPH = { done: '✓', current: '', todo: '' };

/**
 * The journey stepper (A24, M39, I120; plan.md §8.4): Get to Market and Quote to Close, each milestone a dot that opens
 * its tab; the current dot is the milestone owning the deal's next step, so dot and banner agree; "✓ Complete" once
 * every milestone that applies is done. It reads agenda's `journey/` (the shell's one read, shared with the sidebar)
 * and refetches when the tab changes (I.6), since the tab's own writes move it. `compact` drops the labels (the client
 * page's deal card, slice 67).
 */
export default function JourneyStepper({ deal, tab, compact = false }) {
  const navigate = useNavigate();
  const journey = useJourney(deal.id);
  const { refetch } = journey;
  const shown = useRef(tab);

  useEffect(() => {
    if (shown.current === tab) return; // the first draw has just fetched it
    shown.current = tab;
    refetch();
  }, [tab, refetch]);

  const data = journey.data?.journey;
  if (!data) return null;
  const open = (step) => navigate(`/deals/${deal.id}/${step.tab}`);
  return (
    <div className={`bnf-journey${compact ? ' bnf-journey-compact' : ''}`} aria-label="Journey">
      {data.modules.map((module, index) => (
        <div key={module.key} className="bnf-journey-module">
          <div className="bnf-journey-module-label">
            {index + 1} · {module.label}
          </div>
          <div className="bnf-journey-steps">
            {module.steps.map((step, position) => (
              <div
                key={step.key}
                role="button"
                tabIndex={0}
                className={`bnf-journey-step bnf-journey-step-${step.state}`}
                title={step.label}
                aria-current={step.state === 'current' ? 'step' : undefined}
                onClick={() => open(step)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault();
                    open(step);
                  }
                }}
              >
                {position > 0 && <span className="bnf-journey-connector" />}
                <span className="bnf-journey-dot">{GLYPH[step.state]}</span>
                {!compact && <span className="bnf-journey-step-label">{step.label}</span>}
              </div>
            ))}
          </div>
        </div>
      ))}
      {data.complete && <span className="bnf-journey-done-badge">✓ Complete</span>}
    </div>
  );
}
