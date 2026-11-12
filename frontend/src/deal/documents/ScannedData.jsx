import { useMemo, useRef, useState } from 'react';
import { usePlanSources } from '../../api/planReview';
import { displayValue } from '../../lib/fieldValue';
import cx from '../../ui/cx';
import InlineError from '../../ui/InlineError';
import { useToast } from '../../ui/useToast';
import ReviewBulkBar from '../../valuereview/ReviewBulkBar';
import ReviewList from '../../valuereview/ReviewList';
import useMarks from '../../valuereview/useMarks';
import useReviewHotkeys from '../../valuereview/useReviewHotkeys';
import { checkLabel } from './checkWords';

/*
 * The Scanned data panel beside the file (plan.md §8.16, §10.7; E34, E35, E47, E48, E54–E58, D121, D122, D124; the
 * old DocumentsTab's scan panel): what was read from this file (or every proposal file), as the List, worst first.
 * - The head: "Scanned data · Proposal · all N files" and the quality headline with its high / review / missing chips,
 *   counted by the server over the plans the files gave (E34); Hide while the station is expanded (E32).
 * - The file strip: "N AI values to review · M need checking" with Approve, Ignore and Needs checking on this file's
 *   open warnings (E48). Only values Claude doubted, or the locator could not find, are counted (OQ28), and nothing
 *   waits on them. The old app drew it over the Grid only; with no Grid until slice 23 it sits over the List.
 * - The List (ReviewList) with its bulk bar, "Check this file", the keys and ↶ Undo.
 * The keys A, I, C, U and F act on the List's selected value wherever focus is on the tab (useReviewHotkeys). Plan
 * values only: intake, census and questionnaire files join with their owners' `sources/` (slices 39, 65, 43).
 */
export default function ScannedData({ deal, meta, scope, expanded, activeRef, onOpen, check }) {
  const toast = useToast();
  const [bucket, setBucket] = useState('');
  const [hidden, setHidden] = useState(false);
  const listRef = useRef(null);
  const proposal = scope.bucket === 'proposal';
  const sources = usePlanSources(deal.id, { documentIds: scope.ids, bucket, enabled: proposal });
  const marks = useMarks(deal.id);
  const fields = useMemo(
    () => Object.fromEntries((meta.plans?.fields ?? []).map((field) => [field.key, field])),
    [meta.plans],
  );
  const names = useMemo(() => new Map(scope.files.map((file) => [file.id, file.display_name])), [scope.files]);
  const pages = sources.data?.pages ?? [];
  const head = pages[0] ?? null;
  const rows = pages.flatMap((page) => page.rows);
  const listed = proposal && (head?.all.open || head?.all.done);
  const words = scope.ids.length > 1 ? 'these files' : 'this file';

  useReviewHotkeys({
    enabled: Boolean(listed) && !(expanded && hidden),
    onKey: (action) => {
      if (!listRef.current?.act(action)) toast.info('Select a value first: click it in the list');
    },
  });

  const one = (action, row) => marks.run(action, { refs: [row.ref] }, { where: 'that value' });
  const many = (action, list) =>
    marks.run(action, { refs: list.map((row) => row.ref) }, { where: bucket ? 'the values shown' : words });
  const strip = (action) => marks.run(action, { document_ids: scope.ids }, { where: words });

  let body;
  if (!proposal) {
    body = (
      <div className="bb-subtitle bb-mt">
        {scope.bucket === 'census'
          ? 'No census roster yet — map this file from the Census tab to build the grid.'
          : 'Intake documents aren’t scanned yet — assign and preview them here; any fields traced to this file appear once available.'}
      </div>
    );
  } else if (sources.isPending) {
    body = <div className="bb-subtitle bb-mt">Loading the quoted plans…</div>;
  } else if (sources.isError) {
    body = (
      <InlineError
        compact
        title="Could not load the values."
        error={sources.error}
        onRetry={() => sources.refetch()}
        retrying={sources.isFetching}
      />
    );
  } else if (!listed) {
    body = (
      <div className="bb-subtitle bb-mt">
        Nothing read from {words} is on the grid yet — read it with ✦ Work with Claude, and the plans it finds show here.
      </div>
    );
  } else {
    body = (
      <>
        <ReviewBulkBar counts={head.warnings} target={words} busy={marks.busy} onAction={strip} />
        <ReviewList
          ref={listRef}
          rows={rows}
          head={head}
          buckets={meta.review_buckets ?? []}
          filter={bucket}
          onFilter={setBucket}
          scopeWords={scope.ids.length > 1 ? 'these files' : `“${scope.name}”`}
          valueOf={(row) => displayValue(fields[row.key], row.value)}
          fileOf={(row) => (scope.ids.length > 1 ? names.get(row.doc) || '' : '')}
          activeRef={activeRef}
          onOpen={onOpen}
          onMark={many}
          onMarkOne={one}
          busy={marks.busy}
          done={marks.last}
          onUndo={marks.undo}
          undoing={marks.undoing}
          more={{
            has: Boolean(sources.hasNextPage),
            loading: sources.isFetchingNextPage,
            load: () => sources.fetchNextPage(),
            pageSize: head.page_size,
          }}
          check={check && { busy: check.busy, run: check.check, label: checkLabel(scope.ids.length, false) }}
        />
      </>
    );
  }

  const quality = head?.quality;
  return (
    <div className={cx('bb-panel bnf-scan-panel', expanded && hidden && 'bnf-docs-hidden')} data-scanned-data>
      {expanded && hidden && (
        <button type="button" className="bnf-docs-showdata" onClick={() => setHidden(false)} title="Bring the scanned data back">
          ▴ Scanned data
        </button>
      )}
      <div className="bnf-scan-head">
        <div className="bb-panel-title">
          Scanned data
          {scope.label && <span className="bnf-scan-sub"> · {scope.label}</span>}
          {scope.ids.length > 1 && <span className="bnf-scan-sub"> · all {scope.ids.length} files</span>}
        </div>
        {proposal && head && (
          <div className="bnf-quality">
            <span className={`bnf-quality-label bb-${head.headline.tone}`}>{head.headline.label}</span>
            {(quality.high > 0 || quality.low > 0 || quality.missing > 0) && (
              <span className="bnf-quality-chips">
                {quality.high > 0 && <span className="bb-badge bb-badge-green">{quality.high} high</span>}
                {quality.low > 0 && <span className="bb-badge bb-badge-amber">{quality.low} review</span>}
                {quality.missing > 0 && <span className="bb-badge bb-badge-rose">{quality.missing} missing</span>}
              </span>
            )}
          </div>
        )}
        <div className="bnf-scan-actions">
          {expanded && !hidden && (
            <button
              type="button"
              className="bnf-docs-hidedata"
              onClick={() => setHidden(true)}
              title="Collapse this panel so the document fills the screen"
            >
              Hide ▾
            </button>
          )}
        </div>
      </div>
      <div className="bnf-scan-body">{body}</div>
    </div>
  );
}
