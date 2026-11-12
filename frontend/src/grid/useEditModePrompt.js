import { useCallback, useState } from 'react';

/*
 * "Would you like to enter edit mode?" (plan.md §8.21; F72, D-160; the old shared/EditModePrompt.jsx). Outside ✎ Edit
 * a double-click on a cell asks; Yes runs the grid owner's `enter()` (which answers whether Edit is now on) and only
 * then `land(r, c)` opens that cell (useGridKeys' editAt). `on` is the grid's rule (not editing). `ask(event, r, c)`
 * is the cell's onDoubleClick; a double-click on a button, link or input inside the cell is theirs.
 * The dialog is <EditModePrompt {...prompt} />.
 */

const NOT_A_CELL = 'button, a, input, select, textarea, label';

export default function useEditModePrompt({ on, enter, land }) {
  const [pending, setPending] = useState(null); // {r, c}
  const [busy, setBusy] = useState(false);

  const ask = useCallback(
    (event, r, c) => {
      if (!on || event?.target?.closest?.(NOT_A_CELL)) return;
      try {
        window.getSelection()?.removeAllRanges(); // the double-click also selected the word under it
      } catch {
        /* no selection API */
      }
      setPending({ r: String(r), c: String(c) });
    },
    [on],
  );

  const close = () => {
    if (!busy) setPending(null);
  };

  const accept = async () => {
    const at = pending;
    if (!at || busy) return;
    setBusy(true);
    let ok = false;
    try {
      ok = Boolean(await enter());
    } finally {
      setBusy(false);
      setPending(null);
    }
    if (ok) land?.(at.r, at.c);
  };

  return { ask, open: Boolean(pending), busy, accept, close };
}
