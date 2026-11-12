/*
 * Picking cells the way Excel does, as pure rules (plan.md §8.21; E51; the old shared/useGridSelection.js). Cells
 * are (row key, column key) strings over `R` and `C`, the keys on screen in their order; a pick is a Set of
 * "row|col" keys. `useGridSelection` holds the pick and the pointer; this decides which cells a gesture picks.
 */

export const keyOf = (r, c) => `${r}|${c}`;

/** {r, c} from a "row|col" key (a column key may itself hold "|"). */
export function cellOf(key) {
  const [r, ...rest] = String(key).split('|');
  return { r, c: rest.join('|') };
}

export function onGrid(R, C, pos) {
  return Boolean(pos) && R.includes(String(pos.r)) && C.includes(String(pos.c));
}

/** Every key in the rectangle between two cells on screen, row by row; [] when either is off the grid. */
export function rectKeys(R, C, a, b) {
  if (!onGrid(R, C, a) || !onGrid(R, C, b)) return [];
  const [r0, r1] = [R.indexOf(String(a.r)), R.indexOf(String(b.r))].sort((x, y) => x - y);
  const [c0, c1] = [C.indexOf(String(a.c)), C.indexOf(String(b.c))].sort((x, y) => x - y);
  const out = [];
  for (let i = r0; i <= r1; i += 1) {
    for (let j = c0; j <= c1; j += 1) out.push(keyOf(R[i], C[j]));
  }
  return out;
}

/** The cell one step away, clamped to the grid; a cell off the grid stays. */
export function stepCell(R, C, pos, dr, dc) {
  if (!onGrid(R, C, pos)) return pos;
  const i = Math.max(0, Math.min(R.length - 1, R.indexOf(String(pos.r)) + dr));
  const j = Math.max(0, Math.min(C.length - 1, C.indexOf(String(pos.c)) + dc));
  return { r: R[i], c: C[j] };
}

/** A whole column (a header click) or a whole row (a label click), added to `base` when Ctrl/Cmd is held. */
export function lineKeys(R, C, { r = null, c = null }) {
  if (c != null) return R.map((row) => keyOf(row, c));
  if (r != null) return C.map((col) => keyOf(r, col));
  return [];
}

/** A drag from `anchor` to `pos`: over `base` (Ctrl/Cmd keeps the earlier pick), adding or (`add` false) dropping. */
export function dragPick(R, C, base, anchor, pos, add = true) {
  const next = new Set(base);
  for (const key of rectKeys(R, C, anchor, pos)) {
    if (add) next.add(key);
    else next.delete(key);
  }
  return next;
}

/** The picked cells still on screen, in screen order (row by row). */
export function pickedCells(R, C, picks) {
  const out = [];
  if (!picks.size) return out;
  for (const r of R) {
    for (const c of C) if (picks.has(keyOf(r, c))) out.push({ r, c });
  }
  return out;
}

/** Ctrl/Cmd+A: every cell on screen. */
export function allKeys(R, C) {
  return R.length && C.length ? rectKeys(R, C, { r: R[0], c: C[0] }, { r: R[R.length - 1], c: C[C.length - 1] }) : [];
}

/** "Only potential errors": the pick narrowed to the cells `keep(r, c)` keeps. */
export function narrowKeys(picks, keep) {
  const next = new Set();
  for (const key of picks) {
    const { r, c } = cellOf(key);
    if (keep(r, c)) next.add(key);
  }
  return next;
}

/** The cell F opens: the active one while it is picked and on screen, else the first picked cell on screen. */
export function activeOrFirst(R, C, picks, active) {
  if (onGrid(R, C, active) && picks.has(keyOf(active.r, active.c))) return { r: String(active.r), c: String(active.c) };
  return pickedCells(R, C, picks)[0] || null;
}
