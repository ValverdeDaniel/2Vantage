// The sections' boards' pure helpers (plan.md §8.8; B37; C27, C30; old 891f1b3 `intakeReviewRows.js`,
// `censusReviewRows.js`): the filters, what "Select needed gaps" ticks and the census bar's words. The server owns
// every count and status; these only choose which rows show and say them. Words come from /api/meta/ `review`
// (board_statuses, census_segments, origins, rules).

export const EMPTY_INTAKE = { section: '', statuses: [], origins: [], search: '', neededOnly: false, hideAnswered: false };
export const EMPTY_CENSUS = {
  group: '',
  statuses: [],
  origins: [],
  search: '',
  requiredOnly: false,
  hideComplete: false,
  quotedOnly: false,
  hideWaived: false,
};

/** Toggle a value in a list, keeping the order. */
export function toggled(list, value) {
  return list.includes(value) ? list.filter((item) => item !== value) : [...list, value];
}

const has = (text, search) => !search || String(text || '').toLowerCase().includes(search.trim().toLowerCase());

/** How many of a board's filters are on (the "N active · Clear" line). */
export function activeCount(filters, empty) {
  return Object.keys(empty).filter((key) => JSON.stringify(filters[key]) !== JSON.stringify(empty[key])).length;
}

/** The intake rows a set of filters keeps; hidden questions only when the search names them. */
export function intakeRows(rows, filters) {
  return (rows || []).filter((row) => {
    if (!row.shown && !filters.search) return false;
    if (filters.section && row.section !== filters.section) return false;
    if (filters.statuses.length && !filters.statuses.includes(row.status)) return false;
    if (filters.origins.length && !filters.origins.includes(row.origin)) return false;
    if (filters.neededOnly && !row.needed) return false;
    if (filters.hideAnswered && row.status === 'answered') return false;
    return has(row.label, filters.search);
  });
}

/** The intake's sections, in the rows' order: [{key, label}]. */
export function intakeSections(rows) {
  const seen = new Map();
  (rows || []).forEach((row) => {
    if (!seen.has(row.section)) seen.set(row.section, row.section_label);
  });
  return [...seen].map(([key, label]) => ({ key, label }));
}

/** "Select needed gaps": the needed questions still blank that are not in the tray or asked. */
export function neededGaps(rows) {
  return (rows || []).filter((row) => row.shown && row.status === 'gap' && !row.draft_id && !row.asked_at).map((row) => row.ref);
}

/** Where each origin's filled values came from, over the rows: {origin: n}. */
export function originTotals(rows) {
  const out = {};
  (rows || []).forEach((row) => {
    if (row.origin) out[row.origin] = (out[row.origin] || 0) + 1;
  });
  return out;
}

/** A census column's state for the status chips: missing (required blanks), review, client, complete, optional. */
export function columnStates(column) {
  const states = [];
  if (column.counts.missing) states.push('missing');
  if (column.counts.low) states.push('low');
  if (column.counts.client) states.push('client');
  if (column.counts.na) states.push('na');
  if (!column.counts.missing && !column.counts.na) states.push('high');
  return states;
}

/** The census columns a set of filters keeps. */
export function censusColumns(columns, filters) {
  return (columns || []).filter((column) => {
    if (filters.group && column.group !== filters.group) return false;
    if (filters.statuses.length && !columnStates(column).some((state) => filters.statuses.includes(state))) return false;
    if (filters.origins.length && !filters.origins.some((origin) => column.origins[origin])) return false;
    if (filters.requiredOnly && !column.required) return false;
    if (filters.hideComplete && column.counts.missing + column.counts.na === 0) return false;
    if (filters.quotedOnly && !column.quoted) return false;
    if (filters.hideWaived && column.rule === 'waived') return false;
    return has(column.label, filters.search);
  });
}

/** The groups that hold a column, in order: [{key, label, count}] for the preset chips. */
export function groupsOf(columns, groups) {
  return (groups || [])
    .map((group) => ({ ...group, count: (columns || []).filter((column) => column.group === group.key).length }))
    .filter((group) => group.count);
}

/** "3 missing — required on this deal · 2 filled" for the bar's title, from /api/meta/ `census_segments`. */
export function barTitle(column, segments) {
  return (segments || [])
    .filter((segment) => column.counts[segment.key])
    .map((segment) => `${column.counts[segment.key]} ${segment.label.toLowerCase()}`)
    .join(' · ');
}

/** "58 / 60 employees": an employee-only column counts employees (old `peopleWord`). */
export function peopleWord(column) {
  return column.applies === 'employee' ? 'employees' : 'people';
}
