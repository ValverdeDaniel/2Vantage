import { useEffect, useMemo, useRef, useState } from 'react';
import { usePlanSources } from '../../api/planReview';
import useClipTip from '../../grid/useClipTip';
import useGridSizes from '../../grid/useGridSizes';
import { displayValue } from '../../lib/fieldValue';
import cx from '../../ui/cx';
import InlineError from '../../ui/InlineError';
import { useToast } from '../../ui/useToast';
import { REVIEW_KEYS, REVIEW_MODE_KEYS } from '../../valuereview/keys';
import { listHits } from '../../valuereview/listFind';
import ReviewBulkBar from '../../valuereview/ReviewBulkBar';
import useMarks from '../../valuereview/useMarks';
import useReviewHotkeys from '../../valuereview/useReviewHotkeys';
import FindBar from './FindBar';
import StationGrid from './grid/StationGrid';
import useStationGrid from './grid/useStationGrid';
import ScanActions from './ScanActions';
import ScanHead from './ScanHead';
import ScanList from './ScanList';
import useStationFind from './useStationFind';

/*
 * The Scanned data panel beside the file (plan.md §8.16, §10.7; E34–E68, D121–D129; the old DocumentsTab's scan
 * panel): what was read from this file (or every proposal file) as the List, worst first (slice 17), or the Grid, side
 * by side (slice 23), with Find over either, Review mode and ✎ Edit.
 * - The head: "Scanned data · Proposal · all N files", the quality headline (E34) and the buttons (ScanActions).
 * - Find (E60–E64): Ctrl+F, "N of M", Enter steps, Only matches, Esc selects the match; carrier nicknames fold.
 * - The file strip over the Grid (E48): Approve, Ignore, Needs checking on these files' open warnings (OQ28).
 * - The keys A, I, C, U and F (E in Review) act on the List's row or the Grid's pick wherever focus is on the tab.
 * - Review mode (E65): the file follows the value you are on; E or a double-click edits (on the List, on the Grid).
 * `onShow(docId, ref, opts)` opens a value in its file and keeps this panel's scope (D-164); `viewer` is what the
 * viewer shows ({docId, page, ref}); `modes` (useStationModes) is the tab's, which lays the List beside the file. Plan values only: intake, census and questionnaire files join with their owners.
 */
const FOLLOW_MS = 200;

