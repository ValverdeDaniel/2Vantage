import { useState } from 'react';
import { downloadFile } from '../lib/download';
import { useToast } from './useToast';

/*
 * Export ⬇ (H52, H116; 891f1b3 `commissions/ExportButton.jsx`): one button per data table. The server names the file
 * (`fallbackName` covers its absence) and builds it with the screen's own filters and the viewer's tier.
 */
export default function ExportButton({ path, params, fallbackName = 'export.xlsx', label = 'Export ⬇', title }) {
  const toast = useToast();
  const [busy, setBusy] = useState(false);

  async function run() {
    setBusy(true);
    try {
      await downloadFile(path, { params, fallbackName });
    } catch {
      toast.error('Could not build the export');
    } finally {
      setBusy(false);
    }
  }

  return (
    <button
      type="button"
      className="btn btn-secondary btn-sm"
      disabled={busy}
      title={title || 'Download this table as an Excel workbook'}
      onClick={run}
    >
      {busy ? 'Exporting…' : label}
    </button>
  );
}
