import { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useSendFiles } from '../../api/ai';
import { documentsKey, uploadDocument } from '../../api/documents';
import { errorText, formErrorText } from '../../lib/errors';
import { useToast } from '../../ui/useToast';
import { sentToast } from './drawerWords';

/*
 * Attaching files to Claude (plan.md §8.17; D16, D17, D43; the old ScanChat's handleAttach and attachDropped): the 📎
 * button, a drop on the drawer and a drop on the Documents tab all come here, so the stamp and the read cannot differ.
 * - With a kind (the drawer's "Reading" pick, D5) each file is uploaded filed as it — a file whose extension the kind
 *   does not take is left out and said, as a file picker would — and the files just attached are read at once:
 *   attaching is the request (one send, `deals/{id}/ai/sends/`). A drop is never refused while Claude works: the read
 *   queues behind the job ahead.
 * - With no kind (Documents, Overview, a tab whose reader is not set up) each file first says what it is in the
 *   "File as" list; "Upload N files ▸" files them and sends them in one go, each read by its own reader in the send
 *   order (census, questionnaire, intake, then the plans) and the rest only filed.
 * `ensureDeal()` makes the deal first when there is none yet (the quote-first door, D43); `onSent(dealId, sent)` then
 * says where the reads went.
 */
function extension(name) {
  const dot = String(name || '').lastIndexOf('.');
  return dot >= 0 ? name.slice(dot).toLowerCase() : '';
}

export default function useAttach({ dealId, ensureDeal, kind, meta, model, onSent, tab = '' }) {
  const toast = useToast();
  const queryClient = useQueryClient();
  const send = useSendFiles();
  const [pending, setPending] = useState([]);
  const [busy, setBusy] = useState(false);

  async function theDeal() {
    return dealId || (ensureDeal ? await ensureDeal() : null);
  }

  async function sendDocs(id, docs) {
    queryClient.invalidateQueries({ queryKey: documentsKey(id) });
    try {
      const sent = await send.mutateAsync({ dealId: id, documentIds: docs.map((doc) => doc.id), model, tab });
      toast.success(sentToast(docs.length, sent));
      onSent?.(id, sent);
    } catch (error) {
      toast.error(`Filed ${docs.length} file${docs.length === 1 ? '' : 's'}, but Claude could not start: ${errorText(error)}`);
    }
  }

  async function attach(files) {
    const list = Array.from(files || []);
    if (!list.length) return;
    if (!kind) {
      setPending((now) => [...now, ...list.map((file) => ({ file, kind: '' }))]);
      return;
    }
    const accept = meta?.document_kinds?.find((entry) => entry.key === kind)?.accept || [];
    const ok = list.filter((file) => !accept.length || accept.includes(extension(file.name)));
    const refused = list.filter((file) => !ok.includes(file));
    if (refused.length) {
      toast.error(`Not attached: ${refused.map((file) => file.name).join(', ')} (this takes ${accept.join(', ')}).`);
    }
    if (!ok.length) return;
    setBusy(true);
    try {
      const id = await theDeal();
      if (!id) return;
      const docs = [];
      const failed = [];
      for (const file of ok) {
        try {
          docs.push(await uploadDocument(id, { file, kind }));
        } catch (error) {
          failed.push(`${file.name} (${formErrorText(error)})`);
        }
      }
      if (failed.length) toast.error(`Not attached: ${failed.join('; ')}`);
      if (docs.length) await sendDocs(id, docs);
    } catch (error) {
      toast.error(errorText(error));
    } finally {
      setBusy(false);
    }
  }

  // The "File as" list's upload: one file under the kind the person picked (FileAsList calls it per row).
  const uploader = {
    mutateAsync: async (fields) => uploadDocument(await theDeal(), fields),
  };

  return {
    attach,
    pending,
    setPending,
    uploader,
    filed: async (docs) => docs.length && sendDocs(await theDeal(), docs),
    read: async (docs) => {
      setBusy(true);
      try {
        await sendDocs(await theDeal(), docs);
      } finally {
        setBusy(false);
      }
    },
    busy: busy || send.isPending,
  };
}
