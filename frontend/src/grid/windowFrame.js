/*
 * Which rows (or plan columns) a big grid draws (plan.md §8.21; F40, Q.7; the old shared/useWindowedPlans.js). Above
 * a threshold a grid draws the plans in view plus a few either side, and a pad before and after holds the height
 * (or width) of the rest, so the scrollbar and every drawn cell's place are as they were. Pure: `useWindowed` feeds
 * it what it measured.
 */

export const WINDOW_ROWS_OVER = 150;
export const WINDOW_COLS_OVER = 40;
export const PLAN_COL_PX = 160;
export const ROW_GUESS_PX = 40;
export const OVERSCAN = { rows: 20, cols: 4 };
export const FIRST_DRAW = { rows: 60, cols: 12 }; // before the first measure

const clamp = (n, lo, hi) => Math.max(lo, Math.min(hi, n));

/**
 * The drawn range for a list of `count`: {on, first, last, before, after} (pads in px). `range` is the last
 * measured {first, last, n, px} or null; `pin` an index that must stay drawn (the open editor); `unit` the px of one
 * plan column (columns) — rows use the measured height.
 */
export function frame({ axis = 'rows', count, on, range, pin = -1, unit = PLAN_COL_PX }) {
  const active = Boolean(on) && count > 0;
  if (!active) return { on: false, first: 0, last: count - 1, before: 0, after: 0, px: ROW_GUESS_PX };
  const r =
    range && range.n === count ? range : { first: 0, last: Math.min(count - 1, FIRST_DRAW[axis]), px: range?.px };
  let { first, last } = r;
  if (pin >= 0 && pin < count) {
    first = Math.min(first, pin);
    last = Math.max(last, pin);
  }
  const px = r.px || ROW_GUESS_PX;
  const size = axis === 'rows' ? px : unit;
  return {
    on: true,
    first,
    last,
    before: Math.round(first * size),
    after: Math.round((count - 1 - last) * size),
    px,
  };
}

/** The indexes in view now, without overscan: rows from the body's top and the window's height. */
export function rowsInView(bodyTop, viewHeight, px, count) {
  const from = Math.floor(Math.max(0, -bodyTop) / px);
  const to = Math.ceil(Math.max(0, viewHeight - bodyTop) / px);
  return [clamp(from, 0, count - 1), clamp(to, 0, count - 1)];
}

/** The plan columns in view: plan i spans lead + i*size .. lead + (i+1)*size; the sticky lead covers `lead` px. */
export function colsInView(scrollLeft, clientWidth, lead, size, count) {
  const from = Math.floor(scrollLeft / size);
  const to = Math.ceil((scrollLeft + clientWidth - lead) / size);
  return [clamp(from, 0, count - 1), clamp(to, 0, count - 1)];
}

/**
 * The range to draw for what is in view (`seen`), or `now` unchanged while the view stays inside what is drawn with
 * half the overscan to spare — so a scroll inside the overscan costs nothing.
 */
export function nextRange(now, seen, count, px, overscan) {
  const margin = Math.floor(overscan / 2);
  const fine =
    now &&
    now.n === count &&
    Math.abs((now.px || 0) - px) < 2 &&
    (now.first === 0 || seen[0] - now.first >= margin) &&
    (now.last === count - 1 || now.last - seen[1] >= margin);
  if (fine) return now;
  return { first: Math.max(0, seen[0] - overscan), last: Math.min(count - 1, seen[1] + overscan), n: count, px };
}
