import cx from './cx';
import styles from './IconButton.module.css';

/**
 * A square button showing only an icon. `label` is required: it is the accessible name and the tooltip.
 * variant: 'ghost' | 'secondary' | 'danger' · size: 'sm' | 'md'.
 */
export default function IconButton({ label, children, variant = 'ghost', size = 'md', className, type, ...rest }) {
  return (
    <button
      type={type || 'button'}
      aria-label={label}
      title={label}
      className={cx(styles.icon, styles[variant], styles[size], className)}
      {...rest}
    >
      <span aria-hidden="true">{children}</span>
    </button>
  );
}
