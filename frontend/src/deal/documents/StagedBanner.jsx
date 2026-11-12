import { useAiState } from '../../api/ai';

/*
 * The staged banner (plan.md §8.16; E78; the old DocumentsTab's `bnf-staged-banner`): while a read of these files waits
 * for review, the Scanned data panel says that what it lists is still the deal's and that the new read waits below the
 * station ("Review this scan"), where it is used or discarded. Slice 22: an SBC read and Claude's re-check say so.
 */
const WORDS = {
  read: 'Claude re-read the quotes — nothing has changed yet. Review the differences below, then keep whichever read you want.',
  sbc: 'Claude read the SBC — nothing has changed yet. Review its design values below, then use them or discard them.',
  recheck:
    'Claude re-checked the flagged values — nothing has changed yet. Review its card below, then apply what you want.',
};

export default function StagedBanner({ dealId, ids }) {
  const ai = useAiState(dealId);
  const waiting = (ai.data?.waiting || []).find((row) => row.documents.some((id) => ids.includes(id)));
  if (!ai.data?.claude || !waiting) return null;
  const words = waiting.kind === 'recheck' ? WORDS.recheck : waiting.target === 'sbc' ? WORDS.sbc : WORDS.read;
  return (
    <div className="bnf-staged-banner" role="status" data-staged-banner>
      ⚖ {words}
    </div>
  );
}
