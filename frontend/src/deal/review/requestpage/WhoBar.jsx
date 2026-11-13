import cx from '../../../ui/cx';

/*
 * The request page's who bar (plan.md §8.8; L26, L38, L39; old 891f1b3 `FollowUpCart.jsx` the who tabs,
 * `RequestPeople.jsx`): All people (the tray, every link), then every link on a request still open that can still be
 * used — who has it, how often it was opened, the days left, Copy link (copying is the send, OQ82), View ▸ (their page,
 * read-only) and Edit (its settings card). A click on a person puts the Ask card on their link (L42); a • marks changes
 * waiting for Update link there. Then "A new link…" and "People & links (N) ▸", every link ever made.
 */
export default function WhoBar({ people, picked, waiting, actions, readOnly, total, onPick, onEdit, onNewLink, onPeople }) {
  return (
    <div className="rr-reqhead">
      <div className="rr-who" aria-label="Who has a link">
        <span className="rr-who-h">Who</span>
        <button type="button" className={cx('rr-who-all', !picked && 'rr-who-on')} aria-pressed={!picked} onClick={() => onPick(null)}
          title="Every link: a tick waits in the request tray, and goes on whichever link suits">
          <b>All people</b>
          {people.length > 0 && <span className="rr-who-meta"> {people.length}</span>}
        </button>
        {people.map((person) => {
          const on = picked === person.link_id;
          return (
            <div key={person.link_id} className={cx('rr-who-person', on && 'rr-who-on')}>
              <button type="button" className="rr-who-pick" aria-pressed={on} onClick={() => onPick(person)}
                title="Their link: what it asks, ticked here, and their form in the middle">
                {waiting?.[person.request_id] && <span className="rr-who-waiting" title="Changes wait for Update link" />}
                <b>{person.name || 'Private link'}</b>
                <span className="rr-who-meta">
                  {' '}
                  {person.revoked ? 'off' : person.expired ? 'ran out' : `${person.days_left}d left`}
                  {` · opened ${person.opens}×`}
                  {person.submitted_at ? ' · sent back' : ''}
                </span>
              </button>
              <button type="button" className="rr-who-copy" disabled={readOnly || person.revoked || actions.busy}
                title="Copy their personal link to paste anywhere: copying it counts as sending it"
                onClick={() => actions.copyLink({ ...person, sent: person.sent })}>
                Copy link
              </button>
              <a className="rr-who-view" href={`/preview/links/${person.link_id}`} target="_blank" rel="noreferrer" title="Their page, read-only">
                View ▸
              </a>
              <span className="rr-who-access">{person.security === 'pin' ? 'PIN' : 'Private link'}</span>
              <button type="button" className="rr-who-view" onClick={() => onEdit(person)} title="Its settings: who can open it, what they see, when it runs out">
                Edit
              </button>
            </div>
          );
        })}
        {!people.length && <span className="rr-dest-tabs-none">No open link on this deal yet.</span>}
        {!readOnly && (
          <button type="button" className="rr-who-new" onClick={onNewLink} title="A new link: pick who gets it and what it asks">
            A new link…
          </button>
        )}
        <button type="button" className="bnf-override-link rr-who-peoplelink" onClick={onPeople} title="Every link ever made on this deal, with Edit">
          People &amp; links ({total}) ▸
        </button>
      </div>
    </div>
  );
}
