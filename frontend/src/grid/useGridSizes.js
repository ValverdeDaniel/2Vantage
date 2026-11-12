import { useLayoutEffect, useRef, useState } from 'react';
import { useAuth } from '../auth/useAuth';
import {
  EMPTY_SIZES,
  LEAD_COL_PX,
  MAX_PLAN_PX,
  MAX_ROW_PX,
  MIN_PLAN_PX,
  MIN_ROW_PX,
  clamp,
  fitWidth,
  readSizes,
  writeSizes,
} from './gridSizes';

/*
 * Plan columns and rows sized like Excel (plan.md §8.21; F36, D-160; the old shared/useGridSizes.js), on a grid
 * with plans as columns. One width for every plan column (dragging any plan's edge sets them all; by default five
 * fit across); rows one at a time by key (dragging a label's bottom edge); a double-click on a grip resets it;
 * ↺ Reset sizes (`reset`) clears both. A drag writes straight to the DOM and commits once on release, so a big grid
 * does not re-render on every mouse move. `padY` is a body cell's padding plus border, so a row's clip box fits.
 */

const storage = () => (typeof window === 'undefined' ? null : window.localStorage);

export default function useGridSizes({ grid, scrollRef, padY = 15 }) {
  const { user } = useAuth();
  const userId = user?.id ?? null;
  const [state, setState] = useState(() => ({ userId, sizes: readSizes(storage(), userId, grid) }));
  // Another user signs in on this browser: their own sizes, never these.
  if (state.userId !== userId) setState({ userId, sizes: readSizes(storage(), userId, grid) });
  const sizes = state.sizes;
  const [fit, setFit] = useState(200);
  const drag = useRef(null);
  const watch = useRef({ ro: null, box: null });

  // Five across follows the scroller's width; the scroller may mount late, so it is checked after every commit.
  useLayoutEffect(() => {
    const box = scrollRef.current;
    const w = watch.current;
    if (box === w.box) return;
    w.ro?.disconnect();
    w.ro = null;
    w.box = box;
    if (!box || typeof ResizeObserver === 'undefined') return;
    w.ro = new ResizeObserver(() => {
      const next = fitWidth(box.clientWidth);
      if (next != null) setFit((now) => (Math.abs(now - next) < 2 ? now : next));
    });
    w.ro.observe(box); // the observer reports the first size at once
  });
  useLayoutEffect(
    () => () => {
      watch.current.ro?.disconnect();
      watch.current.box = null; // a remount (StrictMode) observes again
    },
    [],
  );

  const planW = sizes.planW ?? fit;

  const commit = (next) => {
    setState((s) => ({ ...s, sizes: next }));
    writeSizes(storage(), userId, grid, next);
  };

  const endDrag = () => {
    const d = drag.current;
    drag.current = null;
    if (!d) return;
    d.table?.classList.remove('bnf-sizing');
    if (!d.moved) return;
    if (d.kind === 'col') commit({ ...sizes, planW: d.px });
    else commit({ ...sizes, rows: { ...sizes.rows, [d.key]: d.px } });
  };

  const startDrag = (event, init) => {
    if (event.button !== 0) return;
    event.preventDefault();
    event.stopPropagation();
    try {
      event.currentTarget.setPointerCapture(event.pointerId);
    } catch {
      /* an old browser */
    }
    const table = event.currentTarget.closest('table');
    table?.classList.add('bnf-sizing');
    drag.current = { ...init, table, moved: false };
  };

  const shared = { onClick: (event) => event.stopPropagation(), onPointerUp: endDrag, onLostPointerCapture: endDrag };

  /** Props for the grip on a plan column's right edge. */
  const colGrip = () => ({
    ...shared,
    className: 'bnf-col-grip',
    role: 'separator',
    'aria-orientation': 'vertical',
    'aria-label': 'Plan column width',
    title: 'Drag to size every plan column · double-click to fit five across',
    onPointerDown: (event) => startDrag(event, { kind: 'col', from: event.clientX, start: planW, px: planW }),
    onPointerMove: (event) => {
      const d = drag.current;
      if (!d || d.kind !== 'col') return;
      const px = clamp(Math.round(d.start + event.clientX - d.from), MIN_PLAN_PX, MAX_PLAN_PX);
      if (px === d.px) return;
      Object.assign(d, { px, moved: true });
      d.table?.style.setProperty('--bnf-plan-w', `${px}px`);
    },
    onDoubleClick: (event) => {
      event.preventDefault();
      event.stopPropagation();
      if (sizes.planW != null) commit({ ...sizes, planW: null });
    },
  });

  /** Props for the grip on a row's bottom edge, in its label cell. */
  const rowGrip = (key) => ({
    ...shared,
    className: 'bnf-row-grip',
    role: 'separator',
    'aria-orientation': 'horizontal',
    'aria-label': 'Row height',
    title: 'Drag to size this row · double-click to reset it',
    onPointerDown: (event) => {
      const tr = event.currentTarget.closest('tr');
      const start = Math.round(tr?.getBoundingClientRect().height || MIN_ROW_PX);
      startDrag(event, { kind: 'row', key, tr, from: event.clientY, start, px: start });
    },
    onPointerMove: (event) => {
      const d = drag.current;
      if (!d || d.kind !== 'row' || d.key !== key || !d.tr) return;
      const px = clamp(Math.round(d.start + event.clientY - d.from), MIN_ROW_PX, MAX_ROW_PX);
      if (px === d.px) return;
      Object.assign(d, { px, moved: true });
      d.tr.style.height = `${px}px`;
      d.tr.style.setProperty('--bnf-clip-h', `${px - padY}px`);
    },
    onDoubleClick: (event) => {
      event.preventDefault();
      event.stopPropagation();
      if (sizes.rows[key] == null) return;
      const rows = { ...sizes.rows };
      delete rows[key];
      commit({ ...sizes, rows });
    },
  });

  /** A row's own height, or nothing (three lines, then the full value on hover). */
  const rowStyle = (key) => {
    const px = sizes.rows[key];
    return px == null ? undefined : { height: `${px}px`, '--bnf-clip-h': `${px - padY}px` };
  };

  /** The table's width for `count` plan columns; every plan <col> reads `planCol()`. */
  const tableStyle = (count) => ({
    '--bnf-plan-w': `${planW}px`,
    width: `calc(${LEAD_COL_PX}px + ${count} * var(--bnf-plan-w))`,
  });

  return {
    planW,
    tableStyle,
    planCol: () => 'var(--bnf-plan-w)',
    colGrip,
    rowGrip,
    rowStyle,
    custom: sizes.planW != null || Object.keys(sizes.rows).length > 0,
    reset: () => commit(EMPTY_SIZES),
  };
}