export default function ScannedData({ deal, meta, scope, expanded, modes, viewer, onShow, check }) {
  const toast = useToast();
  const [bucket, setBucket] = useState('');
  const [hidden, setHidden] = useState(false);
  const [planFilter, setPlanFilter] = useState('all');
  const [rowsOnly, setRowsOnly] = useState(false);
  const [ask, setAsk] = useState(null); // a List value handed to the Grid for editing (E65)
  const listRef = useRef(null);
  const gridRef = useRef(null);
  const scrollRef = useRef(null);
  const followTimer = useRef(null);
  useEffect(() => () => clearTimeout(followTimer.current), []);
  const proposal = scope.bucket === 'proposal';
  const sources = usePlanSources(deal.id, { documentIds: scope.ids, bucket, enabled: proposal });
  const marks = useMarks(deal.id);
  const find = useStationFind(meta.carriers);
  const fields = useMemo(() => Object.fromEntries((meta.plans?.fields ?? []).map((f) => [f.key, f])), [meta.plans]);
  const pages = sources.data?.pages;
  const head = pages?.[0] ?? null;
  const rows = useMemo(() => (pages ?? []).flatMap((page) => page.rows), [pages]);
  const listed = Boolean(proposal && (head?.all.open || head?.all.done));
  const words = scope.ids.length > 1 ? 'these files' : 'this file';
  const gridOn = listed && (modes.view === 'grid' || modes.editing);
  const grid = useStationGrid({
    dealId: deal.id,
    plansMeta: meta.plans,
    scopeIds: scope.ids,
    enabled: gridOn,
    terms: find.terms,
    only: find.only,
    filters: { errorsOnly: planFilter === 'errors', rowsOnly },
  });
  const sizes = useGridSizes({ grid: 'proposal', scrollRef });
  const clipTip = useClipTip();
  const gridPlans = gridOn && !grid.data.pending && !grid.data.error && grid.model.plans.length > 0;

  // Find: the Grid's hits, or the List's loaded rows; a new view or filter starts again at match 1.
  const valueOf = (row) => displayValue(fields[row.key], row.value);
  const listFound = useMemo(
    () =>
      gridOn
        ? []
        : listHits(rows, find.terms, {
            valueOf: (row) => displayValue(fields[row.key], row.value),
            carrierOf: (row) => grid.data.index.get(row.plan_id)?.carrier ?? null,
          }),
    [gridOn, rows, find.terms, fields, grid.data.index],
  );
  const hits = gridOn ? grid.found.hits : listFound;
  const at = find.cursor(hits, [gridOn, planFilter, rowsOnly, bucket].join('~'));
  const step = (dir) => {
    const hit = find.step(at, dir, hits);
    if (gridOn) gridRef.current?.selectHit(hit);
  };
  const leave = () => {
    if (gridOn) {
      gridRef.current?.selectHit(at.current);
      gridRef.current?.focus();
    } else listRef.current?.focus();
    find.setQuery('');
  };

  useReviewHotkeys({
    enabled: listed && !modes.editing && !(expanded && hidden),
    keys: modes.review ? REVIEW_MODE_KEYS : REVIEW_KEYS,
    onKey: (action) => {
      if (gridOn) gridRef.current?.act(action);
      else if (!listRef.current?.act(action)) toast.info('Select a value first: click it in the list');
    },
  });

  const open = (row) => onShow(row.doc, row.ref, { replace: modes.review });
  const followRow = (row) => {
    clearTimeout(followTimer.current);
    followTimer.current = setTimeout(() => onShow(row.doc, row.ref, { replace: true }), FOLLOW_MS);
  };
  const editRow = (row) => {
    modes.pickView('grid');
    setAsk((now) => ({ ref: row.ref, n: (now?.n ?? 0) + 1 }));
  };
  const strip = (action) => marks.run(action, { document_ids: scope.ids }, { where: words });
  const toggleReview = () => {
    modes.setReview(!modes.review);
    (gridOn ? gridRef.current : listRef.current)?.focus();
  };

  let body;
  if (!proposal) {
    body = (
      <div className="bb-subtitle bb-mt">
        {scope.bucket === 'census'
          ? 'No census roster yet — map this file from the Census tab to build the grid.'
          : 'Intake documents aren’t scanned yet — assign and preview them here; any fields traced to this file appear once available.'}
      </div>
    );
  } else if (sources.isPending || (gridOn && grid.data.pending)) {
    body = <div className="bb-subtitle bb-mt">Loading the quoted plans…</div>;
  } else if (sources.isError || (gridOn && grid.data.error)) {
    const failed = sources.isError ? sources : grid.data;
    body = (
      <InlineError compact title="Could not load the values." error={failed.error} onRetry={() => failed.refetch()} />
    );
  } else if (!listed || (gridOn && !gridPlans)) {
    body = (
      <div className="bb-subtitle bb-mt">
        Nothing read from {words} is on the grid yet — read it with ✦ Work with Claude, and the plans it finds show here.
      </div>
    );
  } else if (gridOn) {
    body = (
      <StationGrid
        ref={gridRef}
        deal={deal}
        grid={grid}
        filter={{
          mode: planFilter === 'errors' && grid.model.issues.size ? 'errors' : 'all',
          plans: grid.model.plans.length,
          errorPlans: grid.model.issues.size,
          rowsOnly: rowsOnly && grid.model.issues.size > 0,
          onMode: setPlanFilter,
          onRowsOnly: setRowsOnly,
        }}
        modes={modes}
        find={{ current: at.current, nonce: find.nonce }}
        scrollRef={scrollRef}
        sizes={sizes}
        clipTip={clipTip}
        onShow={onShow}
        viewer={viewer}
        ask={ask}
        onEditDone={() => modes.setEditing(false)}
      />
    );
  } else {
    body = (
      <ScanList
        ref={listRef}
        meta={meta}
        scope={scope}
        head={head}
        rows={rows}
        sources={sources}
        bucket={bucket}
        onBucket={setBucket}
        marks={marks}
        valueOf={valueOf}
        activeRef={viewer.ref}
        check={check}
        review={modes.review}
        find={{ hits: listFound, current: at.current, only: find.only, nonce: find.nonce, words: find.words }}
        onOpen={open}
        onFollow={followRow}
        onEdit={editRow}
      />
    );
  }

  return (
    <div
      className={cx('bb-panel bnf-scan-panel', expanded && hidden && 'bnf-docs-hidden', modes.editing && 'bnf-scan-editing')}
      data-scanned-data
    >
      {expanded && hidden && (
        <button type="button" className="bnf-docs-showdata" onClick={() => setHidden(false)} title="Bring the scanned data back">
          ▴ Scanned data
        </button>
      )}
      <ScanHead scope={scope} head={proposal ? head : null}>
        <ScanActions
          view={gridOn ? 'grid' : 'list'}
          onView={listed && !modes.editing ? modes.pickView : null}
          resetSizes={gridPlans && sizes.custom ? sizes.reset : null}
          onHide={expanded && !hidden ? () => setHidden(true) : null}
          review={modes.review}
          onReview={listed && !modes.editing ? toggleReview : null}
          onEdit={listed && !modes.editing ? () => modes.setEditing(true) : null}
        />
      </ScanHead>
      {listed && (
        <FindBar
          query={find.query}
          onQuery={find.setQuery}
          total={at.total}
          at={at.index}
          onStep={step}
          only={find.rawOnly}
          onOnly={find.setOnly}
          onLeave={leave}
        />
      )}
      {gridPlans && !modes.editing && (
        <ReviewBulkBar counts={head.warnings} target={words} busy={marks.busy} onAction={strip} />
      )}
      <div className={cx('bnf-scan-body', gridPlans && 'bnf-scan-fill')}>{body}</div>
      {clipTip.tip && (
        <div className="bb-tooltip" style={{ left: `${clipTip.tip.x}px`, top: `${clipTip.tip.y}px` }}>
          <div className="bb-tooltip-line bnf-tip-full">{clipTip.tip.text}</div>
        </div>
      )}
    </div>
  );
}
