import { useEffect } from 'react';
import { bySection } from './trayModel';

// A long section (a census column asked for 40 people) lists this many.
const ROWS_SHOWN = 5;

/*
 * The tray bar's pop-up (plan.md §8.8; L50; old 891f1b3 `FollowUpSnippet.jsx`): what is queued, by section, each with ×
 * to take it out, and "Open the request ▸" to the request page, where the tray is sent. A snippet, never the send.
 * Escape or × closes it; what is in it stays.
 */
export default function TraySnippet({ items, sections, destination, busy, onRemove, onOpenRequest, onClose }) {
  useEffect(() => {
    const onKey = (event) => {
      if (event.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);
  const groups = bySection(items, sections);
  return (
    <div className="rr-snippet" role="dialog" aria-label="The request tray">
      <div className="rr-snippet-head">
        <span className="rr-followup-ico" aria-hidden="true">
          ↩
        </span>
        <div className="rr-followup-text">
          <b>Request tray · {items.length}</b>
          <span>{destination || 'Nothing reaches the client until you send it from the request page'}</span>
        </div>
        <button type="button" className="rr-snippet-close" aria-label="Close" onClick={onClose} title="Close the tray: what is in it stays there">
          ×
        </button>
      </div>
      <div className="rr-snippet-list">
        {groups.map((group) => (
          <div key={group.key} className="rr-snippet-group">
            <div className="rr-sheet-group-h">
              {group.label} · {group.list.length}
            </div>
            {group.list.slice(0, ROWS_SHOWN).map((item) => (
              <div key={item.id} className="rr-snippet-item">
                <span
                  className={item.gone || item.why ? 'rr-snippet-warn' : undefined}
                  title={item.gone ? 'No longer on the deal: it will be dropped' : item.why || undefined}
                >
                  {item.title}
                </span>
                <button
                  type="button"
                  className="rr-sheet-x"
                  disabled={busy}
                  aria-label={`Take ${item.title} out of the tray`}
                  title="Take it out of the tray"
                  onClick={() => onRemove(item)}
                >
                  ×
                </button>
              </div>
            ))}
            {group.list.length > ROWS_SHOWN && (
              <div className="rr-snippet-more">and {group.list.length - ROWS_SHOWN} more on the request page</div>
            )}
          </div>
        ))}
        {!items.length && <div className="rr-snippet-more">Nothing is waiting. Add what’s missing on the request page.</div>}
      </div>
      <div className="rr-snippet-foot">
        <button
          type="button"
          className="btn btn-sm btn-violet"
          onClick={onOpenRequest}
          title="The request page: the tray the way the client will get it, and Send"
        >
          Open the request ▸
        </button>
      </div>
    </div>
  );
}
