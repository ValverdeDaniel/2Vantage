import { useRef, useState } from 'react';
import AskButton from '../../shared/AskButton';
import { controlsOf, statusOf } from '../../intake';
import { askRefOf, suffixOf } from './gtmModel';

/**
 * One checklist row in Card 1's frame (M50–M57, M60; old 891f1b3 `GetToMarketCard.jsx` items): the status glyph
 * (Not needed, Waived, Optional, Re-asked, ✓, Missing), the label with "— on file", its detail, what the client sees
 * on a re-asked row, the "Still needed" note, and the controls intake's own card offers (`controlsOf`): ⬆ Attach
 * (documents' upload), On file / Confirmed (intake's tick), ＋ Ask (review's tray) and Not needed / Still needed ▸ /
 * Undo (intake's requirement). `writes` is intake's `useChecklistWrites`; `children` sit under the detail (the form
 * picker), `after` closes the actions (Open questionnaire ▸). One set of controls, two frames (B30).
 */
export default function ReqItem({ dealId, item, writes, accept, form = false, children = null, after = null, wrap = true }) {
  const fileRef = useRef(null);
  const [note, setNote] = useState(null); // the "Still needed" note while its editor is open
  const status = statusOf(item);
  const controls = controlsOf(item);
  const askRef = askRefOf(item);
  const busy = writes.busy;

  const stillNeeded = () => {
    writes.requirement(item.key, 'required', (note || '').trim());
    setNote(null);
  };

  const body = (
    <>
      <div className="bnf-req-line">
        {status.check ? <span className="bb-check">✓</span> : <span className={`bb-badge ${status.cls}`}>{status.text}</span>}
        <span>
          {item.label}
          {suffixOf(item, { form })}
        </span>
      </div>
      {item.detail && <div className="bnf-req-detail">{item.detail}</div>}
      {item.form_detail && <div className="bnf-req-detail">{item.form_detail}</div>}
      {item.forced && item.client_note && (
        <div className="bnf-req-detail bnf-client-note">Client sees: “{item.client_note}”</div>
      )}
      {children}
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
      <div className="bnf-req-actions">
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
                if (file) writes.attach(item.kind, item.label, file);
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
              onChange={(event) => writes.tick(item.key, event.target.checked)}
            />
            <span>{controls.tick}</span>
          </label>
        )}
        {askRef && <AskButton dealId={dealId} refName={askRef} className="btn btn-secondary btn-sm" />}
        {after}
        {controls.override === 'undo' && (
          <button type="button" className="bnf-override-link" disabled={busy} title="Restore the automatic requirement"
            onClick={() => writes.requirement(item.key, '')}>
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
            onClick={() => writes.requirement(item.key, 'waived')}>
            Not needed
          </button>
        )}
      </div>
    </>
  );
  return wrap ? (
    <div className="bnf-req-item" role="group" aria-label={item.label}>
      {body}
    </div>
  ) : (
    body
  );
}
