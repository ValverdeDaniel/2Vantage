import { useEffect, useRef, useState } from 'react';
import { checklistDigest, isOpen, progress, shownCards } from './cardsModel';

/*
 * The RFP page's cards (plan.md §8.12; K6, K7, K9, K10; old CarriersTab.jsx at 891f1b3): open or shut for this visit
 * only (a card with no choice is open unless completed), their marks, "✓ N of M completed" and Collapse all. Marking a
 * card shuts it at once; Undo leaves it as it is. The coverage card's mark comes off on the server when the coverage
 * changes; the checklist's comes off here, after a checklist edit on this page lands while it is marked (K10).
 */
export default function useRfpCards({ cards, available, done, writes, checklist }) {
  const [openCards, setOpenCards] = useState({});
  const shown = shownCards(cards, available);
  const setOpen = (card, open) => setOpenCards((now) => ({ ...now, [card]: open }));

  const digest = checklistDigest(checklist);
  const seen = useRef(digest);
  const markedChecklist = Boolean(done?.checklist);
  const { mark } = writes;
  useEffect(() => {
    const before = seen.current;
    seen.current = digest;
    // The card is open (the edit was made in it), and Undo leaves it open: the producer is mid-edit.
    if (before && digest && before !== digest && markedChecklist) mark('checklist', false);
  }, [digest, markedChecklist, mark]);

  const toggleDone = (card, value) => {
    if (value) setOpen(card, false);
    writes.mark(card, value, {
      onError: () =>
        value &&
        setOpenCards((now) => {
          const { [card]: _gone, ...rest } = now;
          return rest;
        }),
    });
  };

  return {
    shown,
    progress: progress(shown, done),
    allOpen: shown.every((card) => isOpen(openCards, done, card)),
    setAllOpen: (open) => setOpenCards((now) => ({ ...now, ...Object.fromEntries(shown.map((card) => [card, open])) })),
    card: (key) => {
      const open = isOpen(openCards, done, key);
      return {
        done: done?.[key] || null,
        open,
        busy: writes.marking,
        onToggleOpen: () => setOpen(key, !open),
        onToggleDone: (value) => toggleDone(key, value),
      };
    },
  };
}
