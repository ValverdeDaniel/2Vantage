import { useId, useRef } from 'react';
import cx from './cx';
import IconButton from './IconButton';
import styles from './Modal.module.css';
import { useModalDialog } from './useModalDialog';

/**
 * An accessible modal on the native <dialog> (role=dialog, focus trapped, Escape closes, focus returns on close).
 * Renders nothing while `open` is false, so its contents start fresh each time it opens.
 *   open, onClose, title, children (body), footer (actions, right-aligned), size: 'sm' | 'md' | 'lg'
 *   onSubmit: wraps body + footer in a <form noValidate> so Enter submits (give the main button type="submit")
 *   initialFocus: ref to focus first (default: the first field) · dismissible=false hides ✕ and ignores Escape
 */
export default function Modal({ open, ...props }) {
  return open ? <ModalDialog {...props} /> : null;
}

function ModalDialog({ onClose, title, children, footer, size = 'md', onSubmit, initialFocus, dismissible = true }) {
  const ref = useRef(null);
  const titleId = useId();
  useModalDialog(ref, { initialFocus });

  const content = (
    <>
      <div className={styles.body} data-dialog-body>
        {children}
      </div>
      {footer && <div className={styles.footer}>{footer}</div>}
    </>
  );

  return (
    <dialog
      ref={ref}
      className={cx(styles.dialog, styles[size])}
      aria-labelledby={titleId}
      onCancel={(event) => {
        event.preventDefault();
        if (dismissible) onClose?.();
      }}
    >
      <div className={styles.header}>
        <h2 id={titleId} className={styles.title}>
          {title}
        </h2>
        {dismissible && (
          <IconButton label="Close" onClick={onClose}>
            ✕
          </IconButton>
        )}
      </div>
      {onSubmit ? (
        <form
          noValidate
          className={styles.form}
          onSubmit={(event) => {
            // Never the browser's own submit: it would reload the page and drop the dialog mid-save.
            event.preventDefault();
            onSubmit(event);
          }}
        >
          {content}
        </form>
      ) : (
        content
      )}
    </dialog>
  );
}
