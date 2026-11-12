import { doneText } from './reviewWords';

/*
 * The keys, always on screen in their own line (plan.md §8.16; E55, D124; the old GridReviewToolbar's HotkeyLegend
 * and ReviewDone), and what the last action did with its ↶ Undo (E54). `list` is the List's legend (↑↓ move); the
 * Grid's (←→, Shift extends, Esc clears) comes with it in slice 23.
 */

const Key = ({ k }) => <kbd>{k}</kbd>;

export function HotkeyLegend({ list = true }) {
  return (
    <span className="gs-legend" aria-label="Keyboard shortcuts">
      <span>
        <Key k="A" /> approve
      </span>
      <span>
        <Key k="I" /> ignore
      </span>
      <span>
        <Key k="C" /> needs checking
      </span>
      <span>
        <Key k="U" /> clear mark
      </span>
      <span>
        <Key k="F" /> find in file
      </span>
      <span>
        <Key k="↑↓" />
        {list ? null : <Key k="←→" />} move
      </span>
    </span>
  );
}

/** "✓ 3 values approved ↶ Undo" until Undo or the next action; nothing before. */
export function ReviewDone({ done, onUndo, undoing = false }) {
  const text = doneText(done);
  if (!text) return null;
  return (
    <span className="gs-done" role="status">
      {text}
      {onUndo && done.activityId && (
        <button
          type="button"
          className="bnf-linklike gs-undo"
          disabled={undoing}
          onClick={() => onUndo(done)}
          title="Put those values back exactly as they were before"
        >
          {undoing ? 'Undoing…' : '↶ Undo'}
        </button>
      )}
    </span>
  );
}
