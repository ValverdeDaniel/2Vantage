/*
 * The board's plans in the order drawn, and what the arrows on a plan may do (plan.md §5.4, §8.14; F43, F44, F120;
 * OQ13; the old planOrder.js). Pure, over the comparison's plans, which arrive in the server's `order.layout` order
 * (the client's order): nothing here re-decides the order, it only lays it out the way the board reads it — each
 * current plan heading the quotes compared with it — and works out which plans an arrow passes. Stop-loss is ordered
 * like every line (OQ13, reversing the old app's "as entered" rule).
 */

/** A priced version's original, followed to the carrier's own quote; a duplicate is a peer (D-049). */
export function rootOf(plan, byId) {
  let at = plan;
  const seen = new Set();
  while (at?.derived_from && at.derived?.kind !== 'duplicate' && !seen.has(at.id)) {
    seen.add(at.id);
    const parent = byId.get(at.derived_from);
    if (!parent) break;
    at = parent;
  }
  return at;
}

/**
 * {byId, currents, rank, groupOf}: `groupOf(id)` is the current plan a plan sits with (a current plan is its own
 * group; a quote goes with the first current plan it is compared with, `base_ids`, as order.layout groups it), or
 * 'none'; `rank` is each plan's place in the server's order.
 */
export function lineOrder(plans) {
  const byId = new Map(plans.map((plan) => [plan.id, plan]));
  const currents = plans.filter((plan) => plan.role === 'current');
  const currentIds = new Set(currents.map((plan) => plan.id));
  const groupOf = (id) => {
    const plan = byId.get(id);
    if (!plan) return 'none';
    if (plan.role === 'current') return plan.id;
    const root = rootOf(plan, byId);
    if (root.role === 'current') return root.id;
    const base = (root.base_ids ?? [])[0];
    return currentIds.has(base) ? base : 'none';
  };
  return { byId, currents, rank: new Map(plans.map((plan, i) => [plan.id, i])), groupOf };
}

/**
 * The board's rows: the current plans pinned first, then `quotes` (the quotes left to show, in the sort's order).
 * In the client's order with several current plans, each current plan heads the quotes compared with it, as the
 * builder, the Proposal grid and the documents draw them.
 */
export function drawnOrder(order, quotes, inProposal) {
  if (!inProposal || order.currents.length < 2) return [...order.currents, ...quotes];
  const out = [];
  for (const current of order.currents) {
    out.push(current, ...quotes.filter((plan) => order.groupOf(plan.id) === current.id));
  }
  return [...out, ...quotes.filter((plan) => order.groupOf(plan.id) === 'none')];
}

/** Whether a plan takes arrows: a current plan only beside another; never a priced version of a current plan. */
export function canMove(plan, order) {
  if (!plan) return false;
  if (plan.role === 'current') return order.currents.length > 1;
  return rootOf(plan, order.byId).role !== 'current';
}

/**
 * What the arrows on `plan` do on a board showing `shownIds` (in its order): `among`, the ids on screen it can pass
 * (its own group's quotes, or the current plans for a current plan), sent with the move so a step passes the plans
 * a filter hides; and whether it is already `first` or `last` there. A quote moves with its priced versions.
 */
export function arrowsFor(plan, shownIds, order) {
  const { byId, groupOf } = order;
  const group = groupOf(plan.id);
  const among = shownIds.filter((id) => {
    const peer = byId.get(id);
    if (!peer) return false;
    if (plan.role === 'current') return peer.role === 'current';
    return peer.role !== 'current' && rootOf(peer, byId).role !== 'current' && groupOf(id) === group;
  });
  const unitOf = (id) => rootOf(byId.get(id), byId).id;
  const units = [...new Set(among.map(unitOf))];
  const at = units.indexOf(unitOf(plan.id));
  return { among, first: at <= 0, last: at < 0 || at === units.length - 1 };
}
