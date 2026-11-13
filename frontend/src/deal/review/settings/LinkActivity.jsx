import { agoWords, monthDay } from '../reviewModel';

function Row({ label, value }) {
  return (
    <>
      <dt>{label}</dt>
      <dd>{value || '–'}</dd>
    </>
  );
}

/*
 * The settings card's side column (plan.md §8.8; L39; old 891f1b3 `LinkSettingsCard.jsx` `LinkActivity`): what is on
 * this link, then its activity — read, never written. "Opened" is said of the link, never of a person (D-057): anyone
 * holding it counts.
 */
export default function LinkActivity({ person }) {
  return (
    <aside className="rr-settings-side">
      {person.asks?.length > 0 && (
        <div className="rr-person-carries">
          <span className="rr-person-h">On this link</span>
          {person.asks.map((words) => (
            <span key={words} className="rr-person-carry">
              {words}
            </span>
          ))}
        </div>
      )}
      <div className="rr-settings-cell">
        <div className="rr-person-h">Activity</div>
        <dl className="rr-edit-activity">
          <Row label="Sent" value={person.sent_at ? monthDay(person.sent_at) : 'Not copied yet'} />
          <Row label="First opened" value={monthDay(person.opened_at)} />
          <Row label="Last opened" value={agoWords(person.last_opened_at)} />
          <Row label="Times opened" value={String(person.opens || 0)} />
          <Row label="Last saved" value={agoWords(person.last_saved_at)} />
          <Row label="Submitted" value={monthDay(person.submitted_at)} />
        </dl>
        <div className="rr-edit-note">Opened counts the link, not a person: anyone holding it counts.</div>
      </div>
    </aside>
  );
}
