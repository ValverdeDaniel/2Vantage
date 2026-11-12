import { missingLabels } from './formModel';

/*
 * The form's banners (plan.md §8.9; B9), in the old words and classes (891f1b3 `IntakeTab.jsx`): "Required to market"
 * with the first four needed questions still blank, the multi-state note and the census's salary note. The banner's
 * other gaps (an HR contact, the signed BOR, the census) and the ready badge join with readiness (slice 40).
 */
const SHOWN = 4;

export default function IntakeNotes({ sections, notes }) {
  const missing = missingLabels(sections);
  return (
    <>
      {missing.length > 0 && (
        <div className="bnf-next-banner bnf-next-warn">
          <div>
            <div className="bnf-next-label">Required to market</div>
            <div className="bnf-next-text">
              {missing.slice(0, SHOWN).join(' · ')}
              {missing.length > SHOWN && ` · +${missing.length - SHOWN} more`}
            </div>
          </div>
        </div>
      )}
      {notes?.multi_state && (
        <div className="bnf-note-line">🌎 Multi-state group — confirm the carrier footprint before marketing.</div>
      )}
      {notes?.census && <div className="bnf-note-line">⚠ {notes.census}</div>}
    </>
  );
}
