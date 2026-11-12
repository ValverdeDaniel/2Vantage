import { useEffect } from 'react';
import { useToast } from '../../ui/useToast';
import {
  closeDocWindow,
  dealPresence,
  focusDocWindow,
  openDocWindow,
  showInDocWindow,
  useDocWindow,
  useDocWindowMessages,
} from '../../viewer/docWindowLink';

/*
 * The Documents tab's side of the pop-out window (plan.md §8.16; E69–E71, D128, OQ99; the old DocumentsTab's D-125
 * wiring). While a window is open for this client, the viewer here gives way to a slim bar and the scanned data takes
 * the width; the window shows what this tab shows (`show`: the file, the value F opened and its find, the files the
 * scanned data is about), and sends back its page, a file picked there and the review keys pressed there. A relayed
 * key is pressed here, on this window, so it acts on whatever selection the keys act on (the List or the Grid); E never
 * comes (the window does not relay it).
 * `shown` is the file on screen, `show` what goes to the window ({find, what, scope, jumpKey}); `on.page(docId, page)`
 * and `on.open(docId)` are the tab's.
 */
export default function useStationWindow({ deal, shown, show, on }) {
  const toast = useToast();
  const presence = dealPresence(deal);
  const docWin = useDocWindow();
  const popped = docWin.popped && docWin.windowClient === presence.key;
  const signature = JSON.stringify([shown?.id ?? null, show]);

  useEffect(() => {
    showInDocWindow({
      dealId: deal.id,
      client: { key: presence.key, name: presence.name },
      docId: shown?.id ?? null,
      ...JSON.parse(signature)[1],
    });
  }, [deal.id, presence.key, presence.name, shown?.id, signature]);

  useDocWindowMessages((message) => {
    if (!popped) return;
    if (message.type === 'page' && message.docId === shown?.id) on.page(message.docId, message.page);
    else if (message.type === 'key') window.dispatchEvent(new KeyboardEvent('keydown', { key: message.key }));
    else if (message.type === 'open') on.open(Number(message.docId));
  });

  return {
    popped,
    popOut: () => {
      if (!openDocWindow(deal.id, shown?.id, presence.key)) {
        toast.error('Your browser blocked the new window — allow pop-ups for this site, then try again.');
      }
    },
    focus: () => focusDocWindow(deal.id, shown?.id),
    bringBack: closeDocWindow,
  };
}
