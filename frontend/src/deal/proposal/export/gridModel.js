import { cellKey } from './workbookModel';

/*
 * What the workbook grid needs about one tab (plan.md §8.14; J116; the old shared/WorkbookGrid.jsx at 891f1b3): the
 * server's worked-out tab (proposals/viewer/workbook.py) in, lookups out. Nothing here computes a value or applies a
 * number format; the server did both, as Excel does. Pure.
 */

export const HEAD_H = 20;
export const ROW_HEAD_W = 40;
export const PT_PX = 4 / 3;
export const INDENT_PX = 9;
export const WINDOW_OVER = 12; // rows drawn above and below the visible ones
export const WINDOW_FROM = 160; // a tab this short is drawn whole
export const FLAGS = { NUMBER: 1, ERROR: 2, HASHED: 4, LINK: 8, LOGICAL: 16 };
export const VA = { top: 'flex-start', middle: 'center', bottom: 'flex-end' };

/** 0 → 'A', 26 → 'AA'. */
export function columnLetter(index) {
  let n = index + 1;
  let out = '';
  while (n > 0) {
    const rem = (n - 1) % 26;
    out = String.fromCharCode(65 + rem) + out;
    n = Math.floor((n - 1) / 26);
  }
  return out;
}

/** A border's width in pixels ("2px solid #000" reads 2). */
export const edge = (line) => (line ? parseInt(line, 10) || 1 : 0);

/** A cell's look (documents/sheet_style.py's keys) as an inline style at `zoom` (1 = 100%). */
export function lookStyle(st, zoom) {
  const s = {};
  if (st.bg) s.background = st.bg;
  if (st.fg) s.color = st.fg;
  if (st.b) s.fontWeight = 700;
  if (st.i) s.fontStyle = 'italic';
  if (st.u || st.x) s.textDecoration = [st.u && 'underline', st.x && 'line-through'].filter(Boolean).join(' ');
  s.fontSize = `${Math.round((st.s || 11) * PT_PX * zoom * 10) / 10}px`;
  s.textAlign = st.ha || 'left';
  if (st.wrap) s.whiteSpace = 'pre-wrap';
  if (st.bt) s.borderTop = st.bt;
  if (st.br) s.borderRight = st.br;
  if (st.bb) s.borderBottom = st.bb;
  if (st.bl) s.borderLeft = st.bl;
  return s;
}

/** The tab's cells by key, its merges (heads, the cells they cover and whose head covers them) and drop-downs. */
export function tabModel(tab) {
  const cells = new Map();
  (tab?.cells || []).forEach((item) => cells.set(cellKey(item[0], item[1]), item));
  const heads = new Map();
  const covered = new Set();
  const headOf = new Map();
  (tab?.merges || []).forEach(([r, c, rs, cs]) => {
    heads.set(cellKey(r, c), [rs, cs]);
    for (let i = r; i < r + rs; i += 1) {
      for (let j = c; j < c + cs; j += 1) {
        if (i !== r || j !== c) {
          covered.add(cellKey(i, j));
          headOf.set(cellKey(i, j), [r, c]);
        }
      }
    }
  });
  const drops = new Map();
  (tab?.dropdowns || []).forEach((drop) => {
    drop.cells.forEach(([r1, c1, r2, c2]) => {
      for (let r = r1; r <= r2; r += 1) {
        for (let c = c1; c <= c2; c += 1) drops.set(cellKey(r, c), drop);
      }
    });
  });
  return { cells, heads, covered, headOf, drops };
}

/** [0, a, a+b, …]: where each size starts. */
export function prefix(sizes) {
  const out = [0];
  sizes.forEach((size, i) => out.push(out[i] + size));
  return out;
}

/** The rows to draw ({first, last}, indexes into the drawn rows) for a scroll at `top` of `height` pixels: the frozen
 * rows always, then those near the view; a short tab whole. `tops` is prefix() of the row heights. */
export function rowWindow(tops, count, frozen, view, windowed) {
  if (!windowed) return { first: frozen, last: count - 1 };
  const from = view.top + tops[frozen];
  const to = view.top + view.height;
  let lo = frozen;
  while (lo < count - 1 && tops[lo + 1] < from) lo += 1;
  let hi = lo;
  while (hi < count - 1 && tops[hi] < to) hi += 1;
  return { first: Math.max(frozen, lo - WINDOW_OVER), last: Math.min(count - 1, hi + WINDOW_OVER) };
}

/** How far a line of text may run on from drawn column `j` in direction `step`: over empty neighbours, to the next
 * one that holds something (Excel's rule). `holds(c)` says whether column c of the row holds anything. */
export function spillRoom(colsShown, colPx, j, step, holds) {
  let room = 0;
  for (let k = j + step; k >= 0 && k < colsShown.length; k += step) {
    if (holds(colsShown[k])) break;
    room += colPx[k];
  }
  return room;
}
