// Claude on the Census tab (plan.md §8.10, §10.4; C9, C11, D41, D42; slice 51). Pure. Whether the census reader is
// there comes from `/api/meta/` (`ai.targets`, `ai.phi_readers`, `ai.phi_off`): never decided here.

const SCAN_TITLE =
  'Drop the census in Work with Claude: a PDF roster is read person by person and waits here for review; a ' +
  'spreadsheet’s columns are mapped, the ones the usual mapping leaves proposed by Claude from their shapes alone.';

/** {state: 'on' | 'off' | '', why}: the census reader registered, kept off by the PHI-gate switch, or no Claude. */
export function censusReader(meta) {
  const ai = meta?.ai;
  if (!ai) return { state: '', why: '' };
  if ((ai.targets || []).some((entry) => entry.key === 'census')) return { state: 'on', why: SCAN_TITLE };
  if (ai.phi_readers === false) return { state: 'off', why: ai.phi_off || '' };
  return { state: '', why: '' };
}

/** The old staged-read banner's words (891f1b3 CensusTab): "A census file is waiting for review." and its tail. */
export function readBanner(imp) {
  const file = imp.document_name ? `“${imp.document_name}”` : 'A file';
  return `${file} came in through Work with Claude and was read, not applied — nothing on the roster has changed.`;
}

/** The mapping dialog's subtitle for a roster Claude read: no sheet or header row, the people it holds. */
export function readSubtitle(imp, mapped, total) {
  const people = imp.people === 1 ? '1 person' : `${imp.people || 0} people`;
  return `${imp.document_name} · read by Claude · ${people} · ${mapped} of ${total} columns mapped`;
}
