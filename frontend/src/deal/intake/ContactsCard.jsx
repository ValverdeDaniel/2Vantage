import { useState } from 'react';
import { useAddContact, useEditContact, useRemoveContact } from '../../api/intake';
import { errorText } from '../../lib/errors';
import ConfirmDialog from '../../ui/ConfirmDialog';
import { useToast } from '../../ui/useToast';

/*
 * Contacts (plan.md §8.9; B13, M30, OQ106), the old Intake card (891f1b3 `IntakeTab.jsx`, same classes): one subcard
 * per contact — role, name, "main contact" and ×; title, email and phone — with the email check under it, then
 * "＋ Add contact" (an HR admin). The contacts are the client's (`deals.Contact`, renewal-proof) and write through
 * deals' doors; the intake payload carries them with their issues. Fixed (B13): × asks first. Readiness needs an HR
 * admin or benefit administrator with a name and an email. The roles are /api/meta/'s seven (OQ106).
 */
function Subcard({ contact, roles, busy, onSave, onRemove }) {
  const blur = (key) => (event) => event.target.value !== (contact[key] || '') && onSave({ [key]: event.target.value });
  const named = contact.name || contact.role_label;
  return (
    <div className="bnf-subcard" role="group" aria-label={`Contact ${named}`}>
      <div className="bnf-subcard-row">
        <select
          className="bnf-intake-input bnf-w-narrow"
          value={contact.role}
          aria-label="Role"
          disabled={busy}
          onChange={(event) => onSave({ role: event.target.value })}
        >
          {roles.map((role) => (
            <option key={role.key} value={role.key}>
              {role.label}
            </option>
          ))}
        </select>
        <input key={`name:${contact.name}`} className="bnf-intake-input" defaultValue={contact.name} placeholder="Name"
          aria-label="Name" onBlur={blur('name')} />
        <label className="bnf-com-active" title="The client's main contact — what the RFP and the forms print">
          <input
            type="checkbox"
            checked={Boolean(contact.is_primary)}
            disabled={busy}
            onChange={(event) => onSave({ is_primary: event.target.checked })}
          />
          main contact
        </label>
        <button type="button" className="bb-drop-remove" title="Remove contact" aria-label={`Remove ${named}`}
          disabled={busy} onClick={onRemove}>
          ×
        </button>
      </div>
      <div className="bnf-subcard-row">
        <input key={`title:${contact.title}`} className="bnf-intake-input" defaultValue={contact.title}
          placeholder="Title" aria-label="Title" onBlur={blur('title')} />
        <input key={`email:${contact.email}`} className="bnf-intake-input" defaultValue={contact.email}
          placeholder="Email" aria-label="Email" onBlur={blur('email')} />
        <input key={`phone:${contact.phone}`} className="bnf-intake-input bnf-w-narrow" defaultValue={contact.phone}
          placeholder="Phone" aria-label="Phone" onBlur={blur('phone')} />
      </div>
      {(contact.issues || []).map((issue) => (
        <div key={issue.code} className="bnf-issue-line bb-rose">
          {issue.message}
        </div>
      ))}
    </div>
  );
}

export default function ContactsCard({ deal, meta, contacts }) {
  const toast = useToast();
  const add = useAddContact(deal.id, deal.client.id);
  const edit = useEditContact(deal.id);
  const remove = useRemoveContact(deal.id);
  const [removing, setRemoving] = useState(null);
  const busy = add.isPending || edit.isPending || remove.isPending;
  const failed = (fallback) => ({ onError: (error) => toast.error(errorText(error, { fallback })) });
  const roles = meta?.contact_roles || [];

  return (
    <div className="bb-panel bnf-intake-section">
      <div className="bb-panel-title">Contacts</div>
      <div className="bb-panel-sub">At minimum one HR admin with name + email</div>
      {contacts.map((contact) => (
        <Subcard
          key={contact.id}
          contact={contact}
          roles={roles}
          busy={busy}
          onSave={(changes) => edit.mutate({ id: contact.id, changes }, failed('Could not save the contact.'))}
          onRemove={() => setRemoving(contact)}
        />
      ))}
      <button
        type="button"
        className="btn btn-secondary btn-sm"
        disabled={busy}
        onClick={() => add.mutate({}, failed('Could not add the contact.'))}
      >
        ＋ Add contact
      </button>
      <ConfirmDialog
        open={Boolean(removing)}
        title="Remove this contact?"
        message={removing ? `${removing.name || removing.role_label} leaves the client's contacts.` : ''}
        confirmLabel="Remove"
        tone="danger"
        busy={remove.isPending}
        onCancel={() => setRemoving(null)}
        onConfirm={() =>
          remove.mutate(removing.id, { ...failed('Could not remove the contact.'), onSettled: () => setRemoving(null) })
        }
      />
    </div>
  );
}
