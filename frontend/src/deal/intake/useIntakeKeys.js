import { useEffect, useRef } from 'react';

/*
 * Enter and Tab on the form when no answer has the keyboard (B5; D-205), ported from old Vantage 891f1b3
 * `shared/useRestingFormKeys.js`. An open answer handles its own keys; these are the presses that would otherwise be
 * the browser's, and on a form the browser's next stop is a button.
 * - Nothing focused (an answer just closed, a click on the page): Enter and Tab both go on to the form's next answer.
 * - A button or tick box in the form, which only a click can have focused: Tab goes on too; Enter stays a click.
 * Anything else is not ours: another input, the navbar, a dialog or a drawer. `onKey(key, back, target)` decides.
 */
export default function useIntakeKeys({ enabled, rootRef, onKey }) {
  const live = useRef({ enabled, onKey });
  useEffect(() => {
    live.current = { enabled, onKey };
  });

  useEffect(() => {
    const onKeyDown = (event) => {
      if (!live.current.enabled || event.defaultPrevented || event.isComposing) return;
      if ((event.key !== 'Enter' && event.key !== 'Tab') || event.ctrlKey || event.metaKey || event.altKey) return;
      if (document.querySelector('[role="dialog"]')) return;
      const { target } = event;
      const idle = target === document.body || target === document.documentElement;
      const control =
        event.key === 'Tab' &&
        rootRef.current?.contains(target) &&
        target.matches?.('button, a[href], input[type="checkbox"], input[type="radio"]');
      if (!idle && !control) return;
      event.preventDefault();
      live.current.onKey(event.key, event.shiftKey, target);
    };
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [rootRef]);
}
