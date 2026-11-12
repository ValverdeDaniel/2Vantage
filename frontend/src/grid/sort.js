/*
 * Sorting a grid's rows by one column (plan.md §8.21; F32, F33). Pure. A header click sorts by that column and a
 * second click flips the direction; blanks sort last either way, so an unpriced plan never heads a sort by price.
 * While ✎ Edit is on, a grid sorted by a value holds its order (`holdOrder`), so a typed number never moves the row
 * out from under the editor; a new row joins at the end, and the order is taken again when the person changes the
 * sort or a filter themselves (its `key`).
 */

const blank = (value) => value === null || value === undefined || value === '' || Number.isNaN(value);

/** -1, 0 or 1 for two cell values: numbers by size, text without case. Blanks are handled by `sortBy`. */
export function compareValues(a, b) {
  if (typeof a === 'number' && typeof b === 'number') return a === b ? 0 : a < b ? -1 : 1;
  const x = String(a).toLowerCase();
  const y = String(b).toLowerCase();
  return x === y ? 0 : x < y ? -1 : 1;
}

/** `items` sorted by `value(item)`, `dir` 1 ascending or -1 descending; stable, blanks last. */
export function sortBy(items, value, dir = 1) {
  return items
    .map((item, index) => ({ item, index, v: value(item) }))
    .sort((a, b) => {
      const ea = blank(a.v);
      const eb = blank(b.v);
      if (ea || eb) return ea === eb ? a.index - b.index : ea ? 1 : -1;
      return compareValues(a.v, b.v) * dir || a.index - b.index;
    })
    .map((entry) => entry.item);
}

/** The sort after a header click on `key`: the same key flips its direction, another starts ascending. */
export function nextSort(sort, key) {
  if (sort.key === key) return { key, dir: -sort.dir };
  return { key, dir: 1 };
}

/**
 * The order to draw while the order is held (F33): `held` is {key, ids} or null, `key` names the sort and filters
 * the person chose, `ids` the order a fresh sort gives now and `exists` the ids still on the grid. Returns
 * {ids, held}: a new key takes the fresh order; the same key keeps the held order (rows gone from the grid drop,
 * rows a filter would now hide stay) and puts new rows last.
 */
export function holdOrder(held, key, ids, exists) {
  if (!held || held.key !== key) return { ids, held: { key, ids } };
  const kept = held.ids.filter((id) => exists.has(id));
  const known = new Set(held.ids);
  const added = ids.filter((id) => !known.has(id));
  const next = [...kept, ...added];
  const same = next.length === held.ids.length && next.every((id, i) => id === held.ids[i]);
  return { ids: next, held: same ? held : { key, ids: next } };
}
