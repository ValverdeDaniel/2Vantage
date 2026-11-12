import { useState } from 'react';
import copyText from '../clipboard';

/*
 * A new PIN, on the one screen that will ever show it (L64; old 891f1b3 `PinOnce.jsx`): only its hash is stored. It
 * travels apart from the link, so it is never in a copied message. `pin` is six digits; `name` is whose link it is.
 */
export default function PinOnce({ pin, name = '' }) {
  const [copied, setCopied] = useState(false);
  if (!pin) return null;
  async function copy() {
    setCopied(await copyText(pin));
    setTimeout(() => setCopied(false), 2000);
  }
  return (
    <div className="rr-pin-once" role="status">
      <span className="rr-pin-digits" aria-label={`PIN ${pin}`}>
        {pin.slice(0, 3)} {pin.slice(3)}
      </span>
      <button type="button" className="rr-linklike" onClick={copy} title="Copy the PIN alone, to give them another way than the link">
        {copied ? 'Copied ✓' : 'Copy PIN'}
      </button>
      <span className="rr-edit-note">
        Shown this once. Give it to {name || 'them'} yourself, by phone or text: it is not in the link you copy, so the
        link and the PIN travel apart.
      </span>
    </div>
  );
}
