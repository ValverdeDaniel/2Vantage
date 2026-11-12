import { useState } from 'react';
import PinOnce from '../request/PinOnce';

/*
 * What Create link answers (L40; old 891f1b3 `LinkSettingsCard.jsx` `LinkReady`): each person's link, to paste into
 * your own email. Copying is the send (OQ82): the app never sends mail, so a copy marks the link sent. A PIN shows
 * only here, once.
 */
export default function LinkReady({ result, actions, onDone }) {
  const [copied, setCopied] = useState({});
  const count = result.links.length;
  async function copy(link) {
    const person = { ...link, sent: Boolean(copied[link.link_id]) };
    if (await actions.copyLink(person)) setCopied((now) => ({ ...now, [link.link_id]: true }));
  }
  return (
    <div className="rr-linkready" role="status">
      <div className="bb-link-ready">
        <span className="bb-check">✓</span>
        <div>
          {count === 1 ? 'Link ready' : `${count} links ready`}: paste each into your own email. The app never sends
          mail, and copying is what marks it sent.
        </div>
      </div>
      {result.links.map((link) => (
        <div key={link.link_id} className="rr-linkready-row">
          <div className="rr-linkready-who">
            <b>{link.name || 'Private link'}</b>
            {link.email && <span className="rr-edit-note">{link.email}</span>}
            {!link.name && <span className="rr-edit-note">Anyone holding it can open it</span>}
            {copied[link.link_id] && <span className="bb-chip">sent</span>}
          </div>
          <div className="rr-linkready-actions">
            <button type="button" className="btn btn-sm btn-violet" disabled={actions.busy} onClick={() => copy(link)}
              title="Copy their personal link to paste anywhere: copying it counts as sending it">
              Copy link
            </button>
          </div>
          <PinOnce pin={link.pin} name={link.name} />
        </div>
      ))}
      <div className="rr-linkready-foot">
        <button type="button" className="btn btn-sm btn-primary" onClick={onDone} title="Close this: the links are made and waiting to be shared">
          Done
        </button>
      </div>
    </div>
  );
}
