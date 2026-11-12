/*
 * The proposal builder's deal cards, their small rules (plan.md §8.14; J38–J45, J63–J67; the old OutputPanel.jsx,
 * PresentationPagesCard.jsx, NextStepsCard.jsx and the summary and markets cards of ProposalBuilder.jsx at 891f1b3).
 * Pure: the cards' one-line summaries, a page's status words, and the lists a click makes (summary blocks, hidden
 * carriers, next steps, plan experience). Every value, default and word of a rule is the server's (GET
 * deals/{id}/proposal/ and /api/meta/ proposal); these only arrange them.
 */

const plural = (count, one, many = `${one}s`) => (count === 1 ? one : many);

/** "Presentation · a page per carrier" (How the documents look; the Format waits, J36). */
export function outputSummary(output, meta) {
  const layout = meta.layouts.find((entry) => entry.key === output.layout);
  return ['Presentation', layout ? layout.label.toLowerCase() : ''].filter(Boolean).join(' · ');
}

/** A Presentation page's status: switched off, prints, or why not (the ledger, J42). */
export function pageStatus(row, pages) {
  if (row.switchable && pages[row.key] === false) return 'switched off';
  if (row.ready === null || row.ready === undefined) return row.why;
  return row.ready ? 'prints' : row.why;
}

/** Whether a page shows its Fix ▸: on, not ready, and somewhere to fix it. */
export const pageMissing = (row, pages) => !(row.switchable && pages[row.key] === false) && row.ready === false;

/** "4 of 6 pages on". */
export function pagesSummary(ledger, pages) {
  const switchable = ledger.filter((row) => row.switchable);
  return `${switchable.filter((row) => pages[row.key] !== false).length} of ${switchable.length} pages on`;
}

/** The summary's blocks as picked, or the standard set while nothing is picked (every edit builds on it). */
export const summaryBlocks = (summary) => (summary.picked.length ? summary.picked : summary.standard);

/** "Not shown", "5 figures" or "The standard set" (the Executive summary card's summary). */
export function summaryWords(summary) {
  if (!summary.on) return 'Not shown';
  const count = summary.picked.length;
  return count ? `${count} ${plural(count, 'figure')}` : 'The standard set';
}

/** A tick on a block: off when picked, else added at the end. */
export function toggledBlock(blocks, key) {
  return blocks.some((block) => block.key === key) ? blocks.filter((block) => block.key !== key) : [...blocks, { key }];
}

/** A line-scoped block pinned to one line ('' = every line). */
export const pinnedBlock = (blocks, key, line) =>
  blocks.map((block) => (block.key !== key ? block : line ? { key, line } : { key }));

/** Every block in the catalogue, the picked ones keeping their order and pins. */
export function everyBlock(blocks, catalog) {
  const chosen = new Set(blocks.map((block) => block.key));
  return [...blocks, ...catalog.filter((entry) => !chosen.has(entry.key)).map((entry) => ({ key: entry.key }))];
}

/** Where a block is worked out: "whole deal", "Medical only" or "per line". */
export function blockScope(entry, lineLabel) {
  if (entry.scope === 'deal') return 'whole deal';
  return entry.line ? `${lineLabel(entry.line)} only` : 'per line';
}

/** Whether a picked block takes a line pin (a per-line block that belongs to no one line). */
export const takesPin = (entry) => Boolean(entry) && entry.scope === 'line' && !entry.line;

/** The hidden carriers after a Show tick on `id`. */
export function toggledHidden(hidden, id) {
  const next = new Set(hidden);
  if (next.has(id)) next.delete(id);
  else next.add(id);
  return [...next].sort();
}

/** Next steps as saved: rows with words only. */
export const savedSteps = (rows) => rows.filter((row) => (row.text || '').trim());

/** Plan experience as saved: periods with a name only. */
export const savedPeriods = (rows) => rows.filter((row) => String(row.period || '').trim());

/** A stored figure as an input shows it ('' for none). */
export const figureText = (value) => (value === null || value === undefined ? '' : String(value));
