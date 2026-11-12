import { useRef, useState } from 'react';
import { downloadFile } from '../../../lib/download';
import { errorText } from '../../../lib/errors';
import { useToast } from '../../../ui/useToast';

/*
 * "⬇ Client spreadsheet" on the builder's toolbar (plan.md §8.14, §9.4; J24; the old ProposalBuilder.jsx button at
 * 891f1b3): the live workbook as the deal stands, built by the server and saved under its own name
 * (`<Client> - <year> Benefits Proposal-DRAFT.xlsx`, J104). One build per click: a click while the first is still
 * building is answered with a toast. A proposal with nothing to present answers with the server's sentence.
 */
export default function ClientSpreadsheetButton({ dealId }) {
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
      await downloadFile(`deals/${dealId}/proposal/files/xlsx/`, { fallbackName: 'Proposal.xlsx' });
    } catch (error) {
      toast.error(errorText(error, { fallback: 'Could not build the client spreadsheet' }));
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
      title={busy ? 'Preparing the client spreadsheet…' : undefined}
    >
      ⬇ Client spreadsheet
    </button>
  );
}
