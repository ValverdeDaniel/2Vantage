// Edit mode's pure helpers (plan.md §8.8; L34, L35; old 891f1b3 `RequestPage.jsx` edit mode, `requestEntryFlow.js`):
// which box comes next — Enter goes to the next box, Tab to the next required blank — and what a box would save. The
// server's owners clean and store every value; nothing here decides one.

/**
 * The boxes in page order: [{ref, required, blank}] from the intake items (questions only, never a block or a file)
 * or the census blanks (person by person).
 */
export function intakeBoxes(items) {
  return (items || [])
    .filter((item) => item.ref.startsWith('intake:') && !item.ref.startsWith('intake:block:'))
    .map((item) => ({ ref: item.ref, required: Boolean(item.needed), blank: item.status === 'missing' }));
}

export function censusBoxes(blanks) {
  return (blanks?.people || []).flatMap((person) => person.cells.map((cell) => ({ ref: cell.ref, required: cell.required, blank: true })));
}

/** The ref after `ref`: the next box (Enter), or with `requiredOnly` the next required blank (Tab); '' at the end. */
export function nextBox(boxes, ref, requiredOnly = false) {
  const at = boxes.findIndex((box) => box.ref === ref);
  const rest = boxes.slice(at + 1);
  const found = requiredOnly ? rest.find((box) => box.required && box.blank) : rest[0];
  return found ? found.ref : '';
}

/** What a box saves: its typed text when it holds something new, else null (an untouched or emptied box saves nothing). */
export function toSave(draft, saved) {
  const text = String(draft ?? '').trim();
  if (!text || text === saved) return null;
  return text;
}

/** "Saved as the client's, entered by you" / "Saved as typed by you": what the toggle means for the next save. */
export function originWords(relay) {
  return relay ? 'Saved as the client’s answers, entered by you' : 'Saved as typed by you';
}
