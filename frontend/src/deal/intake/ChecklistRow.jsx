import { useRef, useState } from 'react';
import { controlsOf, statusOf } from './checklistModel';

/*
 * One row of the Marketing readiness checklist (B26, B27), the old `bnf-marketing-row` (891f1b3
 * `MarketingChecklist.jsx`): its status, label and detail, "✓ Document on file", the note, what the client sees on a
 * re-asked item, the "Still needed" note editor, and the controls `controlsOf` allows — ⬆ Attach, On file /
 * Confirmed, and Not needed / Still needed ▸ / Undo. The medical questionnaire's and stop-loss disclosure's form
 * pickers come with the questionnaire (B22, slice 42); ＋ Ask with the request tray (slice 56).
 */
export default function ChecklistRow({ item, accept, busy, onTick, onRequirement, onAttach }) {
  const fileRef = useRef(null);
  const [note, setNote] = useState(null); // the "Still needed" note while its editor is open
  const status = statusOf(item);
  const controls = controlsOf(item);
  const classes = ['bnf-marketing-row', item.done && 'is-done', item.waived && 'is-waived', item.status === 'offer' && 'is-offer'];

  const stillNeeded = () => {
    onRequirement(item.key, 'required', (note || '').trim());
    setNote(null);
  };

  return (
    <div className={classes.filter(Boolean).join(' ')} role="group" aria-label={item.label}>
      <div className="bnf-marketing-status">
        {status.check ? <span className="bb-check">✓</span> : <span className={`bb-badge ${status.cls}`}>{status.text}</span>}
      </div>
      <div className="bnf-marketing-body">
        <div className="bnf-marketing-label">{item.label}</div>
        {item.detail && <div className="bnf-marketing-detail">{item.detail}</div>}
        {item.has_document && <div className="bnf-marketing-detail bb-green">✓ Document on file</div>}
        {item.note && <div className="bnf-marketing-detail">“{item.note}”</div>}
        {item.forced && item.client_note && (
          <div className="bnf-marketing-detail bnf-client-note">Client sees: “{item.client_note}”</div>
        )}
        {note !== null && (
          <div className="bnf-override-note">
            <input
              type="text"
              autoFocus
              value={note}
              maxLength={300}
              aria-label="Note the client will see"
              placeholder="Note the client will see (why it's needed again)"
              onChange={(event) => setNote(event.target.value)}
              onKeyDown={(event) => event.key === 'Enter' && stillNeeded()}
            />
            <button type="button" className="btn btn-primary btn-sm" disabled={busy} onClick={stillNeeded}>
              Mark needed
            </button>
            <button type="button" className="btn btn-secondary btn-sm" onClick={() => setNote(null)}>
              Cancel
            </button>
          </div>
        )}
      </div>
      <div className="bnf-marketing-actions">
        {controls.attach && (
          <>
            <input
              ref={fileRef}
              type="file"
              accept={accept}
              style={{ display: 'none' }}
              aria-label={`Attach ${item.label}`}
              onChange={(event) => {
                const file = event.target.files?.[0];
                event.target.value = '';
                if (file) onAttach(item.kind, item.label, file);
              }}
            />
            <button type="button" className="btn btn-secondary btn-sm" disabled={busy} onClick={() => fileRef.current?.click()}>
              ⬆ Attach
            </button>
          </>
        )}
        {controls.tick && (
          <label className="bnf-attest-toggle" title="Confirm this is handled">
            <input
              type="checkbox"
              checked={Boolean(item.attested)}
              disabled={busy}
              onChange={(event) => onTick(item.key, event.target.checked)}
            />
            <span>{controls.tick}</span>
          </label>
        )}
        {controls.override === 'undo' && (
          <button type="button" className="bnf-override-link" disabled={busy} title="Restore the automatic requirement"
            onClick={() => onRequirement(item.key, '')}>
            Undo
          </button>
        )}
        {controls.override === 'still' && (
          <button type="button" className="bnf-override-link is-reask" disabled={busy}
            title="Re-ask the client even though this looks satisfied" onClick={() => setNote('')}>
            Still needed ▸
          </button>
        )}
        {controls.override === 'notNeeded' && (
          <button type="button" className="bnf-override-link" disabled={busy}
            title="Not needed for this group — removes it from the client ask and the readiness gate"
            onClick={() => onRequirement(item.key, 'waived')}>
            Not needed
          </button>
        )}
      </div>
    </div>
  );
}
