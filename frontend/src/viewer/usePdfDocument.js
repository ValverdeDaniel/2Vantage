import { useEffect, useState } from 'react';
import pdfjs from './pdfjs';

/*
 * One PDF, loaded for the viewer (plan.md §8.16; E22). From a URL (same origin, so the session cookie goes with it;
 * the whole file, `disableRange`, ch. 38) or from bytes (a blob the caller already holds). The last six files stay in
 * memory as bytes, keyed by URL, so moving between values and files never downloads a 300-page proposal again; the
 * server's no-store keeps them out of every disk cache. No bytes for 20 s means the viewer did not start: say so.
 */

const STALL_MS = 20000;
const CACHE_MAX = 6;
const CACHE_FILE_BYTES = 80 * 1024 * 1024;
const CACHE_TOTAL_BYTES = 160 * 1024 * 1024;
const STALLED =
  'Could not load the PDF: the viewer did not start in this browser. Reload the page, or download the file instead.';
const cache = new Map();

function cached(key) {
  const bytes = cache.get(key);
  if (!bytes) return null;
  cache.delete(key);
  cache.set(key, bytes);
  return bytes;
}

function keep(key, bytes) {
  if (!bytes || bytes.byteLength > CACHE_FILE_BYTES) return;
  cache.delete(key);
  cache.set(key, bytes);
  const total = () => [...cache.values()].reduce((sum, b) => sum + b.byteLength, 0);
  while (cache.size > CACHE_MAX || (cache.size > 1 && total() > CACHE_TOTAL_BYTES)) {
    cache.delete(cache.keys().next().value);
  }
}

/** The words for a load that failed: a lapsed sign-in is said as such. */
function failure(err) {
  if (err?.status === 401 || err?.status === 403) {
    return 'Your sign-in has expired: reload the page and sign in again to see this file.';
  }
  return `Could not load the PDF (${err?.message || 'unknown error'}).`;
}

/** {pdf, error, progress: {loaded, total} | null} for a URL or bytes (`data`). */
export default function usePdfDocument({ url, data }) {
  const source = url || data || null;
  // Each answer is tagged with the source it answers, so a new file never shows the last one's pages or error.
  const [state, setState] = useState({ source: null, pdf: null, error: '', progress: null });

  useEffect(() => {
    if (!source) return undefined;
    let cancelled = false;
    const key = url || '';
    const bytes = data || (key && cached(key));
    const update = (change) =>
      !cancelled && setState((s) => ({ ...(s.source === source ? s : { source }), ...change }));
    // A copy of the bytes: pdf.js hands its data to the worker.
    const from = bytes ? { data: bytes.slice(0) } : { url, disableRange: true, withCredentials: true };
    const task = pdfjs.getDocument(from);
    let stall = null;
    const arm = () => {
      clearTimeout(stall);
      stall = setTimeout(() => update({ error: STALLED }), STALL_MS);
    };
    arm();
    if (!bytes) {
      task.onProgress = ({ loaded, total }) => {
        arm();
        update({ progress: { loaded, total: total || 0 } });
      };
    }
    task.promise
      .then((pdf) => {
        clearTimeout(stall);
        update({ pdf, error: '', progress: null });
        if (!bytes && key) pdf.getData().then((got) => keep(key, got)).catch(() => {});
      })
      .catch((err) => {
        clearTimeout(stall);
        update({ pdf: null, error: failure(err), progress: null });
      });
    return () => {
      cancelled = true;
      clearTimeout(stall);
      task.destroy();
    };
  }, [source, url, data]);

  if (state.source !== source) return { pdf: null, error: '', progress: null };
  return { pdf: state.pdf || null, error: state.error || '', progress: state.progress || null };
}

export const megabytes = (n) => (n / (1024 * 1024)).toFixed(n < 10 * 1024 * 1024 ? 1 : 0);
