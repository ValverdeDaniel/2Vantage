/*
 * Print… (plan.md §8.14; J115; the old utils/download.js openPrintWindow and printPdfInWindow at 891f1b3, D-196): the
 * window opens on the click itself, before the Letter PDF is built, so a pop-up blocker lets it through; the PDF is then
 * shown in it and the browser's print dialog opened once it has loaded. A window that was blocked, or closed meanwhile,
 * gets nothing: `printPdfInWindow` says false and the caller downloads the file instead, saying why (`BLOCKED`). The
 * browser objects come in `env` (window.open, object URLs, timers, the clock), so the fallback is tested in Vitest.
 */

export const PRINT_WAIT_MS = 15000;
export const BLOCKED = 'Pop-ups are blocked here, so the Letter PDF downloaded instead: open it and print.';
const WAITING = '<p style="font:14px sans-serif;padding:24px">Preparing the pages to print…</p>';

const browser = () => ({
  open: (url, target) => window.open(url, target),
  createUrl: (blob) => URL.createObjectURL(blob),
  revokeUrl: (url) => URL.revokeObjectURL(url),
  later: (fn, ms) => window.setTimeout(fn, ms),
  now: () => Date.now(),
});

/** A window for the pages to print, opened now (call it in the click itself); null when the browser blocked it. */
export function openPrintWindow(env = browser()) {
  const win = env.open('', '_blank');
  try {
    win?.document.write(WAITING);
  } catch {
    /* a window we cannot write to still navigates */
  }
  return win || null;
}

/** Show the PDF `data` in `win` and open its print dialog once it has loaded; false when there is no window to show it
 * in (blocked or closed), when the caller downloads it instead. */
export function printPdfInWindow(win, data, env = browser()) {
  if (!win || win.closed) return false;
  const url = env.createUrl(new Blob([data], { type: 'application/pdf' }));
  win.location.href = url;
  const started = env.now();
  const tryPrint = () => {
    try {
      if (win.closed) return;
      if (win.location.href === url && win.document.readyState === 'complete') {
        win.focus();
        win.print();
        return;
      }
    } catch {
      /* not loaded yet */
    }
    if (env.now() - started < PRINT_WAIT_MS) env.later(tryPrint, 400);
  };
  env.later(tryPrint, 600);
  env.later(() => env.revokeUrl(url), 10 * 60 * 1000);
  return true;
}
