/*
 * The Questionnaire tab's pure helpers (plan.md §8.11; G25, G36–G41). The server is the one engine: each payload says
 * which slots are on screen and in what order (`order`), which required ones are blank (`blanks`) and each dependent
 * picker's option key (`options`). These only read it — no visibility, effect or progress rule lives here.
 *
 * A slot is `field` (a scalar) or `block.<row id>.field` (a row's answer), as the server stores it.
 */

/** {block, rowId, field} of a slot key. */
export function parseSlot(slot) {
  const parts = String(slot).split('.');
  if (parts.length === 3) return { block: parts[0], rowId: Number(parts[1]), field: parts[2] };
  return { block: '', rowId: 0, field: parts[0] };
}

export function slotKey(block, rowId, field) {
  return block ? `${block}.${rowId}.${field}` : field;
}

/** The spec's field for a slot, or null. */
export function fieldOf(spec, slot) {
  const { block, field } = parseSlot(slot);
  const fields = block ? spec.blocks[block]?.fields || [] : spec.sections.flatMap((section) => section.fields);
  return fields.find((one) => one.key === field) || null;
}

/** The text a box shows: what is being typed, else the server's effective value. */
export function shownValue(data, draft, slot) {
  if (Object.prototype.hasOwnProperty.call(draft, slot)) return draft[slot];
  return data.values?.[slot] ?? '';
}

const NONE = Object.freeze([]);

/** A picker's options: its own list, or its row's slice of a dependent table (G12). The same array each time, so a
 * memoised input never re-renders for nothing. */
export function optionsFor(spec, field, optionKey) {
  if (field.options) return field.options;
  if (!field.options_table || !optionKey) return NONE;
  const parent = optionKey.slice(field.options_table.length + 1);
  return spec.tables?.[field.options_table]?.[parent] || NONE;
}

/** The draft once a save landed: only what that save carried goes, and only while it still says the same, so an
 * answer typed during the save survives (G40, D-204 #5). */
export function withoutSaved(draft, saved) {
  const rest = { ...draft };
  Object.entries(saved).forEach(([key, value]) => {
    if (rest[key] === value) delete rest[key];
  });
  return rest;
}

/** Where Enter (the very next question) or Tab (the next blank required one) goes from `from` (G41): both wrap,
 * Shift goes back, never the question it started from; null when there is none. */
export function nextSlot(order, blanks, from, { required = false, back = false } = {}) {
  const pool = back ? [...order].reverse() : order;
  const at = pool.indexOf(from);
  const rotated = at < 0 ? pool : [...pool.slice(at + 1), ...pool.slice(0, at)];
  const blank = new Set(blanks);
  return rotated.find((slot) => !required || blank.has(slot)) || null;
}

/** The fields a row (or the scalars of a section) shows, in the spec's order, from the slots on screen. */
export function shownFields(fields, onScreen, block = '', rowId = 0) {
  return fields.filter((field) => !field.auto && onScreen.has(slotKey(block, rowId, field.key)));
}

/** "N% complete" and its colour (G42). */
export function progressBadge(progress) {
  const pct = progress?.pct ?? 0;
  return { text: `${pct}% complete`, tone: pct >= 100 ? 'bb-green' : 'bb-amber' };
}

/** Whether a slot's answer reads as the deal's (live prefill) or the client's waiting answer (G32, G136). */
export function originWord(status) {
  if (status === 'prefill') return 'Filled in from the deal';
  if (status === 'client') return 'From the client';
  return '';
}
