/*
 * The board's columns (plan.md §8.14; F31, F32, F41; the old AdvisorTab's activeColumns and planSections). Pure.
 * Which keys a preset shows on a line comes from `/api/meta/` (`board.columns`, from quotes/board_presets.py), never
 * from a list here. ☐, ★ and Plan are pinned; a column the sort reads stays on screen even when the preset hides it,
 * so the board shows why the plans stand where they do. Transposed, the same keys are rows in the line's groups.
 */

const PINNED_KINDS = { select: 'select', star: 'star', carrier: 'plan' };
const SORT_ONLY = ['proposal', 'closest'];
const NUMERIC = ['amount', 'percent', 'rate', 'rate4', 'number'];

/** {key: field} from meta's plan fields. */
export function fieldsByKey(meta) {
  return Object.fromEntries((meta?.plans?.fields ?? []).map((field) => [field.key, field]));
}

/** The keys the preset shows on the line, with the sort's column pinned before Flags when the preset hides it. */
export function shownKeys(meta, line, preset, sortKey) {
  const board = meta?.board ?? {};
  const keys = board.columns?.[line]?.[preset] ?? board.columns?.[line]?.[board.default_preset] ?? [];
  const lineKeys = new Set(board.columns?.[line]?.all ?? []);
  const pinned =
    sortKey && !keys.includes(sortKey) && !SORT_ONLY.includes(sortKey) && sortKey !== 'flags' && lineKeys.has(sortKey)
      ? [sortKey]
      : [];
  const at = keys.indexOf('flags');
  return at < 0 ? [...keys, ...pinned] : [...keys.slice(0, at), ...pinned, ...keys.slice(at)];
}

/** One column: {key, kind ('select' | 'star' | 'plan' | 'derived' | 'field'), label, sortable, numeric, field}. */
export function column(meta, key, fields = fieldsByKey(meta)) {
  if (PINNED_KINDS[key]) {
    const pinned = meta?.board?.pinned?.find((p) => p.key === key);
    return { key, kind: PINNED_KINDS[key], label: pinned?.label ?? '', sortable: Boolean(pinned?.sort), numeric: false };
  }
  const derived = meta?.board?.derived?.find((d) => d.key === key);
  if (derived) {
    return { key, kind: 'derived', label: derived.label, sortable: derived.sort, numeric: key === 'total' || key === 'delta' };
  }
  const field = fields[key];
  if (!field) return null;
  return { key, kind: 'field', label: field.label, sortable: true, numeric: NUMERIC.includes(field.type), field };
}

/** The board's columns in rows layout: ☐, ★, Plan, then the preset's. */
export function boardColumns(meta, line, preset, sortKey) {
  const fields = fieldsByKey(meta);
  return ['select', 'star', 'carrier', ...shownKeys(meta, line, preset, sortKey)]
    .map((key) => column(meta, key, fields))
    .filter(Boolean);
}

/**
 * Transposed: the preset's columns as rows, in the line's groups and order (`groups` from the comparison), each
 * derived row where board_presets places it ("start" rows open their group, the rest close it; the cost group
 * closes the grid). → [{group, label, keys}]; a key the layout cannot place still shows, last, under no heading.
 */
export function sections(meta, groups, keys) {
  const wanted = new Set(keys);
  const derived = (meta?.board?.derived ?? []).filter((d) => wanted.has(d.key));
  const labels = meta?.board?.group_labels ?? {};
  const out = groups.map((group) => ({
    group: group.key,
    label: group.label,
    keys: [
      ...derived.filter((d) => d.group === group.key && d.at === 'start').map((d) => d.key),
      ...group.fields.filter((key) => wanted.has(key)),
      ...derived.filter((d) => d.group === group.key && d.at !== 'start').map((d) => d.key),
    ],
  }));
  for (const d of derived) {
    if (out.some((section) => section.group === d.group)) continue;
    const section = { group: d.group, label: labels[d.group] ?? d.group, keys: derived.filter((x) => x.group === d.group).map((x) => x.key) };
    if (d.at === 'start') out.unshift(section);
    else out.push(section);
  }
  const placed = new Set(out.flatMap((section) => section.keys));
  const shown = out.filter((section) => section.keys.length);
  const rest = keys.filter((key) => !placed.has(key));
  return rest.length ? [...shown, { group: null, label: '', keys: rest }] : shown;
}

/** The keys a ⤓ Export prints, in the order drawn: the columns (rows layout) or the rows (transposed). */
export function exportKeys(columns, sectionList = null) {
  if (sectionList) return sectionList.flatMap((section) => section.keys);
  return columns.filter((col) => col.kind === 'derived' || col.kind === 'field').map((col) => col.key);
}
