/*
 * The priced-version draft, pure (plan.md §8.14; F76–F84; the old pricedKinds.js and PricedVersionComposer's draft
 * helpers). Three shapes of money back and the copy beside them share one door, ＋ on a plan: a concession, a
 * bundling discount, a premium holiday, and Duplicate. Their words come from `/api/meta/` (board.priced); every figure
 * a draft shows comes from the server's dry run (`plans/priced/` with dry_run), so nothing here works out money — it
 * only shapes what the person typed into the request the server cleans, prices and words.
 */

export const CONCESSION = 'concession';
export const BUNDLE = 'bundle';
export const HOLIDAY = 'holiday';
export const DUPLICATE = 'duplicate';

/** The family meta of a kind ('concession' when unknown). */
export function familyMeta(priced, key) {
  const families = priced?.families ?? [];
  return families.find((f) => f.key === key) ?? families.find((f) => f.key === CONCESSION) ?? { key, label: key };
}

/** "% 5% CONCESSION": the chip a priced version wears — its family's glyph, then the server's own label. */
export function pricedChipText(priced, derived) {
  const meta = familyMeta(priced, derived?.kind);
  return `${meta.glyph ?? ''} ${String(derived?.label || meta.label || '').toUpperCase()}`.trim();
}

/**
 * Which families a plan's ＋ may open: the in-force plan takes only a premium holiday (the baseline is not an offer;
 * a credit on it is real) and a duplicate (copying the in-force column is what a copy is for).
 */
export function familyAllowed(family, plan) {
  if (plan?.role === 'current') return family === HOLIDAY || family === DUPLICATE;
  return true;
}

/**
 * The quotes a bundling discount covers, from the plan whose ＋ was clicked: every quote of that carrier on the line
 * that can take one — not a current plan, not sold, not itself a version, not one whose rates already include the
 * bundle. Falls back to the anchor alone, so a draft always has something to price.
 */
export function bundleScopeIds(plans, anchor) {
  if (!anchor) return [];
  const ids = (plans ?? [])
    .filter(
      (p) =>
        p.carrier === anchor.carrier &&
        p.role !== 'current' &&
        !p.sold &&
        !(p.derived_from && p.derived?.kind !== DUPLICATE) &&
        p.bundling !== 'included',
    )
    .map((p) => p.id);
  return ids.length ? ids : [anchor.id];
}

/** The plans the docked composer offers: not sold; the current plans only for a premium holiday. */
export function candidates(plans, family) {
  return (plans ?? []).filter((p) => !p.sold && (p.role !== 'current' || family === HOLIDAY));
}

export function emptyDraft(patch) {
  return {
    family: CONCESSION, // concession | bundle | holiday | duplicate
    planIds: [], // the plans being priced, in order
    anchorId: null, // the plan whose ＋ opened the draft
    editId: null, // set: ✎ re-pricing this existing version
    expanded: false, // false: the editor in the draft row; true: the composer docked above the table
    eachOpen: false, // the in-row "Each rate" list
    allOp: 'pct_off',
    allValue: '',
    each: {}, // {rate key: {op, value} | 'keep'}: one rate on its own
    credit: '',
    months: '',
    parts: {}, // {line: {op, value, plan_id}}
    carrier: '', // the carrier a bundled line names when no quote of it is linked
    conditional: true,
    note: '',
    name: '',
    ...patch,
  };
}

/** A new draft for ＋ on `plan`: the in-force plan opens on a premium holiday, every other plan on a concession. */
export function openDraft(plan, expanded) {
  return emptyDraft({
    family: plan.role === 'current' ? HOLIDAY : CONCESSION,
    planIds: [plan.id],
    anchorId: plan.id,
    carrier: plan.carrier,
    expanded,
  });
}

