/*
 * The ticked rows and what to do with them (plan.md §8.14; F53, F57–F61; the old `bnf-advisor-selectbar`): ★ Star
 * and ☆ Unstar in any mode; in ✎ Edit also Move to another line (this deal's lines first), Mark current, Remove
 * current and Delete. Each action takes only the ticked plans it applies to; its toast offers Undo.
 */
export default function SelectBar({ count, todo, editing, busy, moveTo, onMoveTo, lines, otherLines, actions, onDelete, onClear }) {
  if (!count) return null;
  return (
    <div className="bnf-advisor-selectbar">
      <span className="bnf-advisor-selectbar-count">{count} selected</span>
      <button
        type="button"
        className="btn btn-primary btn-sm"
        disabled={!todo.toStar.length || busy.star}
        title="Star the ticked plans: they go on this line's client proposal (it holds 16 with the current plans)"
        onClick={() => actions.star(todo.toStar, true)}
      >
        ★ Star{todo.toStar.length ? ` ${todo.toStar.length}` : ''}
      </button>
      <button
        type="button"
        className="btn btn-secondary btn-sm"
        disabled={!todo.toUnstar.length || busy.star}
        title="Take the star off the ticked plans"
        onClick={() => actions.star(todo.toUnstar, false)}
      >
        ☆ Unstar{todo.toUnstar.length ? ` ${todo.toUnstar.length}` : ''}
      </button>
      {editing && (
        <>
          <label className="bnf-advisor-selectbar-line">
            Move to
            <select className="filter-select" value={moveTo} onChange={(event) => onMoveTo(event.target.value)}>
              <option value="">Pick a line…</option>
              {lines.length > 0 && (
                <optgroup label="On this deal">
                  {lines.map((row) => (
                    <option key={row.key} value={row.key}>
                      {row.label}
                    </option>
                  ))}
                </optgroup>
              )}
              <optgroup label="Other lines">
                {otherLines.map((row) => (
                  <option key={row.key} value={row.key}>
                    {row.label}
                  </option>
                ))}
              </optgroup>
            </select>
          </label>
          <button
            type="button"
            className="btn btn-primary btn-sm"
            disabled={!moveTo || busy.moveLine || !todo.toMove.length}
            title="Move the ticked plans to this line of business; their stars clear, so star them again there"
            onClick={() => actions.moveLine(todo.toMove, moveTo)}
          >
            {busy.moveLine ? 'Moving…' : `Move ${todo.toMove.length} plan${todo.toMove.length === 1 ? '' : 's'} ▸`}
          </button>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            disabled={!todo.toMark.length || busy.role}
            title="Mark the ticked plans as in force today, after any current plans this line already has; their stars clear"
            onClick={() => actions.setRole(todo.toMark, 'current')}
          >
            Mark current{todo.toMark.length ? ` (${todo.toMark.length})` : ''}
          </button>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            disabled={!todo.toUnset.length || busy.role}
            title="The ticked current plans stop being current; they stay on the board as quotes"
            onClick={() => actions.setRole(todo.toUnset, 'alternate')}
          >
            Remove current{todo.toUnset.length ? ` (${todo.toUnset.length})` : ''}
          </button>
          <button
            type="button"
            className="btn btn-danger btn-sm"
            disabled={busy.remove}
            title="Delete the ticked plans from the deal; sold plans stay. Undo brings them back."
            onClick={() => onDelete(todo.toRemove)}
          >
            {busy.remove ? 'Removing…' : `Delete ${todo.toRemove.length}`}
          </button>
        </>
      )}
      <button type="button" className="btn btn-secondary btn-sm" onClick={onClear}>
        Clear
      </button>
    </div>
  );
}
