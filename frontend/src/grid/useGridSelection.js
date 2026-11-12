import { useCallback, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { allKeys, keyOf, lineKeys, onGrid, pickedCells, rectKeys, stepCell } from './cellPick';
import useDragPick from './useDragPick';

/*
 * Pick cells the way Excel does, to review them (plan.md §8.21; E51; the old shared/useGridSelection.js). Click picks
 * one cell; drag picks a rectangle (useDragPick, with edge scroll); Shift+click stretches from the anchor;
 * Ctrl/Cmd+click adds or drops one cell and Ctrl/Cmd+drag adds a rectangle; a column head picks the column and a row
 * label the row. The arrows move the active cell and Shift+arrows stretch; Ctrl/Cmd+A picks every cell on screen;
 * Escape drops the pick. A double-click asks for the cell's source (`onFind`). View mode only: ✎ Edit is
 * useGridKeys'. Cells are (row key, column key) strings over `rows` and `cols`, the keys on screen in their order.
 */
export default function useGridSelection({ enabled, rows, cols, containerRef, onFind, onFollow = null, reveal }) {
  const on = Boolean(enabled);
  const [state, setState] = useState({ on, picks: new Set(), anchor: null, focus: null, active: null });
  if (state.on !== on) setState({ on, picks: new Set(), anchor: null, focus: null, active: null });
  const shape = useMemo(() => ({ R: rows.map(String), C: cols.map(String) }), [rows, cols]);
  const live = useRef({ state, shape, onFind, onFollow, reveal });
  useLayoutEffect(() => {
    live.current = { state, shape, onFind, onFollow, reveal };
  });
  const gesture = useRef(null);

  const commit = useCallback((picks, at = {}) => {
    setState((s) => ({
      ...s,
      picks,
      anchor: at.anchor !== undefined ? at.anchor : s.anchor,
      focus: at.focus !== undefined ? at.focus : s.focus,
      active: at.active !== undefined ? at.active : s.active,
    }));
  }, []);
  const clear = useCallback(() => commit(new Set(), { anchor: null, focus: null, active: null }), [commit]);

  const dragger = useDragPick({
    containerRef,
    shape: () => live.current.shape,
    onDone: (picks, anchor, at) => {
      if (gesture.current) gesture.current.moved = true;
      commit(picks, { anchor, focus: at, active: at });
    },
  });

  const onCellMouseDown = (r, c, event) => {
    if (!on || event.button !== 0 || event.target?.closest?.('[data-gk-editor]')) return;
    const { state: s, shape: sh } = live.current;
    const pos = { r: String(r), c: String(c) };
    const additive = event.ctrlKey || event.metaKey;
    gesture.current = { key: keyOf(pos.r, pos.c), shift: event.shiftKey, moved: false };
    if (event.shiftKey || additive) {
      event.preventDefault(); // no text selection, and the grid keeps the keyboard
      containerRef.current?.focus?.({ preventScroll: true });
    }
    if (event.shiftKey && onGrid(sh.R, sh.C, s.anchor)) {
      const next = new Set(additive ? s.picks : []);
      for (const k of rectKeys(sh.R, sh.C, s.anchor, pos)) next.add(k);
      commit(next, { focus: pos, active: s.active || s.anchor });
      return;
    }
    const base = additive ? new Set(s.picks) : new Set();
    dragger.start(pos, base, !additive || !s.picks.has(keyOf(pos.r, pos.c)), event, new Set(s.picks));
  };

  // The click that ends a mousedown on the same cell: one cell, or a Ctrl toggle. A drag or Shift+click did its work.
  const onCellClick = (r, c, event) => {
    if (!on) return;
    const pos = { r: String(r), c: String(c) };
    const key = keyOf(pos.r, pos.c);
    const g = gesture.current;
    gesture.current = null;
    if (g && g.key === key && (g.moved || g.shift)) return;
    const { state: s, onFollow: follow } = live.current;
    if (event?.ctrlKey || event?.metaKey) {
      const next = new Set(s.picks);
      if (next.has(key)) {
        next.delete(key);
        commit(next);
        return;
      }
      next.add(key);
      commit(next, { anchor: pos, focus: pos, active: pos });
      follow?.(pos.r, pos.c, 'click');
      return;
    }
    commit(new Set([key]), { anchor: pos, focus: pos, active: pos });
    if ((event?.detail ?? 1) < 2) follow?.(pos.r, pos.c, 'click');
  };

  const onCellDoubleClick = (r, c) => {
    if (!on) return;
    const pos = { r: String(r), c: String(c) };
    commit(new Set([keyOf(pos.r, pos.c)]), { anchor: pos, focus: pos, active: pos });
    live.current.onFind?.(pos.r, pos.c);
  };

  const pickLine = (keys, at, event) => {
    if (!on || !keys.length) return;
    const next = new Set(event?.ctrlKey || event?.metaKey ? live.current.state.picks : []);
    for (const k of keys) next.add(k);
    commit(next, { anchor: at, focus: at, active: at });
    containerRef.current?.focus?.({ preventScroll: true });
  };

  const colHeadProps = (c) =>
    on
      ? {
          'data-gs-head': '',
          title: 'Pick this whole column (Ctrl/Cmd+click adds it)',
          onClick: (event) => {
            if (event.target.closest?.('button, a, input')) return;
            const { R } = live.current.shape;
            pickLine(lineKeys(R, [], { c: String(c) }), R.length ? { r: R[0], c: String(c) } : null, event);
          },
        }
      : {};

  const rowHeadProps = (r) =>
    on
      ? {
          'data-gs-head': '',
          title: 'Pick this whole row (Ctrl/Cmd+click adds it)',
          onClick: (event) => {
            const { C } = live.current.shape;
            pickLine(lineKeys([], C, { r: String(r) }), C.length ? { r: String(r), c: C[0] } : null, event);
          },
        }
      : {};

  const MOVES = { ArrowUp: [-1, 0], ArrowDown: [1, 0], ArrowLeft: [0, -1], ArrowRight: [0, 1] };
  const onKeyDown = (event) => {
    const { state: s, shape: sh, onFollow: follow } = live.current;
    if (!on || event.target !== containerRef.current || event.nativeEvent?.isComposing) return;
    const handled = () => {
      event.preventDefault();
      event.stopPropagation();
    };
    const { R, C } = sh;
    if (MOVES[event.key]) {
      if (!R.length || !C.length) return;
      handled();
      const [dr, dc] = MOVES[event.key];
      const from = onGrid(R, C, s.active) ? s.active : { r: R[0], c: C[0] };
      if (event.shiftKey && onGrid(R, C, s.anchor)) {
        const corner = stepCell(R, C, onGrid(R, C, s.focus) ? s.focus : from, dr, dc);
        commit(new Set(rectKeys(R, C, s.anchor, corner)), { focus: corner });
        return;
      }
      const next = onGrid(R, C, s.active) ? stepCell(R, C, from, dr, dc) : from;
      commit(new Set([keyOf(next.r, next.c)]), { anchor: next, focus: next, active: next });
      follow?.(next.r, next.c, 'key');
    } else if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'a') {
      if (!R.length || !C.length) return;
      handled();
      const first = { r: R[0], c: C[0] };
      commit(new Set(allKeys(R, C)), { anchor: first, focus: first, active: s.active || first });
    } else if (event.key === 'Escape' && s.picks.size) {
      handled();
      clear();
    }
  };

  // Keep the active cell on screen as the keys move it.
  const active = state.on === on && on ? state.active : null;
  useLayoutEffect(() => {
    if (!active || dragger.active()) return;
    const show = () => {
      const el = containerRef.current?.querySelector?.(`[data-gs="${CSS.escape(keyOf(active.r, active.c))}"]`);
      el?.scrollIntoView?.({ block: 'nearest', inline: 'nearest' });
    };
    if (live.current.reveal) live.current.reveal(active, show);
    else show();
  }, [active?.r, active?.c]); // eslint-disable-line react-hooks/exhaustive-deps

  const picks = on ? state.picks : new Set();
  return {
    containerProps: { ref: containerRef, tabIndex: on ? 0 : undefined, onKeyDown },
    cellProps: (r, c) =>
      on
        ? {
            'data-gs': keyOf(r, c),
            onMouseDown: (event) => onCellMouseDown(r, c, event),
            onClick: (event) => onCellClick(r, c, event),
            onDoubleClick: () => onCellDoubleClick(r, c),
          }
        : {},
    colHeadProps,
    rowHeadProps,
    isPicked: (r, c) => picks.has(keyOf(r, c)),
    isActive: (r, c) => Boolean(active) && active.r === String(r) && active.c === String(c),
    picked: () => pickedCells(shape.R, shape.C, picks),
    count: picks.size,
    clear,
  };
}
