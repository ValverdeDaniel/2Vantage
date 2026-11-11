import { useEffect, useState } from 'react';
import { errorText } from '../lib/errors';
import cx from './cx';
import styles from './SaveStatus.module.css';
import Spinner from './Spinner';

/**
 * The quiet save marker beside a value (plan.md §8.17): "Saving…", then a tick for a moment, or the error.
 * Pass a TanStack mutation: <SaveStatus mutation={update} />, or status ('idle'|'pending'|'success'|'error') + error.
 */
export default function SaveStatus({ mutation, status = mutation?.status, error = mutation?.error, className }) {
  const stamp = mutation?.submittedAt ?? status;
  const [hiddenStamp, setHiddenStamp] = useState(null);

  useEffect(() => {
    if (status !== 'success') return undefined;
    const timer = setTimeout(() => setHiddenStamp(stamp), 2500);
    return () => clearTimeout(timer);
  }, [status, stamp]);

  let content = null;
  if (status === 'pending') {
    content = (
      <>
        <Spinner size="sm" label="" /> Saving…
      </>
    );
  } else if (status === 'success' && hiddenStamp !== stamp) {
    content = (
      <>
        <span aria-hidden="true" className={styles.tick}>
          ✓
        </span>{' '}
        Saved
      </>
    );
  } else if (status === 'error') {
    content = (
      <span className={styles.error}>
        <span aria-hidden="true">⚠ </span>
        {errorText(error)}
      </span>
    );
  }

  return (
    <span className={cx(styles.status, className)} role="status" aria-live="polite">
      {content}
    </span>
  );
}
