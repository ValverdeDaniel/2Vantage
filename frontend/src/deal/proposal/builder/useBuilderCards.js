import { useState } from 'react';
import { cardId, isOpen, shownCards, stampOf } from './builderModel';

/*
 * The builder's cards: which is open, their marks and Fix ▸ (plan.md §8.14; J18, J23, J42; the old ProposalBuilder.jsx
 * at 891f1b3). Every card collapses and can be marked completed; a completed card starts collapsed for everyone on the
 * deal, until this visit opens or shuts it. "n of N completed" counts the cards on screen, the optional ones apart
 * (`/api/meta/` proposal.cards[].optional). Fix ▸ opens a card (on its line) and scrolls to it, or goes to a deal tab.
 */
export default function useBuilderCards({ proposalMeta, stored, line, writes, onLine, onGoTab }) {
  const [openCards, setOpenCards] = useState({});
  const perLine = (key) => proposalMeta.cards.find((entry) => entry.key === key)?.line;
  const cardOf = (key, onLineKey = line) => (perLine(key) ? { key, line: onLineKey } : { key });
  const setOpen = (card, open) => setOpenCards((now) => ({ ...now, [cardId(card)]: open }));
  const shown = shownCards(proposalMeta, line);
  const optional = new Set(proposalMeta.cards.filter((entry) => entry.optional).map((entry) => entry.key));
  const counted = shown.filter((card) => !optional.has(card.key));
  return {
    progress: { done: counted.filter((card) => stampOf(stored, card)).length, total: counted.length },
    allOpen: shown.every((card) => isOpen(openCards, stored, card)),
    setAllOpen: (open) => setOpenCards((now) => ({ ...now, ...Object.fromEntries(shown.map((c) => [cardId(c), open])) })),
    props: (key) => {
      const card = cardOf(key);
      const open = isOpen(openCards, stored, card);
      return {
        done: stampOf(stored, card),
        open,
        busy: writes.busy,
        onToggleOpen: () => setOpen(card, !open),
        onToggleDone: (done) => {
          if (done) setOpen(card, false);
          writes.mark(card, done);
        },
      };
    },
    fix: (item) => {
      if (item.fix?.tab) {
        onGoTab(item.fix.tab);
        return;
      }
      if (item.line) onLine(item.line);
      setOpen(cardOf(item.fix.card, item.line || line), true);
      requestAnimationFrame(() => {
        document.querySelector(`[data-guide="build-${item.fix.card}"]`)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      });
    },
  };
}
