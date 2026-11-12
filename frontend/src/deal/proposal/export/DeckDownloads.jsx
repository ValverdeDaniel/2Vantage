import { useRef, useState } from 'react';
import api from '../../../api/client';
import { downloadFile, filenameFrom, parseBlobError, saveBlob } from '../../../lib/download';
import { errorText } from '../../../lib/errors';
import { useToast } from '../../../ui/useToast';
import { BLOCKED, openPrintWindow, printPdfInWindow } from './printPdf';

/*
 * A page file's downloads on the deck view's toolbar (plan.md §8.14; J115; the old ExportViewer runDownload at
 * 891f1b3): ⬇ Download PowerPoint and ⬇ Download PDF are the builder's own files; Paper has Print… and ⬇ Download
 * Letter PDF, both the PDF on US Letter (`files/letter/`). Print… opens its window on the click, before the file is
 * built, so a pop-up blocker lets it through, then shows the file in it with the print dialog; when the window was
 * blocked the file downloads instead and a toast says why. One file at a time: a second click while one builds is
 * answered with a toast. Each download writes its `downloaded` row on the server, as the builder's do.
 */
export default function DeckDownloads({ dealId, what }) {
  const toast = useToast();
  const working = useRef(false);
  const [busy, setBusy] = useState(false);

  async function run(d) {
    if (working.current) {
      toast.info('Already working on that — one moment.');
      return;
    }
    const win = d.print ? openPrintWindow() : null;
    working.current = true;
    setBusy(true);
    const url = `deals/${dealId}/proposal/files/${d.path}/`;
    const fallbackName = `Proposal${d.path === 'pptx' ? '.pptx' : '.pdf'}`;
    try {
      if (!d.print) {
        await downloadFile(url, { fallbackName });
        return;
      }
      const response = await api.get(url, { responseType: 'blob' }).catch(async (error) => {
        throw await parseBlobError(error);
      });
      if (!printPdfInWindow(win, response.data)) {
        saveBlob(response.data, filenameFrom(response.headers['content-disposition']) || fallbackName);
        toast.info(BLOCKED);
      }
    } catch (error) {
      win?.close();
      toast.error(errorText(error, { fallback: `Could not build the ${what.name}` }));
    } finally {
      working.current = false;
      setBusy(false);
    }
  }

  return what.downloads.map((d) => (
    <button
      key={d.key}
      type="button"
      className="btn btn-secondary btn-sm"
      onClick={() => run(d)}
      aria-busy={busy || undefined}
      title={d.title}
    >
      {d.label}
    </button>
  ));
}
