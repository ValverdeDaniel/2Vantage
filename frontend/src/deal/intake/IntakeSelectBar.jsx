/*
 * ☑ Select fields' bar (plan.md §8.9; B10), in the old words and classes (891f1b3 `IntakeTab.jsx`, `bb-select-bar`):
 * the count, "Select all missing" (fixed: the blank questions this deal needs, not every blank), ＋ Ask N, ✓ Approve,
 * Ignore, ⚑ Needs checking and Cancel. Approve, Ignore and Needs checking act on the ticked answers that hold a value;
 * ＋ Ask puts the ticked questions in the request tray (B10, B12; slice 56).
 */
export default function IntakeSelectBar({ count, answered, busy, onAllMissing, onMark, onCancel, onAsk, asking = false }) {
  const off = !answered || Boolean(busy);
  return (
    <div className="bb-select-bar">
      <div>
        Pick the fields to ask the client about
        <span className="bb-select-hint">
          {' '}
          — answers already settled (green, with nothing to review) can&apos;t be asked about.
        </span>
      </div>
      <div className="bb-select-bar-right">
        <div className="bb-select-count">{count} selected</div>
        <button type="button" className="btn btn-secondary btn-sm" onClick={onAllMissing}>
          Select all missing
        </button>
        <button
          type="button"
          className="btn btn-violet btn-sm"
          disabled={!count || asking || !onAsk}
          title="Put the ticked questions in the request tray: they go with everything else you ask for, on one link"
          onClick={onAsk}
        >
          ＋ Ask {count || ''}
        </button>
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          disabled={off}
          title="The ticked answers are right: approve them"
          onClick={() => onMark('approve')}
        >
          ✓ Approve
        </button>
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          disabled={off}
          title="Leave the ticked answers as read and stop warning about them"
          onClick={() => onMark('ignore')}
        >
          Ignore
        </button>
        <button
          type="button"
          className="btn btn-secondary btn-sm bnf-review-btn-check"
          disabled={off}
          title="Flag the ticked answers for a second look"
          onClick={() => onMark('check')}
        >
          ⚑ Needs checking
        </button>
        <button type="button" className="btn btn-secondary btn-sm" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </div>
  );
}
