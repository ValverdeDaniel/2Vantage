import { useEffect, useRef } from 'react';
import { keyAction, REVIEW_KEYS } from './keys';

/*
 * The review keys on the window (plan.md §8.16; E55, D124; the old useReviewHotkeys): one listener, so A, I, C, U and
 * F work wherever focus is on the tab — after a click on a toolbar button, or on the file beside the List. Off while
 * `enabled` is false (✎ Edit, a staged review). A handler that takes a key stops it, so no key acts twice.
 */
export default function useReviewHotkeys({ enabled, onKey, keys = REVIEW_KEYS }) {
  const live = useRef({});
  useEffect(() => {
    live.current = { enabled: Boolean(enabled), onKey, keys };
  });

  useEffect(() => {
    const onKeyDown = (event) => {
      const now = live.current;
      if (!now.enabled) return;
      const action = keyAction(event, now.keys);
      if (!action) return;
      event.preventDefault();
      event.stopPropagation();
      now.onKey?.(action);
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, []);
}
