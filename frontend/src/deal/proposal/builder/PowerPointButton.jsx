import { useRef, useState } from 'react';
import { downloadFile } from '../../../lib/download';
import { errorText } from '../../../lib/errors';
import { useToast } from '../../../ui/useToast';

/*
 * "⬇ PowerPoint" on the builder's toolbar, beside "⬇ Client PDF" (plan.md §8.14, §9.6; J24, J141; the old
 * ProposalBuilder.jsx handlePowerPoint at 891f1b3): the same deck as the PDF, replayed as slides by the server and
 * saved under its own file name. One build per click; a click while the first is still building gets a toast, not a
 * second file. A draft wears Draft on every slide until the proposal is issued (OQ35).
 */
export default function PowerPointButton({ dealId }) {
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
      await downloadFile(`deals/${dealId}/proposal/files/pptx/`, { fallbackName: 'Proposal.pptx' });
    } catch (error) {
      toast.error(errorText(error, { fallback: 'Could not build the PowerPoint' }));
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
      title={busy ? 'Preparing the PowerPoint…' : 'A 16:9 deck to present from: every figure the PDF’s'}
    >
      ⬇ PowerPoint
    </button>
  );
}
