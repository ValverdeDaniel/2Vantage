import { useAiState } from '../../api/ai';

/*
 * The staged banner (plan.md §8.16; E78; the old DocumentsTab's `bnf-staged-banner`): while a read of these files waits
 * for review, the Scanned data panel says that what it lists is still the deal's and that the new read waits below the
 * station ("Review this scan"), where it is used or discarded.
 */
export default function StagedBanner({ dealId, ids }) {
  const ai = useAiState(dealId);
  const waiting = (ai.data?.waiting || []).some((row) => row.documents.some((id) => ids.includes(id)));
  if (!ai.data?.claude || !waiting) return null;
  return (
    <div className="bnf-staged-banner" role="status" data-staged-banner>
      ⚖ Claude re-read the quotes — nothing has changed yet. Review the differences below, then keep whichever read you
      want.
    </div>
  );
}
