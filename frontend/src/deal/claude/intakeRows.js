// An intake read's change set as its review body draws it (plan.md §10.5; B40, D112). Pure: no React. Every word for
// a value comes with the change set (labels, funding words, the role) or is the value itself; dates show MM/DD/YYYY.

const ISO_DATE = /^(\d{4})-(\d{2})-(\d{2})$/;

/** A stored answer as the form shows it: a list joined, an ISO date as MM/DD/YYYY, a blank as "—". */
export function shownAnswer(value) {
  if (value === null || value === undefined || value === '') return '—';
  if (Array.isArray(value)) return value.length ? value.join(', ') : '—';
  const date = ISO_DATE.exec(String(value));
  return date ? `${date[2]}/${date[3]}/${date[1]}` : String(value);
}

/** "Medical — add: Example Health Plan · Fully insured · Renewal date 01/01/2027" or "… — fill the blanks: …". */
export function coverageText(item) {
  const parts = (item.values || []).map((value) =>
    value.key === 'carrier' ? value.shown || value.new : `${value.label} ${value.shown || value.new}`,
  );
  return `${item.label} — ${item.coverage ? 'fill the blanks' : 'add'}: ${parts.join(' · ')}`;
}

/** "Jordan Example, HR Manager · jordan@example.com · HR Admin". */
export function contactText(item) {
  const who = [item.name, item.title].filter(Boolean).join(', ');
  return [who, item.email, item.phone, item.role_label].filter(Boolean).join(' · ');
}

/** {answers, coverage, contacts}: the items of each part, with what their rows show. */
export function intakeRows(changeSet) {
  const items = changeSet?.items || [];
  return {
    answers: items
      .filter((item) => item.op === 'answer')
      .map((item) => ({ ...item, shown: shownAnswer(item.new), was: shownAnswer(item.old) })),
    coverage: items.filter((item) => item.op === 'coverage').map((item) => ({ ...item, text: coverageText(item) })),
    contacts: items.filter((item) => item.op === 'contact').map((item) => ({ ...item, text: contactText(item) })),
  };
}
