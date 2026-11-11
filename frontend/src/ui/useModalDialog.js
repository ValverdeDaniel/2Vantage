import { useEffect } from 'react';

const FIELDS = 'input:not([type="hidden"]):not([disabled]), select:not([disabled]), textarea:not([disabled])';
const FOCUSABLE =
  'button:not([disabled]), [href], input:not([type="hidden"]):not([disabled]), select:not([disabled]), ' +
  'textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

/**
 * Opens a native <dialog> as a modal (focus is trapped and the page behind is inert) and focuses, in order:
 * `initialFocus.current`, an element marked data-autofocus, the first field in the body (when `focusField`),
 * the first focusable element. Focus returns to the element that opened it when the dialog unmounts.
 */
export function useModalDialog(ref, { initialFocus, focusField = true } = {}) {
  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return undefined;
    const previous = document.activeElement;
    if (!dialog.open) dialog.showModal();
    const body = dialog.querySelector('[data-dialog-body]') || dialog;
    const target =
      initialFocus?.current ||
      dialog.querySelector('[data-autofocus]') ||
      (focusField && body.querySelector(FIELDS)) ||
      body.querySelector(FOCUSABLE) ||
      dialog.querySelector(FOCUSABLE);
    target?.focus();
    return () => {
      if (dialog.open) dialog.close();
      if (previous instanceof HTMLElement && previous.isConnected) previous.focus();
    };
  }, [ref, initialFocus, focusField]);
}
