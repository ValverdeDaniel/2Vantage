import { useSearchParams } from 'react-router';
import cx from '../../../ui/cx';
import { pickedSection, sectionsOf } from './queueWords';
import SectionQueue from './SectionQueue';

/*
 * The Review view (plan.md §8.8; L11; old 891f1b3 `DealReviewTab.jsx` `view === 'queue'`, `bnf-board-queue`): every
 * section's client answers in one place, one section at a time behind its chip (Census · client, Intake), each with
 * what it holds to review. `?section=` picks the chip and is written on a click; with none, the first section holding
 * something. The AI reads' queue lives in the Documents station (L10, L19); the questionnaires' client answers have
 * their own chip (slice 58, L21: grouped by form and section). A deal that may no longer ask its client only reads
 * (L129).
 */
export default function QueueView({ deal, meta, board }) {
  const [params, setParams] = useSearchParams();
  const sections = sectionsOf(meta, board);
  const picked = pickedSection(sections, params.get('section'));
  const pick = (key) => {
    const next = new URLSearchParams(params);
    next.set('section', key);
    setParams(next, { replace: true });
  };
  return (
    <div className="bnf-board-queue">
      <div className="bnf-board-queuehead">
        <div className="bnf-advisor-views bnf-board-sections" role="group" aria-label="Section">
          <span className="bnf-advisor-views-label">Section</span>
          {sections.map((section) => (
            <button
              key={section.key}
              type="button"
              className={cx('bnf-viewtab', picked?.key === section.key && 'bnf-viewtab-on')}
              aria-pressed={picked?.key === section.key}
              title={`Work the ${section.label} queue here: ${section.count} to review`}
              onClick={() => pick(section.key)}
            >
              {section.label} <span className="rr-pill-count">{section.count}</span>
            </button>
          ))}
        </div>
      </div>
      {picked && (
        <SectionQueue
          key={picked.key}
          dealId={deal.id}
          meta={meta}
          surface={picked.key}
          readOnly={Boolean(board.asks_closed)}
        />
      )}
    </div>
  );
}
