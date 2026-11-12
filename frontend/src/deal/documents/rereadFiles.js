/*
 * Which files the Re-read panel offers (plan.md §8.16, §10.4; E75, E76). Pure. Every kind a proposal reader reads —
 * the quote reader's and, from slice 22, the SBC reader's (meta `ai.targets`, never a list here: rule 1); the old app
 * offered quote files only (E76) — and never a removed file. The panel opens with the file on screen ticked, or every
 * offered file under 📚 All proposals. A re-read starts one read per reader (`byReader`).
 */
const READERS = ['quotes', 'sbc'];

/** The kinds the proposal readers read, from meta; [] without Claude (D26). */
export function readKinds(meta) {
  return (meta?.ai?.targets || []).filter((entry) => READERS.includes(entry.key)).flatMap((entry) => entry.kinds);
}

/** {reader: [file ids]} for the ticked files, each read by the reader of its kind. */
export function byReader(files, meta) {
  const out = {};
  (meta?.ai?.targets || [])
    .filter((entry) => READERS.includes(entry.key))
    .forEach((entry) => {
      const ids = files.filter((file) => entry.kinds.includes(file.kind)).map((file) => file.id);
      if (ids.length) out[entry.key] = ids;
    });
  return out;
}

/** The deal's files the panel offers, in the station's order. */
export function rereadable(files, meta) {
  const kinds = readKinds(meta);
  return (files || []).filter((file) => kinds.includes(file.kind) && !file.archived_at);
}

/** The ids ticked when the panel opens. */
export function firstPicks(offered, shown, allOn) {
  if (allOn) return new Set(offered.map((file) => file.id));
  return new Set(offered.some((file) => file.id === shown?.id) ? [shown.id] : []);
}
