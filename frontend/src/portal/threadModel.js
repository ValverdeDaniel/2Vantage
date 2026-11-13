// The portal's follow-ups and questions, pure (plan.md §8.20; L81, L101, L106; old 891f1b3 `BenefitsClientPortal.jsx`
// newWords, THREAD_WHO). The server sends the cards (`follow_ups`) and decides what a question may be about; these word
// them, list what the page asks for the "Ask about" picker, and say when the page should post its last look.

export const THREAD_WHO = { agency: '', you: 'You asked', colleague: 'A colleague asked' };

/** "New reply" / "New note" / '' on a card. */
export function newWords(card) {
  if (card.replied) return 'New reply';
  if (card.new) return 'New note';
  return '';
}

/** Who wrote a thread entry: "You asked", "A colleague asked", or the agency's short name. */
export function whoWords(entry, short) {
  return THREAD_WHO[entry.who] || short || 'Your broker';
}

/**
 * Everything this page asks, as the server names it, for "Ask a question about…": [{ref, label}] — the intake
 * questions shown, the intake's parts, each person's asked values, each file, their census file.
 */
export function askableItems(page) {
  const out = [];
  (page?.intake?.sections || []).forEach((section) =>
    section.fields.filter((field) => field.shown).forEach((field) => out.push({ ref: `intake:${field.key}`, label: field.label })),
  );
  const blocks = page?.intake?.blocks || {};
  const BLOCKS = { contacts: 'Your contacts', coverage: 'Coverage in force', lines: 'Lines to quote', bor: 'Broker of Record' };
  Object.keys(BLOCKS).forEach((key) => {
    if (blocks[key]) out.push({ ref: `intake:block:${key}`, label: BLOCKS[key] });
  });
  (page?.people || []).forEach((person) =>
    person.fields.forEach((field) => out.push({ ref: `census:${person.id}:${field.column}`, label: `${field.label} — ${person.title}` })),
  );
  (page?.documents || []).forEach((slot) => out.push({ ref: `doc:${slot.slot}`, label: slot.label }));
  if (page?.census_file) out.push({ ref: 'census:file', label: 'Your census file' });
  (page?.questionnaires || []).forEach((card) => out.push({ ref: `qform:${card.form}`, label: card.title }));
  return out;
}

/** Whether anything of ours is new to them: the page posts its last look once it has shown it a while. */
export function hasNews(cards) {
  return (cards || []).some((card) => card.new || card.replied);
}

/** "2 need your answer" for the follow-ups head, or ''. */
export function needWords(cards) {
  const n = (cards || []).filter((card) => card.needs_answer).length;
  return n ? `${n} need${n === 1 ? 's' : ''} your answer` : '';
}
