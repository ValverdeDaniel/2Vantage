// The mapping dialog's pure rules (plan.md §5.3.2, §8.10; C15), ported from old Vantage 891f1b3 `MappingReview.jsx`
// (`setField`, `badge`) with the dry run's words. Pinned by mapping.test.js; the census vocabulary comes from
// /api/meta/ `census.fields`, never from here.

/** The mapping after a column takes `field`: a census column maps one file column, so it leaves any other (old). */
export function chooseField(mapping, column, field) {
  return mapping.map((entry) => {
    if (entry.column === column) return { ...entry, field, confidence: field ? 1 : 0, low: false };
    if (field && entry.field === field) return { ...entry, field: '', confidence: 0, low: false };
    return entry;
  });
}

/** The badge a row wears: Unmapped, Check (n%) for a low-confidence guess, or Mapped (old words and classes). */
export function badge(entry) {
  if (!entry.field) return { label: 'Unmapped', className: 'bb-badge-gray' };
  if (entry.low)
    return {
      label: `Check (${Math.round(entry.confidence * 100)}%)`,
      className: 'bb-badge-amber',
    };
  return { label: 'Mapped', className: 'bb-badge-green' };
}

/** The member's choices to send: [{column, field}] for every column whose field differs from the saved mapping. */
export function mappingChanges(saved, edited) {
  const before = new Map(saved.map((entry) => [entry.column, entry.field || '']));
  return edited
    .filter((entry) => (entry.field || '') !== before.get(entry.column))
    .map((entry) => ({ column: entry.column, field: entry.field || '' }));
}

export function mappedCount(mapping) {
  return mapping.filter((entry) => entry.field).length;
}

/** The census columns as select options, in the order of §4.4: [{value, label}]. */
export function fieldOptions(meta) {
  return (meta?.census?.fields || []).map((field) => ({
    value: field.key,
    label: field.label,
  }));
}

/** Row numbers a select offers: 1…n. */
export function rowNumbers(count) {
  return Array.from({ length: count }, (_, index) => index + 1);
}

/** The import waiting on the deal (newest first in the census page), or null. */
export function waitingImport(imports) {
  return (imports || []).find((imp) => imp.status === 'proposed') || null;
}

/** The latest applied import, for ⟲ Re-map source file, or null. */
export function lastApplied(imports) {
  return (imports || []).find((imp) => imp.status === 'applied' && imp.document_id) || null;
}

const plural = (count, one, many) => `${count} ${count === 1 ? one : many}`;

/** The dry run in words, worst news last: "3 added · 1 changed · 2 removed · 1 kept · 150 unchanged". */
export function dryRunWords(counts) {
  const parts = [
    `${counts.added} added`,
    `${counts.changed} changed`,
    `${counts.removed} removed`,
    `${counts.kept} kept`,
    `${counts.unchanged} unchanged`,
  ];
  return parts.join(' · ');
}

/** The dry run's heading: what the file holds. */
export function fileWords(counts) {
  const people = plural(counts.people, 'person', 'people');
  return `This file lists ${people}: ${plural(counts.employees, 'employee', 'employees')} and ${plural(
    counts.dependents,
    'dependent',
    'dependents',
  )}.`;
}

/** Whether the apply needs the member's explicit go-ahead: anyone would be removed (§5.3.2 step 8). */
export function removesSomeone(answer) {
  return Boolean(answer && answer.counts.removed > 0);
}
