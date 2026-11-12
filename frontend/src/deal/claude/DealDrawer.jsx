import { useEffect, useRef } from 'react';
import { useDocuments } from '../../api/documents';
import ChatBar from './ChatBar';
import ClaudeDrawer, { ReadingPicker } from './ClaudeDrawer';
import Composer from './Composer';
import { claudeDoor } from './door';
import DrawerBody from './DrawerBody';
import DrawerNews from './DrawerNews';
import GuidanceBox from './GuidanceBox';
import LockSwitch from './LockSwitch';
import MessageList from './MessageList';
import useAttach from './useAttach';
import useChat from './useChat';

const LOCK_TABS = new Set(['advisor', 'proposal', 'documents']); // the tabs that read into the plan table (old LOCK_PAGES)
const GUIDANCE_TABS = new Set(['advisor', 'proposal']); // the tabs that work the board (the old boardPage)

/*
 * Work with Claude open over a deal tab (plan.md §8.17; D4–D7, D13, D14, D16, D19, D98, D104; the old WorkWithClaude):
 * the drawer with its "Reading" picker; on the plan tables' tabs the lock switch, and on the board's the client
 * guidance; then the panel: the chat, the deal's files, and what Claude is doing and did. Files dropped on a tab before
 * it opened (the Documents zone, D16) are handed to it once it is here. Mounted only while open, so a closed drawer
 * fetches nothing.
 */
export default function DealDrawer({ deal, tab, meta, state, door, kind, kinds, kindLabels, retryFor, onClose }) {
  const documents = useDocuments(deal.id);
  const attach = useAttach({ dealId: deal.id, kind, meta, model: door.model, tab });
  const chat = useChat({ dealId: deal.id, tab, model: door.model, state });
  const attachRef = useRef(attach);
  useEffect(() => {
    attachRef.current = attach;
  });

  useEffect(() => {
    const waiting = claudeDoor.take();
    if (waiting.length) attachRef.current.attach(waiting);
  }, [door.files.length]);

  return (
    <ClaudeDrawer
      headerExtra={
        <ReadingPicker
          kinds={kinds}
          kind={kind}
          meta={meta}
          labels={kindLabels}
          onKind={claudeDoor.setKind}
          disabled={attach.busy}
        />
      }
      onClose={onClose}
    >
      {LOCK_TABS.has(tab) && <LockSwitch dealId={deal.id} lock={state.lock} />}
      {GUIDANCE_TABS.has(tab) && <GuidanceBox dealId={deal.id} state={state} model={door.model} />}
      <DrawerBody
        dealId={deal.id}
        meta={meta}
        state={state}
        kind={kind}
        kinds={kinds}
        files={documents.data || []}
        attach={attach}
        model={door.model}
        onModel={claudeDoor.setModel}
        chat={{
          bar: <ChatBar dealId={deal.id} chat={chat} disabled={chat.busy} />,
          messages: <MessageList dealId={deal.id} chat={chat} meta={meta} state={state} />,
          composer: <Composer chat={chat} locked={Boolean(state.lock)} />,
        }}
      >
        <DrawerNews
          dealId={deal.id}
          state={state}
          meta={meta}
          onDocuments={tab === 'documents'}
          dismissed={door.dismissed}
          retryFor={retryFor}
          files={documents.data || []}
        />
      </DrawerBody>
    </ClaudeDrawer>
  );
}
