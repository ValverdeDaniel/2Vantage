// The Advisor board's bridge to Work with Claude (plan.md §10.6; D80, F25, F108; the old AdvisorTab `boardApi`:
// getBoard, applyBoard). Module state per deal, shared by two tab folders that never import each other:
// - the Advisor's board registers what it shows (`register(dealId, {get, apply})`); the drawer reads it when a message
//   is sent (`current`), so Claude knows the board's line, filters and shown plans;
// - when a turn ends with a set_board patch, the drawer sends it (`send`): the board applies it at once, or, when the
//   Advisor is not on screen, when it next mounts (the drawer opens the Advisor);
// - Claude's pick (F25) is transient, never saved and one line only: it lives here, so leaving the tab keeps it while
//   the deal is open, and the board's chip removes it (`setPick`).

const boards = new Map(); // dealId -> {get, apply}
const pending = new Map(); // dealId -> patch
const picks = new Map(); // dealId -> pick | null
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

/** Subscribe to pick changes (useSyncExternalStore). */
export function subscribe(listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}
