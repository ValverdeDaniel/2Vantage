import { useLayoutEffect, useRef } from 'react';

/*
 * Frozen panes on a plans-as-columns grid (plan.md §8.21; F35, D-154; styles/benefits-freeze). While the scroller
 * carries `.bnf-freeze`, its header row and label column stick; this measures them into --freeze-head-h and
 * --freeze-label-w, so the scroller's scroll-padding keeps a cell the keys move to clear of them, and follows the
 * header as it grows. Re-observes only when the <thead> it watches changes (the grid mounts late, or transposes).
 */
export default function useFreezePanes(ref) {
  const watched = useRef({ head: null, observer: null });

  useLayoutEffect(() => {
    const scroller = ref.current;
    const frozen = Boolean(scroller) && scroller.classList.contains('bnf-freeze');
    const head = frozen ? scroller.querySelector('thead') : null;
    const w = watched.current;
    if (head === w.head) return;
    w.observer?.disconnect();
    w.head = head;
    w.observer = null;
    if (!head || typeof ResizeObserver === 'undefined') return;
    const sync = () => {
      const corner = head.querySelector('th');
      scroller.style.setProperty('--freeze-head-h', `${head.offsetHeight}px`);
      scroller.style.setProperty('--freeze-label-w', `${corner ? corner.offsetWidth : 0}px`);
    };
    sync();
    w.observer = new ResizeObserver(sync);
    w.observer.observe(head);
  });

  useLayoutEffect(
    () => () => {
      watched.current.observer?.disconnect();
      watched.current.head = null; // a remount (StrictMode) observes again
    },
    [],
  );
}
