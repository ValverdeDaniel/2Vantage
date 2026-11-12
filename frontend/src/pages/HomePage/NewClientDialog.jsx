import { useState } from 'react';
import { useNavigate } from 'react-router';
import { useCreateClient, useUsers } from '../../api/deals';
import { creatableStatuses, useMeta } from '../../api/meta';
import { useAuth } from '../../auth/useAuth';
import { fieldErrors, formErrorText } from '../../lib/errors';
import Button from '../../ui/Button';
import ChipToggles from '../../ui/ChipToggles';
import DateInput from '../../ui/DateInput';
import Field from '../../ui/Field';
import Modal from '../../ui/Modal';
import Select from '../../ui/Select';
import TextInput from '../../ui/TextInput';
import { useToast } from '../../ui/useToast';
import ExistingClients from './ExistingClients';

const SHOWN_FIELDS = ['name', 'relationship', 'effective_date', 'requested_lines', 'owner_id'];
const DEFAULT_LINE = 'medical';

/**
 * New client (plan.md §8.3), in the old modal's look: creates the client and its first deal, then opens the deal.
 * Status is Prospect or Existing client (§5.1; a New client comes only from a sale or Convert to client); `status`
 * presets it (＋ New deal: Prospect; Clients' ＋ New client: Existing client).
 */
export default function NewClientDialog({ onClose, status }) {
  const { user } = useAuth();
  const meta = useMeta().data;
  const users = useUsers();
  const create = useCreateClient();
  const toast = useToast();
  const navigate = useNavigate();
  const lines = (meta?.lines || []).map((line) => ({ value: line.key, label: line.label }));
  const statuses = creatableStatuses(meta);
  const [form, setForm] = useState(() => ({
    name: '',
    relationship: statuses.some((s) => s.key === status) ? status : statuses[0]?.key || '',
    effective_date: '',
    requested_lines: lines.some((line) => line.value === DEFAULT_LINE) ? [DEFAULT_LINE] : [],
    owner_id: user ? String(user.id) : '',
  }));
  const [nameMissing, setNameMissing] = useState(false);
  const errors = fieldErrors(create.error);
  const formError = formErrorText(create.error, SHOWN_FIELDS);

  const owners = users.data?.length ? users.data : user ? [{ id: user.id, name: user.full_name }] : [];
  const set = (key) => (value) => setForm((current) => ({ ...current, [key]: value }));

  function onSubmit(event) {
    event.preventDefault();
    const name = form.name.trim();
    if (!name) {
      setNameMissing(true);
      event.currentTarget.querySelector('input')?.focus(); // the name field, so the fix starts where the error is
      return;
    }
    create.mutate(
      {
        name,
        relationship: form.relationship || statuses[0]?.key,
        effective_date: form.effective_date || null,
        requested_lines: form.requested_lines,
        owner_id: form.owner_id ? Number(form.owner_id) : null,
      },
      {
        onSuccess: ({ client, deal }) => {
          toast.success(`Created ${client.name}.`);
          onClose();
          navigate(`/deals/${deal.id}`);
        },
      },
    );
  }

  return (
    <Modal
      open
      onClose={onClose}
      title="New client"
      sub="Creates the client and its first deal, then opens the deal."
      onSubmit={onSubmit}
      footer={
        <>
          <Button size="sm" onClick={onClose}>
            Cancel
          </Button>
          <Button size="sm" type="submit" variant="primary" busy={create.isPending}>
            Create
          </Button>
        </>
      }
    >
      <Field label="Client name" required error={nameMissing && !form.name.trim() ? 'Enter the client name.' : errors.name}>
        <TextInput value={form.name} maxLength={200} onChange={(event) => set('name')(event.target.value)} />
      </Field>
      <ExistingClients name={form.name} onOpen={onClose} />
      <Field label="Status" error={errors.relationship}>
        <Select
          value={form.relationship || statuses[0]?.key || ''}
          onChange={(event) => set('relationship')(event.target.value)}
          options={statuses.map((s) => ({ value: s.key, label: s.label }))}
        />
      </Field>
      <Field label="Target effective date" error={errors.effective_date}>
        <DateInput value={form.effective_date} onValueChange={set('effective_date')} />
      </Field>
      <Field label="Lines to quote" group error={errors.requested_lines}>
        <ChipToggles options={lines} value={form.requested_lines} onChange={set('requested_lines')} emptyText="No lines yet." />
      </Field>
      <Field label="Owner" error={errors.owner_id}>
        <Select
          value={form.owner_id}
          onChange={(event) => set('owner_id')(event.target.value)}
          placeholder="Unassigned"
          options={owners.map((person) => ({ value: String(person.id), label: person.name }))}
        />
      </Field>
      {formError && (
        <div role="alert" className="error-message">
          {formError}
        </div>
      )}
    </Modal>
  );
}
