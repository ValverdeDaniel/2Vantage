import { useCallback, useLayoutEffect, useRef, useState } from 'react';
import { popUndo, pushUndo } from './undoStack';

/*
 * The ✎ Edit session's undo stack (plan.md §8.21; F70; `undoStack.js` holds the rules). It empties when `session`
 * changes (Edit turned on or off). `push(entry)` after a write the server stored; `take()` pops the newest step for
 * the owner to write back, or returns null.
 */
export default function useUndoStack(session) {
  const [state, setState] = useState({ session, stack: [] });
  if (state.session !== session) setState({ session, stack: [] });
  const stack = state.session === session ? state.stack : [];
  const live = useRef(stack);
  useLayoutEffect(() => {
    live.current = stack;
  });

  const push = useCallback((entry) => {
    setState((s) => ({ ...s, stack: pushUndo(s.stack, entry) }));
  }, []);

  const take = useCallback(() => {
    const { entry, stack: rest } = popUndo(live.current);
    if (!entry) return null;
    live.current = rest;
    setState((s) => ({ ...s, stack: rest }));
    return entry;
  }, []);

  return { push, take, canUndo: stack.length > 0 };
}
