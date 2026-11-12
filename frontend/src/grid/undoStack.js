/*
 * The grid's undo (plan.md §8.21; F70, J74; O.6 #33): one stack per ✎ Edit session, 50 steps deep, newest last. Each
 * step is one cell's write — the value before it and the value the server stored — so Undo writes the earlier value
 * with `expect` set to the stored one, and the server refuses it when the cell changed since. Pure: the grid keeps
 * the stack in state and the owner decides what a write is.
 */

export const UNDO_DEPTH = 50;

/** The stack with `entry` ({cell, before, after, …}) on top; the oldest step falls off past `depth`. */
export function pushUndo(stack, entry, depth = UNDO_DEPTH) {
  return [...stack, entry].slice(-depth);
}

/** {entry, stack}: the newest step and the stack without it; `entry` is null on an empty stack. */
export function popUndo(stack) {
  if (!stack.length) return { entry: null, stack };
  return { entry: stack[stack.length - 1], stack: stack.slice(0, -1) };
}

/** The step an Undo writes: the earlier value, expecting the one the server stored (`after`). */
export function undoWrite(entry) {
  return { cell: entry.cell, value: entry.before, expect: entry.after };
}
