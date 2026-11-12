import { useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router';
import { templateUrl } from '../../../api/quotes';
import EditModePrompt from '../../../grid/EditModePrompt';
import useClipTip from '../../../grid/useClipTip';
import useFreezePanes from '../../../grid/useFreezePanes';
import useGridSizes from '../../../grid/useGridSizes';
import { downloadFile } from '../../../lib/download';
import { errorText } from '../../../lib/errors';
import ConfirmDialog from '../../../ui/ConfirmDialog';
import { useToast } from '../../../ui/useToast';
import ReviewBulkBar from '../../../valuereview/ReviewBulkBar';
import { sections, shownKeys } from '../board/boardColumns';
import { buildBoard } from '../board/boardModel';
import { drawnOrder } from '../board/boardOrder';
import { supersededIds } from '../board/chips';
import SelectBar from '../board/SelectBar';
import TransposedTable from '../board/TransposedTable';
import useBoardActions from '../board/useBoardActions';
import useBoardGrid from '../board/useBoardGrid';
import useBoardReview from '../board/useBoardReview';
import useCellWrites from '../board/useCellWrites';
import useTicks from '../board/useTicks';
import { sourceWords } from '../enrollment/countsModel';
import LineTabs from '../LineTabs';
import PresentedToolbar from './PresentedToolbar';
import { presentedPlans, shortlistWords } from './presentedModel';
import useReread from './useReread';

const PRESET = 'all'; // every row the line's plans fill, in its groups (the old grid's planSections)
const ORDER = { key: 'proposal', dir: 1 }; // the client's order: the arrows move a plan, nothing sorts on a value

/*
 * The Advisor's board in presented mode, the Proposal tab's grid (plan.md §8.15; J70–J94; the old ComparisonGrid.jsx
 * at 891f1b3, ch31: one board, not a second grid): this tab's toolbar, the line tabs with counts, the counts card and
 * notices (`enrollment.panel`, J83), the bulk review bar (J84), the ticked rows' bar, and the board's own transposed
 * table — plans as columns in Proposal order, every row of the line — with its frozen panes, Excel keys, sizes,
 * chips, ◀ ▶ and ⋯ menu (sold, roles and renewals, Attach SBC…, Move to line…, Remove column; J85–J93) and its cost
 * rows (J94). The shortlist shows what the proposal presents until "Show all N plans" (J76).
 */
export default function PresentedGrid({ deal, meta, lines, line, onLine, data, onDialog, enrollment }) {
  const navigate = useNavigate();
  const toast = useToast();
  const [showAll, setShowAll] = useState(false);
  const [editing, setEditing] = useState(false);
  const [leaving, setLeaving] = useState(false);
  const [confirm, setConfirm] = useState(null); // {ids} of plans to remove
  const [moveTo, setMoveTo] = useState({ line, key: '' });
  const lineLabel = (key) => meta.lines.find((row) => row.key === key)?.label ?? key;

  const board = useMemo(() => buildBoard({ comparison: data, meta, line, preset: PRESET, sort: ORDER }), [data, meta, line]);
  const picked = presentedPlans(board.plans, showAll);
  const kept = new Set(picked.shown.map((plan) => plan.id));
  const quotes = board.sorted.filter((plan) => kept.has(plan.id));
  const drawn = drawnOrder(board.order, quotes, true);
  const sectionList = sections(meta, data.groups, shownKeys(meta, line, PRESET, ORDER.key));
  const fieldKeys = sectionList.flatMap((section) => section.keys).filter((key) => board.fields[key]);

  const writes = useCellWrites(deal.id, editing);
  const actions = useBoardActions(deal.id, line, lineLabel);
  const scrollRef = useRef(null);
  const bodyRef = useRef(null);
  const { grid, prompt } = useBoardGrid({
    board,
    drawn,
    fieldKeys,
    orientation: 'cols',
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
  const sizes = useGridSizes({ grid: 'proposal', scrollRef, padY: 17 });
  const clipTip = useClipTip();
  const ticks = useTicks(line, editing, drawn, quotes, board.plans);
  const reread = useReread(deal.id, meta);
  const review = useBoardReview({
    dealId: deal.id,
    comparison: data,
    meta,
    lineLabel: lineLabel(line),
    drawn,
    ticked: drawn.filter((plan) => ticks.ids.has(plan.id)),
    filtering: picked.active,
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
    }
  };
  const ui = {
    editing,
    grid,
    prompt,
    errorOf: writes.errorOf,
    documents: data.documents,
    compliance: meta.board.compliance,
    sources: sourceWords(meta),
    families: meta.board.priced?.families,
    namesById: new Map(board.plans.map((p) => [p.id, `${p.carrier} ${p.name}`])),
    supersededIds: supersededIds(board.plans),
    shownIds: drawn.map((p) => p.id),
    axis: 'x',
    ordering: actions.busy.order,
    linking: actions.busy.links,
    starring: actions.busy.star,
    sort: ORDER,
    sortBy: () => {}, // Proposal order only: a header never sorts here
    ticks,
    review,
    priced: null,
    replacing: false, // the old Plan comparison's heads: chips, carrier, name, arrows and ⋯, never "Replacing:"
    emptyNote: drawn.length ? null : `No plans on ${lineLabel(line)} yet.`,
    actions: { ...actions, remove: (ids) => setConfirm({ ids }), editLinks: (plan) => onDialog({ kind: 'plan', plan }) },
  };
  return (
    <div>
      <PresentedToolbar
        dealId={deal.id}
        edit={{ editing, enter: () => setEditing(true), undo: grid.undo, canUndo: writes.canUndo, done, leaving }}
        sizes={sizes}
        shortlist={{ words: shortlistWords(picked), active: picked.active, toggle: () => setShowAll((was) => !was) }}
        open={{
          importing: () => onDialog({ kind: 'import' }),
          addPlan: () => onDialog({ kind: 'plan', plan: null }),
          downloadTemplate: () => downloadFile(templateUrl(deal.id, line)).catch((e) => toast.error(errorText(e))),
          advisor: () => navigate(`/deals/${deal.id}/advisor`),
        }}
        reread={reread}
      />
      <LineTabs lines={lines} line={line} onPick={onLine} />
      {enrollment}
      <ReviewBulkBar {...review.strip} busy={review.busy} />
      <SelectBar
        count={ticks.count}
        todo={ticks.todo}
        editing={editing}
        busy={actions.busy}
        moveTo={moveTo.line === line ? moveTo.key : ''}
        onMoveTo={(key) => setMoveTo({ line, key })}
        lines={lines.filter((row) => row.line !== line).map((row) => ({ key: row.line, label: row.label }))}
        otherLines={meta.lines.filter((row) => row.key !== line && !lines.some((other) => other.line === row.key))}
        actions={{
          star: (ids, on) => runOnTicks(actions.star(ids, on)),
          setRole: (ids, role) => runOnTicks(actions.setRole(ids, role)),
          moveLine: (ids, to) => runOnTicks(actions.moveLine(ids, to)).then(() => setMoveTo({ line, key: '' })),
        }}
        onDelete={(ids) => setConfirm({ ids, ticks: true })}
        onClear={ticks.clear}
      />
      <div className="bb-grid-card">
        <div className="bb-grid-scroll gk-grid bnf-freeze" onScroll={clipTip.hide} {...grid.containerProps}>
          <TransposedTable board={board} drawn={drawn} sections={sectionList} ui={ui} sizes={sizes} clipTip={clipTip} />
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
        title={`Remove ${confirm?.ids?.length} plan${confirm?.ids?.length === 1 ? '' : 's'}?`}
        message="Sold plans stay; a current plan's renewal becomes an alternate. Undo, or Revert in the Activity log, brings them back."
        confirmLabel="Remove"
        tone="danger"
        onCancel={() => setConfirm(null)}
        onConfirm={() => {
          const asked = confirm;
          setConfirm(null);
          const call = actions.remove(asked.ids);
          if (asked.ticks) runOnTicks(call);
        }}
      />
    </div>
  );
}
