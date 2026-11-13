/*
 * The request tray's bar (plan.md §8.8; L49; old 891f1b3 `FollowUpBar.jsx`, the handoff's "Request tray · N · Send to
 * Dana ▸"): what is going to the client — answers sent back, values to check, missing items asked for — waiting for a
 * person to send it. Sticky at the foot of the tab, never fixed over it. It names where the items go (`destination`,
 * trayModel.destinationOf); "Review & send ▸" opens the snippet, whose "Open the request ▸" goes to the page that sends.
 */
export default function TrayBar({ count, destination, nowhere, onOpen }) {
  if (!count) return null;
  const sub =
    nowhere === count
      ? 'No open link can take these yet: Review & send, then choose who to ask'
      : 'Waiting here until you send it, on the link they already have';
  return (
    <div className="rr-followup-bar" role="region" aria-label="Request tray">
      <span className="rr-followup-ico">↩</span>
      <div className="rr-followup-text">
        <b>
          Request tray · {count}
          {destination ? <span className="rr-followup-dest"> · {destination}</span> : ` item${count === 1 ? '' : 's'}`}
        </b>
        <span>{sub}</span>
      </div>
      <button
        type="button"
        className="btn btn-sm btn-violet"
        onClick={onOpen}
        title="See what is in the tray and where it goes; Open the request there to send it"
      >
        Review &amp; send ▸
      </button>
    </div>
  );
}
