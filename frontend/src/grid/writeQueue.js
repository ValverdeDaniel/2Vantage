/*
 * The per-cell write queue (plan.md §8.21; F71; the old shared/useWriteQueue.js, made per cell). Tab, Tab, Tab is
 * three saves inside a second:
 * - one request in flight per cell; a value typed while one is in flight waits, and a newer one replaces it (the
 *   latest wins), so two edits of one cell never land out of order;
 * - each write expects the value it replaces: the first the value the person saw when the editor opened, a queued
 *   one the value the server stored for the write before it (so `expect` never trips over our own save);
 * - a failure calls `onFailed(cell, error, saved)` with the last saved value, so the grid restores it and shows the
 *   server's message on the cell; anything queued behind it is dropped;
 * - when every cell has settled, `onIdle()` runs once: one refetch per burst.
 * No React: `useWriteQueue` holds one. `send(cell, value, expect)` returns a promise of the value the server stored.
 */

export function createWriteQueue({ send, onFailed = () => {}, onIdle = () => {} }) {
  const cells = new Map(); // cell -> {busy, next: {value, waiters} | null, saved}
  let active = 0;
  let burst = false;
  let idleWaiters = [];

  function idle() {
    if (active > 0) return;
    const fire = burst;
    burst = false;
    const waiters = idleWaiters;
    idleWaiters = [];
    waiters.forEach((resolve) => resolve());
    if (fire) onIdle();
  }

  function done(cell, state, ok) {
    state.busy = false;
    active -= 1;
    const next = state.next;
    state.next = null;
    if (next && ok) {
      run(cell, state, next.value, state.saved, next.waiters);
      return;
    }
    cells.delete(cell);
    idle();
  }

  function run(cell, state, value, expect, waiters) {
    state.busy = true;
    active += 1;
    Promise.resolve()
      .then(() => send(cell, value, expect))
      .then(
        (stored) => {
          state.saved = stored;
          waiters.forEach((w) => w.resolve({ before: expect, after: stored }));
          done(cell, state, true);
        },
        (error) => {
          state.next?.waiters.forEach((w) => w.resolve(null));
          state.next = null;
          onFailed(cell, error, expect);
          waiters.forEach((w) => w.reject(error));
          done(cell, state, false);
        },
      );
  }

  return {
    /**
     * Queue `value` for `cell`, whose value was `base` when the person began. Resolves to {before, after} once the
     * server stored it, to null when a newer value replaced it before it was sent; rejects with the server's error.
     */
    enqueue(cell, value, base) {
      burst = true;
      return new Promise((resolve, reject) => {
        const waiter = { resolve, reject };
        let state = cells.get(cell);
        if (!state) {
          state = { busy: false, next: null, saved: base };
          cells.set(cell, state);
        }
        if (!state.busy) {
          run(cell, state, value, base, [waiter]);
          return;
        }
        state.next?.waiters.forEach((w) => w.resolve(null));
        state.next = { value, waiters: [waiter] };
      });
    },
    /** Whether `cell` has a write in flight or waiting. */
    busy(cell) {
      return cells.has(cell);
    },
    /** Resolves once nothing is in flight (Done ✓ waits for it). */
    settle() {
      if (active === 0) return Promise.resolve();
      return new Promise((resolve) => idleWaiters.push(resolve));
    },
  };
}
