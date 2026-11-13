import { formatAgo, formatDate } from '../../../lib/format';

function Moment({ at, empty }) {
  if (!at) return <span className="bb-empty">{empty}</span>;
  return (
    <>
      {formatAgo(at)}
      <span className="bb-drop-meta"> · {formatDate(at)}</span>
    </>
  );
}

/**
 * The outreach strip (M68; old 891f1b3 `ActivityFeed.jsx`): when we last reached out (the Last contact tile's rule,
 * M37), when anything last came back, and the asks still out — counted per request, run-out ones included — with how
 * long the oldest has waited.
 */
export default function OutreachStrip({ outreach }) {
  const open = outreach.open;
  return (
    <div className="bnf-ov-outreach">
      <div className="bnf-ov-outreach-cell">
        <div className="bnf-ov-outreach-label">Last contact</div>
        <div className="bnf-ov-outreach-value">
          <Moment at={outreach.last_contact_at} empty="Never reached out" />
        </div>
      </div>
      <div className="bnf-ov-outreach-cell">
        <div className="bnf-ov-outreach-label">Last response</div>
        <div className="bnf-ov-outreach-value">
          <Moment at={outreach.last_response_at} empty="Nothing back yet" />
        </div>
      </div>
      <div className="bnf-ov-outreach-cell">
        <div className="bnf-ov-outreach-label">Open asks</div>
        <div className="bnf-ov-outreach-value">
          {open > 0 ? (
            <span className="bb-amber">
              {open} ask{open === 1 ? '' : 's'} unanswered
              {outreach.oldest_days != null && <span className="bb-drop-meta"> · oldest {outreach.oldest_days}d</span>}
            </span>
          ) : (
            <span className="bb-green">None outstanding</span>
          )}
        </div>
      </div>
    </div>
  );
}
