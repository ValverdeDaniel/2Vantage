import { useNavigate, useParams } from 'react-router';

/*
 * ↗: open a value in its file (plan.md §8.16; E18, D-122). A small pin that shows on the cell's hover (the cell wears
 * `bnf-has-src`); the cell's own click stays the grid's. It opens Documents on the value's file with `ref` naming the
 * value ("plan:41:rate_ee"), never the value itself; the station asks the value's owner for its page or cell.
 * Shared (src/viewer/): mounted by other tabs (the Advisor today; Intake and Census with their slices) without loading
 * the station or pdf.js.
 */
export default function SourcePin({ docId, valueRef, fileName = '' }) {
  const navigate = useNavigate();
  const { dealId } = useParams();
  if (!docId || !dealId) return null;
  return (
    <button
      type="button"
      className="bnf-src-pin"
      title={`Open ${fileName || 'the document'} where this was read`}
      aria-label="View in document"
      onClick={(event) => {
        event.stopPropagation();
        const query = new URLSearchParams({ doc: String(docId), ref: valueRef });
        navigate(`/deals/${dealId}/documents?${query}`);
      }}
    >
      ↗
    </button>
  );
}
