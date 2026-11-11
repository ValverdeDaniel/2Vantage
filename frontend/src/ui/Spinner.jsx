import cx from './cx';
import styles from './Spinner.module.css';
import VisuallyHidden from './VisuallyHidden';

/**
 * A spinning ring. `label` is read by screen readers (role=status); pass label="" when the surrounding control
 * already says it is busy. size: 'sm' | 'md' | 'lg'.
 */
export default function Spinner({ size = 'md', label = 'Loading…', className }) {
  const ring = <span className={cx(styles.ring, styles[size], className)} aria-hidden="true" />;
  if (!label) return ring;
  return (
    <span role="status" className={styles.wrap}>
      {ring}
      <VisuallyHidden>{label}</VisuallyHidden>
    </span>
  );
}

/** A centred spinner for a page or panel that has nothing to show yet. */
export function PageSpinner({ label = 'Loading…' }) {
  return (
    <div className={styles.page}>
      <Spinner size="lg" label={label} />
    </div>
  );
}
