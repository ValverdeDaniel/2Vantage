// The Export viewer's bridge to Work with Claude (plan.md §10.6; J120; the old AdvisorTab getPage's `export` branch):
// module state per deal, shared by two tab folders that never import each other, as the board's bridge is. The
// viewer publishes what it shows (the file, the slide or tab, the fits) while it is on screen; the drawer reads it when
// a message is sent (`current`), so Claude is told what the producer sees without the server building anything.

const states = new Map(); // dealId -> viewer state

const id = (dealId) => Number(dealId);

/** The viewer publishes its state; returns the unpublish (a newer state from the same viewer replaces it). */
export function publish(dealId, state) {
  states.set(id(dealId), state);
  return () => {
    if (states.get(id(dealId)) === state) states.delete(id(dealId));
  };
}

/** What the Export viewer shows now, or null when it is not on screen. */
export function current(dealId) {
  return states.get(id(dealId)) ?? null;
}
