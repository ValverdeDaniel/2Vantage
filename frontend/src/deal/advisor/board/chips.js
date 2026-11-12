/*
 * What the Plan cell says about a plan (plan.md §8.14; F62, D-051; the old AdvisorTab's chips). Pure, from plan
 * fields, `derived` and the server's `facts`; the compliance words come from `/api/meta/` (board.compliance).
 * - CURRENT, numbered when the line has several (its slot); BUNDLED on a quote whose rates already include the
 *   bundling discount (F78);
 * - a priced version's chip (its family's glyph and its label), and "superseded" on a quote a priced version replaces;
 * - "⚠ MV · Part D" for the compliance tests the carrier says the plan fails, with the reasons as its title;
 * - "requires …" (what has to sell for a bundled price) and "updated <date>" under a priced version.
 * A duplicate (D-049) is a peer and wears no chip.
 */

/** A copy or priced version's kind, or '' for a carrier's own quote. */
export function pricedKind(plan) {
  const kind = plan?.derived_from ? plan.derived?.kind : '';
  return kind && kind !== 'duplicate' ? kind : '';
}

/** The compliance entries (meta board.compliance) a plan fails, in meta order. */
export function complianceFailures(plan, compliance = []) {
  const failed = new Set(plan?.facts?.compliance ?? []);
  return compliance.filter((entry) => failed.has(entry.key));
}

export function complianceText(failures) {
  return failures.length ? `⚠ ${failures.map((f) => f.short).join(' · ')}` : '';
}

export function complianceTitle(failures) {
  if (!failures.length) return '';
  const names = failures.map((f) => f.label);
  const joined = names.length === 1 ? names[0] : `${names.slice(0, -1).join(', ')} and ${names[names.length - 1]}`;
  return `The carrier says this plan does not meet ${joined}. ${failures.map((f) => f.why).join(' ')}`;
}

/**
 * The chips above the carrier: [{key, className, text, title}]. `currents` are the line's current plans in slot
 * order; `supersededIds` the quotes a priced version was made from; `families` meta's priced-version families.
 */
export function planChips(plan, { currents = [], supersededIds = new Set(), families = [] } = {}) {
  const chips = [];
  if (plan.role === 'current') {
    const slot = currents.findIndex((p) => p.id === plan.id) + 1;
    chips.push({
      key: 'current',
      className: 'bnf-plan-chip bnf-chip-current',
      text: currents.length > 1 && slot > 0 ? `CURRENT ${slot}` : 'CURRENT',
    });
  }
  if (plan.bundling === 'included') {
    chips.push({
      key: 'bundled',
      className: 'bnf-plan-chip bnf-chip-bundled',
      text: 'BUNDLED',
      title:
        'The carrier confirmed these quoted rates already include the bundling discount — a bundled version is refused on this quote',
    });
  }
  const kind = pricedKind(plan);
  if (kind) {
    const family = families.find((f) => f.key === kind);
    const label = plan.derived?.label || kind;
    chips.push({
      key: 'priced',
      className: 'bnf-plan-chip bnf-chip-concession',
      text: `${family?.glyph ? `${family.glyph} ` : ''}${String(label).toUpperCase()}`,
      title: [family?.label, plan.derived?.note].filter(Boolean).join(' — '),
    });
  }
  if (plan.role !== 'current' && supersededIds.has(plan.id)) {
    chips.push({
      key: 'superseded',
      className: 'bnf-plan-chip bnf-chip-superseded',
      text: 'superseded',
      title: "A priced version of this plan exists — this is the carrier's original",
    });
  }
  return chips;
}

/** The ids of the quotes a priced version was made from (a duplicate supersedes nothing). */
export function supersededIds(plans) {
  return new Set(plans.filter((plan) => pricedKind(plan)).map((plan) => plan.derived_from));
}

/**
 * "requires Aetna Dental PPO + any Cigna vision": what a bundled price needs sold, or ''. Each part names its quote as
 * it was when priced (the server keeps the label beside the id), else a plan on this line by id, else the carrier.
 */
export function requiresText(plan, namesById) {
  if (pricedKind(plan) !== 'bundle') return '';
  const parts = plan.derived?.parts ?? (plan.derived?.requires ?? []).map((id) => ({ plan_id: id }));
  return parts
    .map(
      (part) =>
        part.plan_label ||
        namesById.get(part.plan_id) ||
        (part.carrier ? `any ${part.carrier} ${String(part.line).replace(/_/g, ' ')}` : ''),
    )
    .filter(Boolean)
    .join(' + ');
}
