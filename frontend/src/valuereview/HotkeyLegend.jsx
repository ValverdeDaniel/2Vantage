import { doneText } from './reviewWords';

/*
 * The keys, always on screen in their own line (plan.md §8.16; E55, D124, D125; the old GridReviewToolbar's
 * HotkeyLegend and ReviewDone), and what the last action did with its ↶ Undo (E54). `list` is the List's legend (↑↓
 * move); the Grid's adds ←→, Shift extends and Esc clears. `review` is Review mode (D-201, E65): a click finds the value
 * in the file and E edits, so F is not listed. `edit` is ✎ Edit's, where letters type (E67).
 */

const Key = ({ k }) => <kbd>{k}</kbd>;

function EditLegend() {
  return (
    <span className="gs-legend" aria-label="Keyboard shortcuts">
      <span>Click finds in file</span>
      <span>
        Click again, <Key k="F2" /> or type to edit
      </span>
      <span>
        <Key k="Enter" /> down
      </span>
      <span>
        <Key k="Tab" /> right
      </span>
      <span>
        <Key k="Home" /> <Key k="End" /> row ends
      </span>
      <span>
        <Key k="Del" /> blanks
      </span>
      <span>
        <Key k="Esc" /> cancels
      </span>
    </span>
  );
}

export function HotkeyLegend({ list = false, review = false, edit = false }) {
  if (edit) return <EditLegend />;
  const moves = review ? ' move and find' : ' move';
  return (
    <span className="gs-legend" aria-label="Keyboard shortcuts">
      {review && <span>Click finds in file</span>}
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
      {review ? (
        <span>
          <Key k="E" /> or double-click edits
        </span>
      ) : (
        <span>
          <Key k="F" /> find in file
        </span>
      )}
      <span>
        <Key k="↑↓" />
        {list ? null : <Key k="←→" />}
        {moves}
      </span>
      {!list && <span>Shift extends</span>}
      {!list && (
        <span>
          <Key k="Esc" /> clears
        </span>
      )}
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
