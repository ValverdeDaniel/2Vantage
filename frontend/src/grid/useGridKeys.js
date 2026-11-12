import { useCallback, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { changed, cursorAction, editorAction, rowEdge, step } from './gridKeys';

/*
 * Excel's keyboard over a grid while ✎ Edit is on (plan.md §8.21; F69, F72; the old shared/useGridKeys.js at
 * 891f1b3). The hook owns WHERE the cursor is and WHEN an editor is open; the keys themselves are `gridKeys.js`.
 * It knows nothing about values or saving: the owner passes `onCommit(r, c, text, base)` (queued by
 * useWriteQueue) and `onUndo()` (Ctrl+Z, and `undo()` for a ↶ Undo button), which answers the cell it put back
 * ({r, c}) for the cursor to go to, or null. Cells are (row key, column key) strings over `rows` and `cols`, in the
 * order drawn, so a filter that hides a cell simply takes the cursor away.
 *
 * What an editor never writes (the old E17 rules): text unchanged from the cell's value when it opened (`base`, read
 * once through `valueAt`); anything when the window loses focus (the editor stays open for the person's return);
 * anything on a click into a source link marked KEEP_EDITOR. A click into another cell commits, as in Excel.
 *
 * `editAt(r, c)` is the edit prompt's Yes (F72): it opens that cell now, or the moment the grid turns on.
 * A grid that draws only the rows on screen passes `reveal(pos, then)`. `onMove(r, c)` hears every move the keys make
 * (an arrow, Home/End, an editor closed with Enter or Tab), so the Documents station's file can follow the cursor (E65).
 */

const cellId = (r, c) => `${r}|${c}`;

/** Spread on a control that opens a value's source: it never takes the focus from an open editor. */
export const KEEP_EDITOR = { 'data-gk-keep': '', onMouseDown: (event) => event.preventDefault() };

export default function useGridKeys({
  enabled,
  rows,
  cols,
  isEditable,
  valueAt,
  onCommit,
  onUndo,
  onMove = null,
  containerRef,
  reveal,
}) {
  const on = Boolean(enabled);
  const [state, setState] = useState({ on, sel: null, edit: null, armed: null, token: 0 });
  // A session starts with no cursor; a cell the edit prompt armed opens as the grid turns on.
  if (state.on !== on) {
    const pos = on ? state.armed : null;
    const open = pos && isEditable(pos.r, pos.c);
    const token = state.token + 1;
    setState({
      on,
      armed: null,
      token,
      sel: pos,
      edit: open ? { ...pos, seed: null, typed: false, token, base: valueAt(pos.r, pos.c) } : null,
    });
  }

  const shape = useMemo(() => {
    const R = rows.map(String);
    const C = cols.map(String);
    return { R, C, rowSet: new Set(R), colSet: new Set(C) };
  }, [rows, cols]);
  const has = (pos) => Boolean(pos) && shape.rowSet.has(pos.r) && shape.colSet.has(pos.c);
  const cursor = on && has(state.sel) ? state.sel : null;
  const edit = on && has(state.edit) ? state.edit : null;

  // The newest props and state for handlers that outlive their render (a blur after a re-render, a key race).
  const live = useRef(null);
  useLayoutEffect(() => {
    live.current = { on, shape, isEditable, valueAt, onCommit, onUndo, onMove, reveal, edit, cursor };
  });
  const editRef = useRef(null);
  useLayoutEffect(() => {
    editRef.current = edit;
  }, [edit]);

  const focusGrid = useCallback(() => containerRef.current?.focus?.({ preventScroll: true }), [containerRef]);

  const select = useCallback((r, c) => {
    setState((s) => ({ ...s, sel: { r: String(r), c: String(c) } }));
  }, []);

  const startEdit = useCallback((pos, seed = null, typed = false) => {
    const L = live.current;
    if (!pos || !L?.isEditable(pos.r, pos.c)) return false;
    const base = L.valueAt(pos.r, pos.c);
    setState((s) => {
      const token = s.token + 1;
      return { ...s, token, sel: { r: pos.r, c: pos.c }, edit: { r: pos.r, c: pos.c, seed, typed, token, base } };
    });
    return true;
  }, []);

  // Keep the cursor's cell in view; a windowed grid draws it first.
  useLayoutEffect(() => {
    if (!cursor) return;
    const show = () => {
      const el = containerRef.current?.querySelector?.(`[data-gk="${CSS.escape(cellId(cursor.r, cursor.c))}"]`);
      el?.scrollIntoView?.({ block: 'nearest', inline: 'nearest' });
    };
    if (live.current?.reveal) live.current.reveal(cursor, show);
    else show();
  }, [cursor?.r, cursor?.c]); // eslint-disable-line react-hooks/exhaustive-deps

  // Close the open editor once: save (when the text changed) or cancel, then perhaps move.
  const finish = useCallback(
    (text, save, move) => {
      const open = editRef.current;
      if (!open) return;
      editRef.current = null;
      setState((s) => ({ ...s, edit: null }));
      const L = live.current;
      if (save && changed(open.base, text)) L.onCommit(open.r, open.c, text, open.base);
      if (move) {
        const next = step(L.shape.R, L.shape.C, open, move[0], move[1], move[2]);
        select(next.r, next.c);
        L.onMove?.(next.r, next.c);
      }
      if (move || !save) focusGrid();
    },
    [focusGrid, select],
  );

  const editAt = useCallback(
    (r, c) => {
      const pos = { r: String(r), c: String(c) };
      if (live.current?.on) {
        if (!startEdit(pos)) select(pos.r, pos.c);
        focusGrid();
      } else setState((s) => ({ ...s, armed: pos }));
    },
    [focusGrid, select, startEdit],
  );

  const undo = useCallback(() => {
    const L = live.current;
    if (!L?.on || editRef.current) return false;
    const to = L.onUndo?.();
    if (to) {
      select(to.r, to.c);
      focusGrid();
    }
    return Boolean(to);
  }, [focusGrid, select]);

  const onKeyDown = (event) => {
    const L = live.current;
    if (!L?.on || event.target !== containerRef.current || event.nativeEvent?.isComposing) return;
    const action = cursorAction(event);
    if (!action) return;
    const handled = () => {
      event.preventDefault();
      event.stopPropagation();
    };
    if (action.type === 'undo') {
      handled();
      undo();
      return;
    }
    const pos = L.cursor;
    if (!pos) return;
    const { R, C } = L.shape;
    if (action.type === 'move') {
      handled();
      const next = step(R, C, pos, action.dr, action.dc, action.wrap);
      select(next.r, next.c);
      L.onMove?.(next.r, next.c);
    } else if (action.type === 'home' || action.type === 'end') {
      handled();
      const next = rowEdge(C, pos, action.type === 'end');
      select(next.r, next.c);
      L.onMove?.(next.r, next.c);
    } else if (action.type === 'deselect') {
      handled();
      setState((s) => ({ ...s, sel: null }));
    } else if (startEdit(pos, action.seed, action.typed)) {
      handled(); // the key is not ALSO delivered to the input mounting under it
    }
  };

  const clickCell = (r, c) => {
    const L = live.current;
    if (!L?.on) return;
    const pos = { r: String(r), c: String(c) };
    if (L.edit && L.edit.r === pos.r && L.edit.c === pos.c) return;
    if (L.cursor && L.cursor.r === pos.r && L.cursor.c === pos.c) startEdit(pos);
    else select(pos.r, pos.c);
  };

  const cellProps = (r, c) =>
    on
      ? {
          'data-gk': cellId(r, c),
          onClick: () => clickCell(r, c),
          onDoubleClick: () => startEdit({ r: String(r), c: String(c) }),
        }
      : {};

  const isSelected = (r, c) => Boolean(cursor) && cursor.r === String(r) && cursor.c === String(c);
  const isEditing = (r, c) => Boolean(edit) && edit.r === String(r) && edit.c === String(c);

  /** The props for the one open input, or null: its text starts as the typed key or the cell's value. */
  const editorFor = (r, c) => {
    if (!isEditing(r, c)) return null;
    const open = edit;
    return {
      'data-gk-editor': '',
      defaultValue: open.seed != null ? open.seed : (open.base ?? ''),
      ref: (el) => {
        if (!el || el.dataset.gkReady === String(open.token)) return;
        el.dataset.gkReady = String(open.token);
        el.focus({ preventScroll: true });
        try {
          el.setSelectionRange(el.value.length, el.value.length);
        } catch {
          /* not a text input */
        }
      },
      onClick: (event) => event.stopPropagation(),
      onDoubleClick: (event) => event.stopPropagation(),
      onBlur: (event) => {
        if (editRef.current?.token !== open.token) return;
        if (typeof document !== 'undefined' && !document.hasFocus()) return; // the window left: keep the editor
        if (event.relatedTarget?.closest?.('[data-gk-keep]')) return;
        finish(event.target.value, true, null);
      },
      onKeyDown: (event) => {
        if (event.nativeEvent?.isComposing) return;
        const action = editorAction(event, open.typed);
        if (!action) return;
        event.stopPropagation();
        if (action.type === 'caret') return;
        event.preventDefault();
        if (action.type === 'cancel') finish(event.target.value, false, null);
        else finish(event.target.value, true, action.move);
      },
    };
  };

  return {
    containerProps: { ref: containerRef, tabIndex: on ? 0 : undefined, onKeyDown },
    cellProps,
    isSelected,
    isEditing,
    editorFor,
    editing: edit ? { r: edit.r, c: edit.c } : null,
    select,
    editAt,
    focusGrid,
    undo,
  };
}
