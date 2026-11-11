import { useId, useRef } from 'react';
import styles from './Drawer.module.css';
import IconButton from './IconButton';
import { useModalDialog } from './useModalDialog';

/**
 * A side panel sliding in from the right, on the native <dialog> (focus trapped, Escape closes).
 *   open, onClose, title, children, footer, width (CSS length, default 420px)
 * Focus starts on the first focusable element in the body, else the ✕ button.
 */
export default function Drawer({ open, ...props }) {
  return open ? <DrawerPanel {...props} /> : null;
}

function DrawerPanel({ onClose, title, children, footer, width = '420px' }) {
  const ref = useRef(null);
  const titleId = useId();
  useModalDialog(ref, { focusField: false });

  return (
    <dialog
      ref={ref}
      className={styles.drawer}
      style={{ '--drawer-width': width }}
      aria-labelledby={titleId}
      onCancel={(event) => {
        event.preventDefault();
        onClose?.();
      }}
      onMouseDown={(event) => {
        // A press on the backdrop (outside the panel) closes it.
        if (event.target === event.currentTarget) onClose?.();
      }}
    >
      <div className={styles.header}>
        <h2 id={titleId} className={styles.title}>
          {title}
        </h2>
        <IconButton label="Close" onClick={onClose}>
          ✕
        </IconButton>
      </div>
      <div className={styles.body} data-dialog-body>
        {children}
      </div>
      {footer && <div className={styles.footer}>{footer}</div>}
    </dialog>
  );
}
