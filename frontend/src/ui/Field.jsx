import { cloneElement, isValidElement, useId } from 'react';
import cx from './cx';

/**
 * The old form field (`form-group`: the label above, the input full width), with its help line and error. The input
 * gets `id`, `aria-describedby` and `aria-invalid` automatically:
 *   <Field label="Client name" required error={errors.name}><TextInput value={…} onChange={…} /></Field>
 * or with a render function: <Field label="…">{(props) => <MyInput {...props} />}</Field>.
 * A group of chips or checkboxes passes `group`, so the label names the group instead of one input.
 */
export default function Field({ label, help, error, required, id, group = false, className, children }) {
  const autoId = useId();
  const inputId = id || autoId;
  const labelId = `${inputId}-label`;
  const helpId = help ? `${inputId}-help` : undefined;
  const errorId = error ? `${inputId}-error` : undefined;
  const describedBy = [helpId, errorId].filter(Boolean).join(' ') || undefined;
  const controlProps = group
    ? { 'aria-labelledby': labelId, 'aria-describedby': describedBy }
    : { id: inputId, 'aria-describedby': describedBy, 'aria-invalid': error ? true : undefined };

  let control = children;
  if (typeof children === 'function') control = children(controlProps);
  else if (isValidElement(children)) control = cloneElement(children, controlProps);

  const text = (
    <>
      {label}
      {required && <span title="Required"> *</span>}
    </>
  );
  return (
    <div className={cx('form-group', className)}>
      {group ? <label id={labelId}>{text}</label> : <label htmlFor={inputId}>{text}</label>}
      {control}
      {help && (
        <div id={helpId} className="bb-account-sub">
          {help}
        </div>
      )}
      {error && (
        <em id={errorId} className="bnf-saved-error">
          {error}
        </em>
      )}
    </div>
  );
}
