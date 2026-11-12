import { useState } from 'react';
import { useMarkLost } from '../../api/deals';
import { fieldErrors, formErrorText } from '../../lib/errors';
import Button from '../../ui/Button';
import Field from '../../ui/Field';
import Modal from '../../ui/Modal';
import TextInput from '../../ui/TextInput';

const MAX_REASON = 300;

/** Mark as lost (plan.md §5.1): an optional reason of up to 300 characters, as on the old screen ("Why did we lose
 *  it? (optional)"; OQ48). The deal stays editable and can be reopened; a refusal (a sold deal) shows its sentence. */
export default function LostDialog({ deal, onClose }) {
  const markLost = useMarkLost(deal.id);
  const [reason, setReason] = useState('');
  const errors = fieldErrors(markLost.error);
  const formError = formErrorText(markLost.error, ['reason']);

  function onSubmit(event) {
    event.preventDefault();
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
        label="Why did we lose it? (optional)"
        help={`${reason.length} / ${MAX_REASON} characters`}
        error={errors.reason}
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
