import { useRef, useState } from 'react';

/*
 * A commission amount — a percentage, flat dollars a year or per employee per month (§4.6; H1) — in the old look
 * (`commissions/CompInput.jsx` at 891f1b3, `bnf-com-comp`). Saves {type, value} on blur or Enter; a blank saves null
 * to clear it; Escape puts the stored value back. The server parses and refuses (deals/comp.py), never the browser.
 * The types, their buttons and units come from /api/meta/'s `commission_types`. Shared by intake's in-force
 * commission (slice 11) and the commission tab's agreed rates (slice 48).
 */
export default function CompInput({ value, types = [], onCommit, small = false, disabled = false, label }) {
  const stored = { type: value?.type || 'pct', text: value?.value ?? '' };
  const [draft, setDraft] = useState(null);
  const escaped = useRef(false); // Escape blurs without saving
  const type = draft?.type ?? stored.type;
  const text = draft?.text ?? stored.text;

  function commit(nextType = type, nextText = text) {
    setDraft(null);
    const trimmed = String(nextText ?? '').trim();
    if (trimmed === String(stored.text) && nextType === stored.type) return;
    onCommit(trimmed ? { type: nextType, value: trimmed } : null);
  }

  const current = types.find((entry) => entry.key === type);
  return (
    <div className={`bnf-com-comp ${small ? 'bnf-com-comp-sm' : ''}`}>
      <div className="bnf-com-comp-type" role="group" aria-label="Commission type">
        {types.map((entry) => (
          <button
            key={entry.key}
            type="button"
            className={entry.key === type ? 'active' : ''}
            aria-pressed={entry.key === type}
            disabled={disabled}
            title={entry.label}
            onClick={() => {
              if (String(text).trim()) commit(entry.key, text);
              else setDraft({ type: entry.key, text });
            }}
          >
            {entry.short}
          </button>
        ))}
      </div>
      <input
        type="text"
        inputMode="decimal"
        aria-label={label || 'Commission'}
        value={text}
        placeholder={current?.example || ''}
        disabled={disabled}
        onChange={(event) => setDraft({ type, text: event.target.value })}
        onBlur={() => {
          if (escaped.current) {
            escaped.current = false;
            setDraft(null);
          } else if (draft) commit();
        }}
        onKeyDown={(event) => {
          if (event.key === 'Enter') event.currentTarget.blur();
          if (event.key === 'Escape') {
            escaped.current = true;
            event.currentTarget.blur();
          }
        }}
      />
      {current?.unit && <span className="bnf-com-comp-unit">{current.unit}</span>}
    </div>
  );
}
