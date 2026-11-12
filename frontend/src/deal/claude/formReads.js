// A questionnaire read's review card (plan.md §10.5; G99, G100; slice 52). Pure: no React. The entries come from the
// questionnaire's own door, worked out against the form as it stands; every question's words (its label, why it is
// left alone) come with them, and a date shows MM/DD/YYYY. A pick is "<form>:<ref>", as the apply door takes it.
import { shownAnswer } from './intakeRows';

export const pickKey = (form, ref) => `${form}:${ref}`;

/** The entries ticked as Claude proposes the read, across its forms. */
export function initialPicks(reads) {
  const out = new Set();
  (reads || []).forEach((read) =>
    (read?.entries || []).forEach((entry) => {
      if (entry.tick) out.add(pickKey(read.form, entry.ref));
    }),
  );
  return out;
}

export function togglePick(picked, key) {
  const next = new Set(picked);
  if (next.has(key)) next.delete(key);
  else next.add(key);
  return next;
}

export function samePicks(a, b) {
  return a.size === b.size && [...a].every((key) => b.has(key));
}

/** The apply body: nothing for "Use this scan ▸" (the read as Claude proposes it), else exactly what is ticked. */
export function applyBody(picked, initial) {
  return samePicks(picked, initial) ? {} : { select: [...picked] };
}

/** "Medical Conditions 2 → a new row" or "Current plan 1 → row 1 of the form". */
export function rowWhere(entry) {
  const what = `${entry.block_label} ${entry.number}`;
  return entry.target_number ? `${what} → row ${entry.target_number} of the form` : `${what} → a new row`;
}

/** A question's words before its answer: "Medical Category:", "How many …? 2" (the form's own colon kept once). */
function asked(label) {
  const words = String(label || '').replace(/[\s:]+$/, '');
  return /\?$/.test(words) ? `${words} ` : `${words}: `;
}

/** "Medical Category: Cancer · How many total individuals …? 2 (was 1)". */
export function rowText(entry) {
  return (entry.values || [])
    .map((value) => `${asked(value.label)}${shownAnswer(value.new)}${value.old ? ` (was ${shownAnswer(value.old)})` : ''}`)
    .join(' · ');
}

/** {answers, rows, conflicts}: the card's three parts, with what their rows show. */
export function readSections(read) {
  const entries = read?.entries || [];
  const shown = (entry) => ({ ...entry, shown: shownAnswer(entry.new), was: shownAnswer(entry.old) });
  return {
    answers: entries.filter((entry) => entry.kind === 'answer' && entry.state !== 'conflict').map(shown),
    rows: entries.filter((entry) => entry.kind === 'row').map((entry) => ({ ...entry, where: rowWhere(entry), text: rowText(entry) })),
    conflicts: entries.filter((entry) => entry.state === 'conflict').map(shown),
  };
}

/** Why the read cannot be used now, or '': a form signed after it was read (G99: never applied to a signed form). */
export function signedNote(reads) {
  const signed = (reads || []).filter((read) => read?.signed).map((read) => read.label);
  if (!signed.length) return '';
  return `${signed.join(' and ')} ${signed.length === 1 ? 'is' : 'are'} signed, so nothing from this read can be used. Reopen the form on the Questionnaire tab first.`;
}
