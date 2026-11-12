import { useState } from 'react';

/*
 * "Where do I find this?" (plan.md §8.20; L83). Ported from old Vantage 891f1b3 `FieldHelp`: plain-language
 * guidance a click away; a broker's own note shows open and says it is theirs.
 */
export default function FieldHelp({ text, fromBroker = false }) {
  const [open, setOpen] = useState(false);
  if (!text) return null;
  if (fromBroker) {
    return (
      <div className="bnf-field-broker-note">
        <strong>From your broker:</strong> {text}
      </div>
    );
  }
  return (
    <span className="bnf-field-help">
      <button type="button" className="bnf-field-help-toggle" aria-expanded={open} onClick={() => setOpen((v) => !v)}>
        Where do I find this?
      </button>
      {open && <div className="bnf-field-help-body">{text}</div>}
    </span>
  );
}
