import { errorText } from '../lib/errors';
import Button from './Button';
import cx from './cx';
import styles from './InlineError.module.css';

/**
 * A failed request, shown where its data would be, with Try again (plan.md §8.17).
 *   error (any error; turned into text), title, onRetry, retrying (spinner on the button), compact
 */
export default function InlineError({ error, title = 'Could not load this.', onRetry, retrying = false, compact }) {
  return (
    <div role="alert" className={cx(styles.box, compact && styles.compact)}>
      <span className={styles.icon} aria-hidden="true">
        ⚠
      </span>
      <div className={styles.text}>
        <p className={styles.title}>{title}</p>
        {error && <p className={styles.detail}>{errorText(error)}</p>}
      </div>
      {onRetry && (
        <Button size="sm" onClick={onRetry} busy={retrying}>
          Try again
        </Button>
      )}
    </div>
  );
}
