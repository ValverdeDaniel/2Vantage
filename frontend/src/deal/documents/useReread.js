import { useState } from 'react';
import { useAiState, useStartRead } from '../../api/ai';
import { useMeta } from '../../api/meta';
import { errorText } from '../../lib/errors';
import { useToast } from '../../ui/useToast';
import { byReader, firstPicks, rereadable } from './rereadFiles';

/*
 * The Re-read panel's state (plan.md §8.16; E75, E76, D39; the old DocumentsTab's `rereadOpen`/`rereadPick`): offered
 * only with Claude set up (D26) on a file a proposal reader reads (or 📚 All proposals). "↻ Re-read…" opens it with
 * the file on screen ticked; "Re-read N files" starts one read of the ticked files per reader (quotes, SBCs) through
 * the one read door, each waiting for review on this tab, and closes the panel. A refusal (no key, a cap) is a toast.
 */
export default function useReread(dealId, files, shown, allOn) {
  const toast = useToast();
  const { data: meta } = useMeta();
  const ai = useAiState(dealId);
  const start = useStartRead(dealId);
  const [open, setOpen] = useState(false);
  const [picked, setPicked] = useState(new Set());
  const offered = rereadable(files, meta);
  const here = allOn ? offered.length > 0 : offered.some((file) => file.id === shown?.id);
  const available = Boolean(ai.data?.claude && meta?.ai && here);

  function toggleOpen() {
    setPicked(firstPicks(offered, shown, allOn));
    setOpen((was) => !was);
  }

  function toggle(id) {
    const next = new Set(picked);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setPicked(next);
  }

  async function read() {
    const groups = byReader(offered.filter((file) => picked.has(file.id)), meta);
    setOpen(false);
    try {
      for (const [target, ids] of Object.entries(groups)) {
        await start.mutateAsync({ documentIds: ids, target, review: true }); // a re-read always waits (E75)
      }
    } catch (error) {
      toast.error(errorText(error));
    }
  }

  return {
    available,
    open: available && open,
    offered,
    picked,
    busy: start.isPending,
    toggleOpen,
    toggle,
    close: () => setOpen(false),
    read,
  };
}
