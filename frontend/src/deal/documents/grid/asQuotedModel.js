/*
 * A scanned quote as the carrier printed it, as data (plan.md §7.8, §8.14, §8.16, O.3.5; D66, E42, F42; slice 21):
 * the server's printed table (`plans/as-quoted/`) laid over the Advisor's cached comparisons, in the station Grid's
 * shape (stationModel), so the same table draws it, with the same picks, marks, Find and ✎ Edit. Pure.
 * - Columns: the table's plans in the file's column order (a plan whose line is not loaded yet waits).
 * - Rows: one band, "As printed on page 2", the rows in printed order. A row that fills a field shows the plan's live
 *   value (editable, with its marks); a row that fills two (a deductible's single and family halves) is one row per
 *   field, each naming its field. A row that fills none keeps the file's printed text, greyed, and nobody types in it.
 * The browser decides nothing: what is printed and what each row fills are the server's.
 */

import { cellAt } from './stationModel';

export const PRINTED = '@printed:';

/** "page 2", "page 1 (PDF page 2)" when the carrier numbered it differently (E94), "sheet “Medical”". */
export function printedWhere(table) {
  const where = table?.where ?? {};
  if (where.sheet) return `sheet “${where.sheet}”`;
  if (!where.page) return 'the file';
  const label = table.page_label;
  return label && label !== String(where.page) ? `page ${label} (PDF page ${where.page})` : `page ${where.page}`;
}

function linesOf(meta, key) {
  const out = new Set();
  for (const [line, groups] of Object.entries(meta?.line_groups ?? {})) {
    if (groups.some((group) => group.fields.includes(key))) out.add(line);
  }
  return out;
}

function plansById(comparisons) {
  const out = new Map();
  for (const data of comparisons) {
    const files = (data.documents ?? []).map((doc) => doc.id);
    for (const plan of data.plans ?? []) out.set(plan.id, { ...plan, line: data.line, files, fileNames: data.documents });
  }
  return out;
}

function rowsOf(table, plans, meta) {
  const fields = new Map((meta?.fields ?? []).map((field) => [field.key, field]));
  const place = new Map((table.columns ?? []).map((column, at) => [column.plan, at]));
  const rows = [];
  const seen = new Set();
  (table.rows ?? []).forEach((row, n) => {
    if (!row.keys?.length) {
      const printed = Object.fromEntries(plans.map((plan) => [plan.id, row.printed?.[place.get(plan.id)] ?? '']));
      rows.push({ key: `${PRINTED}${n}`, label: row.label, sub: '', field: undefined, lines: new Set(), printed });
      return;
    }
    for (const key of row.keys) {
      if (seen.has(key)) continue; // a field printed twice shows once, where the file first printed it
      seen.add(key);
      const field = fields.get(key);
      const sub = row.keys.length > 1 ? (field?.label ?? key) : '';
      rows.push({ key, label: row.label, sub, field, lines: linesOf(meta, key) });
    }
  });
  return rows;
}

/** The table in the station model's shape: {plans, sections, byId, rowByKey, issues, names, scopeIds, table}. */
export function buildAsQuoted({ table, comparisons = [], meta }) {
  const found = plansById(comparisons);
  const plans = (table?.columns ?? [])
    .filter((column) => found.has(column.plan))
    .map((column) => ({ ...found.get(column.plan), head: column.head }));
  const rows = table ? rowsOf(table, plans, meta) : [];
  const sections = rows.length ? [{ group: 'as-printed', label: `As printed on ${printedWhere(table)}`, rows }] : [];
  const model = {
    table,
    plans,
    sections,
    scopeIds: new Set(table ? [table.document] : []),
    byId: new Map(plans.map((plan) => [String(plan.id), plan])),
    rowByKey: new Map(rows.map((row) => [row.key, row])),
    issues: new Map(),
    names: new Map([...found.values()].map((plan) => [plan.id, `${plan.carrier} ${plan.name}`.trim()])),
  };
  for (const plan of plans) {
    const count = rows.filter((row) => {
      const cell = cellAt(model, row.key, plan.id);
      return cell.here && cell.potential;
    }).length;
    if (count) model.issues.set(plan.id, count);
  }
  return model;
}
