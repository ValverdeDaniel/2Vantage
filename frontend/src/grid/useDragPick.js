import { useEffect, useRef } from 'react';
import { dragPick } from './cellPick';

/*
 * A drag across a grid's cells (plan.md §8.21; E51; the drag half of the old shared/useGridSelection.js). It paints
 * `gs-picked` straight onto the cells (`[data-gs]`) as the pointer moves and saves the pick once, on release, so a
 * 7,000-cell file never re-renders per cell crossed. Near the scroller's edge it scrolls (edge scroll), and a pointer
 * dragged past an edge keeps stretching along it. `shape()` gives {R, C} now; `onDone(picks, anchor, at)` saves.
 */

const EDGE = 40; // px from the scroller's edge that scrolls it mid-drag
const EDGE_STEP = 18; // px per frame

export default function useDragPick({ containerRef, shape, onDone }) {
  const drag = useRef(null);
  const live = useRef({ shape, onDone });
  useEffect(() => {
    live.current = { shape, onDone };
  });

  useEffect(() => {
    const root = () => containerRef.current;
    const cellAt = (x, y) => {
      const el = document.elementFromPoint(x, y)?.closest?.('[data-gs]');
      if (!el || !root()?.contains(el)) return null;
      const [r, ...rest] = el.dataset.gs.split('|');
      return { r, c: rest.join('|') };
    };
    const paint = (next) => {
      const d = drag.current;
      for (const key of d.painted) if (!next.has(key)) d.els.get(key)?.classList.remove('gs-picked');
      for (const key of next) if (!d.painted.has(key)) d.els.get(key)?.classList.add('gs-picked');
      d.painted = next;
    };
    const extendTo = (pos) => {
      const d = drag.current;
      if (!d || !pos) return;
      const key = `${pos.r}|${pos.c}`;
      if (key === d.last) return;
      d.last = key;
      if (!d.moved) {
        d.moved = true;
        root()?.classList.add('gs-dragging');
      }
      window.getSelection?.()?.removeAllRanges?.();
      const { R, C } = live.current.shape();
      paint(dragPick(R, C, d.base, d.anchor, pos, d.add));
      d.pos = pos;
    };
    const follow = () => {
      const d = drag.current;
      const box = root()?.getBoundingClientRect();
      if (!d || !box) return;
      const x = Math.min(Math.max(d.x, box.left + 2), box.right - 2);
      const y = Math.min(Math.max(d.y, box.top + 2), box.bottom - 2);
      extendTo(cellAt(x, y));
    };
    const tick = () => {
      const d = drag.current;
      const el = root();
      if (!d || !el) return;
      d.raf = null;
      const box = el.getBoundingClientRect();
      const dx = d.x < box.left + EDGE ? -EDGE_STEP : d.x > box.right - EDGE ? EDGE_STEP : 0;
      const dy = d.y < box.top + EDGE ? -EDGE_STEP : d.y > box.bottom - EDGE ? EDGE_STEP : 0;
      const before = [el.scrollLeft, el.scrollTop];
      if (dx) el.scrollLeft += dx;
      if (dy) el.scrollTop += dy;
      follow();
      if (el.scrollLeft !== before[0] || el.scrollTop !== before[1]) d.raf = requestAnimationFrame(tick);
    };
    const end = (event) => {
      const d = drag.current;
      if (!d) return;
      if (d.raf) cancelAnimationFrame(d.raf);
      if (event?.type === 'mouseup') {
        d.x = event.clientX;
        d.y = event.clientY;
        follow();
      }
      drag.current = null;
      root()?.classList.remove('gs-dragging');
      if (d.moved) live.current.onDone(d.painted, d.anchor, d.pos || d.anchor);
    };
    const onMove = (event) => {
      const d = drag.current;
      if (!d) return;
      if (!(event.buttons & 1)) {
        end();
        return;
      }
      d.x = event.clientX;
      d.y = event.clientY;
      if (!d.raf) d.raf = requestAnimationFrame(tick);
    };
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', end);
    window.addEventListener('blur', end);
    return () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', end);
      window.removeEventListener('blur', end);
    };
  }, [containerRef]);

  /** Start a drag at `pos` over `base` (the pick it keeps), adding cells or (`add` false) dropping them. */
  const start = (pos, base, add, event, painted) => {
    const els = new Map();
    containerRef.current?.querySelectorAll?.('[data-gs]').forEach((el) => els.set(el.dataset.gs, el));
    drag.current = {
      base,
      add,
      anchor: pos,
      last: `${pos.r}|${pos.c}`,
      moved: false,
      painted,
      els,
      pos: null,
      x: event.clientX,
      y: event.clientY,
      raf: null,
    };
  };

  return { start, active: () => Boolean(drag.current) };
}
