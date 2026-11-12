// The Proposal tab's board in presented mode (plan.md §8.15; J70, J76, J81; the old ComparisonGrid's
// comparisonShape at 891f1b3), pure: which of the line's plans the grid draws and the line tabs' words. A line with
// a shortlist (stars) shows what the proposal presents (quotes' `presented`, current plans first) until "Show all
// N plans"; a line with none shows every plan. The order is always the client's (Proposal order); nothing sorts here.

/** {shown: [plan], shortlist: n starred, all: N plans, active: is the shortlist on}. */
export function presentedPlans(plans, showAll) {
  const shortlist = plans.filter((plan) => plan.starred).length;
  const active = shortlist > 0 && !showAll;
  const shown = active ? plans.filter((plan) => plan.role === 'current' || plan.presented) : plans;
  return { shown, shortlist, all: plans.length, active };
}

/** The ★ Shortlist button's words, or null when the line has no stars (the old button hid then). */
export function shortlistWords({ shortlist, all, active }) {
  if (!shortlist) return null;
  return active ? `Show all ${all} plans` : `★ Shortlist (${shortlist})`;
}

/** The line to draw: the one asked for when the deal has it, else the first. */
export function pickLine(lines, asked) {
  if (!lines?.length) return null;
  return lines.some((row) => row.line === asked) ? asked : lines[0].line;
}

/** The quote files Claude reads again for ⟲ Re-read quotes (J80): the deal's files of the kinds the quote reader
 *  reads, in upload order. */
export function quoteFileIds(documents, meta) {
  const kinds = (meta?.ai?.targets ?? []).find((target) => target.key === 'quotes')?.kinds ?? [];
  return (documents ?? []).filter((doc) => kinds.includes(doc.kind) && !doc.protected).map((doc) => doc.id);
}
