import { useEffect, useRef, useState } from 'react';
import { BEAT_MS, channelName, SILENT_MS } from '../../viewer/docWindowLink';
import { keyAction, REVIEW_KEYS } from '../../valuereview/keys';

/*
 * The pop-out window's side of its link to the Documents tab that opened it (plan.md §8.16; E70, E71, D128; the old
 * DocumentWindow.jsx's channel; viewer/docWindowLink.js is the tab's side). It says hello, beats every BEAT_MS and hears
 * what the tab shows (`show`), where the tab is (`here`, `away`, or a beat's presence) and `close`. It sends back its
 * page, a file picked here (`open`) and the review keys pressed here — A, I, C, U and F, never E (the editor opens in
 * the other window) — which act on the tab's selection. `client` is this window's client key.
 * → {shown, status: waiting | linked | left | gone, elsewhere (the client the tab moved to), post}.
 */
export default function useWindowLink(link, client) {
  const [shown, setShown] = useState(null); // the tab's last `show`
  // Where the tab is: undefined until it has said, null when it left every client page, else {key, name}.
  const [presence, setPresence] = useState(undefined);
  const [gone, setGone] = useState(false); // the tab went silent
  const channel = useRef(null);
  const mine = useRef('');
  const statusRef = useRef('waiting');

  useEffect(() => {
    mine.current = client || mine.current;
  }, [client]);

  const post = (message) => channel.current?.postMessage({ ...message, from: 'window', client: mine.current });

  useEffect(() => {
    if (!link || typeof BroadcastChannel !== 'function') return undefined;
    const ch = new BroadcastChannel(channelName(link));
    channel.current = ch;
    let lastSeen = 0;
    const said = (p) => setPresence(p && p.key ? { key: p.key, name: p.name || '' } : null);
    ch.onmessage = (event) => {
      const message = event.data;
      if (!message || message.from !== 'main') return;
      lastSeen = Date.now();
      setGone(false);
      if (message.type === 'show') {
        // A file of another client is not this window's to show.
        if (message.client?.key && mine.current && message.client.key !== mine.current) return;
        setShown(message);
      } else if (message.type === 'here') said(message);
      else if (message.type === 'away') said(null);
      else if (message.type === 'beat') said(message.presence);
      else if (message.type === 'close') window.close();
    };
    const send = (type) => ch.postMessage({ type, from: 'window', client: mine.current });
    send('hello');
    const beat = window.setInterval(() => {
      send('beat');
      if (lastSeen && Date.now() - lastSeen > SILENT_MS) setGone(true);
    }, BEAT_MS);
    const bye = () => send('closed');
    window.addEventListener('pagehide', bye);
    return () => {
      window.clearInterval(beat);
      window.removeEventListener('pagehide', bye);
      bye();
      ch.close();
      channel.current = null;
    };
  }, [link]);

  const status = gone
    ? 'gone'
    : presence === undefined || !client
      ? 'waiting'
      : presence && presence.key === client
        ? 'linked'
        : 'left';
  useEffect(() => {
    statusRef.current = status;
  }, [status]);

  // The review keys pressed here act on the tab's selection, while linked.
  useEffect(() => {
    const onKey = (event) => {
      const action = keyAction(event, REVIEW_KEYS);
      if (!action || statusRef.current !== 'linked') return;
      event.preventDefault();
      channel.current?.postMessage({ type: 'key', key: event.key.toLowerCase(), from: 'window', client: mine.current });
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  const elsewhere = presence && client && presence.key !== client ? presence.name : '';
  return { shown, status, elsewhere, post };
}
