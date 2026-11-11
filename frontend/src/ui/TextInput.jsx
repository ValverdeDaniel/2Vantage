import cx from './cx';
import styles from './TextInput.module.css';

/**
 * A text input (or a textarea with `multiline`). All other props go to the element; `ref` works (React 19).
 * size: 'sm' | 'md'. Use inside <Field> for the label and error.
 */
export default function TextInput({ multiline = false, size = 'md', className, type = 'text', ...rest }) {
  const classes = cx(styles.input, styles[size], multiline && styles.multiline, className);
  if (multiline) return <textarea className={classes} rows={3} {...rest} />;
  return <input type={type} className={classes} {...rest} />;
}
