/*
 * The intake form as the screen walks it (plan.md §4.5, §5.2; B1, B2, B4, B5). Pure, over /api/meta/'s
 * `intake.form` (the questions) and the intake payload (answers, sources, hidden, needed, status, issues), so the tab
 * can ask it of the copy on screen or of an answer the server just returned.
 *
 * - `buildSections`: the four cards and their rows; the Goals card ends with the client guidance (an answer, never a
 *   question: it is never needed).
 * - `nextRow` (the old intakeFlow.js `nextOpenField`, D-161, D-205): Enter goes to the very next shown question,
 *   filled in or not; Tab (`required`) to the next blank one this deal needs (the star). Both wrap, Shift goes back,
 *   neither returns the row it started from, and both only ever name a question, never a button.
 * - `revealsOthers`: whether another question's shown-when rule hangs on this one; a move from it waits for the
 *   server, which alone says what the answer revealed.
 * - `withAnswer` / `withReply`: the answer just typed on the copy on screen, then the PATCH's reply laid over it.
 */
import { isBlank } from '../shared/fieldValue';

/** The form's cards: [{key, label, rows: [{key, question, value, visible, needed, status, issues, source}]}]. */
export function buildSections(formMeta, data) {
  const hidden = new Set(data?.hidden ?? []);
  const needed = new Set(data?.needed ?? []);
  const answers = data?.answers ?? {};
  const row = (question, guidance = false) => ({
    key: question.key,
    question,
    guidance,
    value: answers[question.key] ?? '',
    visible: !hidden.has(question.key),
    needed: needed.has(question.key),
    status: data?.status?.[question.key] ?? '',
    issues: data?.issues?.[question.key] ?? [],
    source: data?.sources?.[question.key] ?? null,
  });
  return (formMeta?.sections ?? []).map((section) => {
    const rows = section.questions.map((question) => row(question));
    if (formMeta.guidance && formMeta.guidance.section === section.key) rows.push(row(formMeta.guidance, true));
    return { key: section.key, label: section.label, rows };
  });
}

export function allRows(sections) {
  return sections.flatMap((section) => section.rows);
}

/** The next row Enter (or Tab, `required`) goes to from `fromKey`, or null when there is none. */
export function nextRow(sections, fromKey, { required = false, back = false } = {}) {
  const pool = allRows(sections);
  const ordered = back ? [...pool].reverse() : pool;
  const at = ordered.findIndex((row) => row.key === fromKey);
  const rotated = at < 0 ? ordered : [...ordered.slice(at + 1), ...ordered.slice(0, at)];
  return rotated.find((row) => row.visible && (!required || (isBlank(row.value) && row.needed))) || null;
}

/** Whether another question's shown-when rule reads this answer. */
export function revealsOthers(formMeta, key) {
  return (formMeta?.sections ?? []).some((section) => section.questions.some((q) => q.shown_when?.field === key));
}

/** The payload with one answer as typed, before the server has stored it. */
export function withAnswer(data, key, value) {
  if (!data) return data;
  const answers = { ...data.answers };
  if (isBlank(value)) delete answers[key];
  else answers[key] = value;
  return { ...data, answers };
}

const STATE = ['hidden', 'needed', 'status', 'issues', 'readiness', 'notes'];

/** The payload with the answers PATCH's reply laid over it: the changed answers and sources (null: gone), then the
 * form's state as the server now has it. */
export function withReply(data, reply) {
  if (!data) return data;
  const answers = { ...data.answers };
  const sources = { ...data.sources };
  for (const [key, value] of Object.entries(reply.answers ?? {})) {
    if (isBlank(value)) delete answers[key];
    else answers[key] = value;
  }
  for (const [key, entry] of Object.entries(reply.sources ?? {})) {
    if (entry == null) delete sources[key];
    else sources[key] = entry;
  }
  const next = { ...data, answers, sources };
  for (const name of STATE) if (name in reply) next[name] = reply[name];
  return next;
}

/** The labels of the needed questions still blank, in form order: the "Required to market" banner's (B9). */
export function missingLabels(sections) {
  const keys = new Set(missingKeys(sections));
  return allRows(sections)
    .filter((row) => keys.has(row.key))
    .map((row) => row.question.label);
}

/** Whether ☑ Select fields can tick a row (B10): a blank, an open warning or a marked answer; an answer a person
 * stands behind, with nothing to review, cannot be picked. */
export function selectable(row) {
  return isBlank(row.value) || row.status === 'to_check' || Boolean(row.source?.mark);
}

/** "Select all missing" (B10, fixed): the shown questions this deal needs that are still blank. */
export function missingKeys(sections) {
  return allRows(sections)
    .filter((row) => row.visible && row.status === 'missing')
    .map((row) => row.key);
}
