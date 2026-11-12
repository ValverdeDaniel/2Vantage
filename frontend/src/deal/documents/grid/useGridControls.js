import { useCallback, useEffect, useLayoutEffect, useMemo, useRef } from 'react';
import usePlanCellWrites from '../../../api/planWrites';
import useGridKeys from '../../../grid/useGridKeys';
import useGridSelection from '../../../grid/useGridSelection';
import useWindowed from '../../../grid/useWindowed';
import { WINDOW_COLS_OVER } from '../../../grid/windowFrame';
import { useToast } from '../../../ui/useToast';
import useMarks from '../../../valuereview/useMarks';
import { cellAt, gridShape } from './stationModel';

/*
 * Where the station's plans meet src/grid (plan.md §8.16, §8.21; E39, E51–E55, E65–E67, D123, D125; the old
 * DocumentsTab's grid, pick, followCell, findCell, editCell and reviewPicked). Three ways to be on the Grid:
 * - view: a click, a drag, Shift, Ctrl, a head or a label picks (useGridSelection); picking never moves the file
 *   (D-125): F, ↗ Find in file or a double-click opens the value where it was read, in whichever file that is (D-164);
 * - Review mode (D-201, E65): the file follows the cell — at once for a click, 200 ms after the arrows stop — and E
 *   or a double-click opens that one cell for typing (useGridKeys' editor, its keys left to the pick);
 * - ✎ Edit (E66, E67): Excel's keys (useGridKeys); a click also shows the value in its file; each commit is one PATCH
 *   with `expect` through the plan-value door, Ctrl+Z writes the earlier value back.
 * A, I, C, U act on the picked values (a blank takes no mark) through the one marks door, a key above 25 asking first
 * (E52, D126); the answer lands in the Advisor's caches (E53). Above 40 plans only the columns in view are drawn (E39).
 */

const FOLLOW_MS = 200;

