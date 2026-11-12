// What the read door and the review card say (plan.md §10.4, §10.5; D21, D22, D28). Pure. The words for why a part
// failed or a page was left out come from `/api/meta/` (`ai.failed_words`, `ai.left_out_words`), never from here.

/** The document kinds a reader reads, from meta (`ai.targets`); [] without Claude. */
export function readerKinds(meta, target = 'quotes') {
  return meta?.ai?.targets?.find((entry) => entry.key === target)?.kinds || [];
}

/** The read jobs (queued or running) that read any of these files. */
export function readsOn(jobs, ids) {
  return (jobs || []).filter((job) => job.kind === 'read' && job.documents.some((id) => ids.includes(id)));
}

/** "Claude is reading the file · 40% — Reading pages 1–2". */
export function runningText(job) {
  const where = job.status === 'queued' ? 'Waiting to start' : `${job.progress || 0}%`;
  return { text: `Claude is reading ${job.documents.length > 1 ? 'these files' : 'the file'} · ${where}`, line: job.step };
}

/** A read that ended without a change set to review: failed, or waiting past a cap. '' when there is nothing to say. */
export function endedText(job) {
  if (!job || job.kind !== 'read') return '';
  if (job.status === 'failed') return job.error || 'The read failed.';
  if (job.land === 'budget') return job.wait_reason;
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
