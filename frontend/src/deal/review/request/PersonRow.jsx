import { formatDate } from '../../../lib/format';
import { LINK_CLASSES, labelIn, linkDetail } from '../reviewModel';
import PinOnce from './PinOnce';

/*
 * One person on a request (L8; old 891f1b3 `RequestCard.jsx` people rows and `LinkStatus.jsx`): their name and role,
 * the link's state in one vocabulary (said of the link, never of a person: anyone holding the URL counts), and what
 * can be done to it: Copy link (copying is the send), Mark sent / Not sent after all, Extend, Turn off / Turn back on
 * (the old link settings card's switch), New PIN and View as client (L78, slice 54: their page, read-only, in a new
 * tab). Copy message and Nudge arrive with the message drafts (slices 56–57).
 */
export default function PersonRow({ person, meta, actions, readOnly, pin }) {
  const { state } = person;
  const label = labelIn(meta?.link_states, state);
  const name = person.name || 'Private link';
  const busy = actions.busy;
  const live = !['off', 'closed', 'answered'].includes(state);
  return (
    <div className="rr-request-person" data-link-id={person.link_id} role="group" aria-label={`${name}’s link`}>
      <div className="rr-request-personhead">
        <span className="rr-recipient-name">{name}</span>
        {person.role && <span className="rr-recipient-role">{person.role}</span>}
        {person.security === 'pin' && <span className="rr-recipient-role">PIN required</span>}
        <span className="rr-link-status">
          <span className={`rr-link-chip ${LINK_CLASSES[state] || ''}`} title={person.sent_at ? `Sent ${formatDate(person.sent_at)}` : undefined}>
            {label}
          </span>
          <span className="rr-link-detail">{linkDetail(person)}</span>
        </span>
      </div>
      {!readOnly && (
        <div className="rr-request-actions">
          {person.path && live && (
            <button type="button" className="btn btn-secondary btn-sm" disabled={busy} onClick={() => actions.copyLink(person)}
              title="Copy their personal link to paste anywhere: copying it counts as sending it">
              Copy link
            </button>
          )}
          {state !== 'closed' && (
            <a className="rr-linklike" href={`/preview/links/${person.link_id}`} target="_blank" rel="noreferrer"
              title="Their page as they see it, read-only: nothing is saved and no open is counted (L78)">
              View as client
            </a>
          )}
          {state === 'draft' && (
            <button type="button" className="rr-linklike" disabled={busy} onClick={() => actions.markSent(person)}
              title="You sent it another way: mark their link as sent">
              Mark sent
            </button>
          )}
          {person.sent && !person.opened && !person.submitted_at && !person.expired && live && (
            <button type="button" className="rr-linklike" disabled={busy} onClick={() => actions.markSent(person, true)}
              title="Put it back to a draft — it was never actually sent">
              Not sent after all
            </button>
          )}
          {person.can_extend && !person.submitted_at && (
            <button type="button" className="rr-linklike" disabled={busy} onClick={() => actions.extend(person)}
              title="The link lives its own life again from today, never past 30 days from when it was made">
              Extend
            </button>
          )}
          {person.security === 'pin' && live && (
            <button type="button" className="rr-linklike" disabled={busy} onClick={() => actions.newPin(person)}
              title="A new 6-digit PIN, shown to you once: the old one stops working, and a locked link opens again">
              New PIN
            </button>
          )}
          {!person.revoked && state !== 'closed' && (
            <button type="button" className="rr-linklike" disabled={busy} onClick={() => actions.revoke(person)}
              title="Off: the link stops opening now. What they told us stays, and what it asked reads missing until it is back on.">
              Turn off
            </button>
          )}
          {person.can_restore && (
            <button type="button" className="rr-linklike" disabled={busy} onClick={() => actions.restore(person)}
              title="On: the same link opens again, with its own life from now">
              Turn back on
            </button>
          )}
        </div>
      )}
      <PinOnce pin={pin} name={person.name} />
    </div>
  );
}
