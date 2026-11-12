/*
 * Find over the List (plan.md §8.16; E63, D127; the old FileReviewList's `found`): the rows loaded (the server pages
 * them, 200 at a time) that answer the words, in the List's own worst-first order. A row answers with its field, its
 * plan ("Carrier · Plan name"), its value as shown and its plan's carrier, so "UHC" finds UnitedHealthcare's values
 * here too (OQ14). Pure.
 */

import { findFields, placeMatches } from '../lib/findText';

/** The refs of the rows that answer `terms`, in order. `valueOf(row)` is the value as shown; `carrierOf(row)` a key. */
export function listHits(rows, terms, { valueOf = (row) => row.value, carrierOf = () => null } = {}) {
  if (!terms.length) return [];
  return rows
    .filter((row) => placeMatches({ fields: findFields(row.label, row.sub, valueOf(row)), carrier: carrierOf(row) }, terms))
    .map((row) => row.ref);
}

/** "Only matches" on the List: the matching rows, or every row when nothing matches (beside "No matches"). */
export function listShown(rows, hits, only) {
  if (!only || !hits.length) return rows;
  const keep = new Set(hits);
  return rows.filter((row) => keep.has(row.ref));
}
