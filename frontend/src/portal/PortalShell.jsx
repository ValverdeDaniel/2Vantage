import { useState } from 'react';
import { expiryWords } from './portalModel';

/*
 * The portal's frame (plan.md §8.20; L76, L78, L80): outside the app shell, no navbar and no Claude bubble. The old
 * top bar (`bb-portal-topbar`) with the agency's name and initial and "Secure link · expires in N days"; the preview
 * banner for View as client, and the thin note a signed-in person sees on a real link (old D-153 C0 #1: nothing they
 * type there is saved, since staff writes answer 403).
 */
export default function PortalShell({ agency, daysLeft = null, preview = false, staff = false, children }) {
  const [noteOpen, setNoteOpen] = useState(true);
  const name = agency?.name || 'Benefits';
  return (
    <div className={`bb-portal${preview || staff ? ' bnf-portal-readonly' : ''}`}>
      <div className="bb-portal-topbar">
        <div className="bb-portal-logo">{name.charAt(0)}</div>
        <div className="bb-portal-brand">{name}</div>
        {daysLeft !== null && <div className="bb-portal-expiry">{expiryWords(daysLeft)}</div>}
      </div>
      {preview && (
        <div className="bnf-portal-preview" role="status">
          <b>Preview</b> — this is what the client sees. Nothing you type here is saved.
        </div>
      )}
      {!preview && staff && noteOpen && (
        <div className="bnf-portal-staffnote" role="note">
          <span>
            You’re signed in to 2Vantage, so nothing here is saved as the client’s answer. Open it from View as client
            to preview it.
          </span>
          <button
            type="button"
            className="bnf-portal-staffnote-x"
            aria-label="Dismiss"
            title="Dismiss"
            onClick={() => setNoteOpen(false)}
          >
            ×
          </button>
        </div>
      )}
      <div className="bb-portal-body bnf-portal-wide">{children}</div>
    </div>
  );
}
