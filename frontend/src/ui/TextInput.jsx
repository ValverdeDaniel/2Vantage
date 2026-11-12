/**
 * A text input (or a textarea with `multiline`). Inside <Field> the old `form-group` rules style it; elsewhere pass
 * an old class (e.g. `bnf-intake-input`). All other props go to the element; `ref` works (React 19).
 */
export default function TextInput({ multiline = false, type = 'text', ...rest }) {
  if (multiline) return <textarea rows={3} {...rest} />;
  return <input type={type} {...rest} />;
}
