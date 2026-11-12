import { useState } from 'react';
import { useAddToBook, useClientPick } from '../../api/commission';
import { creatableStatuses, useMeta } from '../../api/meta';
import CompInput from '../../deal/shared/CompInput';
import { fieldErrors, formErrorText } from '../../lib/errors';
import { useDebouncedValue } from '../../lib/useDebouncedValue';
import Button from '../../ui/Button';
import DateInput from '../../ui/DateInput';
import Field from '../../ui/Field';
import Modal from '../../ui/Modal';
import Select from '../../ui/Select';
import TextInput from '../../ui/TextInput';
import { useToast } from '../../ui/useToast';

/*
 * Add to book (plan.md §8.18; H58, H112), in the New client dialog's look: a line the agency is paid on that was sold
 * outside the app. The client is found first among the existing ones (archived ones and clients with no deal too); a
 * new outside client is created with no deal and a Status, Existing client by default (§5.1: a client is created as a
 * Prospect or an Existing client). The year with us is optional: earlier records decide, then this, else "year
 * unknown" (OQ72). The server cleans every value and books it.
 */
const TEXT_FIELDS = [
  ['carrier', 'Carrier'],
  ['plan_label', 'Plan'],
  ['premium_annual', 'Premium / yr'],
  ['employees', 'Enrolled (for PEPM)'],
  ['policy_number', 'Policy number'],
  ['year_number', 'Year with us'],
];
const SHOWN = ['client', 'client_name', 'relationship', 'line', 'rate', 'effective_date', ...TEXT_FIELDS.map(([k]) => k)];

export default function AddToBookDialog({ onClose, onAdded }) {
  const toast = useToast();
  const meta = useMeta().data;
  const add = useAddToBook();
  const statuses = creatableStatuses(meta);
  const [search, setSearch] = useState('');
  const [client, setClient] = useState(null);
  const [status, setStatus] = useState('existing_client');
  const [form, setForm] = useState({ line: 'medical', rate: null, effective_date: '' });
  const found = useClientPick(useDebouncedValue(search, 300));
  const errors = fieldErrors(add.error);
  const formError = formErrorText(add.error, SHOWN);
  const set = (key) => (value) => setForm((current) => ({ ...current, [key]: value }));

  function onSubmit() {
    const who = client ? { client: client.id } : { client_name: search.trim(), relationship: status };
    const facts = Object.fromEntries(Object.entries(form).filter(([, value]) => value !== '' && value != null));
    add.mutate(
      { ...who, ...facts },
      {
        onSuccess: (answer) => {
          toast.success('Added to the book');
          onAdded?.(answer.record);
          onClose();
        },
      },
    );
  }

  return (
    <Modal
      open
      onClose={onClose}
      onSubmit={onSubmit}
      title="Add to book"
      sub="Book a line sold outside the app. Search the clients first, or type a new client's name."
      footer={
        <>
          <Button size="sm" onClick={onClose}>
            Cancel
          </Button>
          <Button size="sm" type="submit" variant="primary" busy={add.isPending}>
            Add to book
          </Button>
        </>
      }
    >
      <Field label="Client" required error={errors.client || errors.client_name}>
        {client ? (
          <div className="bnf-com-row">
            <strong>{client.name}</strong>
            {client.archived ? <span className="bb-drop-meta"> (archived)</span> : null}{' '}
            <button type="button" className="bnf-linklike" onClick={() => setClient(null)}>
              change
            </button>
          </div>
        ) : (
          <TextInput
            value={search}
            maxLength={200}
            placeholder="Search clients, or type a new client name"
            onChange={(event) => setSearch(event.target.value)}
          />
        )}
      </Field>
      {!client && (found.data || []).length > 0 && (
        <div className="bnf-com-row">
          {found.data.map((row) => (
            <button key={row.id} type="button" className="bnf-linklike" onClick={() => setClient(row)}>
              {row.name}
              {row.archived ? ' (archived)' : ''}
            </button>
          ))}
        </div>
      )}
      {!client && search.trim() && (
        <Field label="New client's status" error={errors.relationship}>
          <Select
            value={status}
            onChange={(event) => setStatus(event.target.value)}
            options={statuses.map((entry) => ({ value: entry.key, label: entry.label }))}
          />
        </Field>
      )}
      <Field label="Line" required error={errors.line}>
        <Select
          value={form.line}
          onChange={(event) => set('line')(event.target.value)}
          options={(meta?.lines || []).map((line) => ({ value: line.key, label: line.label }))}
        />
      </Field>
      <Field label="Rate" group error={errors.rate}>
        <CompInput value={form.rate} types={meta?.commission_types || []} onCommit={set('rate')} />
      </Field>
      <Field label="Effective date" error={errors.effective_date}>
        <DateInput value={form.effective_date} onValueChange={set('effective_date')} />
      </Field>
      {TEXT_FIELDS.map(([key, label]) => (
        <Field key={key} label={label} error={errors[key]}>
          <TextInput value={form[key] ?? ''} onChange={(event) => set(key)(event.target.value)} />
        </Field>
      ))}
      {formError && (
        <div role="alert" className="error-message">
          {formError}
        </div>
      )}
    </Modal>
  );
}
