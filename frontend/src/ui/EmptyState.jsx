import cx from './cx';
import styles from './EmptyState.module.css';

/**
 * What an empty list or page shows: a title, an optional message (children) and the next action.
 *   title, children, action (a button or link), compact (less padding, for panels)
 */
export default function EmptyState({ title, children, action, compact = false, className }) {
  return (
    <div className={cx(styles.empty, compact && styles.compact, className)}>
      <p className={styles.title}>{title}</p>
      {children && <div className={styles.message}>{children}</div>}
      {action && <div className={styles.action}>{action}</div>}
    </div>
  );
}
