import { useCallback, useLayoutEffect, useMemo, useRef } from 'react';
import useEditModePrompt from '../../../grid/useEditModePrompt';
import useGridKeys from '../../../grid/useGridKeys';
import useWindowed from '../../../grid/useWindowed';
import { WINDOW_ROWS_OVER } from '../../../grid/windowFrame';

/*
 * The board on the grid (plan.md §8.21; F40, F68–F72): which cells the keys walk (the plan values, in the order drawn;
 * rows are plans and columns field keys, swapped when transposed), what a commit and an undo write (`writes`, the
 * board's useCellWrites), which rows are drawn above 150 plans (rows only, F40), and the edit prompt a double-click
 * outside ✎ Edit opens. The grid hooks know nothing about plans; this is where plans meet them.
 */
export default function useBoardGrid({ board, drawn, fieldKeys, orientation, editing, writes, enterEdit, scrollRef, bodyRef }) {
  const rowsLayout = orientation === 'rows';
  const planIds = useMemo(() => drawn.map((plan) => String(plan.id)), [drawn]);
  const rows = rowsLayout ? planIds : fieldKeys;
  const cols = rowsLayout ? fieldKeys : planIds;
  const fieldSet = useMemo(() => new Set(fieldKeys), [fieldKeys]);
  const byId = board.order.byId;
  const at = (r, c) => (rowsLayout ? [Number(r), String(c)] : [Number(c), String(r)]);
  const rowIndex = useMemo(() => new Map(planIds.map((id, i) => [id, i])), [planIds]);

  const revealRow = useRef(null);
  const reveal = useCallback((pos, then) => (revealRow.current ? revealRow.current(pos, then) : then()), []);

  const grid = useGridKeys({
    enabled: editing,
    rows,
    cols,
    isEditable: (r, c) => {
      const [id, key] = at(r, c);
      return byId.has(id) && fieldSet.has(key);
    },
    valueAt: (r, c) => {
      const [id, key] = at(r, c);
      return byId.get(id)?.values?.[key] ?? '';
    },
    onCommit: (r, c, text, base) => {
      const [id, key] = at(r, c);
      writes.commit(id, key, text, base);
    },
    onUndo: () => {
      const went = writes.undo();
      if (!went) return null;
      return rowsLayout ? { r: String(went.planId), c: went.key } : { r: went.key, c: String(went.planId) };
    },
    containerRef: scrollRef,
    reveal,
  });

  const win = useWindowed({
    axis: 'rows',
    count: drawn.length,
    on: rowsLayout && drawn.length > WINDOW_ROWS_OVER,
    pin: rowsLayout && grid.editing ? (rowIndex.get(grid.editing.r) ?? -1) : -1,
    scrollRef,
    bodyRef,
  });
  useLayoutEffect(() => {
    revealRow.current = rowsLayout ? (pos, then) => win.reveal(rowIndex.get(String(pos.r)), then) : null;
  });

  const prompt = useEditModePrompt({ on: !editing, enter: enterEdit, land: grid.editAt });
  return { grid, win, prompt };
}
