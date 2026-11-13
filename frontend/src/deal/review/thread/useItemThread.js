import { useNote, useResolveNote } from '../../../api/reviewTray';
import { errorText } from '../../../lib/errors';
import { useToast } from '../../../ui/useToast';

/*
 * An item's thread, for the queues and the request page (plan.md §8.8; L22; old 891f1b3 `useItemThread.js`): what
 * NoteThread needs to write. A note goes through `POST review/notes/`: to the team, or to the client now (on the link
 * that asks the item), or — with their question open — as our reply, which closes it; "To client" on an item not out
 * with them (`ask`) puts it in the request tray carrying the note instead. Resolve closes a question or an ask that
 * went out. Each write reads the review screens again (useNote). `propsFor({ref, ask?})` → NoteThread's props.
 */
export default function useItemThread(dealId, { readOnly = false } = {}) {
  const note = useNote(dealId);
  const resolveNote = useResolveNote(dealId);
  const toast = useToast();

  function propsFor({ ref, ask = null }) {
    if (readOnly) return { readOnly: true };
    return {
      clientAsk: ask,
      onSend: async (text, audience, { replyTo = null, ask: asking = false } = {}) => {
        let body = { kind: 'note', ref, text, audience };
        if (replyTo) body = { kind: 'reply', question_id: replyTo, text };
        else if (asking) body = { kind: ask?.kind || 'ask', ref, text };
        try {
          await note.mutateAsync(body);
          if (asking) toast.success('In the request tray with your note: it goes when you send it');
          return true;
        } catch (error) {
          toast.error(errorText(error));
          return false;
        }
      },
      onResolve: async (id) => {
        try {
          await resolveNote.mutateAsync(id);
        } catch (error) {
          toast.error(errorText(error));
        }
      },
    };
  }

  return { propsFor };
}
