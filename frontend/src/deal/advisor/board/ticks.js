/*
 * What the ☐ ticks may hold and what each batch action takes (plan.md §8.14; F53, F57–F61; the old AdvisorTab's
 * tickBlock, moveBlock and markBlock). Pure. Ticks live in every mode: outside ✎ Edit the only action is ★ Star /
 * ☆ Unstar, which a current plan never takes, so its box is greyed with the reason; in Edit every row is live, and
 * each action takes only the ticked plans it applies to (the server refuses the rest in words: a bundle's required
 * plan, a client's pick).
 */

/** Why a plan's box is greyed, or ''. */
export function tickBlock(plan, editing) {
  return !editing && plan.role === 'current' ? 'A current plan is always on the proposal — it takes no star' : '';
}

/** The ids of plans that have a copy or priced version made from them. */
export function withVersions(plans) {
  return new Set(plans.map((plan) => plan.derived_from).filter(Boolean));
}

/** Why Move to leaves a ticked plan where it is, or '' (F59; quotes' move_line refuses the same in words). */
export function moveBlock(plan, versioned) {
  if (plan.sold) return 'Sold: its line was booked with the sale';
  if (plan.derived_from) return "A priced version or copy stays on its original's line";
  if (versioned.has(plan.id)) return 'Has priced versions or copies: remove them before moving it';
  return '';
}

/** Why Mark current leaves a ticked plan as it is, or '' (F53). */
export function markBlock(plan) {
  if (plan.role === 'current') return 'Already a current plan';
  if (plan.sold) return 'Sold: the plan the client is buying is not the one in force';
  if (plan.derived_from && plan.derived?.kind !== 'duplicate') {
    return "A priced version: the plan in force is the carrier's own column";
  }
  return '';
}

/**
 * The batch actions over the ticked plans on screen (`ticked`, in the order drawn): {toStar, toUnstar, toMove,
 * toMark, toUnset, toRemove}, each a list of ids.
 */
export function batch(ticked, plans) {
  const versioned = withVersions(plans);
  const ids = (list) => list.map((plan) => plan.id);
  return {
    toStar: ids(ticked.filter((plan) => plan.role !== 'current' && !plan.starred)),
    toUnstar: ids(ticked.filter((plan) => plan.starred)),
    toMove: ids(ticked.filter((plan) => !moveBlock(plan, versioned))),
    toMark: ids(ticked.filter((plan) => !markBlock(plan))),
    toUnset: ids(ticked.filter((plan) => plan.role === 'current')),
    toRemove: ids(ticked),
  };
}

/** Select-all's reach (F57): the quotes the board is showing, never the pinned current plans. */
export function selectable(shownQuotes, editing) {
  return shownQuotes.filter((plan) => !tickBlock(plan, editing)).map((plan) => plan.id);
}
