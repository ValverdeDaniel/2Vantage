import { useRef, useState } from 'react';
import { useNavigate } from 'react-router';
import useClipTip from '../../../grid/useClipTip';
import useGridSizes from '../../../grid/useGridSizes';
import { REVIEW_KEYS } from '../../../valuereview/keys';
import useReviewHotkeys from '../../../valuereview/useReviewHotkeys';
import InlineError from '../../../ui/InlineError';
import ScanActions from '../ScanActions';
import AsQuotedHead from './AsQuotedHead';
import StationGrid from './StationGrid';
import useAsQuotedGrid from './useAsQuotedGrid';

const NO_FIND = { terms: [], only: false };
const NO_VIEWER = { docId: null, ref: null, page: null };

/*
 * The Advisor's "As quoted" table (plan.md §8.14; F42; slice 21): one scanned quote as the carrier printed it, on the
 * station's Grid (useAsQuotedGrid, StationGrid), so it reads, picks, marks and edits as Documents' "As in the file"
 * does: the plans in the file's column order, the rows in printed order, mapped rows live and editable (✎ Edit, each
 * value through the plan PATCH with `expect`), the rows that fill no field greyed with their printed text. F or a
 * double-click opens a value in its file on Documents. `choices` and `onPick` are the chips (one per scanned file).
 */
export default function AsQuotedBoard({ deal, meta, documentId, line, choices, current, onPick }) {
  const navigate = useNavigate();
  const gridRef = useRef(null);
  const scrollRef = useRef(null);
  const [editing, setEditing] = useState(false);
  const [planFilter, setPlanFilter] = useState('all');
  const [rowsOnly, setRowsOnly] = useState(false);
  const grid = useAsQuotedGrid({
    dealId: deal.id,
    plansMeta: meta.plans,
    documentId,
    line,
    enabled: true,
    ...NO_FIND,
    filters: { errorsOnly: planFilter === 'errors', rowsOnly },
  });
  const sizes = useGridSizes({ grid: 'proposal', scrollRef });
  const clipTip = useClipTip();
  useReviewHotkeys({ enabled: !editing, keys: REVIEW_KEYS, onKey: (action) => gridRef.current?.act(action) });

  const show = (docId, ref) => {
    const query = new URLSearchParams({ doc: String(docId), ...(ref ? { ref } : {}) });
    navigate(`/deals/${deal.id}/documents?${query}`);
  };
  const issues = grid.model.issues.size;
  let body;
  if (grid.data.error) {
    body = <InlineError compact title="Could not load the quote." error={grid.data.error} onRetry={grid.data.refetch} />;
  } else if (grid.data.pending || !grid.table) {
    body = <div className="bb-subtitle bb-mt">Loading the quote as printed…</div>;
  } else if (!grid.model.plans.length) {
    body = <div className="bb-subtitle bb-mt">None of this quote’s plans is on the deal now.</div>;
  } else {
    body = (
      <StationGrid
        ref={gridRef}
        deal={deal}
        grid={grid}
        filter={{
          mode: planFilter === 'errors' && issues ? 'errors' : 'all',
          plans: grid.model.plans.length,
          errorPlans: issues,
          rowsOnly: rowsOnly && issues > 0,
          onMode: setPlanFilter,
          onRowsOnly: setRowsOnly,
        }}
        modes={{ review: false, editing }}
        find={{ current: null, nonce: 0 }}
        scrollRef={scrollRef}
        sizes={sizes}
        clipTip={clipTip}
        onShow={show}
        viewer={NO_VIEWER}
        ask={null}
        onEditDone={() => setEditing(false)}
      />
    );
  }
  return (
    <div className="bb-panel bnf-scan-panel" data-as-quoted-board>
      <div className="bnf-scan-head">
        <div className="bb-panel-title">
          As quoted
          {grid.table && <span className="bnf-scan-sub"> · {grid.table.label}</span>}
        </div>
        <ScanActions onEdit={grid.model.plans.length && !editing ? () => setEditing(true) : null} />
      </div>
      <AsQuotedHead table={grid.table} choices={choices} current={current} onPick={onPick} />
      {body}
      {clipTip.tip && (
        <div className="bb-tooltip" style={{ left: `${clipTip.tip.x}px`, top: `${clipTip.tip.y}px` }}>
          <div className="bb-tooltip-line bnf-tip-full">{clipTip.tip.text}</div>
        </div>
      )}
    </div>
  );
}
