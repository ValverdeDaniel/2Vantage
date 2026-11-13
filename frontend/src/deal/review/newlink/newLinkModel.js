// The minimal New link's state and the request body it sends (plan.md §7.13 `POST deals/{id}/review/requests/`; L40,
// L55–L57, L61, L64, L66). Pure. The server checks everything and answers the floor; nothing here decides a rule.

export const NOTHING = '';

/** The builder's doors (L41): `?preset=required` asks what marketing still needs, `census-missing` the census gaps. */
export function presetState(preset) {
  const state = initialState();
  if (preset === 'required') state.intake = 'required';
  if (preset === 'census-missing') state.census = 'missing';
  return state;
}

export function initialState() {
  return {
    contactIds: [], // the client's contacts picked, in the order picked
    typed: [], // [{name, email}] people typed in who are not contacts
    intake: NOTHING, // an intake scope key, or nothing
    census: NOTHING, // a census scope key, or nothing
    censusFile: false,
    documents: false, // any documents the checklist still needs
    security: 'link',
    blank: false,
    expiresOn: '', // YYYY-MM-DD, or '' for the sliding default
    message: '',
  };
}

/** The asks of §6.12's shape, only the parts picked. */
export function asksOf(state) {
  const asks = {};
  if (state.intake) asks.intake = { scope: state.intake };
  if (state.census || state.censusFile) asks.census = { scope: state.census || 'none', file: state.censusFile };
  if (state.documents) asks.documents = { missing: true };
  return asks;
}

export function hasAsk(state) {
  return Object.keys(asksOf(state)).length > 0;
}

/** How many links Create makes: one per person, or one private link to nobody named. */
export function linkCount(state) {
  return Math.max(1, state.contactIds.length + state.typed.length);
}

export function whoCount(state) {
  return state.contactIds.length + state.typed.length;
}

/** The POST body. */
export function bodyOf(state) {
  return {
    people: [...state.contactIds.map((id) => ({ contact_id: id })), ...state.typed.map(({ name, email }) => ({ name, email }))],
    asks: asksOf(state),
    message: state.message.trim(),
    security: state.security,
    blank: state.blank,
    ...(state.expiresOn ? { expires_on: state.expiresOn } : {}),
  };
}

/** What the dry run needs to say the floor: only what can raise it. */
export function floorKey(state) {
  return JSON.stringify(asksOf(state));
}

/** A person typed in, trimmed; null when there is no name. */
export function typedPerson(name, email) {
  const clean = String(name || '').trim().replace(/\s+/g, ' ');
  return clean ? { name: clean, email: String(email || '').trim() } : null;
}

/** Toggle an id in a list, keeping the order picked. */
export function toggled(list, id) {
  return list.includes(id) ? list.filter((item) => item !== id) : [...list, id];
}

/** 'YYYY-MM-DD' of a local day `days` from `from`. */
export function dayIn(days, from = new Date()) {
  const when = new Date(from.getFullYear(), from.getMonth(), from.getDate() + days);
  const pad = (n) => String(n).padStart(2, '0');
  return `${when.getFullYear()}-${pad(when.getMonth() + 1)}-${pad(when.getDate())}`;
}

/** "Create link" / "Create 3 links" / "Creating…" */
export function createWords(state, creating) {
  if (creating) return 'Creating…';
  const count = linkCount(state);
  return `Create ${count > 1 ? `${count} links` : 'link'}`;
}
