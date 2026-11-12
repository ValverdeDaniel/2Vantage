import { describe, expect, it, vi } from 'vitest';
import { openPrintWindow, PRINT_WAIT_MS, printPdfInWindow } from './printPdf';

// A fake browser: window.open, object URLs, timers run by hand, and a clock.
function fakeEnv({ opens = true } = {}) {
  const timers = [];
  const env = {
    clock: 0,
    revoked: [],
    open: vi.fn(() => (opens ? fakeWindow() : null)),
    createUrl: vi.fn(() => 'blob:letter'),
    revokeUrl: (url) => env.revoked.push(url),
    later: (fn, ms) => timers.push({ fn, at: env.clock + ms }),
    now: () => env.clock,
    run(ms) {
      env.clock += ms;
      const due = timers.filter((t) => t.at <= env.clock);
      due.forEach((t) => timers.splice(timers.indexOf(t), 1));
      due.forEach((t) => t.fn());
    },
  };
  return env;
}

function fakeWindow() {
  const win = { closed: false, written: '', location: { href: 'about:blank' }, focus: vi.fn(), print: vi.fn() };
  win.document = {
    readyState: 'loading',
    write: (text) => {
      win.written += text;
    },
  };
  return win;
}

describe('J115 Print… opens its window on the click and falls back to a download', () => {
  it('opens a window at once and says the pages are coming', () => {
    const env = fakeEnv();
    const win = openPrintWindow(env);
    expect(env.open).toHaveBeenCalledWith('', '_blank');
    expect(win.written).toMatch(/Preparing the pages to print/);
  });

  it('answers null when the pop-up was blocked, and printing into no window says false (download instead)', () => {
    const env = fakeEnv({ opens: false });
    const win = openPrintWindow(env);
    expect(win).toBeNull();
    expect(printPdfInWindow(win, new Uint8Array([37, 80, 68, 70]), env)).toBe(false);
    expect(env.createUrl).not.toHaveBeenCalled();
  });

  it('says false for a window closed while the file was built', () => {
    const env = fakeEnv();
    const win = fakeWindow();
    win.closed = true;
    expect(printPdfInWindow(win, new Uint8Array([1]), env)).toBe(false);
  });

  it('shows the PDF in the window and opens the print dialog once it has loaded', () => {
    const env = fakeEnv();
    const win = fakeWindow();
    expect(printPdfInWindow(win, new Uint8Array([37, 80, 68, 70]), env)).toBe(true);
    expect(win.location.href).toBe('blob:letter');
    expect(env.createUrl.mock.calls[0][0].type).toBe('application/pdf');
    env.run(600);
    expect(win.print).not.toHaveBeenCalled(); // still loading: it tries again
    win.document.readyState = 'complete';
    env.run(400);
    expect(win.focus).toHaveBeenCalled();
    expect(win.print).toHaveBeenCalledTimes(1);
    env.run(10 * 60 * 1000);
    expect(env.revoked).toEqual(['blob:letter']);
  });

  it('stops trying after the wait when the window never loads', () => {
    const env = fakeEnv();
    const win = fakeWindow();
    printPdfInWindow(win, new Uint8Array([1]), env);
    for (let ms = 0; ms <= PRINT_WAIT_MS + 1000; ms += 400) env.run(400);
    win.document.readyState = 'complete';
    env.run(400);
    expect(win.print).not.toHaveBeenCalled();
  });
});
