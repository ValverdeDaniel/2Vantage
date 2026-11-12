import { useState } from 'react';
import { useMarkLost } from '../../api/deals';
import { fieldErrors, formErrorText } from '../../lib/errors';
import Button from '../../ui/Button';
import Field from '../../ui/Field';
import Modal from '../../ui/Modal';
import TextInput from '../../ui/TextInput';

const MAX_REASON = 300;

/** Mark as lost (plan.md §5.1): a reason of 1–300 characters. The deal stays editable and can be reopened. */
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
      sub="Everything stays editable, and you can reopen the deal later."
      size="sm"
      footer={
        <>
          <Button size="sm" onClick={onClose}>
            Cancel
          </Button>
          <Button size="sm" type="submit" variant="danger" busy={markLost.isPending}>
            Confirm lost
          </Button>
        </>
      }
    >
      <Field
        label="Why did we lose it?"
        required
        help={`${reason.length} / ${MAX_REASON} characters`}
        error={missing && !reason.trim() ? 'Give a reason.' : errors.reason}
      >
        <TextInput multiline maxLength={MAX_REASON} value={reason} onChange={(event) => setReason(event.target.value)} />
      </Field>
      {formError && (
        <div role="alert" className="error-message">
          {formError}
        </div>
      )}
    </Modal>
  );
}
