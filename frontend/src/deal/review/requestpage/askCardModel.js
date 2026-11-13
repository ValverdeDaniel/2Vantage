// The Ask card's pure state (plan.md §7.13 `POST review/requests/{rid}/form/`; L36, L39, L42; old 891f1b3
// `useLinkBuilder.js` link mode). A tick on a question is a draft in the tray named for the request (L42 "ticks are
// drafts", so it survives a reload); what comes off, a part switched on or off, the level and each person's settings
// wait here until Update link, the one write. The server says what the request carries now (`target.on_link`) and
// decides every rule; these only say where an item stands on THIS link and build the body.

/** The change waiting for Update link: nothing yet. */
export function emptyChange() {
  return {
    off: { refs: [], columns: [], parts: [] },
    on: { intake: '', census: '', columns: [], census_file: null, documents_missing: null, blocks: [] },
    security: '',
    settings: {},
    message: null,
  };
}

const toggled = (list, value) => (list.includes(value) ? list.filter((item) => item !== value) : [...list, value]);

/** `?target=link:<id>` → {kind: 'link', id}; `new` → {kind: 'new'}; else null (All people: ticks go to the tray). */
export function targetOf(params) {
  const raw = params.get('target') || '';
  if (raw === 'new') return { kind: 'new' };
  const [kind, id] = raw.split(':');
  return kind === 'link' && /^\d+$/.test(id || '') ? { kind: 'link', id: Number(id) } : null;
}

/** How many things wait for Update link (the drafts named for the request count too). */
export function changeCount(change, target) {
  const on = change.on;
  return (
    change.off.refs.length +
    change.off.columns.length +
    change.off.parts.length +
    on.columns.length +
    on.blocks.length +
    (on.intake ? 1 : 0) +
    (on.census ? 1 : 0) +
    (on.census_file !== null ? 1 : 0) +
    (on.documents_missing !== null ? 1 : 0) +
    (change.security ? 1 : 0) +
    Object.keys(change.settings).length +
    (change.message !== null ? 1 : 0) +
    Object.keys(target?.drafted || {}).length
  );
}

/** Where an item stands on the picked link: coming_off, will_add, on_link, or its own status (asked elsewhere…). */
export function itemState(item, target, change) {
  if (change.off.refs.includes(item.ref)) return 'coming_off';
  if (target?.drafted?.[item.ref]) return 'will_add';
  if (target?.on_link?.includes(item.ref)) return 'on_link';
  return item.status;
}

export const STATE_WORDS = { coming_off: 'Coming off', will_add: 'Will be added', on_link: 'On their link' };
export const STATE_CLASSES = { coming_off: 'rr-rail-chip-off', will_add: 'rr-rail-chip-cart', on_link: 'rr-rail-chip-asked' };

/** What a tick does on the picked link: take it off, put it back, draft it for the request, or take the draft out. */
export function tickAction(item, target, change) {
  const state = itemState(item, target, change);
  if (state === 'coming_off') return { kind: 'keep', ref: item.ref };
  if (state === 'will_add') return { kind: 'undraft', id: target.drafted[item.ref] };
  if (state === 'on_link') return { kind: 'off', ref: item.ref };
  return { kind: 'draft', ref: item.ref };
}

/** The change after a person takes an item off, or keeps it after all. */
export function withOff(change, ref) {
  return { ...change, off: { ...change.off, refs: toggled(change.off.refs, ref) } };
}

/** A part's value as the switch shows it: the change's, else the request's ('' when off). */
export function partValue(target, change, part) {
  const parts = target?.parts || {};
  if (change.off.parts.includes(part)) return '';
  if (part === 'intake') return change.on.intake || (parts.intake === 'blocks' ? '' : parts.intake || '');
  if (part === 'census') return change.on.census || (parts.census === 'none' ? '' : parts.census || '');
  if (part === 'census_file') return change.on.census_file ?? Boolean(parts.census_file);
  return change.on.documents_missing ?? Boolean(parts.documents_missing);
}

/** The change after a part's switch moves to `value` ('' takes the part off). */
export function withPart(change, target, part, value) {
  const parts = target?.parts || {};
  const off = { ...change.off, parts: change.off.parts.filter((key) => key !== part) };
  const on = { ...change.on };
  if (part === 'census_file' || part === 'documents_missing') {
    const was = Boolean(parts[part]);
    on[part] = value === was ? null : value;
    return { ...change, on };
  }
  const was = part === 'intake' ? parts.intake : parts.census === 'none' ? '' : parts.census;
  on[part] = '';
  if (!value) {
    if (was) off.parts = [...off.parts, part];
  } else if (value !== was) {
    on[part] = value;
  }
  return { ...change, off, on };
}

/** The change after a census column's tick: on the link it comes off, otherwise its blanks are asked. */
export function withColumn(change, column, onLink) {
  if (onLink) return { ...change, off: { ...change.off, columns: toggled(change.off.columns, column) } };
  return { ...change, on: { ...change.on, columns: toggled(change.on.columns, column) } };
}

/** The change after one person's setting moves (blank, expires_on, nudge_on); `null` drops it. */
export function withSetting(change, linkId, key, value) {
  const own = { ...(change.settings[linkId] || {}) };
  if (value === null) delete own[key];
  else own[key] = value;
  const settings = { ...change.settings, [linkId]: own };
  if (!Object.keys(own).length) delete settings[linkId];
  return { ...change, settings };
}

/** The Update link (and dry run) body. */
export function bodyOf(change, target) {
  const on = Object.fromEntries(Object.entries(change.on).filter(([, value]) => value !== null && value !== '' && !(Array.isArray(value) && !value.length)));
  const off = Object.fromEntries(Object.entries(change.off).filter(([, value]) => value.length));
  return {
    ids: Object.values(target?.drafted || {}),
    ...(Object.keys(off).length ? { off } : {}),
    ...(Object.keys(on).length ? { on } : {}),
    ...(change.security ? { security: change.security } : {}),
    ...(Object.keys(change.settings).length ? { settings: change.settings } : {}),
    ...(change.message !== null ? { message: change.message } : {}),
  };
}

/** "Update link" / "Update 2 links" / "Updating…" */
export function updateWords(target, updating) {
  if (updating) return 'Updating…';
  const count = target?.link_ids?.length || 1;
  return count > 1 ? `Update ${count} links` : 'Update link';
}

const plural = (n, one) => `${n} ${one}${n === 1 ? '' : 's'}`;

/** "12 intake · 40 census values · their census file": what the link would ask (the dry run's live numbers). */
export function numberWords(numbers) {
  if (!numbers) return '';
  const words = [];
  if (numbers.intake) words.push(`${numbers.intake} intake`);
  if (numbers.blocks) words.push(plural(numbers.blocks, 'part'));
  if (numbers.values) words.push(plural(numbers.values, 'census value'));
  if (numbers.census_file) words.push('their census file');
  if (numbers.documents) words.push(plural(numbers.documents, 'document'));
  return words.join(' · ') || 'nothing yet';
}
