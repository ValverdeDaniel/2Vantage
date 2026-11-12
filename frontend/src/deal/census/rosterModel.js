/*
 * The roster grid's rules, pure (plan.md §8.10, §8.21; C1–C3, C6; the old CensusGrid.jsx at 891f1b3): which line
 * groups the chips toggle and which start hidden, the columns drawn, a cell's colour, words and hover, a dependent's
 * label, and the cached page with a person's new values laid over it. The vocabularies (columns, groups, choices,
 * widths) come from /api/meta/ (`meta.census`); nothing here lists a column.
 */

// A cell's colour by its review mark (OQ28; the old `reviewMarkClass`), else by its status.
const REVIEW_CLASS = {
  check: 'bb-cell-check',
  to_check: 'bb-cell-low',
  ignored: 'bb-cell-ignored',
  approved: 'bb-cell-approved',
};
const REVIEW_TITLE = {
  check: 'Needs checking — someone flagged this value',
  to_check: 'To review — the reader was unsure of this value',
  ignored: 'Warning ignored — the value stays as read',
  approved: 'Approved — a person checked this value',
};
const RELAYED = new Set(['client', 'relay']);

/** The groups a chip turns on and off (C2): those of lines (medical, dental, vision, life, disability). */
export function chipGroups(census) {
  const lines = census?.group_lines || {};
  return (census?.groups || []).filter((group) => lines[group.key]);
}

/** The chips that start off: a line group none of whose columns the server put in scope (C2's default). */
export function defaultHidden(census, columns) {
  const inScope = new Set(columns || []);
  const fields = census?.fields || [];
  return new Set(
    chipGroups(census)
      .filter((group) => !fields.some((field) => field.group === group.key && inScope.has(field.key)))
      .map((group) => group.key),
  );
}

/** The columns drawn, in display order: every field but those of hidden groups. */
export function shownFields(census, hidden) {
  return (census?.fields || []).filter((field) => !hidden.has(field.group));
}

/** 'missing' (a required blank) · 'client' (the client's, or entered for them) · 'high' (on file) · 'na' (blank). */
export function cellStatus(member, key) {
  if ((member.missing || []).includes(key)) return 'missing';
  if (!member.values?.[key]) return 'na';
  return RELAYED.has(member.sources?.[key]?.origin) ? 'client' : 'high';
}

/** The red or amber underline of a validation issue (one severity word, C21; the old `issueClass`). */
export function issueClass(issues) {
  const found = issues || [];
  if (found.some((issue) => issue.severity === 'error')) return 'bnf-cell-error';
  if (found.some((issue) => issue.severity === 'warning')) return 'bnf-cell-warn';
  return '';
}

export function cellClass(member, key) {
  const base = REVIEW_CLASS[member.review?.[key]] || `bb-cell-${cellStatus(member, key)}`;
  return [base, issueClass(member.issues?.[key])].filter(Boolean).join(' ');
}

/** What a coded column accepts, in words (the server sends the choices); a long list is pointed at, not recited. */
export function acceptsText(field) {
  const values = (field.choices || []).map((choice) => choice.value);
  if (!values.length) return '';
  return values.length > 8 ? 'Start typing to pick from the list.' : `Accepts: ${values.join(' · ')}`;
}

/** The header's hover: the column's help, then what it accepts. */
export function columnHint(field) {
  return [field.help, acceptsText(field)].filter(Boolean).join('\n');
}

/** The ⓘ beside a coded column's label: its glyph plus the header's gap. */
export const hintRoom = (field) => (field.choices?.length ? 16 : 0);

/** A cell's hover: its mark, then its issues (else what the column accepts) (C3). */
export function cellTitle(member, field) {
  const issues = member.issues?.[field.key] || [];
  const rest = issues.length ? issues.map((issue) => issue.message).join('\n') : acceptsText(field);
  return [REVIEW_TITLE[member.review?.[field.key]], rest].filter(Boolean).join('\n') || undefined;
}

/** A stored value as the grid shows it: a date `MM/DD/YYYY` (§5.3.1), anything else as stored. */
export function shownValue(field, value) {
  const text = value == null ? '' : String(value);
  const iso = /^(\d{4})-(\d{2})-(\d{2})$/.exec(text);
  return field.type === 'date' && iso ? `${iso[2]}/${iso[3]}/${iso[1]}` : text;
}

/** The cell's words: '＋ Add' on a required blank (locked or not, as the old grid said it), '—' on any other blank. */
export function cellText(member, field) {
  const value = member.values?.[field.key];
  if (value) return shownValue(field, value);
  return cellStatus(member, field.key) === 'missing' ? '＋ Add' : '—';
}

/** "Avery Smith", from the person's own name cells. */
export function personName(member) {
  const value = (key) => String(member.values?.[key] || '').trim();
  return [value('first_name'), value('last_name')].filter(Boolean).join(' ');
}

/** Who a dependent is to the employee above, short enough for the Person column. */
export function depLabel(member) {
  const relationship = String(member.values?.relationship || '').trim();
  if (!relationship) return 'dep';
  return /domestic/i.test(relationship) ? 'Partner' : relationship;
}

/** The write queue's cell: "<member id>|<key>". */
export const cellOf = (memberId, key) => `${memberId}|${key}`;

export function splitCell(cell) {
  const at = cell.indexOf('|');
  return [Number(cell.slice(0, at)), cell.slice(at + 1)];
}

/** The cached page with one person's typed value shown at once (the server's answer corrects it). */
export function withValue(page, memberId, key, value) {
  if (!page?.members) return page;
  return {
    ...page,
    members: page.members.map((member) =>
      member.id === memberId ? { ...member, values: { ...member.values, [key]: value ?? '' } } : member,
    ),
  };
}

/** The cached page with a hand edit's answer laid over it (C6): the person, the stored summary and review counts. */
export function withAnswer(page, answer) {
  if (!page?.members || !answer?.member) return page;
  return {
    ...page,
    summary: answer.summary ?? page.summary,
    review: answer.review ?? page.review,
    members: page.members.map((member) => (member.id === answer.member.id ? answer.member : member)),
  };
}

/** "census:<id>:<key>" refs of the picked cells that hold a value (a blank takes no mark). */
export function filledRefs(page, picked) {
  const byId = new Map((page?.members || []).map((member) => [member.id, member]));
  return [...picked].filter((ref) => {
    const [, id, key] = ref.split(':');
    return Boolean(byId.get(Number(id))?.values?.[key]);
  });
}
