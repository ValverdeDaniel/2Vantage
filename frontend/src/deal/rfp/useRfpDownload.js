import { useState } from 'react';
import { rfpFilePath } from '../../api/rfp';
import { downloadFile } from '../../lib/download';
import { errorText } from '../../lib/errors';
import { useToast } from '../../ui/useToast';

/*
 * One door for the RFP's file downloads (plan.md §7.11; K50, K51, K113): the file is built on the server and named
 * there; the button says "Building…" while it is; a refusal (no census yet, 409) or a failure is a toast in words. The
 * check before the download (K69, K70) joins with slice 46.
 */
export default function useRfpDownload(dealId) {
  const toast = useToast();
  const [busy, setBusy] = useState('');
  const download = async (key, fallbackName = 'census.xlsx') => {
    setBusy(key);
    try {
      await downloadFile(rfpFilePath(dealId, key), { fallbackName });
    } catch (error) {
      toast.error(errorText(error, { fallback: 'Could not build that file.' }));
    } finally {
      setBusy('');
    }
  };
  return { busy, download };
}
