import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { ToastContext } from './useToast';

/**
 * The one toast provider (plan.md §3.9, §8.22), in the old look: one `bb-toast` at the foot of the screen, the newest
 * replacing the last; errors in the error colour (`bb-toast-error`). A click dismisses it. Wrap the app once;
 * components call useToast().
 */
export default function ToastProvider({ children }) {
  const [toast, setToast] = useState(null);
  const timer = useRef(null);
  const nextId = useRef(1);

  const dismiss = useCallback((id) => {
    setToast((current) => (current && (id === undefined || current.id === id) ? null : current));
  }, []);

  const show = useCallback(
    (message, { tone = 'success', duration = tone === 'error' ? 8000 : 5000 } = {}) => {
      const id = nextId.current++;
      clearTimeout(timer.current);
      setToast({ id, message, tone });
      if (duration) timer.current = setTimeout(() => dismiss(id), duration);
      return id;
    },
    [dismiss],
  );

  useEffect(() => () => clearTimeout(timer.current), []);

  const value = useMemo(
    () => ({
      show,
      dismiss,
      success: (message, options) => show(message, { ...options, tone: 'success' }),
      error: (message, options) => show(message, { ...options, tone: 'error' }),
      info: (message, options) => show(message, { ...options, tone: 'info' }),
    }),
    [show, dismiss],
  );

  return (
    <ToastContext value={value}>
      {children}
      {toast &&
        createPortal(
          <div
            key={toast.id}
            className={toast.tone === 'error' ? 'bb-toast bb-toast-error' : 'bb-toast'}
            role={toast.tone === 'error' ? 'alert' : 'status'}
            onClick={() => dismiss(toast.id)}
          >
            {toast.message}
          </div>,
          document.body,
        )}
    </ToastContext>
  );
}
