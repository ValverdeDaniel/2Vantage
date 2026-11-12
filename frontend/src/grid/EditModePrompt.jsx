/*
 * The edit prompt's dialog (F72; the old shared/EditModePrompt.jsx markup: `progress-overlay` > `bb-modal
 * bnf-edit-prompt`). Props are useEditModePrompt's {open, busy, accept, close}; `sub` is the grid's own sentence.
 */

const GRID_WORDS = 'This grid is read-only until ✎ Edit is on. Every value you change is saved as you type, and the change history keeps the earlier one.';

export default function EditModePrompt({ open, busy, accept, close, sub = GRID_WORDS }) {
  if (!open) return null;
  return (
    <div className="progress-overlay" onClick={close}>
      <div
        className="bb-modal bnf-edit-prompt"
        role="dialog"
        aria-modal="true"
        aria-labelledby="bnf-edit-prompt-title"
        onClick={(event) => event.stopPropagation()}
        onKeyDown={(event) => {
          if (event.key === 'Escape') {
            event.preventDefault();
            event.stopPropagation();
            close();
          }
        }}
      >
        <div className="bb-modal-header">
          <div>
            <div className="bb-modal-title" id="bnf-edit-prompt-title">
              Would you like to enter edit mode?
            </div>
            <div className="bb-modal-sub">{sub}</div>
          </div>
        </div>
        <div className="bb-modal-actions">
          <button type="button" className="btn btn-secondary btn-sm" onClick={close} disabled={busy}>
            Not now
          </button>
          <button type="button" className="btn btn-primary btn-sm" onClick={accept} disabled={busy} autoFocus>
            {busy ? 'Opening…' : 'Enter edit mode'}
          </button>
        </div>
      </div>
    </div>
  );
}