export default function useGridControls({ dealId, model, view, review, editing, scrollRef, sizes, onShow, viewer }) {
  const toast = useToast();
  const marks = useMarks(dealId, { toastDone: false });
  const writes = usePlanCellWrites(dealId, editing);
  const { rows, cols } = useMemo(() => gridShape(view), [view]);
  const slots = useMemo(() => new Map(cols.map((c, at) => [c, at])), [cols]);
  const live = useRef(null);
  const followTimer = useRef(null);
  useEffect(() => () => clearTimeout(followTimer.current), []);
  const revealRef = useRef(null);
  const reveal = useCallback((pos, then) => (revealRef.current ? revealRef.current(pos, then) : then()), []);
  const isEditable = (r, c) => Boolean(cellAt(model, r, c)?.applies);

  const keys = useGridKeys({
    enabled: editing || review,
    rows,
    cols,
    isEditable,
    valueAt: (r, c) => cellAt(model, r, c)?.raw ?? '',
    onCommit: (r, c, text, base) => writes.commit(Number(c), r, text, base),
    onUndo: () => {
      const went = writes.undo();
      return went ? { r: went.key, c: String(went.planId) } : null;
    },
    onMove: (r, c) => live.current?.moved(r, c),
    containerRef: scrollRef,
    reveal,
  });
  const pickOn = !editing && cols.length > 0;
  const pick = useGridSelection({
    enabled: pickOn,
    rows,
    cols,
    containerRef: scrollRef,
    onFind: (r, c) => live.current?.findCell(r, c),
    onFollow: review ? (r, c, how) => live.current?.follow(r, c, how) : null,
    onEdit: review ? (r, c) => live.current?.editCell(r, c) : null,
    reveal,
  });
  const win = useWindowed({
    axis: 'cols',
    count: cols.length,
    on: cols.length > WINDOW_COLS_OVER,
    pin: keys.editing ? (slots.get(keys.editing.c) ?? -1) : -1,
    size: sizes.planW,
    scrollRef,
  });
  useLayoutEffect(() => {
    revealRef.current = (pos, then) => win.reveal(slots.get(String(pos.c)), then);
  });

  /** The file follows the cell (Review, ✎ Edit): at once for a click, a beat after the keys stop. */
  function follow(r, c, how) {
    clearTimeout(followTimer.current);
    const cell = cellAt(model, r, c);
    let show = null;
    if (cell?.doc != null) show = () => onShow(cell.doc, cell.ref, { replace: true });
    // A cell with nothing to find leaves the file on its page, without the last value's box.
    else if (review && viewer.ref) show = () => onShow(viewer.docId, '', { replace: true, page: viewer.page });
    if (!show) return;
    if (how === 'click') show();
    else followTimer.current = setTimeout(show, FOLLOW_MS);
  }

  /** F, ↗ Find in file, a double-click: the value where it was read, in whichever file that is (D-164). */
  function findCell(r, c) {
    const cell = cellAt(model, r, c);
    if (cell?.doc != null) onShow(cell.doc, cell.ref);
    else if (!review) {
      toast.info(
        cell?.raw
          ? 'This value has no file to show it in: it was typed or carried over, not read'
          : 'Nothing was read into this cell',
      );
    }
  }

  function editCell(r, c) {
    if (!isEditable(r, c)) toast.info('That cell can’t be edited');
    else keys.editAt(r, c);
  }

  function moved(r, c) {
    if (review) pick.setOnly(r, c);
    if (review || editing) follow(r, c, 'key');
  }
  useLayoutEffect(() => {
    live.current = { follow, findCell, editCell, moved };
  });

  const picked = pickOn ? pick.picked() : [];
  const valued = picked.map(({ r, c }) => cellAt(model, r, c)).filter((cell) => cell && cell.raw !== '');

  async function reviewPicked(action, cells, { fromKey = false } = {}) {
    if (!cells.length) {
      toast.info('Nothing to review there: the cell is blank');
      return;
    }
    const refs = [...new Set(cells.map((cell) => cell.ref))];
    const where = refs.length === 1 ? 'that value' : 'the selected values';
    await marks.run(action, { refs }, { where, fromKey, count: refs.length });
    scrollRef.current?.focus?.({ preventScroll: true }); // the keys keep working after a toolbar button
  }

  /** A key from the tab's hotkeys (A, I, C, U, F; E in Review). */
  function act(action) {
    if (action === 'find' || action === 'edit') {
      const at = pick.activeCell();
      if (!at) toast.info(`Select a value first, then press ${action === 'find' ? 'F' : 'E'}`);
      else if (action === 'find') findCell(at.r, at.c);
      else editCell(at.r, at.c);
      return;
    }
    if (!valued.length) toast.info('Select a value first: click it, or drag across several');
    else reviewPicked(action, valued, { fromKey: true });
  }

  /** A Find step or Esc from the box: a value's match is picked (and, in Review, found in the file). */
  function selectHit(hit) {
    if (!pickOn || hit?.kind !== 'cell') return;
    pick.setOnly(hit.r, hit.c);
    if (review) follow(hit.r, hit.c, 'key');
  }

  /** E or a double-click on the List in Review: the List has no editor, so the value opens on the Grid (E65). */
  function editRef(ref) {
    const [, id, ...rest] = String(ref).split(':');
    const r = rest.join(':');
    if (!rows.includes(r) || !cols.includes(id)) {
      toast.info('A filter on the Grid hides that value: clear it, then edit it there');
      return;
    }
    pick.setOnly(r, id);
    follow(r, id, 'click');
    editCell(r, id);
  }

  return {
    keys,
    pick: pickOn ? pick : null,
    win,
    marks,
    writes,
    containerProps: editing ? keys.containerProps : pick.containerProps,
    pickBar: pickOn
      ? {
          picked: picked.length,
          count: valued.length,
          errors: valued.filter((cell) => cell.potential).length,
          busy: marks.busy,
          review,
          onAction: (action) => reviewPicked(action, valued),
          onFind: () => act('find'),
          onNarrow: () => pick.narrow((r, c) => Boolean(cellAt(model, r, c)?.potential)),
          onClear: pick.clear,
        }
      : null,
    act,
    selectHit,
    editRef,
    onEditClick: (r, c) => follow(r, c, 'click'),
    focus: () => scrollRef.current?.focus?.({ preventScroll: true }),
    reveal,
  };
}
