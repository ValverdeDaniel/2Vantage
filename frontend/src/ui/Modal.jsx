import { useId, useRef } from 'react';
import { createPortal } from 'react-dom';
import cx from './cx';
import { useModalLayer } from './useModalLayer';

// The old modal (SavedFilterBar, ProposalShareModal): .progress-overlay centres a .bb-modal; sm is the 480 px one.
const SIZES = { sm: 'bnf-saved-modal', md: '', lg: '' };

/**
 * An accessible modal in the old look: a dialog over a dimmed page (the app behind is inert), Escape and a press on
 * the backdrop close it, focus returns on close. Renders nothing while `open` is false, so it starts fresh each time.
 *   open, onClose, title, sub (the grey line under the title), children (body), footer (the action buttons),
 *   hint (the footer's grey note), size: 'sm' | 'md' | 'lg'
 *   onSubmit: the dialog is a <form noValidate> so Enter submits (give the main button type="submit")
 *   initialFocus: ref to focus first (default: the first field) · dismissible=false ignores Escape and the backdrop
 */
export default function Modal({ open, ...props }) {
  return open ? <ModalLayer {...props} /> : null;
}

function ModalLayer({
  onClose,
  title,
  sub,
  children,
  footer,
  hint,
  size = 'md',
  onSubmit,
  initialFocus,
  dismissible = true,
}) {
  const ref = useRef(null);
  const titleId = useId();
  useModalLayer(ref, { initialFocus, onEscape: dismissible ? onClose : undefined });

  const Shell = onSubmit ? 'form' : 'div';
  const formProps = onSubmit
    ? {
        noValidate: true,
        onSubmit: (event) => {
          // Never the browser's own submit: it would reload the page and drop the dialog mid-save.
          event.preventDefault();
          onSubmit(event);
        },
      }
    : {};

  return createPortal(
    <div
      className="progress-overlay"
      onMouseDown={(event) => {
        if (dismissible && event.target === event.currentTarget) onClose?.();
      }}
    >
      <Shell
        ref={ref}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className={cx('bb-modal', SIZES[size])}
        {...formProps}
      >
        <div className="bb-modal-header">
          <div>
            <div id={titleId} className="bb-modal-title">
              {title}
            </div>
            {sub && <div className="bb-modal-sub">{sub}</div>}
          </div>
        </div>
        <div className="bb-request-form" data-dialog-body>
          {children}
        </div>
        {footer && (
          <div className="bb-modal-footer">
            <span className="bb-modal-footer-hint">{hint}</span>
            <span className="bb-custom-actions">{footer}</span>
          </div>
        )}
      </Shell>
    </div>,
    document.body,
  );
}
