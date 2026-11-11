import { useState } from 'react';
import { Link, useNavigate } from 'react-router';
import { useClients, useCreateClient, useUsers } from '../../api/deals';
import { relationships, useMeta } from '../../api/meta';
import { useAuth } from '../../auth/useAuth';
import { fieldErrors, formErrorText } from '../../lib/errors';
import { useDebouncedValue } from '../../lib/useDebouncedValue';
import Button from '../../ui/Button';
import DateInput from '../../ui/DateInput';
import Field from '../../ui/Field';
import Modal from '../../ui/Modal';
import MultiSelect from '../../ui/MultiSelect';
import Select from '../../ui/Select';
import TextInput from '../../ui/TextInput';
import { useToast } from '../../ui/useToast';
import styles from './NewClientDialog.module.css';

const SHOWN_FIELDS = ['name', 'relationship', 'effective_date', 'requested_lines', 'owner_id'];
const DEFAULT_LINE = 'medical';

// "Already here? Example Co. — open": up to 5 existing clients whose name contains what was typed.
function ExistingClients({ name, onOpen }) {
  const typed = useDebouncedValue(name.trim(), 250);
  const matches = useClients({ q: typed }, { enabled: typed.length >= 2 });
  const rows = typed.length >= 2 ? (matches.data?.results || []).slice(0, 5) : [];
  return (
    <div aria-live="polite" className={styles.existing}>
      {rows.length > 0 && (
        <>
          <p className={styles.existingTitle}>Already here?</p>
          <ul className={styles.existingList}>
            {rows.map((row) => (
              <li key={row.id}>
                {row.name} —{' '}
                <Link to={`/deals/${row.deal.id}`} onClick={onOpen}>
                  open<span className={styles.srOnly}> {row.name}</span>
                </Link>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}

/** New client (plan.md §8.3): creates the client and its first deal, then opens the deal. */
export default function NewClientDialog({ onClose }) {
  const { user } = useAuth();
  const meta = useMeta().data;
  const users = useUsers();
  const create = useCreateClient();
  const toast = useToast();
  const navigate = useNavigate();
  const lines = (meta?.lines || []).map((line) => ({ value: line.key, label: line.label }));
  const [form, setForm] = useState(() => ({
    name: '',
    relationship: 'new',
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
        relationship: form.relationship,
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
      onSubmit={onSubmit}
      footer={
        <>
          <Button onClick={onClose}>Cancel</Button>
          <Button type="submit" variant="primary" busy={create.isPending}>
            Create
          </Button>
        </>
      }
    >
      <Field label="Client name" required error={nameMissing && !form.name.trim() ? 'Enter the client name.' : errors.name}>
        <TextInput value={form.name} maxLength={200} onChange={(event) => set('name')(event.target.value)} />
      </Field>
      <ExistingClients name={form.name} onOpen={onClose} />
      <div className={styles.row}>
        <Field label="Type" error={errors.relationship}>
          <Select
            value={form.relationship}
            onChange={(event) => set('relationship')(event.target.value)}
            options={relationships(meta).map((type) => ({ value: type.key, label: type.label }))}
          />
        </Field>
        <Field label="Target effective date" error={errors.effective_date}>
          <DateInput value={form.effective_date} onValueChange={set('effective_date')} />
        </Field>
      </div>
      <Field label="Lines to quote" error={errors.requested_lines}>
        <MultiSelect
          options={lines}
          value={form.requested_lines}
          onChange={set('requested_lines')}
          label="Lines to quote"
          placeholder="Search lines…"
          emptyText="No lines yet."
        />
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
        <p role="alert" className={styles.error}>
          <span aria-hidden="true">⚠ </span>
          {formError}
        </p>
      )}
    </Modal>
  );
}
