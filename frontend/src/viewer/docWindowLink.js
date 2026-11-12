import { useEffect, useRef, useSyncExternalStore } from 'react';

/*
 * The link between a deal page and the window its file pops out into (plan.md §8.16; E69–E71, D128, OQ99; the old
 * shared/docWindowLink.js, D-125). One link per browser tab, named by an id kept in sessionStorage, so a reload of the
 * deal page finds its window again and another tab's window never answers this one. Messages ride a BroadcastChannel
 * of that name, inside this browser only; they carry ids, a page and the value's find, never a file.
 *
 * The deal page's side (this module's state, one per tab):
 * - `openDocWindow` opens or brings forward the window (980×1100); null when the browser blocked it;
 * - `showInDocWindow` says what the Documents tab shows (the file and the value F opened), kept so a window that opens
 *   later gets it at once;
 * - `useDocWindowPresence` is called by every page that shows a client (the deal layout; the client page from its
 *   slice): while one is mounted the window hears `here` with that client; when the last one goes it hears `away`,
 *   after a short grace, so a move between tabs of the same client never reads as leaving (E71).
 * The window's side is deal/documents/useWindowLink.js. Both send a `beat` every BEAT_MS; silence past SILENT_MS means
 * the other side is gone.
 */

export const BEAT_MS = 2000;
export const SILENT_MS = 6500;
const AWAY_GRACE_MS = 400;
const LINK_KEY = 'vantage.docwin.link';

export const channelName = (id) => `vantage-docwin-${id}`;
export const windowPath = (dealId, docId, id) =>
  `/deals/${dealId}/documents/${docId}/window?link=${encodeURIComponent(id)}`;

/** Which client a deal is, and the words the window shows for it: {key, name, dealId, year}. */
export function dealPresence(deal) {
  if (!deal) return null;
  return {
    key: `client:${deal.client.id}`,
    name: deal.client.name || '',
    dealId: deal.id,
    year: deal.effective_date ? String(deal.effective_date).slice(0, 4) : '',
  };
}

function storedLink() {
  try {
    return sessionStorage.getItem(LINK_KEY) || '';
  } catch {
    return '';
  }
}

function newLink() {
  const id = crypto.randomUUID ? crypto.randomUUID() : `${Date.now().toString(36)}${Math.random().toString(36).slice(2)}`;
  try {
    sessionStorage.setItem(LINK_KEY, id);
  } catch {
    /* a private window keeps no storage: the link lasts this page */
  }
  return id;
}

/* ---- The deal page's side ---------------------------------------------------------------------------------------- */

const main = {
  id: '',
  channel: null,
  popped: false,
  windowClient: '', // the client key the open window is for
  lastSeen: 0,
  beatTimer: null,
  awayTimer: null,
  presence: null,
  lastShow: null,
  subs: new Set(),
  poppedSubs: new Set(),
};

function connect(create) {
  if (main.channel) return true;
  const id = storedLink() || (create ? newLink() : '');
  if (!id || typeof BroadcastChannel !== 'function') return false;
  main.id = id;
  main.channel = new BroadcastChannel(channelName(id));
  main.channel.onmessage = (event) => receive(event.data);
  return true;
}

function send(message) {
  if (connect(false)) main.channel.postMessage({ ...message, from: 'main' });
}

const notifyPopped = () => main.poppedSubs.forEach((fn) => fn());

function setPopped(on) {
  if (on && !main.beatTimer) {
    main.beatTimer = window.setInterval(() => {
      send({ type: 'beat', presence: main.presence });
      if (Date.now() - main.lastSeen > SILENT_MS) setPopped(false);
    }, BEAT_MS);
  }
  if (!on && main.beatTimer) {
    window.clearInterval(main.beatTimer);
    main.beatTimer = null;
  }
  if (main.popped !== on) {
    main.popped = on;
    notifyPopped();
  }
}

function receive(message) {
  if (!message || message.from !== 'window') return;
  main.lastSeen = Date.now();
  if (message.type === 'closed') {
    setPopped(false);
  } else {
    if (message.client && message.client !== main.windowClient) {
      main.windowClient = message.client;
      notifyPopped();
    }
    setPopped(true);
    if (message.type === 'hello') {
      send(main.presence ? { type: 'here', ...main.presence } : { type: 'away' });
      if (main.lastShow) send(main.lastShow);
    }
  }
  main.subs.forEach((fn) => fn(message));
}

/** Open, or bring forward, this tab's window on a deal's file. Null when the browser blocked it (E69). */
export function openDocWindow(dealId, docId, clientKey) {
  connect(true);
  const win = window.open(windowPath(dealId, docId, main.id), `vantage-docwin-${main.id}`, 'popup=yes,width=980,height=1100');
  if (win) {
    main.lastSeen = Date.now();
    main.windowClient = clientKey || main.windowClient;
    setPopped(true);
    notifyPopped();
  }
  return win;
}

/** Bring the open window to the front without reloading it; open it afresh when it is gone. */
export function focusDocWindow(dealId, docId) {
  if (!connect(false)) return null;
  const win = window.open('', `vantage-docwin-${main.id}`);
  if (!win) return null;
  try {
    if (win.location.href === 'about:blank') win.location.href = windowPath(dealId, docId, main.id);
  } catch {
    /* not ours to read */
  }
  win.focus?.();
  return win;
}

/** "Bring it back here": the window closes itself and the file shows on the tab again. */
export function closeDocWindow() {
  send({ type: 'close' });
  setPopped(false);
}

export function showInDocWindow(payload) {
  main.lastShow = { type: 'show', ...payload };
  if (main.popped) send(main.lastShow);
}

const subscribePopped = (fn) => {
  main.poppedSubs.add(fn);
  return () => main.poppedSubs.delete(fn);
};

/** Is a window open, and for which client? Re-renders on either changing. */
export function useDocWindow() {
  const popped = useSyncExternalStore(subscribePopped, () => main.popped);
  const windowClient = useSyncExternalStore(subscribePopped, () => main.windowClient);
  return { popped, windowClient };
}

/** What the window says (its page, a key pressed there, a file picked there), while mounted. */
export function useDocWindowMessages(handler) {
  const ref = useRef(handler);
  useEffect(() => {
    ref.current = handler;
  });
  useEffect(() => {
    const fn = (message) => ref.current?.(message);
    main.subs.add(fn);
    return () => {
      main.subs.delete(fn);
    };
  }, []);
}

/* Presence: which client this tab is on (E71). Every mounted caller registers; the newest is announced. When the last
   one unmounts, `away` follows after AWAY_GRACE_MS unless another has mounted by then. A caller still loading (`info`
   null) keeps whatever it said last. Nothing is sent before a window was ever opened in this tab. */
const present = new Map();
let presenceSeq = 0;

function announce() {
  window.clearTimeout(main.awayTimer);
  if (present.size) {
    main.presence = [...present.values()].pop();
    send({ type: 'here', ...main.presence });
    return;
  }
  main.awayTimer = window.setTimeout(() => {
    if (present.size) return;
    const left = main.presence;
    main.presence = null;
    send({ type: 'away', ...(left || {}) });
  }, AWAY_GRACE_MS);
}

export function useDocWindowPresence(info) {
  const token = useRef(0);
  const signature = info ? JSON.stringify(info) : '';
  useEffect(() => {
    if (!token.current) {
      presenceSeq += 1;
      token.current = presenceSeq;
    }
    if (!signature) return;
    present.delete(token.current);
    present.set(token.current, JSON.parse(signature));
    announce();
  }, [signature]);
  useEffect(
    () => () => {
      if (present.delete(token.current)) announce();
    },
    [],
  );
}
