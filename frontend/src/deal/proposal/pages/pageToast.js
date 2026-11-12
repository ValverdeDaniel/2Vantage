/*
 * The banner when a write adds a page (plan.md §8.14; F38; the old ProposalPages.jsx "moved" effect, 7385bb3): "Medical
 * now runs to 3 comparison pages: Cigna LocalPlus 1000 moved to page 3." Pure: it compares the pages before and after
 * a refetch of the same line.
 */

/** What a later refetch is compared with: the line, its page count and where each plan first shows. */
export function pageMemo(line, pages) {
  const pageOf = new Map();
  for (const page of pages ?? []) {
    for (const id of page.plan_ids) if (!pageOf.has(id)) pageOf.set(id, page.n);
  }
  return { line, count: (pages ?? []).length, pageOf };
}

/**
 * The banner's words, or '' when nothing to say: another line, the first read, or no page added. The plan named is
 * the first option on the last page that showed on another page before.
 */
export function movedNote(before, line, pages, byId, lineLabel) {
  const count = pages?.length ?? 0;
  if (!before || before.line !== line || !count || before.count >= count) return '';
  const last = pages[count - 1].plan_ids.map((id) => byId.get(id)).filter(Boolean);
  const mover = last.find((plan) => plan.kind !== 'current' && before.pageOf.get(plan.plan_id) !== count);
  return `${lineLabel} now runs to ${count} comparison pages${mover ? `: ${mover.words} moved to page ${count}` : ''}.`;
}
