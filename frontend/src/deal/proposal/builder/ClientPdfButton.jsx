import { useRef, useState } from 'react';
import { downloadFile } from '../../../lib/download';
import { errorText } from '../../../lib/errors';
import { useToast } from '../../../ui/useToast';

/*
 * "⬇ Client PDF" on the builder's toolbar (plan.md §8.14, §9.7; J24; the old ProposalBuilder.jsx button at 891f1b3):
 * the deck as it stands, drawn by the server and saved under its own file name. One build per click: a click while
 * the first is still building is answered with a toast, not a second file. A draft wears Draft on every page until
 * the proposal is issued (OQ35). The PowerPoint and the client spreadsheet buttons join with their files.
 */
export default function ClientPdfButton({ dealId }) {
  const toast = useToast();
  const working = useRef(false);
  const [busy, setBusy] = useState(false);

  async function download() {
    if (working.current) {
      toast.info('Already working on that — one moment.');
      return;
    }
    working.current = true;
    setBusy(true);
    try {
      await downloadFile(`deals/${dealId}/proposal/files/pdf/`, { fallbackName: 'Proposal.pdf' });
    } catch (error) {
      toast.error(errorText(error, { fallback: 'Could not build the proposal PDF' }));
    } finally {
      working.current = false;
      setBusy(false);
    }
  }

  return (
    <button
      type="button"
      className="btn btn-secondary btn-sm"
      onClick={download}
      aria-busy={busy || undefined}
      title={busy ? 'Preparing the client PDF…' : 'A 16:9 deck to print or send: every page the PowerPoint will have'}
    >
      ⬇ Client PDF
    </button>
  );
}
