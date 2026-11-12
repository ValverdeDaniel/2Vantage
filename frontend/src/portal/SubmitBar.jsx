import { plural } from './portalModel';

/*
 * The portal's foot (plan.md §8.20; L95, L98, L106). Ported from old Vantage 891f1b3 `BenefitsClientPortal.jsx`: the
 * "✓ Saved automatically at …" note, a save that did not land said over the form with Try again (D-208), the lock
 * line with "Stuck? Get help ▸" to the agency's own address (P10), Save progress, and Submit, which first says how
 * many items are still open ("N items still open — submit anyway?"). On a phone the buttons wrap under the line.
 */
export function SavedNote({ note, problem, onRetry, busy }) {
  return (
    <>
      {note && (
        // The old sheets give `bnf-saved-note` one line with an ellipsis (a plan-finder rule of the same name); on a
        // phone the sentence wraps instead (§8.20, slice 54).
        <div className="bb-portal-card bnf-saved-note" role="status" style={{ whiteSpace: 'normal' }}>
          <span className="bb-check">✓</span> {note}
        </div>
      )}
      {problem && (
        <div className="bb-portal-card bnf-save-problem" role="alert">
          <span>{problem}</span>
          {onRetry && (
            <button type="button" className="btn btn-secondary btn-sm" onClick={onRetry} disabled={busy}>
              Try again
            </button>
          )}
        </div>
      )}
    </>
  );
}

export default function SubmitBar({ agency, accountName, short, open, confirming, busy, disabled, onSave, onSubmit }) {
  const subject = encodeURIComponent(`Help with ${accountName || 'our'} benefits intake`);
  return (
    <div className="bb-portal-footer" style={{ flexWrap: 'wrap', gap: 12 }}>
      <div className="bb-portal-lock">
        🔒 Only the items above are shared with you.
        {agency?.email && (
          <>
            {' · '}
            <a className="bnf-help-link" href={`mailto:${agency.email}?subject=${subject}`}>
              Stuck? Get help ▸
            </a>
          </>
        )}
      </div>
      <div className="bnf-portal-actions" style={{ flexWrap: 'wrap' }}>
        <button type="button" className="btn btn-secondary bb-portal-submit" onClick={onSave} disabled={busy || disabled}>
          {busy ? 'Saving…' : 'Save progress'}
        </button>
        <button type="button" className="btn btn-primary bb-portal-submit" onClick={onSubmit} disabled={busy || disabled}>
          {busy ? 'Working…' : confirming ? `${plural(open, 'item')} still open — submit anyway?` : `Submit to ${short} ▸`}
        </button>
      </div>
    </div>
  );
}

export function ThankYou({ short }) {
  return (
    <div className="bb-portal-card bb-portal-center bb-portal-thanks">
      <div className="bb-done-check bb-done-check-lg">✓</div>
      <div className="bb-portal-thanks-title">Thank you — sent to {short}</div>
      <div className="bb-subtitle">Your benefits team has what they need. You can close this window.</div>
    </div>
  );
}
