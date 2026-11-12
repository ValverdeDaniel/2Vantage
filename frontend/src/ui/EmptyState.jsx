import cx from './cx';

/**
 * What an empty list or page shows, in the old `empty-state` box: the words, an optional line under them and the
 * next action (plan.md §8.22).
 *   title, children, action (a button or link), className
 */
export default function EmptyState({ title, children, action, className }) {
  return (
    <div className={cx('empty-state', className)}>
      <div>{title}</div>
      {children && <div className="bb-mt">{children}</div>}
      {action && <div className="bb-mt">{action}</div>}
    </div>
  );
}
