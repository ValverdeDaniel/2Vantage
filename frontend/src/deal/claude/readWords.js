// What the read door and the review card say (plan.md §10.4, §10.5; D21, D22, D28). Pure. The words for why a part
// failed or a page was left out come from `/api/meta/` (`ai.failed_words`, `ai.left_out_words`), never from here.

/** The document kinds a reader reads, from meta (`ai.targets`); [] without Claude. */
export function readerKinds(meta, target = 'quotes') {
  return meta?.ai?.targets?.find((entry) => entry.key === target)?.kinds || [];
}

/** The read jobs (queued or running) that read any of these files. */
export function readsOn(jobs, ids) {
  const reading = (job) => job.kind === 'read' || job.kind === 'recheck'; // a re-check reads them again (slice 22)
  return (jobs || []).filter((job) => reading(job) && job.documents.some((id) => ids.includes(id)));
}

/** "Claude is reading the file · 40% — Reading pages 1–2". */
export function runningText(job) {
  const where = job.status === 'queued' ? 'Waiting to start' : `${job.progress || 0}%`;
  const doing = job.kind === 'recheck' ? 'Claude is re-checking the flagged values in' : 'Claude is reading';
  return { text: `${doing} ${job.documents.length > 1 ? 'these files' : 'the file'} · ${where}`, line: job.step };
}

/** A read that ended without a change set to review: failed, or waiting past a cap. '' when there is nothing to say. */
export function endedText(job) {
  if (!job || (job.kind !== 'read' && job.kind !== 'recheck')) return '';
  if (job.status === 'failed') return job.error || 'The read failed.';
  if (job.land === 'budget') return job.wait_reason;
  if (job.kind === 'recheck' && job.status === 'done' && !job.counts?.items && job.counts?.unverified) {
    const n = job.counts.unverified;
    return `Claude re-checked ${n} flagged value${n === 1 ? '' : 's'} and could not find ${n === 1 ? 'it' : 'them'} on ${n === 1 ? 'its page' : 'their pages'}: still flagged, check by hand.`;
  }
  return '';
}

function named(doc, nameOf) {
  return nameOf(doc) || 'a file';
}

/** "Part of this read could not be finished: renewal.pdf, pages 1–2 (Claude did not answer …)." or ''. */
export function failedText(parts, nameOf, words) {
  if (!parts?.length) return '';
  const said = parts.map((part) => `${named(part.doc, nameOf)}, ${part.where} (${words?.[part.reason] || part.reason})`);
  return `Part of this read could not be finished: ${said.join('; ')}. The plans below are what the rest found.`;
}

/** "Not read: page 3 of renewal.pdf (only the running header and footer)." or ''. */
export function leftOutText(entries, nameOf, words) {
  if (!entries?.length) return '';
  const said = entries.map((entry) => {
    const pages = entry.pages.length === 1 ? `page ${entry.pages[0]}` : `pages ${entry.pages.join(', ')}`;
    const why = entry.why.map((key) => words?.[key] || key).join('; ');
    return `${pages} of ${named(entry.doc, nameOf)} (${why})`;
  });
  return `Not read: ${said.join('; ')}.`;
}

/** "2 current plans · 2 renewals · read with Sonnet 5.5 · $0.04". */
export function summaryLine(changeSet, models) {
  const model = models?.find((entry) => entry.key === changeSet.model)?.label || changeSet.model;
  const cost = changeSet.cost_usd ? ` · $${Number(changeSet.cost_usd).toFixed(2)}` : '';
  return `${changeSet.summary}${model ? ` · read with ${model}` : ''}${cost}`;
}

/** The toast after "Use this scan": the old app's "Scan applied — 2 current plans · 2 renewals"; a read that found
 *  nothing new says so in the server's words. */
export function landedToast(landed) {
  if (!landed?.activity_ids?.length) return landed?.summary || 'Nothing changed.';
  return `Scan applied — ${landed.summary}`;
}

/** The strip under a used read: "✓ Used Claude's read — 2 current plans · 2 renewals"; a read that landed by itself
 *  (an admin's or a direct person's, D71) says so: "✓ Claude's read landed — …". */
export function landedText(news) {
  if (news.kind === 'recheck') return `✓ Applied Claude’s re-check — ${news.summary}`; // slice 22 (D93, E77)
  return news.auto ? `✓ Claude’s read landed — ${news.summary}` : `✓ Used Claude’s read — ${news.summary}`;
}

const count = (n, one, many) => `${n} ${n === 1 ? one : many}`;

/** A census read's card (D29, slice 51): what was read, never who — "“roster.pdf” was read, not applied: 12 people
 *  (8 employees, 4 dependents). Nothing on the roster has changed …". */
export function censusReadHead(item, fileName) {
  const file = fileName ? `“${fileName}”` : 'The file';
  const what = item.read
    ? `${count(item.people, 'person', 'people')} (${count(item.employees, 'employee', 'employees')}, ${count(
        item.dependents,
        'dependent',
        'dependents',
      )})`
    : `${count(item.columns, 'column', 'columns')} mapped${item.assisted ? `, ${item.assisted} proposed by Claude from their shapes` : ''}`;
  return `${file} was read, not applied: ${what}. Nothing on the roster has changed — see who would be added, changed, removed and kept on the Census tab, then apply it there.`;
}

/** What ↶ Undo this run asks first (the old ScanChat's confirm). */
export const UNDO_ASK =
  'The plans this read added come off and the values it changed go back to what they were. A plan someone has ' +
  'starred, recommended, sold, packaged, linked or typed into since stays.';

/** What ↶ Undo this run asks first, by what the read wrote: a filled form's answers and rows (slice 52), else plans. */
export function undoAsk(news) {
  if (news?.target === 'questionnaire') {
    return (
      'The answers this read put on the form go back to what they were, and the rows it added come off. A row ' +
      'someone typed into since stays.'
    );
  }
  return UNDO_ASK;
}

/** What ↻ Try again asks first (the old ScanChat's "Undo this run and send the same message again on Opus 5.5?"). */
export function retryAsk(label) {
  return `Undo this run and read the same files again with ${label}? ${UNDO_ASK}`;
}

/** The toast after an Undo: what came back, and what stayed. */
export function undoneToast(undone) {
  const kept = undone?.kept?.length ? ` ${undone.kept.join(', ')} stayed: someone worked on it since.` : '';
  const skipped = undone?.skipped?.length ? ` Left as they are: ${undone.skipped.join(' ')}` : '';
  return `Undone — the deal is back to how it was before that read.${kept}${skipped}`;
}
