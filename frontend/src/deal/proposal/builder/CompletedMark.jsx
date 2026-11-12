import { formatDate } from '../../../lib/format';

/*
 * A card's "Mark completed" control (plan.md §8.14; J18; the old shared/CompletedMark.jsx at 891f1b3): the button, or
 * once marked, who marked it and when, with Undo. `done` is the stamp ({by, at}) or null.
 */
export default function CompletedMark({ done, busy, onToggleDone }) {
  return (
    <span className="bnf-bcard-mark">
      {done ? (
        <>
          <span
            className="bnf-bcard-badge"
            title={`Marked completed${done.by ? ` by ${done.by}` : ''}${done.at ? ` on ${formatDate(done.at)}` : ''}`}
          >
            ✓ Completed
            {done.by ? ` · ${done.by}` : ''}
            {done.at ? `, ${formatDate(done.at)}` : ''}
          </span>
          <button
            type="button"
            className="bnf-override-link"
            title="Take the completed mark off this card"
            disabled={busy}
            onClick={() => onToggleDone(false)}
          >
            Undo
          </button>
        </>
      ) : (
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          title="You reviewed this card and it is what you want: mark it and put it away"
          disabled={busy}
          onClick={() => onToggleDone(true)}
        >
          ✓ Mark completed
        </button>
      )}
    </span>
  );
}
