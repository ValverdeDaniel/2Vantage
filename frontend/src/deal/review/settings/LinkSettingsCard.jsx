import PinOnce from '../request/PinOnce';
import { withSetting } from '../requestpage/askCardModel';
import { GiveAccess, CorrectAddress } from './AccessCells';
import { EndedExpiry, LiveExpiry, NudgeReminder } from './DateCells';
import LinkActivity from './LinkActivity';
import { linkStatus, othersWaiting, statusNote } from './settingsModel';

const FILLED = 'What we have shows, for them to check or change.';
const BLANK = 'Only what they answer shows, never what else we hold.';

/*
 * Edit link settings (plan.md §8.8; L39, L60–L64, L66, L69; old 891f1b3 `LinkSettingsCard.jsx` `EditLinkSettings`,
 * D-188): one card under the who bar for one person's link, in the New link card's row order. Who can open it, what
 * they see, when it runs out, the reminder to nudge and the note wait for Update link with the Ask card's ticks (`card`,
 * the same request's: settings never change what a link asks); these act at once — the on/off switch, New PIN (shown
 * once), Extend, Correct the address (only before anyone opened it), Give someone else access and Copy link. A link that
 * ended, or a deal that only reads, has no `card`: the card says how it stands and keeps what still acts.
 */
export default function LinkSettingsCard({ deal, person, card, meta, actions, readOnly, people, onClose }) {
  const status = linkStatus(person);
  const active = status === 'active';
  const name = person.name || 'Private link';
  const own = card?.change.settings[person.link_id] || {};
  const pick = (key, value) => card.set((now) => withSetting(now, person.link_id, key, value));
  const level = (meta?.levels || []).find((item) => item.key === (card?.change.security || person.security));
  const others = card ? othersWaiting(card.change.settings, person.link_id, people) : [];
  const message = card?.change.message ?? person.message;
  return (
    <div className="rr-newlink" data-link-id={person.link_id} aria-label="Edit link settings">
      <div className="rr-newlink-head">
        <b>Edit link settings</b>
        <span className="rr-settings-who">{name}</span>
        {card && <span className="rr-edit-note">Nothing is saved until Update link.</span>}
        <span className="rr-settings-actions">
          {active && person.path && (
            <>
              <button type="button" className="btn btn-sm btn-secondary" disabled={actions.busy} onClick={() => actions.copyLink(person)}>
                ⧉ Copy link
              </button>
              <a className="btn btn-sm btn-secondary" href={`/preview/links/${person.link_id}`} target="_blank" rel="noreferrer">
                View ▸
              </a>
            </>
          )}
          {card && (
            <button type="button" className="btn btn-sm btn-violet" disabled={card.updating || !card.count || Boolean(card.waitingOn)}
              title={card.waitingOn || 'Update their link now, with anything ticked. No email goes out'} onClick={card.update}>
              {card.updateLabel}
            </button>
          )}
          <button type="button" className="rr-linklike" onClick={onClose} title={card?.count ? 'Close this: your changes keep waiting for Update link' : 'Close this'}>
            Close
          </button>
        </span>
      </div>
      {card?.waitingOn && card.count > 0 && <div className="rr-edit-note" role="status">{card.waitingOn}</div>}
      {others.length > 0 && <div className="rr-edit-note" role="status">Going with this update too: {others.join(' · ')}.</div>}
      <div className="rr-settings-body">
        <div className="rr-newlink-grid">
          <div className="rr-newlink-h">Status</div>
          <div className="rr-settings-cell">
            {active || status === 'revoked' ? (
              <label className="rr-edit-switch">
                <input type="checkbox" role="switch" checked={active} disabled={actions.busy || (!active && (readOnly || !person.can_restore))}
                  aria-label={active ? `Turn ${name}’s link off` : `Turn ${name}’s link back on`}
                  onChange={(event) => (event.target.checked ? actions.restore(person) : actions.revoke(person))} />
                <b>{active ? 'Active' : 'Turned off'}</b>
              </label>
            ) : (
              <b>{status === 'expired' ? 'Ran out' : 'Request closed'}</b>
            )}
            <div className="rr-edit-note">{statusNote(person, name)}</div>
          </div>
          <div className="rr-newlink-h">Who gets it</div>
          <div className="rr-settings-cell">
            <div className="rr-edit-row">
              <b>{name}</b>
              {person.email && <span>{person.email}</span>}
              {person.can_correct && !readOnly && <CorrectAddress person={person} actions={actions} />}
            </div>
            {active && !readOnly && <GiveAccess deal={deal} person={person} name={name} />}
          </div>
          <div className="rr-newlink-h">Who can open it</div>
          <div className="rr-settings-cell">
            {card ? (
              <div className="rr-newlink-levels" role="radiogroup" aria-label="Who can open it">
                {(meta?.levels || []).map((item) => (
                  <label key={item.key} className="rr-edit-level">
                    <input type="radio" name={`settings-access-${person.link_id}`} checked={level?.key === item.key}
                      onChange={() => card.set((now) => ({ ...now, security: item.key === person.security ? '' : item.key }))} />
                    <span>
                      <b>{item.label}</b> {level?.key === item.key ? item.means : ''}
                    </span>
                  </label>
                ))}
                <div className="rr-edit-note">This goes for everyone on this request. A raise makes a new PIN for each, shown once.</div>
              </div>
            ) : (
              <div className="rr-edit-note">
                <b>{level?.label}:</b> {level?.means}.
              </div>
            )}
            {active && person.security === 'pin' && !readOnly && (
              <div className="rr-edit-row">
                <button type="button" className="btn btn-sm btn-secondary" disabled={actions.busy} onClick={() => actions.newPin(person)}
                  title="Make a new PIN: the old one stops working, and anyone with the link types the new one">
                  New PIN
                </button>
                {person.pin_locked && <span className="rr-edit-warn">Five wrong tries locked this PIN: a new one lets them back in.</span>}
              </div>
            )}
            <PinOnce pin={actions.pins[person.link_id]} name={name} />
          </div>
          <div className="rr-newlink-h">What they see</div>
          {card ? (
            <div className="rr-newlink-levels" role="radiogroup" aria-label="What they see">
              {[[false, 'Filled in', FILLED], [true, 'Blank', BLANK]].map(([blank, words, means]) => (
                <label key={words} className="rr-edit-level">
                  <input type="radio" name={`settings-view-${person.link_id}`} checked={(own.blank ?? person.blank) === blank}
                    onChange={() => pick('blank', blank === person.blank ? null : blank)} />
                  <span>
                    <b>{words}</b> {means}
                  </span>
                </label>
              ))}
            </div>
          ) : (
            <div className="rr-edit-note">
              <b>{person.blank ? 'Blank' : 'Filled in'}:</b> {person.blank ? BLANK : FILLED}
            </div>
          )}
          {(active || status === 'expired') && (
            <>
              <div className="rr-newlink-h">Expires</div>
              {card && active ? (
                <LiveExpiry person={person} pending={own.expires_on} busy={actions.busy} onPick={(day) => pick('expires_on', day)}
                  onExtend={() => {
                    pick('expires_on', null);
                    actions.extend(person);
                  }} />
              ) : (
                <EndedExpiry person={person} readOnly={readOnly} actions={actions} />
              )}
            </>
          )}
          {card && active && (
            <>
              <div className="rr-newlink-h">Remind me to nudge</div>
              <NudgeReminder person={person} pending={own.nudge_on} ends={own.expires_on || person.expires_at?.slice(0, 10)}
                onPick={(day) => pick('nudge_on', day === (person.nudge_on || '') ? null : day)} />
            </>
          )}
          <div className="rr-newlink-h">A note for them</div>
          {card ? (
            <textarea rows={2} maxLength={meta?.message_limit ?? 1000} value={message} aria-label="A note for them"
              placeholder="Shown at the top of their page." onChange={(event) => card.set((now) => ({ ...now, message: event.target.value }))} />
          ) : (
            <div className="rr-edit-note">{person.message || '—'}</div>
          )}
        </div>
        <LinkActivity person={person} />
      </div>
    </div>
  );
}
