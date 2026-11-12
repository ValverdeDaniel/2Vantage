/*
 * A toast's words with its Undo (plan.md §8.22; F59–F61, E54): Undo reverts the write's Activity row
 * (POST activity/{id}/revert/), which refuses in words when a later write changed the same plans.
 */
export default function UndoNote({ text, onUndo }) {
  return (
    <span>
      {text}
      {onUndo && (
        <>
          {' · '}
          <button type="button" className="bnf-linklike" onClick={onUndo}>
            Undo
          </button>
        </>
      )}
    </span>
  );
}
