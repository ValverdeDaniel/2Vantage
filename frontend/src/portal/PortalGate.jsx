import { useState } from 'react';
import { detailOf, verifyPin } from './portalApi';

/*
 * The PIN screen (plan.md §8.20; L77; OQ80). Ported from old Vantage 891f1b3 `linkguard/LinkCodeGate.jsx` in its
 * markup, classes (`lg-*`) and words, PIN side only: an emailed code waits for outbound mail (L65). Nothing on the
 * link shows until the six digits are right; five wrong ones lock it until whoever sent it makes a new PIN.
 */
export default function PortalGate({ token, agency, locked = false, onVerified }) {
  const [code, setCode] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(locked ? 'locked' : '');
  const [lockedNow, setLockedNow] = useState(locked);

  async function verify(event) {
    event.preventDefault();
    if (code.length < 6) return;
    setBusy(true);
    setError('');
    try {
      await verifyPin(token, code);
      onVerified();
    } catch (failure) {
      const body = failure?.response?.data || {};
      if (body.locked) setLockedNow(true);
      setError(detailOf(failure) || 'That PIN did not work.');
      setCode('');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="lg-gate">
      <div className="lg-card">
        <div className="lg-brand">{agency?.name || 'Your benefits team'}</div>
        <h1 className="lg-title">This link is protected</h1>
        <p className="lg-text">
          What we asked for opens once you enter the PIN you were given. Ask whoever sent you this link if you do not
          have it. It keeps a forwarded link from showing your information to anyone else.
        </p>
        {lockedNow ? (
          <div className="lg-error" role="alert">
            {error && error !== 'locked'
              ? error
              : 'This link is locked after too many wrong PINs. Ask whoever sent it to you for a new PIN.'}
          </div>
        ) : (
          <form onSubmit={verify} className="lg-form">
            <label className="lg-label" htmlFor="lg-code">
              Your 6-digit PIN
            </label>
            <input
              id="lg-code"
              className="lg-input"
              inputMode="numeric"
              autoComplete="off"
              maxLength={6}
              value={code}
              onChange={(event) => setCode(event.target.value.replace(/\D/g, ''))}
              autoFocus
            />
            <div className="lg-actions">
              <button type="submit" className="btn btn-primary lg-btn" disabled={busy || code.length < 6}>
                {busy ? 'Checking…' : 'Open'}
              </button>
            </div>
            {error && (
              <div className="lg-error" role="alert">
                {error}
              </div>
            )}
          </form>
        )}
      </div>
    </div>
  );
}
