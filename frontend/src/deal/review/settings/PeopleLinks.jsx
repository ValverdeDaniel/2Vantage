import { labelIn, monthDay } from '../reviewModel';
import { linkStatus, peopleOf } from './settingsModel';

/*
 * People & links (plan.md §8.8; L38; old 891f1b3 `RequestPeople.jsx`): a drawer over the request page with every link
 * ever made on the deal, the open ones first, then the ones that ended; each says how it stands and offers Edit, which
 * closes the drawer and opens that link's settings card on the page, and, while it opens, Copy link and View ▸. Nothing
 * is emailed from here (OQ82).
 */
function PersonRow({ person, meta, actions, onEdit }) {
  const status = linkStatus(person);
  const live = status === 'active';
  const level = (meta?.levels || []).find((item) => item.key === person.security);
  return (
    <div className={`rr-person${live ? '' : ' rr-person-ended'}`}>
      <div className="rr-person-head">
        <b>{person.name || 'Private link'}</b>
        {!live && <span className="rr-person-status">{labelIn(meta?.link_states, person.state)}</span>}
        <span className="rr-person-access" title={level?.means}>
          {level?.label}
        </span>
      </div>
      {person.email && <div className="rr-person-line">{person.email}</div>}
      <div className="rr-person-line">
        {live && person.expires_at ? `Expires ${monthDay(person.expires_at)} · ` : ''}
        opened {person.opens}×{person.submitted_at ? ` · submitted ${monthDay(person.submitted_at)}` : ''}
      </div>
      <div className="rr-person-line rr-edit-note">On it: {person.asks.join(' · ') || 'nothing'}</div>
      <div className="rr-person-actions">
        <button type="button" className="btn btn-sm btn-secondary" onClick={() => onEdit(person)}
          title="See and change this link: whether it is on, who can open it, when it runs out">
          Edit
        </button>
        {live && person.path && (
          <>
            <button type="button" className="btn btn-sm btn-secondary" disabled={actions.busy} onClick={() => actions.copyLink(person)}>
              ⧉ Copy link
            </button>
            <a className="btn btn-sm btn-secondary" href={`/preview/links/${person.link_id}`} target="_blank" rel="noreferrer">
              View ▸
            </a>
          </>
        )}
      </div>
    </div>
  );
}

export default function PeopleLinks({ requests, meta, actions, readOnly, onEdit, onNew, onClose }) {
  const people = peopleOf(requests);
  const active = people.filter((person) => linkStatus(person) === 'active');
  const ended = people.filter((person) => linkStatus(person) !== 'active');
  const row = (person) => <PersonRow key={person.link_id} person={person} meta={meta} actions={actions} onEdit={onEdit} />;
  return (
    <div className="rr-people-scrim" role="presentation" onClick={onClose}>
      <aside className="rr-people" role="dialog" aria-label="People and links" onClick={(event) => event.stopPropagation()}>
        <div className="rr-people-head">
          <b>People &amp; links</b>
          {!readOnly && (
            <button type="button" className="btn btn-sm btn-violet" onClick={onNew} title="Make a new link for someone: pick who, and what it asks">
              ＋ New link
            </button>
          )}
          <button type="button" className="rr-linklike rr-people-close" aria-label="Close" title="Close" onClick={onClose}>
            ×
          </button>
        </div>
        <div className="rr-people-sub">Nothing is emailed from here: copy a link to send it.</div>
        {active.map(row)}
        {!active.length && <div className="rr-rail-note">No link is open on this deal.</div>}
        {ended.length > 0 && <div className="rr-person-h rr-people-ended">Ended</div>}
        {ended.map(row)}
      </aside>
    </div>
  );
}
