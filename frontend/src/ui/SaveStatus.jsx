import { useEffect, useState } from 'react';
import { errorText } from '../lib/errors';
import cx from './cx';

/**
 * The quiet save marker beside a value (plan.md §8.22), in the old "Saving…" note's look (`bnf-q-saving`):
 * "Saving…", then "✓ Saved" for a moment, or the error in rose.
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
  if (status === 'pending') content = 'Saving…';
  else if (status === 'success' && hiddenStamp !== stamp) content = '✓ Saved';
  else if (status === 'error') content = <span className="bb-rose">⚠ {errorText(error)}</span>;

  return (
    <span className={cx('bnf-q-saving', className)} role="status" aria-live="polite">
      {content}
    </span>
  );
}
