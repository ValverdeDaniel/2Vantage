/*
 * The request page's who bar (plan.md §8.8; L26; old 891f1b3 `FollowUpCart.jsx` the who tabs): every link on a request
 * still open that can still be used, each with who has it, how often it was opened and the days left, Copy link
 * (copying is the send, OQ82) and View ▸ (their page, read-only); then "A new link…". Picking a person is slice 57's
 * (the Ask card); here the chips only say who is out and give their links.
 */
export default function WhoBar({ people, actions, readOnly, onNewLink }) {
  return (
    <div className="rr-reqhead">
      <div className="rr-who" aria-label="Who has a link">
        <span className="rr-who-h">Who</span>
        <span className="rr-who-all rr-who-on">
          <b>All people</b>
          {people.length > 0 && <span className="rr-who-meta"> {people.length}</span>}
        </span>
        {people.map((person) => (
          <div key={person.link_id} className="rr-who-person">
            <span className="rr-who-pick">
              <b>{person.name || 'Private link'}</b>
              <span className="rr-who-meta">
                {' '}
                {person.revoked ? 'off' : person.expired ? 'ran out' : `${person.days_left}d left`}
                {` · opened ${person.opens}×`}
                {person.submitted_at ? ' · sent back' : ''}
              </span>
            </span>
            <button
              type="button"
              className="rr-who-copy"
              disabled={readOnly || person.revoked || actions.busy}
              title="Copy their personal link to paste anywhere: copying it counts as sending it"
              onClick={() => actions.copyLink({ ...person, sent: person.sent })}
            >
              Copy link
            </button>
            <a className="rr-who-view" href={`/preview/links/${person.link_id}`} target="_blank" rel="noreferrer" title="Their page, read-only">
              View ▸
            </a>
          </div>
        ))}
        {!people.length && <span className="rr-dest-tabs-none">No open link on this deal yet.</span>}
        {!readOnly && (
          <button type="button" className="rr-who-new" onClick={onNewLink} title="A new link: pick who gets it and what it asks">
            A new link…
          </button>
        )}
      </div>
    </div>
  );
}
