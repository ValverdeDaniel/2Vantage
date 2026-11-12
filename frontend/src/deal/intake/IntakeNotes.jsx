import { bannerTail } from './checklistModel';
import { missingLabels } from './formModel';

/*
 * The form's banners (plan.md §8.9; B9), in the old words and classes (891f1b3 `IntakeTab.jsx`): while the deal is
 * Blocked, "Required to market" with the first four needed questions still blank, then the gate's other gaps (HR
 * contact, Signed BOR, Census; slice 40); the multi-state note and the census's salary note. As the old banner did, it
 * shows only while a needed question is blank.
 */
const SHOWN = 4;

export default function IntakeNotes({ sections, notes, ready }) {
  const missing = missingLabels(sections);
  const blocked = !ready || ready.state === 'blocked';
  return (
    <>
      {blocked && missing.length > 0 && (
        <div className="bnf-next-banner bnf-next-warn">
          <div>
            <div className="bnf-next-label">Required to market</div>
            <div className="bnf-next-text">
              {missing.slice(0, SHOWN).join(' · ')}
              {missing.length > SHOWN && ` · +${missing.length - SHOWN} more`}
              {bannerTail(ready)}
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
