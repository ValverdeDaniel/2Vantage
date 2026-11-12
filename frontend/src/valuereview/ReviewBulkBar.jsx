/*
 * The review strip (plan.md §8.14, §8.16; E48, F65, OQ28; the old ReviewBulkBar): "N AI values to review · M need
 * checking" on what the page names (`target`: "this file", "the 2 ticked plans", "every plan on Medical"), with
 * ✓ Approve, Ignore and ⚑ Needs checking on exactly those open warnings. Nothing waits on it: it is a count with three
 * doors (OQ28). With nothing open it says so in one muted line. `counts` = {open, check, unflagged}. Ignore and Needs
 * checking are off when every open warning is already flagged. Claude's re-check joins in slice 22 (F66); the old
 * walkthrough link is dropped (E49).
 */
export default function ReviewBulkBar({ counts, target, busy = '', onAction }) {
  const { open = 0, check = 0, unflagged = 0 } = counts || {};
  if (!open) {
    return (
      <div className="bnf-review-bar bnf-review-bar-clear" data-review-bar="clear">
        <span className="bnf-review-bar-count">✓ No AI warnings to review</span>
        {target && <span className="bnf-review-bar-target">on {target}</span>}
      </div>
    );
  }
  return (
    <div className="bnf-review-bar" data-review-bar={open}>
      <span className="bnf-review-bar-count">
        <b>{open}</b> AI value{open === 1 ? '' : 's'} to review
        {check > 0 && <span className="bnf-review-bar-check"> · {check} need checking</span>}
      </span>
      {target && <span className="bnf-review-bar-target">on {target}</span>}
      <span className="bnf-review-bar-actions">
        <button
          type="button"
          className="btn btn-primary btn-sm"
          disabled={Boolean(busy)}
          title="The values are right as read: approve them and the warnings clear"
          onClick={() => onAction('approve')}
        >
          {busy === 'approve' ? 'Approving…' : `✓ Approve ${open}`}
        </button>
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          disabled={Boolean(busy) || !unflagged}
          title="Leave the values as read and stop warning about them, on the record (the Change history lists who and when, with Revert)"
          onClick={() => onAction('ignore')}
        >
          {busy === 'ignore' ? 'Ignoring…' : `Ignore ${unflagged || ''}`.trim()}
        </button>
        <button
          type="button"
          className="btn btn-secondary btn-sm bnf-review-btn-check"
          disabled={Boolean(busy) || !unflagged}
          title="Flag them for a second look: they stay counted and the Needs checking filter finds them"
          onClick={() => onAction('check')}
        >
          {busy === 'check' ? 'Flagging…' : `⚑ Needs checking ${unflagged || ''}`.trim()}
        </button>
      </span>
    </div>
  );
}
