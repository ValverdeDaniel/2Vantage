/*
 * The buttons under the file row (`bnf-doc-controls`; plan.md §8.16; E10, E15, E32, E69, E75): ✎ File, Remove (refused
 * for a protected file, O.3.7), ↻ Re-read… (with Claude, on a file the quote reader reads; slice 19), ⛶ Expand /
 * ✕ Collapse (Esc collapses) and ⧉ New window (slice 65), both hidden while the
 * file is out in its own window. A removed file shows only Expand: it comes back
 * through "Show removed files". "Check this file" (E59) sits in the Scanned data List's bulk bar, as in the old app
 * (slice 17); its progress strip stays under these buttons.
 */
export default function FileControls({ file, editing, expanded, popped, reread, onEdit, onRemove, onExpand, onPopOut }) {
  const removed = Boolean(file.archived_at);
  return (
    <div className="bnf-doc-controls">
      {!removed && (
        <button
          type="button"
          className="bnf-doc-edit"
          disabled={editing}
          onClick={onEdit}
          title="Rename this file or change what kind of document it is"
        >
          ✎ File
        </button>
      )}
      {!removed && (
        <button
          type="button"
          className="bnf-doc-remove"
          disabled={editing || file.protected}
          title={file.protected ? 'An issued proposal or a signed form is kept.' : undefined}
          onClick={onRemove}
        >
          Remove
        </button>
      )}
      {!removed && reread?.available && (
        <button
          type="button"
          className="bnf-doc-edit"
          disabled={editing}
          aria-expanded={reread.open}
          onClick={reread.toggleOpen}
          title="Have Claude read chosen quote files again, held for you to review before anything changes"
        >
          ↻ Re-read…
        </button>
      )}
      {!popped && (
        <button
          type="button"
          className="bnf-docs-expand-btn"
          onClick={onExpand}
          title={expanded ? 'Back to the normal layout (Esc)' : 'Expand the document to the whole screen'}
        >
          {expanded ? '✕ Collapse' : '⛶ Expand'}
        </button>
      )}
      {!popped && (
        <button
          type="button"
          className="bnf-docs-expand-btn bnf-docs-popout-btn"
          onClick={onPopOut}
          title="Open this file in its own window — put it on another screen and keep the scanned data here"
        >
          ⧉ New window
        </button>
      )}
    </div>
  );
}
