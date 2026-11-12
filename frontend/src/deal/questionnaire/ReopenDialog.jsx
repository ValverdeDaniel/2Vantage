import { useState } from 'react';
import { useReopen } from '../../api/questionnaire';
import { errorText } from '../../lib/errors';
import Modal from '../../ui/Modal';
import { useToast } from '../../ui/useToast';

/*
 * "Reopen the form" (G54; OQ55: any user, with a reason). The reason stays on the form; both signatures clear, and
 * the prefill nobody confirmed goes live again. The signed copy, once slice 43 files one, stays in Documents.
 */
export default function ReopenDialog({ deal, form, open, onClose }) {
  const toast = useToast();
  const reopen = useReopen(deal.id, form);
  const [reason, setReason] = useState('');
  const submit = () => {
    if (!reason.trim()) return;
    reopen.mutate(reason, {
      onSuccess: () => {
        toast.success('The form is open again');
        setReason('');
        onClose();
      },
    });
  };
  return (
    <Modal
      open={open}
      onClose={onClose}
      size="sm"
      title="Reopen the form"
      sub="The signatures clear and the form can be edited again. Say why; the reason stays with the form."
      onSubmit={submit}
      footer={
        <>
          <button type="button" className="btn btn-secondary btn-sm" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="btn btn-primary btn-sm" disabled={!reason.trim() || reopen.isPending}>
            Reopen the form
          </button>
        </>
      }
    >
      <textarea
        className="bnf-intake-input"
        rows={3}
        maxLength={300}
        aria-label="Why the form is reopened"
        value={reason}
        onChange={(event) => setReason(event.target.value)}
      />
      {reopen.isError && (
        <div role="alert" className="error-message bb-mt">
          {errorText(reopen.error)}
        </div>
      )}
    </Modal>
  );
}
