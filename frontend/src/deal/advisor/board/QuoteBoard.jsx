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
import ReviewBulkBar from '../../../valuereview/ReviewBulkBar';
import PricedComposer from '../priced/PricedComposer';
import { buttonLabel, sourceWords } from '../enrollment/countsModel';
import usePricedDraft from '../priced/usePricedDraft';
import BoardHead from './BoardHead';
import FilterCard from './FilterCard';
import { emptyNote, hitsOn } from './finder';
import { exportKeys, sections, shownKeys } from './boardColumns';
import { buildBoard, countLine, transposeState } from './boardModel';
import { drawnOrder } from './boardOrder';
import { supersededIds } from './chips';
import RowsTable from './RowsTable';
import SelectBar from './SelectBar';
import TableBar from './TableBar';
import TransposedTable from './TransposedTable';
import useBoardActions from './useBoardActions';
import useBoardConfig from './useBoardConfig';
import useBoardFilters from './useBoardFilters';
import useBoardGrid from './useBoardGrid';
import useBoardReview from './useBoardReview';
import useCellWrites from './useCellWrites';
import useFindFlash from './useFindFlash';
import useTicks from './useTicks';

/*
 * The quote board (plan.md §8.14; F5, F9, F31–F36, F40, F57–F62, F68–F73, F93): one line's comparison as the old
 * Advisor drew it — the board header, the ticked rows' bar, then the table card with its presets, sort and ⇄
 * Transpose. Above them the filter card (slice 10): the finder, the filters and the saved setups, one config kept in
 * the URL (useBoardConfig) that narrows the quotes before they are drawn. The config and ✎ Edit carry across line
 * switches; ticks do not. While ✎ Edit is on and a column sort is set, the rows hold their order until the person
 * changes the sort or a filter (F33). Under the board header, the review strip: "N AI values to review" on the ticked,
 * filtered or line's plans, with Approve, Ignore and Needs checking (F65; slice 17). In ✎ Edit, ＋ on a plan prices a
 * version of it (slice 35, F76–F84): the draft lives in the table, or docked above it in PricedComposer. Above the
 * table, `enrollment.panel`: the counts card or the split and census notices (slice 13, F85–F91). ▦ Pages swaps the
 * table for `pages.render(preset)`, "What the client will see" (slice 14, F37), the Columns tab picking its rows.
 */
