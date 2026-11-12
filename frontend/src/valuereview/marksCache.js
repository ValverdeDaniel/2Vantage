/*
 * Review marks on the Advisor's compact comparison (plan.md §7.8, §10.7; E53, F63–F65). Pure.
 *
 * A comparison cell carries `s` ('to_check' while the value is an open warning, the server's one rule, OQ28), `m`
 * (the mark it shows: 'check', or 'ignored' / 'approved' where they settle a doubt) and `p` (a potential error that is
 * not an open warning: the locator could not find or pin it down and nobody dealt with it; E50, D123). The browser
 * never decides what needs review: it counts the server's flags and lays a review's answer over the cached cells, so
 * the board agrees with the station without a refetch (E53).
 */

/** A potential error (E50, D123; the server's `potential_error`): an open warning, or `p`. */
export const isPotential = (cell) => cell?.s === 'to_check' || Boolean(cell?.p);

/** {open, check, unflagged} over compact cells: "⚠ N to review · ⚑ k" and the strip's buttons. */
export function cellCounts(cells) {
  let open = 0;
  let check = 0;
  for (const cell of cells) {
    if (cell?.s !== 'to_check') continue;
    open += 1;
    if (cell.m === 'check') check += 1;
  }
  return { open, check, unflagged: open - check };
}

/** One plan's counts. */
export function planCounts(plan) {
  return cellCounts(Object.values(plan?.cells ?? {}));
}

/** The keys of a plan's open warnings, in the board's field order (`keys`). */
export function flaggedKeys(plan, keys) {
  return keys.filter((key) => plan?.cells?.[key]?.s === 'to_check');
}

function patchedCell(cell, change) {
  const next = { ...(cell ?? {}) };
  delete next.m;
  delete next.p;
  if (next.s === 'to_check') delete next.s;
  if (change.cell?.s) next.s = change.cell.s;
  if (change.cell?.m) next.m = change.cell.m;
  if (change.cell?.p) next.p = change.cell.p;
  return next;
}

/**
 * The comparison with a marks answer laid over it: each changed value's `s` and `m`, each changed plan's
 * `facts.flags` and `facts.incomplete`. Plans the answer does not name are returned as they were (same object).
 */
export function patchComparison(data, answer) {
  if (!data || !answer) return data;
  const byPlan = new Map();
  for (const change of answer.values ?? []) {
    if (!byPlan.has(change.plan_id)) byPlan.set(change.plan_id, []);
    byPlan.get(change.plan_id).push(change);
  }
  const facts = new Map((answer.plans ?? []).map((plan) => [plan.id, plan]));
  if (!byPlan.size && !facts.size) return data;
  return {
    ...data,
    plans: data.plans.map((plan) => {
      const changes = byPlan.get(plan.id);
      const counted = facts.get(plan.id);
      if (!changes && !counted) return plan;
      const cells = { ...plan.cells };
      for (const change of changes ?? []) cells[change.key] = patchedCell(cells[change.key], change);
      return {
        ...plan,
        cells,
        facts: counted ? { ...plan.facts, flags: counted.flags, incomplete: counted.incomplete } : plan.facts,
      };
    }),
  };
}
