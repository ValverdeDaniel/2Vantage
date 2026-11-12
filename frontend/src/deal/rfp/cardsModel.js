// The RFP page's cards, pure (plan.md §8.12; K6, K7, K9, K10; old CarriersTab.jsx at 891f1b3): which show, which are
// open, the "✓ N of M completed" count, and when a checklist edit on the page takes the checklist's mark off.

/** The cards this deal shows, in page order: meta's five, less those not built or not loaded yet. */
export function shownCards(cards, available) {
  return (cards || []).map((card) => card.key).filter((key) => available[key]);
}

/** A card with no choice this visit is open unless completed, which is how a completed card comes back shut (K9). */
export function isOpen(openCards, done, card) {
  return card in openCards ? openCards[card] : !done?.[card];
}

/** "✓ N of M completed" over the cards on the page (K6). */
export function progress(shown, done) {
  const marked = shown.filter((card) => done?.[card]).length;
  return { done: marked, total: shown.length, all: shown.length > 0 && marked === shown.length };
}

/**
 * What a checklist edit changes, as one string: each row's state and the meter. The page compares it before and after
 * intake's checklist answers land, and takes the checklist's mark off when it moved (K10: intake never sees rfp).
 */
export function checklistDigest(checklist) {
  if (!checklist) return null;
  const rows = (checklist.items || []).map((item) =>
    [item.key, item.status, item.done, item.attested, item.waived, item.has_document, item.forced].join(':'),
  );
  return [checklist.tier, checklist.required, checklist.done, ...rows].join('|');
}
