import { useState } from 'react';
import { batch, selectable, tickBlock } from './ticks';

/*
 * The ☐ ticks of one line's board (plan.md §8.14; F57; `ticks.js` holds the rules). Switching line drops them; they
 * live in and out of ✎ Edit. `drawn` are the plans on screen in their order, `shownQuotes` the quotes among them
 * (select-all's reach), `plans` every plan of the line.
 */

const NONE = new Set();

export default function useTicks(line, editing, drawn, shownQuotes, plans) {
  const [state, setState] = useState({ line, ids: NONE });
  const ids = state.line === line ? state.ids : NONE;
  const change = (fn) =>
    setState((s) => {
      const next = new Set(s.line === line ? s.ids : NONE);
      fn(next);
      return { line, ids: next };
    });
  const ticked = drawn.filter((plan) => ids.has(plan.id) && !tickBlock(plan, editing));
  return {
    ids,
    count: ticked.length,
    todo: batch(ticked, plans),
    selectable: selectable(shownQuotes, editing),
    block: (plan) => tickBlock(plan, editing),
    hint: (plan) =>
      !editing
        ? 'Tick to star or unstar this plan'
        : plan.role === 'current'
          ? 'Tick to remove it as a current plan, or to move it to another line'
          : 'Tick to star it, move it to another line, or mark it current',
    toggle: (id) =>
      change((next) => {
        if (next.has(id)) next.delete(id);
        else next.add(id);
      }),
    setMany: (list, on) =>
      change((next) => {
        for (const id of list) {
          if (on) next.add(id);
          else next.delete(id);
        }
      }),
    clear: () => setState({ line, ids: NONE }),
  };
}
