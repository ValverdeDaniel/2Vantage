/*
 * Which files the Re-read panel offers (plan.md §8.16, §10.4; E75, E76). Pure. Every kind Claude's quote reader reads
 * (meta `ai.targets`, never a list here: rule 1) — the old app offered quote files only (E76) — and never a removed
 * file. The panel opens with the file on screen ticked, or every offered file under 📚 All proposals.
 */

/** The kinds the quote reader reads, from meta; [] without Claude (D26). */
export function readKinds(meta) {
  return meta?.ai?.targets?.find((entry) => entry.key === 'quotes')?.kinds || [];
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
