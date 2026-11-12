import { useEffect, useRef, useState } from 'react';
import pdfjs from '../../../viewer/pdfjs';

// No document after this long means pdf.js did not start in this browser (the old WATCHDOG_MS).
const WATCHDOG_MS = 20000;

/** The bytes of a base64 string. */
export function bytesOf(base64) {
  const raw = atob(base64);
  const bytes = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i += 1) bytes[i] = raw.charCodeAt(i);
  return bytes;
}

/*
 * The deck preview's PDF, opened with the one pdf.js build (src/viewer/pdfjs.js; plan.md §8.14; J109; the old
 * ExportViewer usePdfDocument at 891f1b3): {doc, failed}. The last document stays open until the next has opened, so a
 * rebuild never blanks the slides on screen (J107: the last copy is kept); `failed` says pdf.js could not open it here.
 */
export default function useDeckDocument(base64) {
  const [state, setState] = useState({ doc: null, failed: false });
  const held = useRef(null);
  useEffect(() => {
    if (!base64) return undefined;
    let cancelled = false;
    const task = pdfjs.getDocument({ data: bytesOf(base64) });
    const watchdog = setTimeout(() => {
      if (!cancelled) setState((now) => ({ ...now, failed: true }));
    }, WATCHDOG_MS);
    task.promise
      .then((doc) => {
        clearTimeout(watchdog);
        if (cancelled) {
          task.destroy();
          return;
        }
        const old = held.current;
        held.current = task;
        setState({ doc, failed: false });
        old?.destroy();
      })
      .catch(() => {
        clearTimeout(watchdog);
        if (!cancelled) setState((now) => ({ ...now, failed: true }));
        task.destroy();
      });
    return () => {
      cancelled = true;
      clearTimeout(watchdog);
    };
  }, [base64]);
  useEffect(
    () => () => {
      held.current?.destroy();
      held.current = null;
    },
    [],
  );
  return state;
}
