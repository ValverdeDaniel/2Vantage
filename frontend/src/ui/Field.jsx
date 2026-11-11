import { cloneElement, isValidElement, useId } from 'react';
import cx from './cx';
import styles from './Field.module.css';

/**
 * Label + input slot + help + error. The input gets `id`, `aria-describedby` and `aria-invalid` automatically:
 *   <Field label="Client name" required error={errors.name}><TextInput value={…} onChange={…} /></Field>
 * or with a render function: <Field label="…">{(props) => <MyInput {...props} />}</Field>.
 * hideLabel keeps the label for screen readers only. `inline` puts the label beside the input.
 */
export default function Field({ label, help, error, required, id, hideLabel, inline, className, children }) {
  const autoId = useId();
  const inputId = id || autoId;
  const helpId = help ? `${inputId}-help` : undefined;
  const errorId = error ? `${inputId}-error` : undefined;
  const describedBy = [helpId, errorId].filter(Boolean).join(' ') || undefined;
  const controlProps = { id: inputId, 'aria-describedby': describedBy, 'aria-invalid': error ? true : undefined };

  let control = children;
  if (typeof children === 'function') control = children(controlProps);
  else if (isValidElement(children)) control = cloneElement(children, controlProps);

  return (
    <div className={cx(styles.field, inline && styles.inline, className)}>
      <label htmlFor={inputId} className={cx(styles.label, hideLabel && styles.hidden)}>
        {label}
        {required && (
          <span className={styles.required} title="Required">
            {' '}
            *
          </span>
        )}
      </label>
      <div className={styles.control}>
        {control}
        {help && (
          <p id={helpId} className={styles.help}>
            {help}
          </p>
        )}
        {error && (
          <p id={errorId} className={styles.error}>
            <span aria-hidden="true">⚠ </span>
            {error}
          </p>
        )}
      </div>
    </div>
  );
}
