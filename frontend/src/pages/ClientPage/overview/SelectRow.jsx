/**
 * A fact whose value is a pick (old ClientHeaderCard.jsx's `SelectRow` at 891f1b3): the `bb-account-row` look with a
 * `<select>` that commits on change. `options` are [{value, label, disabled?, title?}]: a refused move shows greyed,
 * with its sentence as the tooltip. The server's sentence for a refusal shows under the label (`error`).
 */
export default function SelectRow({ label, value, options, onChange, hint = '', empty = '', disabled, error = '' }) {
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
      <select
        className="bnf-intake-input bnf-cw-select"
        aria-label={label}
        value={value ?? ''}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
      >
        {empty && <option value="">{empty}</option>}
        {options.map((option) => (
          <option key={option.value} value={option.value} disabled={option.disabled} title={option.title}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  );
}
