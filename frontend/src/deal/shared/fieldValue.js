/*
 * A typed answer's text, for FieldInput and the rows that show it (plan.md §4.5, §5.2; B3). Pure: the server's one
 * cleaner (intake/values.py `clean_value`) stores and refuses; these only show a stored answer and shape what a person
 * types. A multi answer is stored as a list (B3) and typed as text ("FL, GA"): the chips follow the text, and the
 * server splits it the same way (commas, semicolons, slashes or spaces).
 */

const MULTI_SPLIT = /[,;/\s]+/;

export function isBlank(value) {
  return value == null || value === '' || (Array.isArray(value) && value.length === 0);
}

/** A stored answer as a row shows it: a list joined with commas, anything else as stored. */
export function shownValue(value) {
  if (isBlank(value)) return '';
  return Array.isArray(value) ? value.join(', ') : String(value);
}

/** The text an editor opens with: the stored answer as it would be typed. */
export function draftOf(value) {
  return shownValue(value);
}

/** The options a multi's text names (as written in the options, in typed order, once each) and the parts it does
 * not (shown as they were typed). */
export function multiParts(text, options = []) {
  const picked = [];
  const unknown = [];
  for (const part of String(text ?? '').split(MULTI_SPLIT)) {
    const word = part.trim();
    if (!word) continue;
    const match = options.find((option) => String(option).toLowerCase() === word.toLowerCase());
    if (match === undefined) unknown.push(word);
    else if (!picked.includes(match)) picked.push(match);
  }
  return { picked, unknown };
}

/** The multi's text with `option` switched on or off (a chip click); unknown parts stay for the server to refuse. */
export function toggleOption(text, option, options = []) {
  const { picked, unknown } = multiParts(text, options);
  const next = picked.includes(option) ? picked.filter((one) => one !== option) : [...picked, option];
  return [...next, ...unknown].join(', ');
}

/** Whether what the editor holds is the stored answer, so closing it writes nothing. */
export function sameAnswer(text, stored) {
  return String(text ?? '').trim() === draftOf(stored).trim();
}

/** The affix a number question wears in its editor: $ before money, % after a percent. */
export function affixes(type) {
  return { before: type === 'money' ? '$' : '', after: type === 'percent' ? '%' : '' };
}
