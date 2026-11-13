import { byDestination, bySection, possessive } from '../tray/trayModel';

function expiryWords(iso) {
  if (!iso) return '';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '';
  const day = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  return date.getTime() <= Date.now() ? `ran out ${day}: it lives again when sent` : `runs out ${day}`;
}

function Items({ list, sections, readOnly, busy, onRemove, whys = true }) {
  return bySection(list, sections).map((group) => (
    <div key={group.key} className="rr-sheet-group">
      <div className="rr-sheet-group-h">
        {group.label} · {group.list.length}
      </div>
      {group.list.map((item) => (
        <div key={item.id} className="rr-sheet-item rr-cart-item">
          <div>
            <b>{item.title}</b>
            <span>{item.text || (item.kind === 'sendback' ? 'Sent back to check' : 'Asked for')}</span>
            {whys && item.why && <span className="rr-sheet-warn">{item.why}</span>}
          </div>
          {!readOnly && (
            <button type="button" className="rr-sheet-x" disabled={busy} title="Take it out of the tray" aria-label={`Take ${item.title} out of the tray`} onClick={() => onRemove(item.id)}>
              ×
            </button>
          )}
        </div>
      ))}
    </div>
  ));
}

/*
 * Going out (plan.md §8.8; L37, L52, L53; old 891f1b3 `FollowUpCart.jsx`): what is in the tray, a card per link it goes
 * on — who has it, when it runs out — then what no open link can take ("Choose who ▸" makes one new link for them),
 * then what is gone (dropped on send). Send puts everything that has a link on it, each link in its own write, keeping
 * what went if one refuses; the result says what went where. The app sends no email: the client sees it on the link
 * they already have (OQ82).
 */
export default function GoingOut({ tray, sections, readOnly, busy, result, onSend, onRemove, onChooseWho, onDismiss }) {
  const items = tray?.items || [];
  const { links, nowhere, gone } = byDestination(items);
  const cards = Object.fromEntries((tray?.links || []).map((card) => [card.key, card]));
  const sendable = links.reduce((sum, group) => sum + group.list.length, 0);
  return (
    <div className="rr-cart" aria-label="Going out">
      <div className="rr-reqpage-colhead">
        <b>Going out</b>
        <span>{items.length ? `${items.length} in the request tray` : 'The request tray is empty'}</span>
      </div>
      {result && (
        <div className="rr-cart-result" role="status">
          {result.sent > 0 && (
            <div className="bb-link-ready">
              <span className="bb-check">✓</span>
              <div>
                {result.sent} follow-up{result.sent === 1 ? '' : 's'} added to{' '}
                {result.targets.length === 1 ? `${possessive(result.targets[0].names)} secure link` : `${result.targets.length} secure links`}. They see
                them at the top of their to-do list. Nothing was emailed: tell them it is there.
              </div>
            </div>
          )}
          {result.waiting?.length > 0 && (
            <div className="rr-sheet-warn-box">
              {result.waiting.length} item{result.waiting.length === 1 ? ' has' : 's have'} no open link to join: choose who to ask below.
            </div>
          )}
          <div className="rr-cart-result-foot">
            <button type="button" className="btn btn-sm btn-primary" onClick={onDismiss} title="Clear this summary of the send">
              Done
            </button>
          </div>
        </div>
      )}
      {links.map((group) => {
        const card = cards[group.key] || {};
        return (
          <div key={group.key} className="rr-dest">
            <div className="rr-dest-head">
              <div>
                <b>{`${possessive(group.target.names)} link`}</b>
                <span>{expiryWords(group.target.expires_at)}</span>
              </div>
            </div>
            {(card.people || []).map((person) => (
              <div key={person.link_id} className="rr-dest-person">
                <span>
                  <b>{person.name || 'Their link'}</b>
                  {person.sent_at ? ' · sent' : ' · not sent yet'}
                  {` · opened ${person.opened || 0}×`}
                </span>
              </div>
            ))}
            <Items list={group.list} sections={sections} readOnly={readOnly} busy={busy} onRemove={onRemove} />
          </div>
        );
      })}
      {nowhere.length > 0 && (
        <div className="rr-dest rr-dest-new">
          <div className="rr-dest-head">
            <div>
              <b>Needs a new link</b>
              <span>No open link can take these: choose who to ask, and they go on the new link.</span>
            </div>
            {!readOnly && (
              <button type="button" className="btn btn-sm btn-violet" disabled={busy} title="Pick who to ask: a new link carries these, and they go out on it" onClick={() => onChooseWho(nowhere.map((item) => item.id))}>
                Choose who ▸
              </button>
            )}
          </div>
          {[...new Set(nowhere.filter((item) => item.why_code !== 'needs_link').map((item) => item.why))].map((why) => (
            <div key={why} className="rr-sheet-warn">
              {why}
            </div>
          ))}
          <Items list={nowhere} sections={sections} readOnly={readOnly} busy={busy} onRemove={onRemove} whys={false} />
        </div>
      )}
      {gone.length > 0 && (
        <div className="rr-dest rr-dest-none">
          <div className="rr-dest-head">
            <div>
              <b>No longer on the deal</b>
              <span>Sending the tray drops these.</span>
            </div>
          </div>
          <Items list={gone} sections={sections} readOnly={readOnly} busy={busy} onRemove={onRemove} />
        </div>
      )}
      {!items.length && !result && <div className="rr-cart-empty">Nothing in the tray yet. Tick a question on the left, or ＋ Add all for a section.</div>}
      {!readOnly && sendable > 0 && (
        <div className="rr-askfoot-actions">
          <button type="button" className="btn btn-violet" disabled={busy} title="Put these on the links they go on: the client sees them there, nothing is emailed" onClick={() => onSend({})}>
            {busy ? 'Sending…' : `Send ${sendable} ▸`}
          </button>
        </div>
      )}
    </div>
  );
}
