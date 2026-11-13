import { useState } from 'react';
import { useAddContact } from '../../../api/intake';
import { useMeta } from '../../../api/meta';
import { errorText } from '../../../lib/errors';
import { useToast } from '../../../ui/useToast';

/*
 * "＋ Add a person to the deal" (plan.md §8.8; L73; old 891f1b3 `RecipientPicker.jsx` `onAddPerson`): a new contact of
 * the client, through deals' own door (`POST clients/{id}/contacts/`), with the role a person picks — nothing is
 * pre-picked (Ch. 7), so a CFO added only to receive a link never passes the intake's contacts gate as an HR admin
 * (B21). Once added they are ticked. The roles' words come from /api/meta/ `contact_roles` (client side only).
 */
export default function AddPerson({ dealId, clientId, disabled, onAdded }) {
  const roles = (useMeta().data?.contact_roles || []).filter((role) => role.client_side);
  const add = useAddContact(dealId, clientId);
  const toast = useToast();
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ name: '', email: '', role: '' });
  if (!open) {
    return (
      <button type="button" className="rr-linklike rr-recipient-new" disabled={disabled} onClick={() => setOpen(true)}
        title="Someone the client has not told us about yet: they join the client's contacts">
        ＋ Add a person to the deal
      </button>
    );
  }
  const ready = form.name.trim() && form.role;
  const save = () =>
    add
      .mutateAsync({ name: form.name.trim(), email: form.email.trim(), role: form.role })
      .then((contact) => {
        onAdded(contact);
        setForm({ name: '', email: '', role: '' });
        setOpen(false);
      })
      .catch((error) => toast.error(errorText(error, { fallback: 'Could not add that person.' })));
  return (
    <div className="rr-recipient-add">
      <input type="text" value={form.name} placeholder="Their name" aria-label="The new person's name"
        onChange={(event) => setForm({ ...form, name: event.target.value })} />
      <input type="email" value={form.email} placeholder="their email (optional)" aria-label="The new person's email"
        onChange={(event) => setForm({ ...form, email: event.target.value })} />
      <select value={form.role} aria-label="Their role" onChange={(event) => setForm({ ...form, role: event.target.value })}>
        <option value="">Their role…</option>
        {roles.map((role) => (
          <option key={role.key} value={role.key}>
            {role.label}
          </option>
        ))}
      </select>
      <button type="button" className="btn btn-secondary btn-sm" disabled={!ready || add.isPending} onClick={save}
        title={ready ? 'Add them to the client’s contacts and to who gets a link' : 'Give a name and pick their role'}>
        {add.isPending ? 'Adding…' : 'Add to the deal'}
      </button>
      <button type="button" className="rr-linklike" onClick={() => setOpen(false)}>
        Cancel
      </button>
    </div>
  );
}
