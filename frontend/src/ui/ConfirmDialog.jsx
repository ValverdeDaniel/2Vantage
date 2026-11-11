import { useRef } from 'react';
import { errorText } from '../lib/errors';
import Button from './Button';
import styles from './ConfirmDialog.module.css';
import Modal from './Modal';

/**
 * "Are you sure?" Focus starts on Cancel; Escape cancels.
 *   open, title, message, confirmLabel='Confirm', cancelLabel='Cancel', tone: 'primary' | 'danger',
 *   busy (confirm shows a spinner), error (shown under the message), onConfirm, onCancel
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
          <Button ref={cancelRef} onClick={onCancel} disabled={busy}>
            {cancelLabel}
          </Button>
          <Button variant={tone === 'danger' ? 'danger' : 'primary'} busy={busy} onClick={onConfirm}>
            {confirmLabel}
          </Button>
        </>
      }
    >
      {message && <p className={styles.message}>{message}</p>}
      {error && (
        <p role="alert" className={styles.error}>
          <span aria-hidden="true">⚠ </span>
          {errorText(error)}
        </p>
      )}
    </Modal>
  );
}