export default function QuoteBoard({ deal, meta, lines, line, onLine, data, prefs, onDialog, enrollment, pages }) {
  const toast = useToast();
  const boardMeta = meta.board;
  const view = useBoardConfig(boardMeta, prefs);
  const { config, set } = view;
  const { preset, sort } = config;
  const [editing, setEditing] = useState(false);
  const [leaving, setLeaving] = useState(false);
  const [held, setHeld] = useState(null);
  const [moveTo, setMoveTo] = useState({ line, key: '' });
  const [confirm, setConfirm] = useState(null); // {kind: 'delete', ids} | {kind: 'clear'}
  const [exporting, setExporting] = useState(false);
  const lineLabel = (key) => meta.lines.find((row) => row.key === key)?.label ?? key;

  const board = useMemo(() => buildBoard({ comparison: data, meta, line, preset, sort }), [data, meta, line, preset, sort]);
  const filters = useBoardFilters({ dealId: deal.id, meta, lines, line, config, quotes: board.quotes, sorted: board.sorted });
  let quotes = filters.shown;
  if (editing && !board.inProposal) {
    const key = JSON.stringify([line, { ...config, layout: null, preset: null }]);
    const kept = holdOrder(held, key, quotes.map((p) => p.id), new Set(board.quotes.map((p) => p.id)));
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
  const pricedKit = { dealId: deal.id, line, plans: board.plans, meta, rateBasis: data.rate_basis, fields: board.fields };
  const priced = usePricedDraft({ ...pricedKit, lineLabel });
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
  const finderRef = useRef(null);
  const here = hitsOn(filters.finder, line);
  const showPlan = useFindFlash({ drawn, rowsLayout: shown === 'rows', win, scrollRef, soleHit: here.length === 1 ? here[0] : null });

  const review = useBoardReview({
    dealId: deal.id,
    comparison: data,
    meta,
    lineLabel: lineLabel(line),
    drawn,
    ticked: drawn.filter((plan) => ticks.ids.has(plan.id)),
    filtering: Boolean(filters.active || filters.finder.active),
  });

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
      priced.cancel();
    }
  };
  const exportBoard = async () => {
    setExporting(true);
    const columns = exportKeys(board.columns, shown === 'cols' ? sectionList : null);
    await actions.exportBoard({ line, plans: drawn.map((p) => p.id), columns, orientation: shown });
    setExporting(false);
  };
  const openCounts = () => onDialog(enrollment.open ? null : { kind: 'counts' });
  const otherIds = new Set(lines.map((row) => row.line));

  const ui = {
    editing,
    grid,
    prompt,
    errorOf: writes.errorOf,
    documents: data.documents,
    compliance: boardMeta.compliance,
    sources: sourceWords(meta), // where a total's enrollment came from, in words (F86)
    families: boardMeta.priced?.families, // the priced-version chip's glyph (F62, F84)
    namesById: new Map(board.plans.map((p) => [p.id, `${p.carrier} ${p.name}`])),
    supersededIds: supersededIds(board.plans),
    shownIds: drawn.map((p) => p.id),
    axis: shown === 'cols' ? 'x' : 'y',
    ordering: actions.busy.order,
    linking: actions.busy.links,
    starring: actions.busy.star,
    sort,
    sortBy: (key) => set((now) => ({ sort: nextSort(now.sort, key) })),
    ticks,
    review, // the flags chip's menu (F63)
    priced: editing ? priced : null, // ＋ / ✎ / ✕ and the draft's stack (F76–F84; slice 35)
    // Drawn only when no quote is (F17): why nothing shows.
    emptyNote: quotes.length
      ? null
      : emptyNote({ finder: filters.finder, line, lineLabel: lineLabel(line), others: filters.others, quoteCount: board.quotes.length }),
    actions: {
      ...actions,
      remove: (ids) => setConfirm({ kind: 'delete', ids }),
      editLinks: (plan) => onDialog({ kind: 'plan', plan }),
    },
  };

  return (
    <div className="bnf-advisor-tab-split">
      <div>
        <FilterCard
          meta={meta}
          line={line}
          lineLabel={lineLabel(line)}
          view={view}
          filters={filters}
          currents={board.currents.length}
          finderRef={finderRef}
          onFind={() => (filters.finder.active && quotes.length ? showPlan(quotes[0].id) : null)}
          onPickLine={onLine}
          onCounts={() => onDialog({ kind: 'counts' })}
        />
        <BoardHead
          dealId={deal.id}
          lines={lines}
          line={line}
          onLine={onLine}
          count={countLine({ shown: quotes.length, quotes: board.quotes, currents: board.currents, packages: data.packages })}
          editing={editing}
          starred={board.quotes.filter((p) => p.starred).length}
          ui={{
            quoteCount: board.quotes.length,
            counts: board.plans.length ? { label: buttonLabel(data.enrollment, lineLabel(line)), open: enrollment.open } : null,
            busy: { exporting, remove: actions.busy.remove },
            open: {
              activity: () => onDialog({ kind: 'activity' }),
              counts: openCounts,
              importing: () => onDialog({ kind: 'import' }),
              addPlan: () => onDialog({ kind: 'plan', plan: null }),
              clearLine: () => setConfirm({ kind: 'clear' }),
            },
            edit: { enter: () => setEditing(true), undo: grid.undo, canUndo: writes.canUndo, done, leaving, priced },
            actions: {
              exportBoard,
              clearShortlist: actions.clearShortlist,
              downloadTemplate: () => downloadFile(templateUrl(deal.id, line)).catch((e) => toast.error(errorText(e))),
            },
          }}
        />
        <ReviewBulkBar
          counts={review.strip.counts}
          target={review.strip.target}
          busy={review.busy}
          onAction={review.strip.onAction}
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
        {editing && priced.draft?.expanded && <PricedComposer kit={priced} />}
        {enrollment.panel}
        <div className="bb-grid-card">
          <TableBar
            board={boardMeta}
            preset={preset}
            onPreset={(next) => set({ preset: next })}
            sort={sort}
            onSort={(next) => set({ sort: next })}
            currents={board.currents.length}
            sizes={sizes}
            transpose={{ shown, blocked, max, count: drawn.length, pick: prefs.pickOrientation }}
            pages={pages}
          />
          {pages?.on ? pages.render(preset) : (
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
          )}
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
