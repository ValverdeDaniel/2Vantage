import { useEffect, useImperativeHandle, useLayoutEffect, useRef, useState } from 'react';
import GridTable from './GridTable';
import GridToolbar from './GridToolbar';
import { hitKey } from './gridFind';
import useGridControls from './useGridControls';

/*
 * The Scanned data panel's Grid (plan.md §8.16; E36–E41, E50–E55, E60–E67, D123, D125, D129): what was read from the
 * file (or every proposal file) side by side, plans across and benefits down, with the toolbar above it — the plan
 * filters, the pick bar and the keys (GridToolbar) — and Find's marks on it. The panel owns the data and Find
 * (ScannedData, useStationGrid); this draws and holds the pick and the editor (useGridControls). `ref` takes the tab's
 * keys (`act`), Find's steps (`selectHit`), the way back to the keyboard (`focus`); `ask` = {ref, n} opens a value the
 * List handed over for editing (E65). ✎ Edit's ↶ Undo and Done ✓ sit in the toolbar's keys row: Done waits for the
 * last save before the grid leaves Edit (`onEditDone`).
 */
export default function StationGrid({
  ref,
  deal,
  grid,
  filter,
  modes,
  find,
  scrollRef,
  sizes,
  clipTip,
  onShow,
  viewer,
  ask,
  onEditDone,
}) {
  const { model, shown, found } = grid;
  const controls = useGridControls({
    dealId: deal.id,
    model,
    view: shown,
    review: modes.review,
    editing: modes.editing,
    scrollRef,
    sizes,
    onShow,
    viewer,
  });

  useImperativeHandle(ref, () => ({ act: controls.act, selectHit: controls.selectHit, focus: controls.focus }));
  const [leaving, setLeaving] = useState(false);
  const edit = {
    canUndo: controls.writes.canUndo,
    undo: () => controls.keys.undo(),
    leaving,
    done: async () => {
      setLeaving(true);
      try {
        await controls.writes.settle();
      } finally {
        setLeaving(false);
        onEditDone();
      }
    },
  };

  // The current match is scrolled into view (a plan column not drawn yet is drawn first).
  const current = find.current;
  useLayoutEffect(() => {
    if (!current) return;
    const show = () =>
      scrollRef.current
        ?.querySelector?.(`[data-sf="${CSS.escape(current.key)}"]`)
        ?.scrollIntoView?.({ block: 'nearest', inline: 'nearest' });
    controls.reveal(current, show);
  }, [current?.key, find.nonce]); // eslint-disable-line react-hooks/exhaustive-deps

  // A value the List handed over for editing, once.
  const asked = useRef(null);
  useEffect(() => {
    if (!ask || asked.current === ask.n) return;
    asked.current = ask.n;
    controls.editRef(ask.ref);
  });

  const at = current ? found.index.get(current.key) : -1;
  const ui = {
    model,
    names: model.names,
    activeRef: viewer.ref,
    editing: modes.editing,
    keys: controls.keys,
    pick: controls.pick,
    win: controls.win,
    sizes,
    clipTip,
    containerProps: controls.containerProps,
    errorOf: controls.writes.errorOf,
    onEditClick: controls.onEditClick,
    find: {
      classes: (r, c) => {
        const n = found.index.get(hitKey(r, c));
        if (n == null) return '';
        return n === at ? 'sf-hit sf-current' : 'sf-hit';
      },
      props: (r, c) => (found.index.has(hitKey(r, c)) ? { 'data-sf': hitKey(r, c) } : {}),
    },
  };

  return (
    <>
      <GridToolbar
        filter={filter}
        pick={controls.pickBar}
        done={controls.marks.last}
        onUndo={controls.marks.undo}
        undoing={controls.marks.undoing}
        edit={modes.editing ? edit : null}
      />
      <GridTable view={shown} ui={ui} />
    </>
  );
}
