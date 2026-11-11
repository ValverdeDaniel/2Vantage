import cx from './cx';
import styles from './Skeleton.module.css';
import VisuallyHidden from './VisuallyHidden';

/**
 * Grey placeholder bars while a layout's first data loads (plan.md §8.17).
 *   lines (number of bars), height (bar height, CSS length), width (last bar's width), label (screen readers)
 */
export default function Skeleton({ lines = 3, height = '14px', width = '60%', label = 'Loading…', className }) {
  return (
    <div role="status" className={cx(styles.skeleton, className)}>
      {Array.from({ length: lines }, (_, index) => (
        <span
          key={index}
          aria-hidden="true"
          className={styles.bar}
          style={{ height, width: index === lines - 1 && lines > 1 ? width : '100%' }}
        />
      ))}
      <VisuallyHidden>{label}</VisuallyHidden>
    </div>
  );
}
