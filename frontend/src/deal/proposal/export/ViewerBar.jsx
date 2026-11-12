/*
 * The Export viewer's toolbar (plan.md §8.14; J112; the old ExportViewer and WorkbookViewer toolbars at 891f1b3): the
 * file chips, the view's own controls (`children`), the Draft badge, the status line ("Built 2:05 PM · 13 tabs",
 * "Rebuilding…", "The deal changed since this copy"), ↻ Refresh and the file's download. Each view (the spreadsheet;
 * from slice 30 the deck) fills it.
 */
export default function ViewerBar({ chips, children, draft, status, building, onRefresh, download }) {
  return (
    <div className="bnf-xv-toolbar">
      {chips}
      <span className="bnf-xv-spacer" />
      {children}
      {draft && (
        <span className="bnf-xv-draft" title="Not issued yet, so the download wears the Draft mark too">
          Draft
        </span>
      )}
      <span className="bnf-xv-status" role="status">
        {status}
      </span>
      <button
        type="button"
        className="btn btn-secondary btn-sm"
        onClick={onRefresh}
        aria-busy={building || undefined}
      >
        ↻ Refresh
      </button>
      {download}
    </div>
  );
}
