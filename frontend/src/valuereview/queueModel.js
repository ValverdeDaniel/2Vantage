/*
 * The keyboard review queue's pure rules (plan.md §8.8; L15; old 891f1b3 `reviewrequest/ReviewQueue.jsx`): which item
 * comes next after a decision, how J/K move, what A and X say on hover, and the keys. Shared by every queue (O.4
 * `valuereview/`); the Documents station keeps its own keys (`keys.js`).
 */

// A approves, X sends back (or corrects), R leaves it for later, N notes, E corrects, U keeps ours, J/K and the arrows
// move, ? lists the keys (L15). `keyAction` lowercases the key, so the arrows read `arrowdown` / `arrowup`.
export const QUEUE_KEYS = {
  a: 'approve',
  x: 'reject',
  r: 'later',
  n: 'note',
  e: 'correct',
  u: 'clear',
  j: 'next',
  k: 'prev',
  arrowdown: 'next',
  arrowup: 'prev',
  '?': 'help',
};

export const DEFAULT_KEY_LABELS = { a: 'approve', x: 'correct', r: 'later' };

/** The next item nobody decided and nobody left for later, after `fromId`, wrapping round; null when none is left. */
export function nextOpen(list, fromId, decided = {}, skipped = new Set()) {
  const at = list.findIndex((item) => item.id === fromId);
  for (let step = 1; step <= list.length; step += 1) {
    const item = list[(at + step + list.length) % list.length];
    if (item.id !== fromId && !decided[item.id] && !skipped.has(item.id)) return item.id;
  }
  return null;
}

/** The item `step` places from `focusId`, held at the ends; null on an empty list. */
export function movedFrom(list, focusId, step) {
  if (!list.length) return null;
  const at = Math.max(0, list.findIndex((item) => item.id === focusId));
  return list[Math.min(list.length - 1, Math.max(0, at + step))].id;
}

/** What A does on an item, said on hover (its config's own words). */
export function approveWords(cfg) {
  return cfg.needsValue
    ? `${cfg.approve} (A): type the value, then on to the next`
    : `${cfg.approve} (A): accept it as it stands, then on to the next`;
}

/** What X does on an item, said on hover; a blocked X says why. */
export function rejectWords(cfg) {
  if (cfg.rejectBlocked) return cfg.rejectBlocked;
  if (cfg.rejectMode === 'value') return `${cfg.reject} (X): type the right value yourself`;
  if (cfg.rejectNow) return `${cfg.reject} (X): a note that shows on their link at once`;
  return `${cfg.reject} (X): back to the client with a note, through the request tray, sent from the request page`;
}

/** The "?" list: every key the focused item takes beyond A, X, R and the arrows. */
export function moreKeys(cfg, readOnly) {
  return [
    ...(readOnly ? [] : (cfg.extras || []).filter((extra) => extra.key).map((extra) => [extra.key, extra.label])),
    ...(cfg.noteAction && !readOnly ? [['N', 'note']] : []),
    ['J', 'next'],
    ['K', 'previous'],
  ];
}

/** "3 of 8 reviewed · 1 for later" and the bar's width. */
export function progress(items, decided, skipped) {
  const done = items.filter((item) => decided[item.id]).length;
  const later = items.filter((item) => skipped.has(item.id) && !decided[item.id]).length;
  return { done, later, pct: items.length ? Math.round((done / items.length) * 100) : 0 };
}
