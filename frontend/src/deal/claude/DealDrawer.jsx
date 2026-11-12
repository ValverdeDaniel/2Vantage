import { useEffect, useRef } from 'react';
import { useDocuments } from '../../api/documents';
import ClaudeDrawer, { ReadingPicker } from './ClaudeDrawer';
import { claudeDoor } from './door';
import DrawerBody from './DrawerBody';
import DrawerNews from './DrawerNews';
import useAttach from './useAttach';

/*
 * Work with Claude open over a deal tab (plan.md §8.17; D4, D5, D13, D14, D16; the old WorkWithClaude): the drawer with
 * its "Reading" picker, the panel with the deal's files, and what Claude is doing and did. Files dropped on a tab
 * before it opened (the Documents zone, D16) are handed to it once it is here. Mounted only while open, so a closed
 * drawer fetches nothing.
 */
export default function DealDrawer({ deal, tab, meta, state, door, kind, kinds, retryFor, onClose }) {
  const documents = useDocuments(deal.id);
  const attach = useAttach({ dealId: deal.id, kind, meta, model: door.model });
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
        <ReadingPicker kinds={kinds} kind={kind} meta={meta} onKind={claudeDoor.setKind} disabled={attach.busy} />
      }
      onClose={onClose}
    >
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
