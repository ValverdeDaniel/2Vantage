/**
 * A native select. options: [{value, label, disabled?}]; `placeholder` adds a first option with value "".
 * Values are strings in the DOM: convert ids back with Number() in onChange. Inside <Field> the old `form-group`
 * rules style it; elsewhere pass an old class (`filter-select`, `bnf-select`).
 */
export default function Select({ options = [], placeholder, ...rest }) {
  return (
    <select {...rest}>
      {placeholder !== undefined && <option value="">{placeholder}</option>}
      {options.map((option) => (
        <option key={option.value} value={option.value} disabled={option.disabled}>
          {option.label}
        </option>
      ))}
    </select>
  );
}
