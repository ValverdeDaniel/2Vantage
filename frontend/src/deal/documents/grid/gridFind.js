/*
 * Find over the station's Grid (plan.md §8.16; E60–E64, D127; the old DocumentsTab's gridFind and "Only matches").
 * Pure. Hits are read off what the filters leave on screen, in reading order — the plans' heads left to right, then
 * each row from its label across — each at the most specific place that explains it (src/lib/findText's `findHit`):
 * a head `@head|<plan>`, a label `<row>|@label`, a value `<row>|<plan>`. A head answers to the Advisor finder's texts
 * (name, plan number, carrier, network, plan type, codes) and its carrier, so "UHC" finds UnitedHealthcare (E62, E64).
 */

import { findFields, findHit, placeMatches } from '../../../lib/findText';
import { displayValue } from '../../../lib/fieldValue';
import { cellAt } from './stationModel';

export const HEAD = '@head';
export const LABEL = '@label';
export const hitKey = (r, c) => `${r}|${c}`;

/** A plan's head as a find place: the finder index's texts and carrier (`index` by id), else its own fields. */
export function headPlace(plan, index) {
  const entry = index?.get(plan.id);
  if (entry) return { fields: findFields(...(entry.texts ?? [])), carrier: entry.carrier ?? null };
  const values = plan.values ?? {};
  return { fields: findFields(plan.name, plan.plan_number, plan.carrier, values.network, values.plan_type), carrier: null };
}

/**
 * {hits: [{key, r, c, kind}], rowsHit, colsHit, heads, labels, index: Map(key → n)} for `terms` over `view` ({plans,
 * sections} on screen) of `model`. No terms, no hits.
 */
export function gridFind(model, view, terms, index) {
  const hits = [];
  const rowsHit = new Set();
  const colsHit = new Set();
  let heads = 0;
  let labels = 0;
  const add = (r, c, kind) => {
    hits.push({ key: hitKey(r, c), r: String(r), c: String(c), kind });
    if (kind === 'head') heads += 1;
    else rowsHit.add(String(r));
    if (kind === 'label') labels += 1;
    else colsHit.add(String(c));
  };
  if (terms.length) {
    const cols = view.plans.map((plan) => ({ plan, place: headPlace(plan, index) }));
    for (const { plan, place } of cols) if (placeMatches(place, terms)) add(HEAD, plan.id, 'head');
    for (const section of view.sections) {
      for (const row of section.rows) {
        const label = { fields: findFields(row.label) };
        if (placeMatches(label, terms)) add(row.key, LABEL, 'label');
        for (const { plan, place } of cols) {
          const cell = cellAt(model, row.key, plan.id);
          if (!cell?.raw) continue;
          const value = { fields: findFields(cell.raw, displayValue(row.field, cell.raw)) };
          if (findHit(terms, value, label, place)) add(row.key, plan.id, 'cell');
        }
      }
    }
  }
  return { hits, rowsHit, colsHit, heads, labels, index: new Map(hits.map((hit, n) => [hit.key, n])) };
}

/**
 * "Only matches" (E63): the plans and rows with no hit go. A head's hit keeps its whole plan, so any head hit keeps
 * every row; a label's hit keeps its whole row, so any label hit keeps every plan ("aetna" shows the Aetna plans
 * whole). With no hit at all the grid stays whole beside "No matches".
 */
export function onlyMatches(view, found) {
  const rowsNarrow = !found.heads && found.rowsHit.size > 0;
  const plansNarrow = !found.labels && found.colsHit.size > 0;
  return {
    plans: plansNarrow ? view.plans.filter((plan) => found.colsHit.has(String(plan.id))) : view.plans,
    sections: rowsNarrow
      ? view.sections
          .map((section) => ({ ...section, rows: section.rows.filter((row) => found.rowsHit.has(row.key)) }))
          .filter((section) => section.rows.length)
      : view.sections,
  };
}
