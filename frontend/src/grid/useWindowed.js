import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { LEAD_COL_PX } from './gridSizes';
import { OVERSCAN, PLAN_COL_PX, ROW_GUESS_PX, colsInView, frame, nextRange, rowsInView } from './windowFrame';

/*
 * Draw only the plans on screen (plan.md §8.21; F40, Q.7; the old shared/useWindowedPlans.js). `axis` 'rows' (the
 * Advisor's plans as rows; `bodyRef` is its <tbody>) or 'cols' (plans as columns in `scrollRef`, each `size` px).
 * `on` is the caller's rule (its threshold); `pin` an index that must stay drawn (the open editor). Returns the
 * drawn range with its pads, `slice(list)` and `reveal(index, then)`: a plan not drawn yet is drawn first, then
 * `then` (the caller's scrollIntoView) runs. Everything that addresses a plan by key keeps the whole list: the keys
 * and the selection step through every row, and only what needs the DOM goes through `reveal`.
 */
export default function useWindowed({ axis = 'rows', count, on, pin = -1, size = 0, scrollRef, bodyRef }) {
  const rows = axis === 'rows';
  const overscan = OVERSCAN[rows ? 'rows' : 'cols'];
  const unit = size > 0 ? size : PLAN_COL_PX;
  const [range, setRange] = useState(null);
  const drawn = frame({ axis, count, on, range, pin, unit });
  const live = useRef({ ...drawn, count, unit });
  useLayoutEffect(() => {
    live.current = { ...drawn, count, unit };
  });
  const pending = useRef(null);

  // Rows: the drawn rows' real average height, so the pads track the page.
  const measure = useCallback(() => {
    const L = live.current;
    const body = bodyRef?.current;
    if (!rows || !body || L.last < L.first) return L.px || ROW_GUESS_PX;
    const height = body.getBoundingClientRect().height - L.before - L.after;
    const px = height > 0 ? height / (L.last - L.first + 1) : 0;
    return px >= 8 ? Math.round(px * 10) / 10 : L.px || ROW_GUESS_PX;
  }, [rows, bodyRef]);

  const update = useCallback(() => {
    const L = live.current;
    if (!L.on) return;
    const px = measure();
    let seen = null;
    if (rows && bodyRef?.current) {
      seen = rowsInView(bodyRef.current.getBoundingClientRect().top, window.innerHeight, px, L.count);
    } else if (!rows && scrollRef.current) {
      const box = scrollRef.current;
      seen = colsInView(box.scrollLeft, box.clientWidth, LEAD_COL_PX, L.unit, L.count);
    }
    if (seen) setRange((now) => nextRange(now, seen, L.count, px, overscan));
  }, [rows, bodyRef, scrollRef, measure, overscan]);

  // One listener per grid: any scroll on the page (capture: a scroller's own scroll does not bubble) and a resize.
  useEffect(() => {
    let raf = 0;
    const onMove = () => {
      if (raf || !live.current.on) return;
      raf = requestAnimationFrame(() => {
        raf = 0;
        update();
      });
    };
    window.addEventListener('scroll', onMove, true);
    window.addEventListener('resize', onMove);
    return () => {
      if (raf) cancelAnimationFrame(raf);
      window.removeEventListener('scroll', onMove, true);
      window.removeEventListener('resize', onMove);
    };
  }, [update]);

  // A new list (or windowing turned on) is measured on the next frame; a reveal waiting for its plan runs once it is
  // drawn, or is dropped if a scroll moved the window elsewhere first.
  const shape = drawn.on ? count : -1;
  useLayoutEffect(() => {
    if (shape < 0) return undefined;
    const raf = requestAnimationFrame(() => update());
    return () => cancelAnimationFrame(raf);
  }, [shape, update]);
  useLayoutEffect(() => {
    const then = pending.current;
    if (!then) return;
    const L = live.current;
    if (!L.on || (then.index >= L.first && then.index <= L.last)) {
      pending.current = null;
      then.run();
    } else if ((then.tries += 1) > 2) pending.current = null;
  });

  const reveal = useCallback(
    (index, then) => {
      const L = live.current;
      const run = then || (() => {});
      if (!L.on || index == null || index < 0 || index >= L.count || (index >= L.first && index <= L.last)) {
        run();
        return;
      }
      pending.current = { index, run, tries: 0 };
      const half = rows ? OVERSCAN.rows : OVERSCAN.cols * 2;
      setRange({
        first: Math.max(0, index - half),
        last: Math.min(L.count - 1, index + half),
        n: L.count,
        px: L.px,
      });
    },
    [rows],
  );

  return {
    ...drawn,
    slice: (list) => (drawn.on ? list.slice(drawn.first, drawn.last + 1) : list),
    reveal,
  };
}
