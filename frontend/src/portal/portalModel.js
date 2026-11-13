/*
 * The client portal's pure rules (plan.md §8.20; L81, L83, L95, L96; Part L, L.6). Ported from old Vantage 891f1b3
 * `BenefitsClientPortal.jsx` (`conditionMet`, `computeChecklist`, `todoStatus`, `portalBases`, the compare-and-set
 * bookkeeping) onto 2V's payload: every answer is a ref (`intake:<key>`, `intake:block:<block>`,
 * `census:<member>:<column>`, and from slice 58 `q:<form>:<slot>`, questionnaireModel.js) with the value the page
 * shows and its base (a version stamp, never the value).
 *
 * The answers' state is one reducer: `values` (what is on screen), `sent` (what the server last took), `bases`,
 * `conflicts` (someone else changed it: keep theirs or use mine) and `errors` (refused, until changed again). What
 * goes in the next save is `pendingAnswers`: only what changed since it was last taken (L.6 Ch. 14g).
 */
import { draftOf, isBlank } from '../deal/shared/fieldValue';
import { formSeeds, formStatus, liveFormItem } from './questionnaireModel';

export const intakeRef = (key) => `intake:${key}`;
export const blockRef = (block) => `intake:block:${block}`;
export const cellRef = (memberId, column) => `census:${memberId}:${column}`;

const ANSWER_BLOCKS = ['contacts', 'coverage', 'lines'];

/** {values, bases} from a payload: the value each ref shows and the base it was read under. */
export function seeds(page) {
  const values = {};
  const bases = {};
  for (const section of page?.intake?.sections || []) {
    for (const field of section.fields) {
      values[intakeRef(field.key)] = draftOf(field.value);
      bases[intakeRef(field.key)] = field.base;
    }
  }
  for (const block of ANSWER_BLOCKS) {
    const found = page?.intake?.blocks?.[block];
    if (found) {
      values[blockRef(block)] = found.value || [];
      bases[blockRef(block)] = found.base;
    }
  }
  for (const person of page?.people || []) {
    for (const field of person.fields) {
      values[cellRef(person.id, field.column)] = field.value || '';
      bases[cellRef(person.id, field.column)] = field.base;
    }
  }
  const forms = formSeeds(page?.questionnaires);
  return { values: { ...values, ...forms.values }, bases: { ...bases, ...forms.bases } };
}

export function same(a, b) {
  if (isBlank(a) && isBlank(b)) return true;
  return JSON.stringify(a) === JSON.stringify(b);
}

export function initialAnswers(page) {
  const { values, bases } = seeds(page);
  return { values, sent: { ...values }, bases, conflicts: {}, errors: {} };
}

function without(map, ref) {
  const next = { ...map };
  delete next[ref];
  return next;
}

/** The answers' reducer. */
export function answersReducer(state, action) {
  switch (action.type) {
    case 'set':
      return { ...state, values: { ...state.values, [action.ref]: action.value }, errors: without(state.errors, action.ref) };
    case 'saved':
      return {
        ...state,
        sent: { ...state.sent, ...action.sent },
        bases: { ...state.bases, ...action.bases },
        errors: Object.fromEntries(Object.entries(state.errors).filter(([ref]) => !(ref in action.sent))),
      };
    case 'conflicts':
      return { ...state, conflicts: { ...state.conflicts, ...Object.fromEntries(action.list.map((c) => [c.ref, c])) } };
    case 'refused':
      return { ...state, errors: { ...state.errors, ...action.errors } };
    case 'keepTheirs': {
      const conflict = state.conflicts[action.ref];
      if (!conflict) return state;
      const theirs = Array.isArray(conflict.theirs) ? conflict.theirs : draftOf(conflict.theirs);
      return {
        ...state,
        values: { ...state.values, [action.ref]: theirs },
        sent: { ...state.sent, [action.ref]: theirs },
        bases: { ...state.bases, [action.ref]: conflict.base },
        conflicts: without(state.conflicts, action.ref),
      };
    }
    case 'useMine': {
      const conflict = state.conflicts[action.ref];
      if (!conflict) return state;
      return { ...state, bases: { ...state.bases, [action.ref]: conflict.base }, conflicts: without(state.conflicts, action.ref) };
    }
    case 'adopt': {
      // A form's fresh state after a save or a row (slice 58): the slots it now shows that this page did not know yet
      // join with the value and base the server read them under; anything known stays as it is.
      const values = { ...state.values };
      const sent = { ...state.sent };
      const bases = { ...state.bases };
      for (const [ref, base] of Object.entries(action.bases || {})) {
        if (!(ref in bases)) bases[ref] = base;
        if (!(ref in values)) {
          values[ref] = action.values?.[ref] ?? '';
          sent[ref] = values[ref];
        }
      }
      return { ...state, values, sent, bases };
    }
    case 'reseed': {
      // A fresh payload (a poll saw the form change, or people were added): its values and bases, keeping anything
      // typed here that has not been taken yet.
      const next = initialAnswers(action.page);
      for (const [ref, value] of Object.entries(state.values)) {
        if (ref in next.values && !same(value, state.sent[ref])) next.values[ref] = value;
      }
      return { ...next, conflicts: state.conflicts, errors: state.errors };
    }
    default:
      return state;
  }
}

