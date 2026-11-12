import cx from '../../ui/cx';

/*
 * The Scanned data panel's buttons, in the old order (plan.md §8.16; E32, E35, E65, E66; the old DocumentsTab's
 * `bnf-scan-actions`): ☰ List / ▦ Grid (remembered in this browser), ↺ Reset sizes while the Grid has sizes of the
 * person's own, Hide ▾ while expanded, ○ Review / ◉ Review and ✎ Edit. The old ⟲ History rail is gone with versions
 * (E72); the Change history card below the station stands in for it.
 */
export default function ScanActions({ view, onView, resetSizes, onHide, review, onReview, onEdit }) {
  return (
    <div className="bnf-scan-actions">
      {onView && (
        <span className="bnf-scan-viewtoggle" role="group" aria-label="Show this file's values as">
          <button
            type="button"
            className={cx('bnf-docs-expand-btn', view === 'list' && 'is-on')}
            aria-pressed={view === 'list'}
            onClick={() => onView('list')}
            title="This file's values, worst first, beside the file"
          >
            ☰ List
          </button>
          <button
            type="button"
            className={cx('bnf-docs-expand-btn', view === 'grid' && 'is-on')}
            aria-pressed={view === 'grid'}
            onClick={() => onView('grid')}
            title="What was read from this file (or every proposal file), side by side"
          >
            ▦ Grid
          </button>
        </span>
      )}
      {resetSizes && (
        <button
          type="button"
          className="bnf-docs-expand-btn bnf-docs-resetsizes-btn"
          onClick={resetSizes}
          title="Plan columns back to five across and every row back to three lines, here and on the Proposal tab (your sizes, in this browser)"
        >
          ↺ Reset sizes
        </button>
      )}
      {onHide && (
        <button
          type="button"
          className="bnf-docs-hidedata"
          onClick={onHide}
          title="Collapse this panel so the document fills the screen"
        >
          Hide ▾
        </button>
      )}
      {onReview && (
        <button
          type="button"
          className={cx('bnf-docs-expand-btn bnf-docs-review-btn', review && 'is-on')}
          aria-pressed={review}
          onClick={onReview}
          title="Review mode: click a value or move with the arrows and the file finds it. A approves, I ignores; E or a double-click edits."
        >
          {review ? '◉ Review' : '○ Review'}
        </button>
      )}
      {onEdit && (
        <button
          type="button"
          className="bnf-docs-expand-btn"
          onClick={onEdit}
          title="Correct anything the scan got wrong — each value saves as you go, and every change is in the change history"
        >
          ✎ Edit
        </button>
      )}
    </div>
  );
}
