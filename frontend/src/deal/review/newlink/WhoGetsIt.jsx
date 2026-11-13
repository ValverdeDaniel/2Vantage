import { useState } from 'react';
import AddPerson from './AddPerson';
import { toggled, typedPerson } from './newLinkModel';

/*
 * Who gets it (L56, L57, L73; old 891f1b3 `RecipientPicker.jsx`): the client's contacts, a tick each, someone typed
 * in by name with an optional address, or "＋ Add a person to the deal", who joins the client's contacts with the role
 * a person picks (nothing pre-picked, Ch. 7) and is ticked. A name is enough while copying the link is the send (OQ82).
 * Nobody picked is a private link anyone holding it can open.
 */
export default function WhoGetsIt({ contacts, state, onChange, disabled, dealId = null, clientId = null }) {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  function add() {
    const person = typedPerson(name, email);
    if (!person) return;
    onChange({ typed: [...state.typed, person] });
    setName('');
    setEmail('');
  }
  return (
    <div className="rr-recipients">
      {contacts.length === 0 && <div className="rr-recipients-empty">No contacts on this deal yet — type a person below.</div>}
      {contacts.map((contact) => (
        <label key={contact.id} className="rr-recipient" title={contact.email || 'No email address on file'}>
          <input
            type="checkbox"
            checked={state.contactIds.includes(contact.id)}
            disabled={disabled}
            onChange={() => onChange({ contactIds: toggled(state.contactIds, contact.id) })}
          />
          <span className="rr-recipient-name">{contact.name || contact.email || contact.role_label}</span>
          <span className="rr-recipient-role">{contact.role_label}</span>
          <span className="rr-recipient-email">{contact.email || '(no email)'}</span>
        </label>
      ))}
      {state.typed.map((person, index) => (
        <div key={`${person.name}-${person.email}`} className="rr-recipient rr-recipient-typed">
          <span className="rr-recipient-name">{person.name}</span>
          {person.email && <span className="rr-recipient-email">{person.email}</span>}
          <button type="button" className="rr-linklike" disabled={disabled} title="Take this person off the list"
            onClick={() => onChange({ typed: state.typed.filter((_p, i) => i !== index) })}>
            remove
          </button>
        </div>
      ))}
      <div className="rr-recipient-add">
        <input type="text" value={name} placeholder="or type a name" aria-label="Their name" disabled={disabled}
          onChange={(e) => setName(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault();
              add();
            }
          }} />
        <input type="email" value={email} placeholder="their email (optional)" aria-label="Their email" disabled={disabled}
          onChange={(e) => setEmail(e.target.value)} />
        <button type="button" className="btn btn-secondary btn-sm" disabled={disabled || !name.trim()} onClick={add}
          title="Add this person to who gets a link">
          Add
        </button>
      </div>
      {dealId && clientId && (
        <AddPerson dealId={dealId} clientId={clientId} disabled={disabled}
          onAdded={(contact) => onChange({ contactIds: [...state.contactIds, contact.id] })} />
      )}
    </div>
  );
}
