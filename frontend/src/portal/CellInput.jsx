/*
 * One census answer's box (plan.md §3.9 `CellInput`; L88; C35). Ported from old Vantage 891f1b3 `CensusCellInput`:
 * a list when the column has accepted values (the tiers with Waived, gender, relationship, state), else text, with
 * the money sign the agent's form shows. A value on file that is none of the choices stays choosable, so opening the
 * page never changes it. SSN never reaches the portal (OQ16), so there is no masked box.
 *
 * field: {column, label, type, choices} · value · onChange(text) · disabled
 */
function choicesWith(field, value) {
  const choices = (field.choices || []).map((choice) => ({ value: choice.value, label: choice.label }));
  if (value && !choices.some((choice) => choice.value === value)) choices.push({ value, label: value });
  return choices;
}

export default function CellInput({ field, value, onChange, disabled = false }) {
  const text = value ?? '';
  if ((field.choices || []).length) {
    return (
      <select value={text} disabled={disabled} aria-label={field.label} onChange={(event) => onChange(event.target.value)}>
        <option value="">Select…</option>
        {choicesWith(field, text).map((choice) => (
          <option key={choice.value} value={choice.value}>
            {choice.label}
          </option>
        ))}
      </select>
    );
  }
  const box = (
    <input
      type="text"
      inputMode={['money', 'number'].includes(field.type) ? 'decimal' : undefined}
      placeholder={field.type === 'date' ? 'MM/DD/YYYY' : undefined}
      aria-label={field.label}
      value={text}
      disabled={disabled}
      onChange={(event) => onChange(event.target.value)}
    />
  );
  if (field.type === 'money') {
    return (
      <div className="bnf-intake-numwrap">
        <span className="bnf-intake-affix">$</span>
        {box}
      </div>
    );
  }
  return box;
}
