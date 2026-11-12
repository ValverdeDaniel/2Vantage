import { useState } from 'react';
import { formatDate } from '../../../lib/format';
import { REQUEST_CLASSES, agoWords, labelIn } from '../reviewModel';
import PersonRow from './PersonRow';

/*
 * One request: the same ask to one or more people, a personal link each (L8, L55; old 891f1b3 `RequestCard.jsx`):
 * its state, what it asks, who made it and when, the message, a row per person, and Close… with a reason (L70).
 * Props only; every action is `actions` (useLinkActions). `children` render under the foot (the lane's chips).
 */
export default function RequestCard({ request, meta, actions, readOnly = false, children = null }) {
  const [closing, setClosing] = useState(false);
  const reasons = meta?.close_reasons || [];
  const [reason, setReason] = useState(reasons[0]?.key || 'answered_elsewhere');
  const label = labelIn(meta?.request_states, request.state);
  const open = request.state !== 'closed';
  return (
    <div className="rr-request" data-request-id={request.id} role="group" aria-label={`Request: ${request.asks.join(' · ')}`}>
      <div className="rr-request-head">
        <span className={`rr-link-chip ${REQUEST_CLASSES[request.state] || ''}`}>
          {label}
          {request.state === 'closed' && request.close_reason_label ? ` — ${request.close_reason_label.toLowerCase()}` : ''}
        </span>
        <span className="rr-request-asks">
          {request.asks.map((words) => (
            <span key={words} className="bb-chip">
              {words}
            </span>
          ))}
        </span>
        <span className="rr-request-meta" title={formatDate(request.created_at)}>
          {request.created_by ? `by ${request.created_by} · ` : ''}
          {agoWords(request.created_at)}
          {request.answered_by && ` · answered by ${request.answered_by}'s link`}
        </span>
      </div>
      {request.message && <div className="rr-request-message">“{request.message}”</div>}
      <div className="rr-request-people">
        {request.recipients.map((person) => (
          <PersonRow
            key={person.link_id}
            person={person}
            meta={meta}
            actions={actions}
            readOnly={readOnly}
            pin={actions.pins[person.link_id]}
          />
        ))}
      </div>
      <div className="rr-request-foot">
        {!readOnly && open && !closing && (
          <button type="button" className="rr-linklike" disabled={actions.busy} onClick={() => setClosing(true)}
            title="Close this request: pick why, then every link on it stops working">
            Close…
          </button>
        )}
        {closing && (
          <span className="rr-request-close">
            <select value={reason} onChange={(e) => setReason(e.target.value)} aria-label="Why close it">
              {reasons.map((item) => (
                <option key={item.key} value={item.key}>
                  {item.label}
                </option>
              ))}
            </select>
            <button type="button" className="btn btn-secondary btn-sm" disabled={actions.busy}
              title="Close it now, for the reason picked: every link on it stops working"
              onClick={() => {
                actions.close(request, reason);
                setClosing(false);
              }}>
              Close the request
            </button>
            <button type="button" className="rr-linklike" onClick={() => setClosing(false)} title="Leave the request open: nothing changes">
              Keep it open
            </button>
            <span className="rr-request-closenote">Every link on it stops working.</span>
          </span>
        )}
      </div>
      {children}
    </div>
  );
}
