import { useRef, useState } from 'react';

/**
 * One click-to-edit fact (M24; old Vantage 891f1b3 `overview/OverviewRow.jsx`, the `bb-account-row` pattern): click
 * (or Enter) to edit; Enter or blur commits, Escape cancels; an unchanged value never round-trips; a read-only row
 * only shows. `options` ([{value, label}]) makes it a select for a vocabulary (Funding, Situs state), which commits on
 * change. The server's sentence shows under the label (`error`); `after` sits beside the value (a source link).
 *   onCommit(raw): the trimmed text or the picked value; the caller writes it through the value's owner.
 */
export default function FactRow({
  label,
  value,
  display,
  onCommit,
  type = 'text',
  placeholder = '',
  readOnly = false,
  hint = '',
  options = null,
  error = '',
  after = null,
}) {
  const [editing, setEditing] = useState(false);
  const cancelled = useRef(false);
  const current = String(value ?? '');
  const shown = display !== undefined ? display : current;

  function commit(raw) {
    setEditing(false);
    if (cancelled.current) {
      cancelled.current = false;
      return;
    }
    const next = String(raw ?? '').trim();
    if (next !== current) onCommit(next);
  }

  function keys(event) {
    if (event.key === 'Enter') event.currentTarget.blur();
    if (event.key === 'Escape') {
      cancelled.current = true;
      event.currentTarget.blur();
    }
  }

  let control;
  if (editing && !readOnly && options) {
    control = (
      <select
        className="bb-account-input"
        aria-label={label}
        autoFocus
        defaultValue={current}
        onChange={(event) => commit(event.target.value)}
        onBlur={() => setEditing(false)}
        onKeyDown={(event) => event.key === 'Escape' && setEditing(false)}
      >
        <option value="">—</option>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    );
  } else if (editing && !readOnly) {
    control = (
      <input
        className="bb-account-input"
        aria-label={label}
        autoFocus
        type={type}
        defaultValue={current}
        placeholder={placeholder}
        onBlur={(event) => commit(event.target.value)}
        onKeyDown={keys}
      />
    );
  } else {
    control = (
      <div
        className={`bb-account-value ${shown ? '' : 'bb-empty'} ${readOnly ? 'bnf-ov-readonly' : ''}`}
        role={readOnly ? undefined : 'button'}
        tabIndex={readOnly ? undefined : 0}
        aria-label={readOnly ? undefined : `${label}: ${shown || 'not set'}. Click to edit`}
        onClick={readOnly ? undefined : () => setEditing(true)}
        onKeyDown={readOnly ? undefined : (event) => event.key === 'Enter' && setEditing(true)}
        title={readOnly ? undefined : 'Click to edit'}
      >
        {shown || '—'}
        {after}
      </div>
    );
  }

  return (
    <div className="bb-account-row bnf-ov-row">
      <div className="bb-account-label">
        {label}
        {hint && <span className="bnf-ov-row-hint">{hint}</span>}
        {error && (
          <span role="alert" className="bnf-ov-row-hint bb-rose">
            {error}
          </span>
        )}
      </div>
      {control}
    </div>
  );
}
