import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import cx from './cx';
import IconButton from './IconButton';
import styles from './Toast.module.css';
import { ToastContext } from './useToast';

const ICONS = { success: '✓', error: '⚠', info: 'ℹ' };
const LABELS = { success: 'Done', error: 'Error', info: 'Note' };
let nextId = 1;

/** The one toast provider (plan.md §3.9). Wrap the app once; components call useToast(). */
export default function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const timers = useRef(new Map());

  const dismiss = useCallback((id) => {
    setToasts((list) => list.filter((toast) => toast.id !== id));
    clearTimeout(timers.current.get(id));
    timers.current.delete(id);
  }, []);

  const show = useCallback(
    (message, { tone = 'success', duration = tone === 'error' ? 8000 : 5000 } = {}) => {
      const id = nextId++;
      setToasts((list) => [...list, { id, message, tone }].slice(-4));
      if (duration) timers.current.set(id, setTimeout(() => dismiss(id), duration));
      return id;
    },
    [dismiss],
  );

  useEffect(() => {
    const pending = timers.current;
    return () => pending.forEach((timer) => clearTimeout(timer));
  }, []);

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
      <section className={styles.region} aria-label="Notifications" aria-live="polite">
        {toasts.map((toast) => (
          <div key={toast.id} className={cx(styles.toast, styles[toast.tone])}>
            <span className={styles.icon} aria-hidden="true">
              {ICONS[toast.tone]}
            </span>
            <p className={styles.message}>
              <span className={styles.srOnly}>{LABELS[toast.tone]}: </span>
              {toast.message}
            </p>
            <IconButton label="Dismiss" size="sm" onClick={() => dismiss(toast.id)}>
              ✕
            </IconButton>
          </div>
        ))}
      </section>
    </ToastContext>
  );
}
