import { useIsMutating, useQueryClient } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { lastPreview, usePreview, useProposal } from '../../../api/proposals';
import { previewError } from './exportFiles';

// How long the deal must sit still while you look before its copy is built again (J107; the old SETTLE_MS).
export const SETTLE_MS = 900;

/** `value`, at once the first time, then each change only once it has held for `delay` ms. */
function useSettled(value, delay) {
  const [settled, setSettled] = useState(null);
  useEffect(() => {
    if (value == null || value === settled) return undefined;
    const timer = setTimeout(() => setSettled(value), settled == null ? 0 : delay);
    return () => clearTimeout(timer);
  }, [value, settled, delay]);
  return settled ?? value;
}

/*
 * One file's copy in the Export viewer (plan.md §8.14; J107, F3; the old useExportPreview.js at 891f1b3): built only
 * while it is on screen (`shown`) and nothing is saving, keyed on the builder's `stamps` settled 900 ms (at once on
 * arrival), so a completed mark or a download never rebuilds it and a burst of edits builds once. The last copy stays
 * on screen while the next builds (`stale` says the deal moved since); a refusal (409, the download's own sentence)
 * replaces it, a failure keeps it. Refresh builds again on demand.
 */
export default function usePreviewCopy(dealId, { file, tab, shown }) {
  const queryClient = useQueryClient();
  const builder = useProposal(dealId);
  const stamps = builder.data?.stamps;
  const wanted = stamps ? `${stamps.files}|${stamps.firm}` : null;
  const settled = useSettled(wanted, SETTLE_MS);
  const [files, firm] = settled ? settled.split('|') : [];
  const saving = useIsMutating() > 0;
  const query = usePreview(dealId, {
    file,
    tab,
    stamps: settled ? { files, firm } : null,
    enabled: shown && !saving,
  });
  const { refused, failed } = previewError(query.error);
  const data = refused ? null : (query.data ?? (failed ? lastPreview(queryClient, dealId, file) : undefined));
  return {
    data: data ?? null,
    building: query.isFetching || (!data && !refused && !failed),
    stale: Boolean(data) && (query.isPlaceholderData || wanted !== settled || saving),
    refused,
    failed: failed || (builder.isError && !data ? 'Could not read the proposal.' : ''),
    refresh: () => query.refetch(),
  };
}
