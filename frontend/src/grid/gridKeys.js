/*
 * Excel's keys over a grid, as pure rules (plan.md §8.21; F69; the old shared/useGridKeys.js at 891f1b3). One click
 * selects, a second click, F2 or typing edits; Enter and Shift+Enter move down and up, Tab and Shift+Tab right and
 * left (wrapping to the next row), the arrows move, Home and End go to the row's first and last cell, Delete and
 * Backspace open an empty editor (nothing is written until it is committed), Escape drops the cursor or cancels the
 * editor, Ctrl+Z (⌘Z) undoes. Cells are addressed by (row key, column key) strings, never by index, so the cursor
 * survives a reload or a re-sort. The grid knows nothing about plans: `useGridKeys` applies these answers.
 */

const ARROWS = { ArrowUp: [-1, 0], ArrowDown: [1, 0], ArrowLeft: [0, -1], ArrowRight: [0, 1] };

const clamp = (n, lo, hi) => Math.max(lo, Math.min(hi, n));

/**
 * The cell `dr` rows and `dc` columns from `pos` over row keys `R` and column keys `C`, clamped to the grid. With
 * `wrap` (Tab) a step past the row's end goes to the next row's first cell, and before its start to the previous
 * row's last. A position not on the grid stays where it is.
 */
export function step(R, C, pos, dr, dc, wrap = false) {
  let ri = R.indexOf(String(pos?.r));
  let ci = C.indexOf(String(pos?.c));
  if (ri < 0 || ci < 0) return pos;
  ri += dr;
  ci += dc;
  if (wrap && ci >= C.length) {
    if (ri + 1 < R.length) {
      ri += 1;
      ci = 0;
    } else ci = C.length - 1;
  } else if (wrap && ci < 0) {
    if (ri - 1 >= 0) {
      ri -= 1;
      ci = C.length - 1;
    } else ci = 0;
  }
  return { r: R[clamp(ri, 0, R.length - 1)], c: C[clamp(ci, 0, C.length - 1)] };
}

/**
 * What a key does while the cursor rests on a cell (the grid has focus), or null when the key is not the grid's:
 *   {type: 'undo'} · {type: 'move', dr, dc, wrap} · {type: 'home'} · {type: 'end'} · {type: 'deselect'}
 *   {type: 'edit', seed, typed}: F2 opens on the value (seed null); Delete/Backspace on an empty box; a printable key
 *   replaces the value with itself, as in Excel.
 * `key` is a KeyboardEvent-like {key, shiftKey, ctrlKey, metaKey, altKey}.
 */
export function cursorAction({ key, shiftKey = false, ctrlKey = false, metaKey = false, altKey = false }) {
  const mod = ctrlKey || metaKey;
  if (mod && !shiftKey && !altKey && String(key).toLowerCase() === 'z') return { type: 'undo' };
  if (ARROWS[key]) return { type: 'move', dr: ARROWS[key][0], dc: ARROWS[key][1], wrap: false };
  switch (key) {
    case 'Enter':
      return { type: 'move', dr: shiftKey ? -1 : 1, dc: 0, wrap: false };
    case 'Tab':
      return { type: 'move', dr: 0, dc: shiftKey ? -1 : 1, wrap: true };
    case 'Home':
      return { type: 'home' };
    case 'End':
      return { type: 'end' };
    case 'Escape':
      return { type: 'deselect' };
    case 'F2':
      return { type: 'edit', seed: null, typed: false };
    case 'Delete':
    case 'Backspace':
      return { type: 'edit', seed: '', typed: true };
    default:
      if (String(key).length === 1 && !mod && !altKey) return { type: 'edit', seed: key, typed: true };
      return null;
  }
}

/**
 * What a key does inside the open editor, or null to let the input have it:
 *   {type: 'commit', move: [dr, dc, wrap]} (Enter, Tab; an arrow when the edit began by typing) · {type: 'cancel'}
 *   (Escape) · {type: 'caret'} (an arrow in an editor opened by a click or F2 moves the caret and stays there).
 */
export function editorAction({ key, shiftKey = false }, typed) {
  if (key === 'Enter') return { type: 'commit', move: [shiftKey ? -1 : 1, 0, false] };
  if (key === 'Tab') return { type: 'commit', move: [0, shiftKey ? -1 : 1, true] };
  if (key === 'Escape') return { type: 'cancel' };
  if (ARROWS[key]) return typed ? { type: 'commit', move: [...ARROWS[key], false] } : { type: 'caret' };
  return null;
}

/** Whether a commit writes: text the same as the cell's value when its editor opened writes nothing (F69). */
export function changed(base, text) {
  return String(text ?? '').trim() !== String(base ?? '').trim();
}

/** The first and last cell of `pos`'s row. */
export function rowEdge(C, pos, end) {
  return { r: pos.r, c: end ? C[C.length - 1] : C[0] };
}
