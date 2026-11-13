import PinOnce from '../request/PinOnce';
import { numberWords, updateWords } from './askCardModel';

const plural = (n, one) => `${n} ${one}${n === 1 ? '' : 's'}`;

/*
 * The Ask card's foot (plan.md §8.8; L36, L42, L64; old 891f1b3 `LinkSettingsCard.jsx` `BuildFooter`, the Ask list's
 * foot in link mode): what goes on and comes off in words, what the link would then ask, who it reaches, the level —
 * a level too low for what is ticked says so and offers the raise (a link already out never rises by itself), one a
 * person may lower once nothing needs it — the warnings, why it cannot go, and Update link. What Update link answered
 * stays here: each new PIN, this once.
 */
export default function AskFoot({ card, target, meta, readOnly }) {
  const { plan, change, count } = card;
  const levels = meta?.levels || [];
  const level = change.security || target.security;
  const floor = plan?.floor?.level || 'link';
  const rank = (key) => levels.findIndex((item) => item.key === key);
  const words = (key) => levels.find((item) => item.key === key)?.label || key;
  const owed = plan?.owed;
  return (
    <div className="rr-askfoot">
      <div className="rr-askfoot-sum">
        <b>{count ? `${plural(count, 'change')} waiting` : 'Nothing changed yet'}</b>
        <span className="rr-edit-note">
          {target.names.length ? `Reaches ${target.names.join(', ')}` : 'A private link'} · {words(level)}
        </span>
      </div>
      {plan && count > 0 && (
        <div className="rr-askfoot-message">
          {plan.adds.length > 0 && <div>Goes on: {plan.adds.join(' · ')}</div>}
          {plan.offs.length > 0 && <div>Comes off: {plan.offs.join(' · ')}</div>}
          {plan.numbers && Object.keys(plan.numbers).length > 0 && <div className="rr-edit-note">Their form then asks {numberWords(plan.numbers)}.</div>}
        </div>
      )}
      {(owed || rank(level) > rank(floor)) && !readOnly && (
        <div className="rr-newlink-levels" role="radiogroup" aria-label="Who can open it">
          {levels.map((item) => (
            <label key={item.key} className={`rr-edit-level${rank(item.key) < rank(floor) ? ' rr-edit-level-off' : ''}`}>
              <input type="radio" name={`ask-level-${target.request_id}`} checked={level === item.key} disabled={rank(item.key) < rank(floor)}
                onChange={() => card.set((now) => ({ ...now, security: item.key === target.security ? '' : item.key }))} />
              <span>
                <b>{item.label}</b> {item.means}
              </span>
            </label>
          ))}
          {target.link_ids.length > 1 && <div className="rr-edit-note">This goes for everyone on this request: {target.names.join(', ')}.</div>}
        </div>
      )}
      {(plan?.warnings || []).map((warning) => (
        <div key={warning} className="rr-sheet-warn">
          {warning}
        </div>
      ))}
      {plan?.refused && (
        <div className={owed ? 'rr-sheet-warn' : 'rr-edit-note'} role="status">
          {plan.refused}
        </div>
      )}
      <div className="rr-askfoot-actions">
        {count > 0 && (
          <button type="button" className="rr-linklike" onClick={card.reset} title="Drop what waits here: the drafts in the tray stay">
            Undo changes
          </button>
        )}
        <button type="button" className="btn btn-violet" disabled={readOnly || card.updating || card.planning || !count || Boolean(plan?.refused)}
          title={plan?.refused || 'Update their link now: their form shows it at the same address. No email goes out: copy them a message after'}
          onClick={card.update}>
          {updateWords(target, card.updating)}
        </button>
      </div>
      {card.done && (
        <div className="rr-linkready" role="status">
          <div className="bb-link-ready">
            <span className="bb-check">✓</span>
            <div>
              {card.done.request.recipients.length === 1 ? 'Their link is updated' : 'Their links are updated'}: their form shows it
              now, at the same address. The app never sends mail, so copy them a message if you want them to look.
            </div>
          </div>
          {card.done.pins.map((made) => (
            <PinOnce key={made.link_id} pin={made.pin} name={made.name} />
          ))}
          <div className="rr-linkready-foot">
            <button type="button" className="btn btn-sm btn-primary" onClick={card.dismiss}>
              Done
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
