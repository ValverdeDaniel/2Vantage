/*
 * Where a priced-version draft sits on the board (plan.md §8.14; F76; the old AdvisorTab tables), pure: with plans as
 * rows a blue row and a draft row go under each plan the draft prices; transposed, a blue column and a draft column
 * go right of it; the source plan goes pink. `kit` is usePricedDraft's (null outside ✎ Edit).
 */
import { DUPLICATE, HOLIDAY, familyMeta } from './pricedKinds';

/** Whether a drawn plan is the source of the open draft. */
export function isSource(plan, kit) {
  return Boolean(kit?.rowFor(plan.id));
}

/** Transposed: [{key, plan, source} | {key, formula: true} | {key, draft}] in the order drawn. */
export function stackColumns(drawn, kit) {
  const out = [];
  for (const plan of drawn) {
    const shown = kit?.rowFor(plan.id);
    out.push({ key: plan.id, plan, source: Boolean(shown) });
    if (shown) out.push({ key: `formula-${plan.id}`, formula: true }, { key: shown.id, draft: shown });
  }
  return out;
}

/** The blue row's label: the family, and once for the two that change no rate, that they don't. */
export function formulaLabel(kit) {
  const label = String(familyMeta(kit.priced, kit.draft.family).label).toUpperCase();
  if (kit.draft.family === HOLIDAY) return `${label} · rates unchanged`;
  if (kit.draft.family === DUPLICATE) return `${label} · a copy with its rates`;
  return label;
}
