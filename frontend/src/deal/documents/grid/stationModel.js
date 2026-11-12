/*
 * The station's Grid as data (plan.md §8.16; E36–E41, E50, D123; the old DocumentsTab's docPlans, proposalSections,
 * planIssues and gridShape). Pure: the Advisor's cached comparisons in, the grid out, so arriving from the Advisor is
 * instant (E36) and the browser decides nothing the server did not say.
 * - Columns: the plans with a value read from the files in scope, line by line in the deal's line order, each line's
 *   plans in the server's one order (current in slot order, then the quotes under the plan they compare to; E37).
 * - Rows: the fields of those plans' lines, in the field groups' order with a band per group (E38); a field that does
 *   not apply to a plan's line is a blank cell nobody can type in.
 * - Cells: the compact flags (`s`, `m`, `p`, `d`), the file each value came from, whether that is a file in scope
 *   (underlined) or another (greyer; E41), and whether it is a potential error (E50; `marksCache.isPotential`).
 * Rows are field keys and columns plan ids, as strings, for src/grid's hooks.
 */

import { isPotential } from '../../../valuereview/marksCache';

/** "plan:41:rate_ee": a value's ref (the marks door, ↗ and `?ref=`). */
export const refOf = (planId, key) => `plan:${planId}:${key}`;

/** The plans of every loaded line that a file in `scopeIds` gave a value, each with its line and its cells' files. */
function scopedPlans(comparisons, scopeIds) {
  const out = [];
  for (const data of comparisons) {
    const files = (data.documents ?? []).map((doc) => doc.id);
    for (const plan of data.plans ?? []) {
      const docs = Object.values(plan.cells ?? {})
        .map((cell) => (cell?.d != null ? files[cell.d] : null))
        .filter((id) => id != null);
      if (docs.some((id) => scopeIds.has(id))) out.push({ ...plan, line: data.line, files, fileNames: data.documents });
    }
  }
  return out;
}

/** The bands and rows for the lines in `lines` (meta's per-line groups), in meta's group and field order. */
function sectionsFor(meta, lines) {
  const fields = new Map((meta?.fields ?? []).map((field, index) => [field.key, { field, index }]));
  const byGroup = new Map();
  for (const line of lines) {
    for (const group of meta?.line_groups?.[line] ?? []) {
      if (!byGroup.has(group.key)) byGroup.set(group.key, new Map());
      const rows = byGroup.get(group.key);
      for (const key of group.fields) {
        if (!rows.has(key)) rows.set(key, new Set());
        rows.get(key).add(line);
      }
    }
  }
  return (meta?.groups ?? [])
    .filter((group) => byGroup.has(group.key))
    .map((group) => ({
      group: group.key,
      label: group.label,
      rows: [...byGroup.get(group.key)]
        .map(([key, on]) => ({ key, lines: on, field: fields.get(key)?.field, at: fields.get(key)?.index ?? 1e9 }))
        .sort((a, b) => a.at - b.at)
        .map(({ key, lines: on, field }) => ({ key, label: field?.label ?? key, field, lines: on })),
    }));
}

/** One cell: {raw, flags, doc, docName, here, applies, potential, ref}. `r` a field key, `c` a plan id. */
export function cellAt(model, r, c) {
  const plan = model.byId.get(String(c));
  const row = model.rowByKey.get(String(r));
  if (!plan || !row) return null;
  const flags = plan.cells?.[row.key] ?? {};
  const doc = flags.d != null ? (plan.files[flags.d] ?? null) : null;
  return {
    raw: plan.values?.[row.key] ?? '',
    flags,
    doc,
    docName: doc != null ? (plan.fileNames?.[flags.d]?.name ?? '') : '',
    here: doc != null && model.scopeIds.has(doc),
    applies: row.lines.has(plan.line),
    potential: isPotential(flags),
    ref: refOf(plan.id, row.key),
  };
}

/**
 * The grid for the files in `scopeIds`: {plans, sections, byId, rowByKey, issues, names, scopeIds}. `issues` counts each
 * plan's potential errors read from these files (the head's ⚠ N, E40, and the "⚠ Potential errors" filter, E50).
 */
export function buildStationGrid({ comparisons = [], meta, scopeIds }) {
  const plans = scopedPlans(comparisons, scopeIds);
  const lines = [...new Set(plans.map((plan) => plan.line))];
  const sections = sectionsFor(meta, lines);
  const model = {
    plans,
    sections,
    scopeIds,
    byId: new Map(plans.map((plan) => [String(plan.id), plan])),
    rowByKey: new Map(sections.flatMap((section) => section.rows.map((row) => [row.key, row]))),
    issues: new Map(),
    // Every plan's "Carrier Name", for a renewal's "The renewal of …" (its current plan may read from no file here).
    names: new Map(comparisons.flatMap((data) => (data.plans ?? []).map((p) => [p.id, `${p.carrier} ${p.name}`.trim()]))),
  };
  for (const plan of plans) {
    let count = 0;
    for (const section of sections) {
      for (const row of section.rows) {
        const cell = cellAt(model, row.key, plan.id);
        if (cell.here && cell.potential) count += 1;
      }
    }
    if (count) model.issues.set(plan.id, count);
  }
  return model;
}

/**
 * What the filters leave (E50, D123): {plans, sections}. "⚠ Potential errors" keeps the plans with one from these
 * files; "Only rows with potential errors" keeps the rows with one in a plan shown. Off while nothing is left to show.
 */
export function filterGrid(model, { errorsOnly = false, rowsOnly = false } = {}) {
  const any = model.issues.size > 0;
  const plans = errorsOnly && any ? model.plans.filter((plan) => model.issues.has(plan.id)) : model.plans;
  if (!(rowsOnly && any)) return { plans, sections: model.sections };
  const keep = (row) =>
    plans.some((plan) => {
      const cell = cellAt(model, row.key, plan.id);
      return cell.here && cell.potential;
    });
  const sections = model.sections
    .map((section) => ({ ...section, rows: section.rows.filter(keep) }))
    .filter((section) => section.rows.length);
  return { plans, sections };
}

/** The rows and columns on screen, as src/grid's hooks address them. */
export function gridShape(view) {
  return {
    rows: view.sections.flatMap((section) => section.rows.map((row) => row.key)),
    cols: view.plans.map((plan) => String(plan.id)),
  };
}
