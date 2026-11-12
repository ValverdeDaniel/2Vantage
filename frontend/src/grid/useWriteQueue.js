import { useCallback, useLayoutEffect, useRef, useState } from 'react';
import { errorText } from '../lib/errors';
import { createWriteQueue } from './writeQueue';

/*
 * A grid's per-cell write queue (plan.md §8.21; `writeQueue.js` holds the rules): `enqueue(cell, value, base)`
 * returns the queue's promise ({before, after}, null when replaced, or the server's error). A failure calls
 * `onFailed(cell, saved)` so the owner restores the last saved value, and the server's message stays on the cell
 * (`errorOf(cell)`) until that cell is written again. `onIdle()` runs once a burst has settled (one refetch).
 */

/** A failed write in words: a refusal's own sentence (409 {detail, keys}), else the error as the app words it. */
export function refusalText(error) {
  const detail = error?.response?.data?.detail;
  return typeof detail === 'string' ? detail : errorText(error);
}

export default function useWriteQueue({ send, onFailed, onIdle }) {
  const live = useRef({ send, onFailed, onIdle });
  useLayoutEffect(() => {
    live.current = { send, onFailed, onIdle };
  });
  const [errors, setErrors] = useState({});
  const queueRef = useRef(null);

  // Made on first use, from a handler: the queue outlives every render.
  const queue = useCallback(() => {
    if (!queueRef.current) {
      queueRef.current = createWriteQueue({
        send: (cell, value, expect) => live.current.send(cell, value, expect),
        onFailed: (cell, error, saved) => {
          setErrors((now) => ({ ...now, [cell]: refusalText(error) }));
          live.current.onFailed?.(cell, saved, error);
        },
        onIdle: () => live.current.onIdle?.(),
      });
    }
    return queueRef.current;
  }, []);

  const enqueue = useCallback(
    (cell, value, base) => {
      setErrors((now) => {
        if (!(cell in now)) return now;
        const next = { ...now };
        delete next[cell];
        return next;
      });
      return queue().enqueue(cell, value, base);
    },
    [queue],
  );

  const settle = useCallback(() => queue().settle(), [queue]);

  return { enqueue, settle, errorOf: (cell) => errors[cell] || '' };
}
