import { useMemo, useRef, useState } from 'react';
import { templateUrl } from '../../../api/quotes';
import EditModePrompt from '../../../grid/EditModePrompt';
import { holdOrder, nextSort } from '../../../grid/sort';
import useClipTip from '../../../grid/useClipTip';
import useFreezePanes from '../../../grid/useFreezePanes';
import useGridSizes from '../../../grid/useGridSizes';
import { downloadFile } from '../../../lib/download';
import { errorText } from '../../../lib/errors';
import ConfirmDialog from '../../../ui/ConfirmDialog';
import cx from '../../../ui/cx';
import { useToast } from '../../../ui/useToast';
import BoardHead from './BoardHead';
import { exportKeys, sections, shownKeys } from './boardColumns';
import { buildBoard, countLine, transposeState } from './boardModel';
import { drawnOrder } from './boardOrder';
import { supersededIds } from './chips';
import RowsTable from './RowsTable';
import SelectBar from './SelectBar';
import TableBar from './TableBar';
import TransposedTable from './TransposedTable';
import useBoardActions from './useBoardActions';
import useBoardGrid from './useBoardGrid';
import useCellWrites from './useCellWrites';
import useTicks from './useTicks';

/*
 * The quote board (plan.md §8.14; F5, F9, F31–F36, F40, F57–F62, F68–F73, F93): one line's comparison as the old
 * Advisor drew it — the board header, the ticked rows' bar, then the table card with its presets, sort and ⇄
 * Transpose. The preset, the sort and ✎ Edit carry across line switches; ticks do not. While ✎ Edit is on and a
 * column sort is set, the rows hold their order until the person changes the sort (F33).
 */
