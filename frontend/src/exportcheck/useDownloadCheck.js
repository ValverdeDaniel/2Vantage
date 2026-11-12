import { useCallback, useRef, useState } from 'react';
import { errorText } from '../lib/errors';

/*
 * The check before a download (G65, G66, K69, K70; the old useExportCheck): `run` reads the check for what is about
 * to go out and opens the modal; `download` sends the report's `ack` with the file request. When the file changed
 * since the modal opened, the server answers 409 with the fresh report and the modal shows that one instead, so a new
 * problem is never sent unseen. Count and warn: nothing is refused.
 *   run({label, check: () => report, download: (ack) => file name})
 *   state: {request, report, loading, busy, error, stale} | null
 */
export default function useDownloadCheck({ onDone } = {}) {
  const [state, setState] = useState(null);
  const live = useRef(null);
  live.current = state;

  const close = useCallback(() => setState(null), []);

  const run = useCallback(async (request) => {
    setState({ request, report: null, loading: true, busy: false, error: '', stale: false });
    try {
      const report = await request.check();
      setState((s) => (s?.request === request ? { ...s, report, loading: false } : s));
    } catch (error) {
      setState((s) => (s?.request === request ? { ...s, loading: false, error: errorText(error) } : s));
    }
  }, []);

  const download = useCallback(async () => {
    const s = live.current;
    if (!s?.report) return;
    setState({ ...s, busy: true, error: '' });
    try {
      const name = await s.request.download(s.report.ack);
      setState(null);
      onDone?.(name);
    } catch (error) {
      const fresh = error?.response?.status === 409 ? error.response.data?.report : null;
      if (fresh) setState({ ...s, report: fresh, busy: false, stale: true });
      else setState({ ...s, busy: false, error: errorText(error) });
    }
  }, [onDone]);

  return { state, run, download, close };
}
