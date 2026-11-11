import styles from './Badge.module.css';
import cx from './cx';

/**
 * A short label. tone: 'neutral' | 'brand' | 'info' | 'success' | 'warning' | 'danger' | 'muted'.
 * The text carries the meaning; the colour only reinforces it.
 */
export default function Badge({ tone = 'neutral', icon, children, className, ...rest }) {
  return (
    <span className={cx(styles.badge, styles[tone], className)} {...rest}>
      {icon && <span aria-hidden="true">{icon}</span>}
      {children}
    </span>
  );
}
