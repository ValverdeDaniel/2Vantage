import { useRef } from 'react';
import { errorText } from '../lib/errors';
import Button from './Button';
import Modal from './Modal';

/**
 * "Are you sure?" Focus starts on Cancel; Escape cancels.
 *   open, title, message, confirmLabel='Confirm', cancelLabel='Cancel', tone: 'primary' | 'danger',
 *   busy (confirm disabled while it runs), error (shown under the message), onConfirm, onCancel
 */
export default function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  tone = 'primary',
  busy = false,
  error,
  onConfirm,
  onCancel,
}) {
  const cancelRef = useRef(null);
  return (
    <Modal
      open={open}
      onClose={onCancel}
      title={title}
      size="sm"
      initialFocus={cancelRef}
      footer={
        <>
          <Button ref={cancelRef} size="sm" onClick={onCancel} disabled={busy}>
            {cancelLabel}
          </Button>
          <Button size="sm" variant={tone === 'danger' ? 'danger' : 'primary'} busy={busy} onClick={onConfirm}>
            {confirmLabel}
          </Button>
        </>
      }
    >
      {message && <p className="bb-subtitle">{message}</p>}
      {error && (
        <div role="alert" className="error-message bb-mt">
          {errorText(error)}
        </div>
      )}
    </Modal>
  );
}
