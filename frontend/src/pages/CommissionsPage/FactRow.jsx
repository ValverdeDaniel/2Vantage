import { useRef, useState } from 'react';

/*
 * One click-to-edit fact (891f1b3 `overview/OverviewRow.jsx`, the `bb-account-row` pattern): click to edit, Enter or
 * blur commits, Escape cancels without committing, an unchanged value never round-trips. `onCommit(raw)` writes.
 */
export default function FactRow({ label, value, display, onCommit, type = 'text', placeholder = '', readOnly, hint }) {
  const [editing, setEditing] = useState(false);
  const cancelled = useRef(false);
  const shown = display !== undefined ? display : value;

  function commit(raw) {
    setEditing(false);
    if (cancelled.current) {
      cancelled.current = false;
      return;
    }
    const next = String(raw ?? '').trim();
    if (next === String(value ?? '')) return;
    onCommit(next);
  }

  return (
    <div className="bb-account-row bnf-ov-row">
      <div className="bb-account-label">
        {label}
        {hint && <div className="bb-drop-meta" style={{ fontWeight: 400 }}>{hint}</div>}
      </div>
      {editing && !readOnly ? (
        <input
          className="bb-account-input"
          aria-label={label}
          autoFocus
          type={type}
          defaultValue={value ?? ''}
          placeholder={placeholder}
          onBlur={(event) => commit(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter') event.currentTarget.blur();
            if (event.key === 'Escape') {
              cancelled.current = true;
              event.currentTarget.blur();
            }
          }}
        />
      ) : (
        <div
          className={`bb-account-value ${shown ? '' : 'bb-empty'} ${readOnly ? 'bnf-ov-readonly' : ''}`}
          role={readOnly ? undefined : 'button'}
          tabIndex={readOnly ? undefined : 0}
          onClick={readOnly ? undefined : () => setEditing(true)}
          onKeyDown={readOnly ? undefined : (event) => event.key === 'Enter' && setEditing(true)}
          title={readOnly ? undefined : 'Click to edit'}
        >
          {shown || '—'}
        </div>
      )}
    </div>
  );
}