/** {ref: {value, base}}: what changed since the server last took it, less what waits on a conflict or a refusal. */
export function pendingAnswers(state) {
  const out = {};
  for (const [ref, value] of Object.entries(state.values)) {
    if (ref in state.conflicts || ref in state.errors) continue;
    if (!same(value, state.sent[ref])) out[ref] = { value, base: state.bases[ref] ?? '' };
  }
  return out;
}

/** The `sent` map a save took: each ref's value as it was sent. */
export function sentValues(answers) {
  return Object.fromEntries(Object.entries(answers).map(([ref, entry]) => [ref, entry.value]));
}

/** A question's rule (§4.5 `shown_when`; old `conditionMet`, intake/values.py `shown`) over a raw answer. */
export function ruleMet(rule, raw) {
  if (!rule) return true;
  const text = String(Array.isArray(raw) ? raw.join(', ') : (raw ?? '')).trim();
  const op = rule.op || 'nonempty';
  if (op === 'nonempty') return text !== '';
  if (op === 'eq') return text === String(rule.value ?? '');
  const number = parseFloat(text.replace(/[$,]/g, ''));
  const target = parseFloat(String(rule.value));
  if (Number.isNaN(number) || Number.isNaN(target)) return false;
  if (op === 'gt') return number > target;
  if (op === 'gte') return number >= target;
  return false;
}

/** Whether a question shows now: its rule re-read as they type when the page also asks its question, else as the
 * server read it. */
export function fieldShown(field, values) {
  return field.shown_when ? ruleMet(field.shown_when, values[intakeRef(field.shown_when.field)]) : field.shown;
}

/** The to-do list recounted from what is on screen and the files staged (old `computeChecklist`): the server's
 * rule (review/rules/portal.py `rail`), so the counts never jump on the first keystroke. */
export function liveRail(page, values, staged = {}, states = {}) {
  const items = (page?.checklist?.items || []).map((item) => {
    if (item.kind === 'questionnaire') {
      const card = (page.questionnaires || []).find((one) => `questionnaire_${one.form}` === item.key);
      return liveFormItem(item, card, card && (states[card.form] || card.state));
    }
    if (item.key === 'intake') {
      const shown = (page.intake?.sections || []).flatMap((s) => s.fields).filter((f) => fieldShown(f, values));
      const filled = shown.filter((f) => f.locked || !isBlank(values[intakeRef(f.key)])).length;
      return { ...item, filled, total: shown.length, done: filled >= shown.length };
    }
    if (item.key === 'people') {
      const cells = (page.people || []).flatMap((p) => p.fields.map((f) => values[cellRef(p.id, f.column)]));
      const filled = cells.filter((value) => !isBlank(value)).length;
      return { ...item, filled, total: cells.length, done: filled >= cells.length };
    }
    if (item.key === 'census' && staged.census_file?.length) return { ...item, done: true, staged: true };
    if (item.kind === 'document' && staged[item.key.slice(4)]?.length) return { ...item, done: true, staged: true };
    return item;
  });
  const done = items.filter((item) => item.done).length;
  return { items, done, total: items.length };
}

/** The words beside a to-do row (old `todoStatus`). */
export function todoStatus(item) {
  if (item.kind === 'questionnaire') return formStatus(item);
  if (item.kind === 'fields') return `${item.filled} of ${item.total}`;
  if (item.staged) return 'attached — save to send';
  if (item.done) return 'received';
  return 'needed';
}

export function plural(count, one, many = `${one}s`) {
  return `${count} ${count === 1 ? one : many}`;
}

export function expiryWords(days) {
  return `Secure link · expires in ${plural(days, 'day')}`;
}

/** "Saved automatically at 3:41 PM — you can come back to this link any time." (old `stamp`). */
export function savedWords(prefix, when = new Date()) {
  const time = when.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
  return `${prefix} at ${time} — you can come back to this link any time.`;
}

/** A person's fields under their headings, in the order they come (old `groupCensusFields`). */
export function groupFields(fields) {
  const groups = [];
  const index = {};
  for (const field of fields || []) {
    const key = field.group || '';
    if (index[key] === undefined) {
      index[key] = groups.length;
      groups.push({ key, label: field.group_label || '', fields: [] });
    }
    groups[index[key]].fields.push(field);
  }
  return groups;
}

/** Nothing on the page asks for anything ("Nothing is needed from you right now", L105). */
export function nothingAsked(page) {
  const intake = page?.intake;
  const asksIntake = Boolean(intake && (intake.sections.length || Object.keys(intake.blocks || {}).length));
  const asksForms = Boolean(page?.questionnaires?.length);
  return (
    !asksIntake && !asksForms && !page?.people?.length && !page?.census_file && !page?.documents?.length && !page?.add_people
  );
}