/** The draft ✎ reopens on an existing version, from its `derived` record, locked to its family. */
export function draftFromVersion(plan) {
  const derived = plan.derived ?? {};
  const all = derived.all ?? null;
  const parts = Object.fromEntries(
    (derived.parts ?? []).map((part) => [
      part.line,
      { op: part.op, value: String(part.value), plan_id: part.plan_id ?? null },
    ]),
  );
  const each = Object.fromEntries(
    Object.entries(derived.each ?? {}).map(([key, item]) => [
      key,
      item === 'keep' ? item : { ...item, value: String(item.value) },
    ]),
  );
  return emptyDraft({
    family: derived.kind,
    editId: plan.id,
    anchorId: plan.derived_from,
    planIds: [plan.derived_from],
    expanded: true,
    allOp: all?.op ?? 'pct_off',
    allValue: all ? String(all.value) : '',
    each,
    credit: derived.credit?.annual != null ? String(derived.credit.annual) : '',
    months: derived.credit?.months != null ? String(derived.credit.months) : '',
    parts,
    carrier: plan.carrier,
    conditional: derived.conditional !== false,
    note: derived.note ?? '',
  });
}

const filled = (value) => value !== '' && value != null;

/** The bundle's lines with an amount, as the server's `parts`. */
export function bundleParts(draft) {
  return Object.entries(draft.parts ?? {})
    .filter(([, part]) => filled(part?.value) && Number(part.value) !== 0)
    .map(([line, part]) => ({
      line,
      op: part.op || 'pct_off',
      value: part.value,
      ...(part.plan_id ? { plan_id: part.plan_id } : draft.carrier ? { carrier: draft.carrier } : {}),
    }));
}

/**
 * The request for any family — one builder behind the in-row ✓, the composer's Add and the dry run, so they never send
 * different things. → {body} or {error} (the old wording) when nothing has been typed yet.
 */
export function draftBody(draft, words = {}) {
  const body = { kind: draft.family, note: draft.note, name: draft.name };
  if (draft.family === DUPLICATE) {
    if (draft.planIds.length !== 1) return { error: 'Pick exactly one plan to duplicate' };
    return { body: { name: draft.name } };
  }
  if (draft.family === CONCESSION) {
    if (filled(draft.allValue)) body.all = { op: draft.allOp, value: draft.allValue };
    const each = Object.fromEntries(
      Object.entries(draft.each ?? {}).filter(([, item]) => item === 'keep' || filled(item?.value)),
    );
    if (Object.keys(each).length) body.each = each;
    if (!body.all && !Object.values(each).some((item) => item !== 'keep')) {
      return { error: 'Set a change for all rates, or for at least one rate' };
    }
  } else if (draft.family === BUNDLE) {
    body.parts = bundleParts(draft);
    body.conditional = draft.conditional;
    if (!body.parts.length) return { error: 'Enter at least one line’s bundling percentage or dollar amount' };
  } else {
    if (!filled(draft.credit) && !filled(draft.months))
      return { error: 'Enter a dollar credit or a number of free months' };
    body.credit = filled(draft.credit) ? { annual: draft.credit } : { months: draft.months };
    if (filled(draft.credit) && !draft.editId && draft.planIds.length > 1) {
      return { error: words.one_plan_credit || 'A dollar credit belongs to one plan' };
    }
  }
  if (!draft.editId && !draft.planIds.length) return { error: 'Pick at least one plan to price' };
  return { body: draft.editId ? body : { ...body, plan_ids: draft.planIds } };
}

/** What an override's empty choice inherits: "as all (% off 5)"; nothing where the all-rates change does not reach. */
export function inheritLabel(draft, key, priced) {
  if (!filled(draft.allValue)) return '';
  const pct = (priced?.pct_ops ?? []).includes(draft.allOp);
  if (key === priced?.quoted && !pct) return '';
  const op = (priced?.ops ?? []).find((o) => o.key === draft.allOp);
  return `as all (${op?.label ?? draft.allOp} ${draft.allValue})`;
}

/** "requires Aetna Dental PPO + any Cigna vision": what a bundled version needs sold, for internal screens. */
export function requirementDetail(derived, lineLabel = (key) => key) {
  if (derived?.kind !== BUNDLE) return '';
  return (derived.parts ?? [])
    .map(
      (part) =>
        part.plan_label || (part.carrier ? `any ${part.carrier} ${String(lineLabel(part.line)).toLowerCase()}` : ''),
    )
    .filter(Boolean)
    .join(' + ');
}
