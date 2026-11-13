/*
 * The questionnaires on the client's page, pure (plan.md §8.20; G83–G98, L91; slice 58). The server is the one engine
 * (G25: no cascade, visibility or progress rule here): each form's `state` says what is on screen, its values, bases,
 * rows, blanks and progress, and a save answers it again. These only turn it into the page's answers (refs
 * `q:<form>:<slot>`, in the same reducer as the intake's and the census's), pick the latest state of each form, and
 * word the to-do rail and the signature's hold, as old Vantage 891f1b3 `BenefitsClientPortal.jsx` did.
 */

export const formRef = (form, slot) => `q:${form}:${slot}`;

/** {values, bases} of every slot on screen of every form asked online, from the states given. */
export function formSeeds(cards, states = {}) {
  const values = {};
  const bases = {};
  for (const card of cards || []) {
    const state = states[card.form] || card.state;
    if (!state) continue;
    for (const slot of state.order || []) {
      values[formRef(card.form, slot)] = state.values?.[slot] ?? '';
      bases[formRef(card.form, slot)] = state.bases?.[slot] ?? '';
    }
  }
  return { values, bases };
}

/** The form's draft for the paper layout: what is typed here and not taken yet, by slot. */
export function formDraft(form, answers) {
  const prefix = `q:${form}:`;
  const out = {};
  for (const [ref, value] of Object.entries(answers?.values || {})) {
    if (!ref.startsWith(prefix)) continue;
    const sent = answers.sent?.[ref];
    if (value !== sent && !(value === '' && (sent === undefined || sent === null))) out[ref.slice(prefix.length)] = value;
  }
  return out;
}

/** The spec as this page shows it: only the sections holding something on screen (a narrowed form's own). */
export function specOnScreen(spec, state) {
  if (!spec || !state) return spec;
  const onScreen = new Set(state.order || []);
  const blocks = new Set(state.blocks || []);
  const sections = spec.sections.filter(
    (section) => section.fields.some((field) => onScreen.has(field.key)) || section.blocks.some((key) => blocks.has(key)),
  );
  return { ...spec, sections };
}

/** A to-do row of a form, recounted from its latest state (G95: done only once signed, or a narrowed form answered). */
export function liveFormItem(item, card, state) {
  if (!card) return item;
  if (!state) return { ...item, signed: Boolean(card.signed) };
  const { filled, total } = state.progress || { filled: 0, total: 0 };
  const signed = Boolean(card.signed);
  const done = signed || (card.narrowed && filled >= total);
  return { ...item, filled, total, signed, narrowed: card.narrowed, done };
}

/** The words beside a form's to-do row (old `todoStatus`): "signed", "3 of 9", "9 of 9 — please sign". */
export function formStatus(item) {
  if (item.signed) return 'signed';
  if (item.total === undefined) return item.done ? 'received' : 'needed';
  const count = `${item.filled} of ${item.total}`;
  if (item.narrowed) return count;
  return item.filled >= item.total ? `${count} — please sign` : count;
}

/** "Not signed yet — 2 required answers are still blank." for a signature the blanks held. */
export function holdWords(hold) {
  const blank = Math.max(0, (hold?.total || 0) - (hold?.filled || 0));
  return `Not signed yet — ${blank} required answer${blank === 1 ? ' is' : 's are'} still blank.`;
}

/** The intro over a form (old words): a narrowed ask, or the whole form to review and sign. */
export function introWords(card) {
  if (card.narrowed) {
    return 'Your broker needs these questions from this form. Your answers save automatically — you can close this page and come back to the same link.';
  }
  return 'Your broker has pre-filled everything we already know. Please review it, answer the remaining questions, and sign at the bottom. Your answers save automatically — you can close this page and come back to the same link.';
}
