/*
 * The selected cell's drop-down, read-only (plan.md §8.14; J116; the old WorkbookGrid overlay at 891f1b3): Excel's
 * prompt under the cell, and on ▾ the list it offers, the cell's own pick marked. Picking changes nothing: the file
 * opens with the pick it was built with (Daniel's 2026-11-05 "as exported").
 */
export default function DropdownPop({ drop, value, open, x, y, minWidth }) {
  if (!open && !drop.prompt) return null;
  return (
    <div className="xg-pop" style={{ left: x, top: y + 2, minWidth }}>
      {open ? (
        <div className="xg-list" role="listbox" aria-label="The list in this drop-down">
          <div className="xg-list-note">Picking here changes nothing: the file opens with the pick shown.</div>
          {drop.list.map((item, n) => (
            <div key={n} className={`xg-list-item ${item === value ? 'xg-list-on' : ''}`}>
              {item}
            </div>
          ))}
        </div>
      ) : (
        <div className="xg-prompt" role="note">
          {drop.title && <b>{drop.title}</b>}
          <div>{drop.prompt}</div>
        </div>
      )}
    </div>
  );
}
