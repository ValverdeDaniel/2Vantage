/*
 * The Re-read panel under the file's buttons (plan.md §8.16; E75; the old DocumentsTab's `bnf-reread-panel`): tick the
 * files Claude should read again, then "Re-read N files". The read waits here for review ("Review this scan" below
 * the file): nothing on the deal changes until a person uses it. `reread` is useReread's state.
 */
export default function RereadPanel({ reread }) {
  const count = reread.picked.size;
  return (
    <div className="bnf-reread-panel" data-reread-panel>
      <div className="bnf-reread-note">
        Claude reads the ticked files again and holds the new read for you to compare — nothing on the deal changes
        until you use it. A read past its cost cap waits before anything is sent.
      </div>
      {reread.offered.map((file) => (
        <label key={file.id}>
          <input type="checkbox" checked={reread.picked.has(file.id)} onChange={() => reread.toggle(file.id)} />
          {file.display_name || file.original_name}
        </label>
      ))}
      <div className="bnf-reread-actions">
        <button
          type="button"
          className="btn btn-sm btn-primary"
          disabled={!count || reread.busy}
          onClick={reread.read}
        >
          Re-read {count} file{count === 1 ? '' : 's'}
        </button>
        <button type="button" className="btn btn-sm btn-secondary" onClick={reread.close}>
          Cancel
        </button>
      </div>
    </div>
  );
}