export default function QuoteBoard({ deal, meta, lines, line, onLine, data, prefs, onDialog }) {
  const toast = useToast();
  const boardMeta = meta.board;
  const [preset, setPreset] = useState(boardMeta.default_preset);
  const [sort, setSort] = useState({ key: boardMeta.default_sort, dir: 1 });
  const [editing, setEditing] = useState(false);
  const [leaving, setLeaving] = useState(false);
  const [held, setHeld] = useState(null);
  const [moveTo, setMoveTo] = useState({ line, key: '' });
  const [confirm, setConfirm] = useState(null); // {kind: 'delete', ids} | {kind: 'clear'}
  const [exporting, setExporting] = useState(false);
  const lineLabel = (key) => meta.lines.find((row) => row.key === key)?.label ?? key;

  const board = useMemo(() => buildBoard({ comparison: data, meta, line, preset, sort }), [data, meta, line, preset, sort]);
  let quotes = board.sorted;
  if (editing && !board.inProposal) {
    const kept = holdOrder(held, JSON.stringify([line, sort]), board.sorted.map((p) => p.id), new Set(board.quotes.map((p) => p.id)));
    if (kept.held !== held) setHeld(kept.held);
    quotes = kept.ids.map((id) => board.order.byId.get(id)).filter(Boolean);
  } else if (held) setHeld(null);
  const drawn = drawnOrder(board.order, quotes, board.inProposal);

  const max = boardMeta.transpose_max;
  const { blocked, shown } = transposeState(drawn.length, max, prefs.orientation);
  const keys = shownKeys(meta, line, preset, sort.key);
  const sectionList = sections(meta, data.groups, keys);
  const fieldKeys =
    shown === 'rows'
      ? board.columns.filter((col) => col.kind === 'field').map((col) => col.key)
      : sectionList.flatMap((s) => s.keys).filter((key) => board.fields[key]);

  const writes = useCellWrites(deal.id, editing);
  const actions = useBoardActions(deal.id, line, lineLabel);
  const scrollRef = useRef(null);
  const bodyRef = useRef(null);
  const { grid, win, prompt } = useBoardGrid({
    board,
    drawn,
    fieldKeys,
    orientation: shown,
    editing,
    writes,
    enterEdit: () => {
      setEditing(true);
      return true;
    },
    scrollRef,
    bodyRef,
  });
  useFreezePanes(scrollRef);
  const sizes = useGridSizes({ grid: 'advisor', scrollRef, padY: 17 });
  const clipTip = useClipTip();
  const ticks = useTicks(line, editing, drawn, quotes, board.plans);
  const target = moveTo.line === line ? moveTo.key : '';

  const runOnTicks = (promise) =>
    promise.then((answer) => {
      if (answer) ticks.clear();
    });
  const done = async () => {
    setLeaving(true);
    try {
      await writes.settle();
    } finally {
      setLeaving(false);
      setEditing(false);
    }
  };
  const exportBoard = async () => {
    setExporting(true);
    const columns = exportKeys(board.columns, shown === 'cols' ? sectionList : null);
    await actions.exportBoard({ line, plans: drawn.map((p) => p.id), columns, orientation: shown });
    setExporting(false);
  };
  const typed = board.plans.filter((p) => p.enrollment_on && Object.values(p.enrollment ?? {}).some(Number)).length;
  const otherIds = new Set(lines.map((row) => row.line));

  const ui = {
    editing,
    grid,
    prompt,
    errorOf: writes.errorOf,
    documents: data.documents,
    compliance: boardMeta.compliance,
    namesById: new Map(board.plans.map((p) => [p.id, `${p.carrier} ${p.name}`])),
    supersededIds: supersededIds(board.plans),
    shownIds: drawn.map((p) => p.id),
    axis: shown === 'cols' ? 'x' : 'y',
    ordering: actions.busy.order,
    linking: actions.busy.links,
    starring: actions.busy.star,
    sort,
    sortBy: (key) => setSort((now) => nextSort(now, key)),
    ticks,
    emptyNote: board.quotes.length
      ? 'No plans match the current filters.'
      : `No quoted plans on ${lineLabel(line)} yet — only the current plans.`,
    actions: {
      ...actions,
      remove: (ids) => setConfirm({ kind: 'delete', ids }),
      editLinks: (plan) => onDialog({ kind: 'plan', plan }),
    },
  };

  return (
    <div className="bnf-advisor-tab-split">
      <div>
        <BoardHead
          dealId={deal.id}
          lines={lines}
          line={line}
          onLine={onLine}
          count={countLine({ shown: board.sorted.length, quotes: board.quotes, currents: board.currents, packages: data.packages })}
          editing={editing}
          starred={board.quotes.filter((p) => p.starred).length}
          ui={{
            quoteCount: board.quotes.length,
            counts: data.rate_basis === 'composite' && board.plans.length ? { typed, label: lineLabel(line).toLowerCase() } : null,
            busy: { exporting, remove: actions.busy.remove },
            open: {
              activity: () => onDialog({ kind: 'activity' }),
              counts: () => onDialog({ kind: 'counts' }),
              importing: () => onDialog({ kind: 'import' }),
              addPlan: () => onDialog({ kind: 'plan', plan: null }),
              clearLine: () => setConfirm({ kind: 'clear' }),
            },
            edit: { enter: () => setEditing(true), undo: grid.undo, canUndo: writes.canUndo, done, leaving },
            actions: {
              exportBoard,
              clearShortlist: actions.clearShortlist,
              downloadTemplate: () => downloadFile(templateUrl(deal.id, line)).catch((e) => toast.error(errorText(e))),
            },
          }}
        />
        <SelectBar
          count={ticks.count}
          todo={ticks.todo}
          editing={editing}
          busy={actions.busy}
          moveTo={target}
          onMoveTo={(key) => setMoveTo({ line, key })}
          lines={lines.filter((row) => row.line !== line).map((row) => ({ key: row.line, label: row.label }))}
          otherLines={meta.lines.filter((row) => row.key !== line && !otherIds.has(row.key))}
          actions={{
            star: (ids, on) => runOnTicks(actions.star(ids, on)),
            setRole: (ids, role) => runOnTicks(actions.setRole(ids, role)),
            moveLine: (ids, to) => runOnTicks(actions.moveLine(ids, to)).then(() => setMoveTo({ line, key: '' })),
          }}
          onDelete={(ids) => setConfirm({ kind: 'delete', ids, ticks: true })}
          onClear={ticks.clear}
        />
        <div className="bb-grid-card">
          <TableBar
            board={boardMeta}
            preset={preset}
            onPreset={setPreset}
            sort={sort}
            onSort={setSort}
            currents={board.currents.length}
            sizes={sizes}
            transpose={{ shown, blocked, max, count: drawn.length, pick: prefs.pickOrientation }}
          />
          <div
            className={cx('bb-grid-scroll gk-grid', shown === 'cols' && 'bnf-freeze')}
            onScroll={clipTip.hide}
            {...grid.containerProps}
          >
            {shown === 'rows' ? (
              <RowsTable board={board} drawn={drawn} ui={ui} win={win} bodyRef={bodyRef} />
            ) : (
              <TransposedTable board={board} drawn={drawn} sections={sectionList} ui={ui} sizes={sizes} clipTip={clipTip} />
            )}
          </div>
        </div>
      </div>
      <EditModePrompt {...prompt} />
      {clipTip.tip && (
        <div className="bb-tooltip" style={{ left: `${clipTip.tip.x}px`, top: `${clipTip.tip.y}px` }}>
          <div className="bb-tooltip-line bnf-tip-full">{clipTip.tip.text}</div>
        </div>
      )}
      <ConfirmDialog
        open={Boolean(confirm)}
        title={confirm?.kind === 'clear' ? `Remove every quoted plan on ${lineLabel(line)}?` : `Remove ${confirm?.ids?.length} plan${confirm?.ids?.length === 1 ? '' : 's'}?`}
        message={
          confirm?.kind === 'clear'
            ? 'Current and sold plans stay. Undo, or Revert in the Activity log, brings the rest back.'
            : "Sold plans stay; a current plan's renewal becomes an alternate. Undo, or Revert in the Activity log, brings them back."
        }
        confirmLabel="Remove"
        tone="danger"
        onCancel={() => setConfirm(null)}
        onConfirm={() => {
          const asked = confirm;
          setConfirm(null);
          const call = asked.kind === 'clear' ? actions.clearLine() : actions.remove(asked.ids);
          if (asked.ticks) runOnTicks(call);
        }}
      />
    </div>
  );
}
