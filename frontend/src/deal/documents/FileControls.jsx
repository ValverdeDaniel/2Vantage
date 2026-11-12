/*
 * The buttons under the file row (`bnf-doc-controls`; plan.md §8.16; E10, E15, E32): ✎ File, Remove (refused for a
 * protected file, O.3.7) and ⛶ Expand / ✕ Collapse (Esc collapses). A removed file shows only Expand: it comes back
 * through "Show removed files".
 */
export default function FileControls({ file, editing, expanded, onEdit, onRemove, onExpand }) {
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
      <button
        type="button"
        className="bnf-docs-expand-btn"
        onClick={onExpand}
        title={expanded ? 'Back to the normal layout (Esc)' : 'Expand the document to the whole screen'}
      >
        {expanded ? '✕ Collapse' : '⛶ Expand'}
      </button>
    </div>
  );
}
