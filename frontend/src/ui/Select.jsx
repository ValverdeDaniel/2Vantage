import cx from './cx';
import styles from './Select.module.css';

/**
 * A native select. options: [{value, label, disabled?}]; `placeholder` adds a first option with value "".
 * Values are strings in the DOM: convert ids back with Number() in onChange. size: 'sm' | 'md'.
 */
export default function Select({ options = [], placeholder, size = 'md', className, ...rest }) {
  return (
    <select className={cx(styles.select, styles[size], className)} {...rest}>
      {placeholder !== undefined && <option value="">{placeholder}</option>}
      {options.map((option) => (
        <option key={option.value} value={option.value} disabled={option.disabled}>
          {option.label}
        </option>
      ))}
    </select>
  );
}
