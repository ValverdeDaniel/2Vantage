// The Advisor board's bridge to Work with Claude (plan.md §10.6; D80, F25, F108; the old AdvisorTab `boardApi`:
// getBoard, applyBoard). Module state per deal, shared by two tab folders that never import each other:
// - the Advisor's board registers what it shows (`register(dealId, {get, apply})`); the drawer reads it when a message
//   is sent (`current`), so Claude knows the board's line, filters and shown plans;
// - when a turn ends with a set_board patch, the drawer sends it (`send`): the board applies it at once, or, when the
//   Advisor is not on screen, when it next mounts (the drawer opens the Advisor);
// - Claude's pick (F25) is transient, never saved and one line only: it lives here, so leaving the tab keeps it while
//   the deal is open, and the board's chip removes it (`setPick`);
// - what the board draws (`publish`, `viewOf`), for ⚖ Rank in the drawer's guidance box (slice 37).

const boards = new Map(); // dealId -> {get, apply}
const pending = new Map(); // dealId -> patch
const picks = new Map(); // dealId -> pick | null
const views = new Map(); // dealId -> {line, shown_ids, total}: what the board draws now (⚖ Rank's label; slice 37)
const listeners = new Set();

const id = (dealId) => Number(dealId);

function notify() {
  listeners.forEach((listener) => listener());
}

/** The board registers itself; returns the unregister. A patch that waited is applied now. */
export function register(dealId, board) {
  boards.set(id(dealId), board);
  const waiting = pending.get(id(dealId));
  if (waiting) {
    pending.delete(id(dealId));
    board.apply(waiting);
  }
  return () => {
    if (boards.get(id(dealId)) === board) boards.delete(id(dealId));
  };
}

/** What the board shows now ({line, config, shown_ids, total, pick}), or null when the Advisor is not on screen. */
export function current(dealId) {
  return boards.get(id(dealId))?.get() ?? null;
}

/** Hand a set_board patch to the board; true when it was applied at once. */
export function send(dealId, patch) {
  if (!patch) return false;
  const board = boards.get(id(dealId));
  if (board) {
    board.apply(patch);
    return true;
  }
  pending.set(id(dealId), patch);
  return false;
}

export function pickOf(dealId) {
  return picks.get(id(dealId)) ?? null;
}

export function setPick(dealId, pick) {
  picks.set(id(dealId), pick && Array.isArray(pick.plan_ids) ? pick : null);
  notify();
}

/** The board publishes what it draws as it changes (its line, the plans its filters show, how many quotes), so the
 *  drawer's ⚖ Rank says "Rank filtered (N)" at once; null when the board leaves the screen (slice 37, OQ44). */
export function publish(dealId, view) {
  const before = views.get(id(dealId)) ?? null;
  const same =
    before && view && before.line === view.line && before.total === view.total &&
    before.shown_ids.join(',') === view.shown_ids.join(',');
  if (same || (!before && !view)) return;
  if (view) views.set(id(dealId), view);
  else views.delete(id(dealId));
  notify();
}

export function viewOf(dealId) {
  return views.get(id(dealId)) ?? null;
}

/** Subscribe to pick and view changes (useSyncExternalStore). */
export function subscribe(listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}
