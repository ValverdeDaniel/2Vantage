import { useState } from 'react';
import { useUpdateClient } from '../../api/deals';
import { relationships } from '../../api/meta';
import { fieldErrors, formErrorText } from '../../lib/errors';
import Button from '../../ui/Button';
import Field from '../../ui/Field';
import Modal from '../../ui/Modal';
import Select from '../../ui/Select';
import TextInput from '../../ui/TextInput';
import styles from './Dialogs.module.css';

/** Edit the client's name and type (PATCH clients/{id}/). */
export default function ClientDialog({ deal, meta, onClose }) {
  const update = useUpdateClient(deal);
  const [name, setName] = useState(deal.client.name);
  const [relationship, setRelationship] = useState(deal.client.relationship);
  const [missing, setMissing] = useState(false);
  const errors = fieldErrors(update.error);
  const formError = formErrorText(update.error, ['name', 'relationship']);

  function onSubmit(event) {
    event.preventDefault();
    if (!name.trim()) {
      setMissing(true);
      return;
    }
    update.mutate({ name: name.trim(), relationship }, { onSuccess: onClose });
  }

  return (
    <Modal
      open
      onClose={onClose}
      onSubmit={onSubmit}
      title="Edit client"
      size="sm"
      footer={
        <>
          <Button onClick={onClose}>Cancel</Button>
          <Button type="submit" variant="primary" busy={update.isPending}>
            Save
          </Button>
        </>
      }
    >
      <Field label="Client name" required error={missing && !name.trim() ? 'Enter the client name.' : errors.name}>
        <TextInput value={name} maxLength={200} onChange={(event) => setName(event.target.value)} />
      </Field>
      <Field label="Type" error={errors.relationship}>
        <Select
          value={relationship}
          onChange={(event) => setRelationship(event.target.value)}
          options={relationships(meta).map((type) => ({ value: type.key, label: type.label }))}
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
