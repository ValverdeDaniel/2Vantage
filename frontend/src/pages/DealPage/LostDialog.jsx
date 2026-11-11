import { useState } from 'react';
import { useMarkLost } from '../../api/deals';
import { fieldErrors, formErrorText } from '../../lib/errors';
import Button from '../../ui/Button';
import Field from '../../ui/Field';
import Modal from '../../ui/Modal';
import TextInput from '../../ui/TextInput';
import styles from './Dialogs.module.css';

const MAX_REASON = 300;

/** Mark lost (plan.md §5.1): a reason of 1–300 characters. The deal stays editable and can be reopened. */
export default function LostDialog({ deal, onClose }) {
  const markLost = useMarkLost(deal.id);
  const [reason, setReason] = useState('');
  const [missing, setMissing] = useState(false);
  const errors = fieldErrors(markLost.error);
  const formError = formErrorText(markLost.error, ['reason']);

  function onSubmit(event) {
    event.preventDefault();
    if (!reason.trim()) {
      setMissing(true);
      return;
    }
    markLost.mutate(reason.trim(), { onSuccess: onClose });
  }

  return (
    <Modal
      open
      onClose={onClose}
      onSubmit={onSubmit}
      title={`Mark ${deal.client.name} lost`}
      size="sm"
      footer={
        <>
          <Button onClick={onClose}>Cancel</Button>
          <Button type="submit" variant="danger" busy={markLost.isPending}>
            Mark lost
          </Button>
        </>
      }
    >
      <p className={styles.note}>Everything stays editable, and you can reopen the deal later.</p>
      <Field
        label="Reason"
        required
        help={`${reason.length} / ${MAX_REASON} characters`}
        error={missing && !reason.trim() ? 'Give a reason.' : errors.reason}
      >
        <TextInput multiline maxLength={MAX_REASON} value={reason} onChange={(event) => setReason(event.target.value)} />
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
