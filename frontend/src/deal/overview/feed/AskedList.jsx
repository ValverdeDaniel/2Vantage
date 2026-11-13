import { useState } from 'react';
import { formatDate } from '../../../lib/format';

const SHOWN = 4; // links before "Show all N" (old LINKS_COLLAPSED)

// The link chip's look by state: review's own classes (reviewrequest.css), as the request card draws them.
const STATE_CLASSES = {
  answered: 'rr-link-answered',
  off: 'rr-link-expired',
  closed: 'rr-link-covered',
  covered: 'rr-link-covered',
  draft: 'rr-link-draft',
  lapsed_draft: 'rr-link-expired',
  expired: 'rr-link-expired',
  opened: 'rr-link-opened',
  waiting: 'rr-link-waiting',
};

/**
 * "Who we've asked" (M69; old 891f1b3 `ActivityFeed.jsx`): "N back · M waiting · K expired", then each link — the
 * person and their role, what it asks, "shared request" when several people were asked the same thing, the link's
 * state in review's words, and the days left on a link still waiting — four at first, then Show all N (the server
 * sends at most 50); last, "Never asked: …", the client's contacts no link went to. Hidden until a link exists.
 */
export default function AskedList({ outreach }) {
  const [all, setAll] = useState(false);
  const links = outreach.links || [];
  if (!links.length) return null;
  const shown = all ? links : links.slice(0, SHOWN);
  return (
    <div className="bnf-ov-links">
      <div className="bnf-ov-links-head">
        <span>Who we’ve asked</span>
        <span className="bb-drop-meta">
          {outreach.answered} back · {outreach.waiting} waiting
          {outreach.expired ? ` · ${outreach.expired} expired` : ''}
        </span>
      </div>
      {shown.map((link) => (
        <div key={link.link_id} className="bnf-ov-link">
          <span className="bnf-ov-link-who">
            {link.name || 'Private link'}
            {link.role && <span className="bb-drop-meta"> · {link.role}</span>}
          </span>
          <span className="bnf-ov-link-asks" title={link.asks.join(' · ')}>
            {link.asks.join(' · ') || '—'}
          </span>
          <span className="bnf-ov-link-state">
            {link.shared && (
              <span className="bb-chip" title="One of several people asked the same thing">
                shared request
              </span>
            )}
            <span className="rr-link-status">
              <span
                className={`rr-link-chip ${STATE_CLASSES[link.state] || ''}`}
                title={link.sent_at ? `Sent ${formatDate(link.sent_at)}` : undefined}
              >
                {link.state_label}
              </span>
            </span>
            {link.days_left != null && <span className="bb-drop-meta"> {link.days_left}d left</span>}
          </span>
        </div>
      ))}
      {links.length > SHOWN && (
        <button type="button" className="bnf-override-link" onClick={() => setAll(!all)}>
          {all ? 'Show fewer' : `Show all ${outreach.links_total}`}
        </button>
      )}
      {outreach.never_asked.length > 0 && (
        <div className="bb-drop-meta bnf-ov-link-unasked">Never asked: {outreach.never_asked.join(', ')}</div>
      )}
    </div>
  );
}
