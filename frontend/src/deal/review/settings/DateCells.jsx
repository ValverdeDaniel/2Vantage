import { useState } from 'react';
import { dayIn } from '../newlink/newLinkModel';
import { monthDay } from '../reviewModel';
import { dayBefore, dayOf } from './settingsModel';

const DATE_WORDS = 'A date you pick holds: their saves no longer push it out. A new ask from us still gives the link its life again.';

/*
 * When a link runs out, and the reminder to nudge them (plan.md §8.8; L39, L61, L69; I35–I39; old 891f1b3
 * `LinkSettingsCard.jsx` `LiveExpiry`, `LinkExpiry`, `NudgeReminder`). On a live link the date and the reminder wait
 * for Update link with the ticks (`pending` holds them), while Extend goes at once; on a link that ran out, the date has
 * its own Save. A reminder is a day before the link runs out; that day it shows on the Agenda, and the client sees
 * nothing. The server holds every rule on the day; `max` here only saves a refused pick.
 */
export function LiveExpiry({ person, pending, onPick, onExtend, busy }) {
  return (
    <div className="rr-settings-cell">
      <div className="rr-edit-row">
        <input type="date" value={pending || dayOf(person.expires_at)} min={dayIn(0)} max={dayOf(person.ceiling_at)}
          aria-label="When this link runs out" onChange={(event) => onPick(event.target.value || null)} />
        <button type="button" className="btn btn-sm btn-secondary" disabled={busy} onClick={onExtend}
          title="Give the link its life again from today, now: never past its 30-day limit">
          Extend
        </button>
        <span className="rr-edit-note">latest {monthDay(person.ceiling_at)}</span>
      </div>
      <div className="rr-edit-note">{DATE_WORDS}</div>
    </div>
  );
}

export function EndedExpiry({ person, readOnly, actions }) {
  const current = dayOf(person.expires_at);
  const [day, setDay] = useState(null);
  const shown = day ?? current;
  const save = async () => {
    if (await actions.setting(person, 'expiry', { day: shown }, `The link now runs to ${monthDay(`${shown}T12:00:00`)}`)) setDay(null);
  };
  return (
    <div className="rr-settings-cell">
      <div className="rr-edit-row">
        <input type="date" value={shown} min={dayIn(0)} max={dayOf(person.ceiling_at)} disabled={readOnly || !person.can_extend}
          aria-label="When this link runs out" onChange={(event) => setDay(event.target.value)} />
        {day !== null && day !== current && (
          <button type="button" className="btn btn-sm btn-primary" disabled={actions.busy || !day} onClick={save}>
            Save
          </button>
        )}
        {!readOnly && person.can_extend && (
          <button type="button" className="btn btn-sm btn-secondary" disabled={actions.busy} onClick={() => actions.extend(person)}>
            Extend
          </button>
        )}
        <span className="rr-edit-note">latest {monthDay(person.ceiling_at)}</span>
      </div>
      <div className="rr-edit-note">{DATE_WORDS}</div>
    </div>
  );
}

export function NudgeReminder({ person, pending, ends, onPick }) {
  const who = person.name || 'them';
  const day = pending === undefined ? person.nudge_on || '' : pending || '';
  return (
    <div className="rr-settings-cell">
      <div className="rr-edit-row">
        <input type="date" value={day} min={dayIn(0)} max={dayBefore(ends)} aria-label={`The day to remind you to nudge ${who}`}
          onChange={(event) => onPick(event.target.value || '')} />
        {day && (
          <button type="button" className="rr-linklike" title="Take this reminder off" onClick={() => onPick('')}>
            Remove
          </button>
        )}
        {person.nudge_done_at && <span className="rr-edit-note">Nudged {monthDay(person.nudge_done_at)}</span>}
      </div>
      <div className="rr-edit-note">
        That day it shows on your Agenda: nudge {who} about this form. They see nothing. It goes away by itself if they
        submit or this link ends.
      </div>
    </div>
  );
}
