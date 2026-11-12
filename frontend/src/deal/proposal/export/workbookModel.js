/*
 * The Excel view's rules (plan.md §8.14; J116, J118; the old WorkbookViewer.jsx at 891f1b3): the checks' words and
 * levels, a tab's dot, the cells the checks mark, the arrow keys over merges, and which tab a request asks for. The
 * checks themselves are the server's (proposals/viewer/workbook_checks.py). Pure.
 */

export const CHECK_WORDS = {
  error: ['formula error', 'formula errors'],
  hash: ['number shows ####', 'numbers show ####'],
  cut: ['cut off', 'cut off'],
  tight: ['tight', 'tight'],
};
export const LEVEL = { error: 'bad', hash: 'bad', cut: 'bad', tight: 'warn' };
export const MODE_KEY = 'vantage.export.sheetMode';

/** The worst a tab's checks found, for its dot: 'bad', 'warn' or null. */
export function tabLevel(counts) {
  if (counts?.error || counts?.hash || counts?.cut) return 'bad';
  return counts?.tight ? 'warn' : null;
}

/** ["2 cut off", "1 tight"]: each kind a tab has, in order, with its count. */
export function countWords(counts) {
  return Object.keys(CHECK_WORDS)
    .filter((kind) => counts?.[kind])
    .map((kind) => `${counts[kind]} ${CHECK_WORDS[kind][counts[kind] === 1 ? 0 : 1]}`);
}

/** The tab's checks as one list, worst kind first, each with its kind. */
export function checkList(tab) {
  if (!tab) return [];
  return Object.keys(CHECK_WORDS).flatMap((kind) => (tab.checks?.[kind] || []).map((check) => ({ ...check, kind })));
}

export const cellKey = (r, c) => r * 4096 + c;

/** {cellKey: 'bad' | 'warn'}: the mark each checked cell wears, the worse one winning. */
export function markMap(checks) {
  const out = new Map();
  checks.forEach((check) => {
    const k = cellKey(check.r, check.c);
    if (!out.has(k) || LEVEL[check.kind] === 'bad') out.set(k, LEVEL[check.kind]);
  });
  return out;
}

const MOVES = { ArrowLeft: [0, -1], ArrowRight: [0, 1], ArrowUp: [-1, 0], ArrowDown: [1, 0] };

/** The cell an arrow key moves to from `cell` ({r, c}), as Excel moves: inside a merge it lands on the merge's own
 * cell, and leaving one rightward or downward steps past it. null for a key that moves nothing. */
export function stepCell(tab, cell, key) {
  if (!(key in MOVES) || !cell || !tab) return null;
  const [dr, dc] = MOVES[key];
  let r = Math.min(tab.rows - 1, Math.max(0, cell.r + dr));
  let c = Math.min(tab.cols - 1, Math.max(0, cell.c + dc));
  for (const [mr, mc, rs, cs] of tab.merges || []) {
    if (r >= mr && r < mr + rs && c >= mc && c < mc + cs) {
      if (dc > 0 && cell.c >= mc && cell.c < mc + cs) c = Math.min(tab.cols - 1, mc + cs);
      else if (dr > 0 && cell.r >= mr && cell.r < mr + rs) r = Math.min(tab.rows - 1, mr + rs);
      else {
        r = mr;
        c = mc;
      }
      break;
    }
  }
  return { r, c };
}

/** The tab a request asks for: '' (the tab the file opens on) for the opening tab or none picked, so the opening
 * tab is built once under one key; else the picked tab's title. */
export function requestedTab(selected, opensOn) {
  return selected && selected !== opensOn ? selected : '';
}

export function readMode(storage) {
  try {
    return storage?.getItem(MODE_KEY) === 'pages' ? 'pages' : 'screen';
  } catch {
    return 'screen';
  }
}

export function writeMode(storage, mode) {
  try {
    storage?.setItem(MODE_KEY, mode);
  } catch {
    /* private mode: the choice lasts until the page is left */
  }
}
