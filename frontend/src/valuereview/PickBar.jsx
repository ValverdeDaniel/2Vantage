/*
 * What the picked cells are and what to do with them (plan.md §8.16; E52, D123, D125, D126; the old GridReviewToolbar's
 * pick bar): "N selected · M potential errors", then ✓ Approve, Ignore, ⚑ Needs checking — each naming its key and its
 * count, acting at once (a key above 25 values asks first; the buttons never do) — ↗ Find in file (not in Review mode,
 * where the file follows the cell), "Only potential errors (M)" and ✕. Always drawn while the grid shows, so picking a
 * cell never moves the grid under the pointer. `pick` = {picked, count, errors, busy, review, onAction, onFind,
 * onNarrow, onClear}: `picked` counts every picked cell, `count` those holding a value (a blank takes no mark).
 */

const Key = ({ k }) => <kbd>{k}</kbd>;

function what(pick) {
  const n = pick.count;
  if (n) {
    const errors = pick.errors > 0 ? ` · ${pick.errors} potential error${pick.errors === 1 ? '' : 's'}` : '';
    return (
      <>
        <b>{n}</b> selected{errors}
      </>
    );
  }
  if (pick.picked > 1) return 'Blank cells: nothing to review';
  return pick.review
    ? 'Click a value or use the arrows: the file finds it'
    : 'Click a value to select it; drag, Shift+click or Ctrl+click for more';
}

export default function PickBar({ pick }) {
  const n = pick.count;
  const busy = Boolean(pick.busy);
  return (
    <div className="gs-pick">
      <span className="gs-pick-what">{what(pick)}</span>
      <button
        type="button"
        className="btn btn-sm btn-secondary"
        disabled={busy || !n}
        onClick={() => pick.onAction('approve')}
        title="The selected values are right as read: approve them (A)"
      >
        {pick.busy === 'approve' ? (
          'Approving…'
        ) : (
          <>
            ✓ Approve{n ? ` ${n}` : ''} <Key k="A" />
          </>
        )}
      </button>
      <button
        type="button"
        className="btn btn-sm btn-secondary"
        disabled={busy || !n}
        onClick={() => pick.onAction('ignore')}
        title="Leave the selected values as read and stop warning about them, listed on Overview (I)"
      >
        {pick.busy === 'ignore' ? (
          'Saving…'
        ) : (
          <>
            Ignore <Key k="I" />
          </>
        )}
      </button>
      <button
        type="button"
        className="btn btn-sm btn-secondary"
        disabled={busy || !n}
        onClick={() => pick.onAction('check')}
        title="Flag the selected values for a second look (C)"
      >
        {pick.busy === 'check' ? (
          'Saving…'
        ) : (
          <>
            ⚑ Needs checking <Key k="C" />
          </>
        )}
      </button>
      {!pick.review && (
        <button
          type="button"
          className="btn btn-sm btn-secondary"
          disabled={!n}
          onClick={pick.onFind}
          title="Show the selected value where it was read in the file (F, or double-click it)"
        >
          ↗ Find in file <Key k="F" />
        </button>
      )}
      {pick.errors > 0 && pick.errors < n && (
        <button
          type="button"
          className="btn btn-sm btn-secondary"
          disabled={busy}
          onClick={pick.onNarrow}
          title="Keep only the selected values that are potential errors"
        >
          Only potential errors ({pick.errors})
        </button>
      )}
      {pick.picked > 0 && (
        <button
          type="button"
          className="btn btn-sm btn-secondary gs-pick-clear"
          onClick={pick.onClear}
          aria-label="Clear the selection"
          title="Clear the selection (Esc)"
        >
          ✕
        </button>
      )}
    </div>
  );
}
