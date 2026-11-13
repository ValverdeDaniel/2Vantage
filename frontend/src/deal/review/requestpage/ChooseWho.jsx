import { useState } from 'react';
import { useClientContacts } from '../../../api/review';
import WhoGetsIt from '../newlink/WhoGetsIt';
import { whoCount } from '../newlink/newLinkModel';

/*
 * "Choose who ▸" (plan.md §8.8; L37, L52, L53; old 891f1b3 `FollowUpCart.jsx` onNewRequest): who the new link for the
 * tray's homeless items goes to — the client's contacts, someone typed in, or nobody (a private link). Send makes one
 * request carrying exactly what they ask, at the security those items need (a census value raises it to a PIN by
 * itself), and the items go out on it; its links and any PIN come back once (LinkReady).
 */
export default function ChooseWho({ deal, count, busy, onSend, onCancel }) {
  const contacts = useClientContacts(deal.id, deal.client.id);
  const [state, setState] = useState({ contactIds: [], typed: [] });
  const people = [...state.contactIds.map((id) => ({ contact_id: id })), ...state.typed.map(({ name, email }) => ({ name, email }))];
  return (
    <div className="rr-newlink" role="group" aria-label="Choose who to ask">
      <div className="rr-newlink-head">
        <b>Choose who to ask</b>
        <span className="rr-edit-note">
          {count} item{count === 1 ? '' : 's'} go on one new link. Nobody picked is a private link anyone holding it can open.
        </span>
      </div>
      <WhoGetsIt contacts={contacts.data?.contacts || []} state={state} onChange={(part) => setState((now) => ({ ...now, ...part }))} disabled={busy} />
      <div className="rr-sheet-footer">
        <button type="button" className="rr-linklike" disabled={busy} onClick={onCancel}>
          Cancel
        </button>
        <button type="button" className="btn btn-sm btn-violet" disabled={busy} title="Make the link and put these on it: nothing is emailed, you copy and share it next" onClick={() => onSend({ people })}>
          {busy ? 'Sending…' : `Send on ${whoCount(state) > 1 ? `${whoCount(state)} new links` : 'a new link'} ▸`}
        </button>
      </div>
    </div>
  );
}
