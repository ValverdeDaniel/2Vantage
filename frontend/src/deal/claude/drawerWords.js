// What Work with Claude's drawer, pill and strip say (plan.md §8.17; D5, D8, D9, D13, D21–D24, D34, D76; the old
// ScanChat, chatControls and ClaudeStrip). Pure. The readers each tab reads for, the file kinds and their labels, the
// models and the send order come from `/api/meta/` (`ai`, `document_kinds`), never from here.

/** The file kinds Claude reads on this tab (D5): its readers' kinds, in meta's order; [] where each file says what it
 *  is (Overview, Documents) or no reader is set up for the tab yet. */
export function tabKinds(meta, tab) {
  const targets = meta?.ai?.tabs?.[tab] || [];
  const kinds = targets.flatMap((key) => meta.ai.targets.find((entry) => entry.key === key)?.kinds || []);
  return [...new Set(kinds)];
}

/** Every file kind some registered reader reads. */
export function readKinds(meta) {
  return [...new Set((meta?.ai?.targets || []).flatMap((entry) => entry.kinds))];
}

// Where each reader puts what it reads, in the drawer's words (slice 51: the census and intake readers).
const INTO = { census: 'the census', intake: 'Intake' };

/** {target, into, waits, members} for files of `kind`: the reader that reads them, where it puts them, whether its
 *  reads always wait for review (meta's `waits`, the reader's `must_review`) and whether it reads member pages. */
export function readsInto(meta, kind) {
  const entry = (meta?.ai?.targets || []).find((target) => target.kinds.includes(kind));
  const target = entry?.key || '';
  return { target, into: INTO[target] || 'the plans', waits: Boolean(entry?.waits), members: target === 'census' };
}

export function kindLabel(meta, key) {
  return meta?.document_kinds?.find((kind) => kind.key === key)?.label || key;
}

/** "37 pages · 4 left out (member data) · 12 image pages" (D13), from the file's upload screen. A reader that reads
 *  member pages by design (the census's, slice 51) leaves none out. */
export function fileFacts(doc, readsMemberPages = false) {
  const screen = doc.screen || {};
  const bits = [];
  if (doc.page_count) bits.push(`${doc.page_count} page${doc.page_count === 1 ? '' : 's'}`);
  const left = readsMemberPages ? 0 : screen.left_out_pages?.length || 0;
  const images = screen.image_pages?.length || 0;
  if (left) bits.push(`${left} left out (member data)`);
  if (images) bits.push(`${images} image page${images === 1 ? '' : 's'}`);
  return bits.join(' · ');
}

/** The facts' tooltip: which pages are left out and why, and what image pages mean (the old chipTitle). */
export function factsTitle(doc, readsMemberPages = false) {
  const screen = doc.screen || {};
  const left = screen.left_out_pages || [];
  return (
    [
      left.length && !readsMemberPages
        ? `Pages that may hold member data are left out of what Claude is sent: ${left.join(', ')}.`
        : '',
      screen.image_pages?.length
        ? 'Image pages have no text layer: Claude reads them, but the checks cannot look at them.'
        : '',
    ]
      .filter(Boolean)
      .join(' ') || 'What Claude is sent of this file'
  );
}

/** "Deal $0.12 of $25.00" (D8): what Claude has cost on the deal, against its budget. */
export function spendLine(spend) {
  if (!spend) return '';
  const usd = (value) => `$${Number(value || 0).toFixed(2)}`;
  return `Deal ${usd(spend.usd)}${spend.budget_usd ? ` of ${usd(spend.budget_usd)}` : ''}`;
}

export function modelLabel(meta, key) {
  return meta?.ai?.models?.find((model) => model.key === key)?.label || key || '';
}

/** "Last read: Sonnet 5.5 · $0.05" (D8): the newest finished read's run summary, for everyone. */
export function lastRunLine(recent, meta) {
  const job = (recent || []).find((entry) => entry.kind === 'read' && entry.status !== 'queued');
  if (!job || !Number(job.cost_usd)) return '';
  return `Last read: ${modelLabel(meta, job.model)} · $${Number(job.cost_usd).toFixed(2)}`;
}

/** The model "Try again" reads with (D76): the next up the ladder this person may use, else ''. */
export function nextModel(meta, model, canOpus) {
  const ladder = meta?.ai?.ladder || [];
  const at = ladder.indexOf(model || meta?.ai?.default_model);
  const later = at < 0 ? [] : ladder.slice(at + 1);
  const allowed = later.filter((key) => canOpus || !meta.ai.models.find((entry) => entry.key === key)?.admins_only);
  return allowed[0] || '';
}

/** What a running job's card says it is doing (D22). */
export function runningTitle(job) {
  if (job.status === 'queued' && job.queue_position) {
    return `Waiting for the job ahead (${job.queue_position === 1 ? 'next' : `${job.queue_position} in line`})`;
  }
  if (job.kind === 'locate') return 'Checking the values against the files';
  if (job.kind === 'issue') return 'Building the proposal files'; // Issue to client (slice 32): not Claude's
  if (job.kind === 'turn') return 'Answering your message';
  if (job.kind === 'rank') return 'Ranking plans against the client guidance'; // ⚖ Rank (slice 37)
  const files = job.documents.length === 1 ? 'the file' : `${job.documents.length} files`;
  return `Reading ${files}`;
}

/** The strip's line while Claude works (D34): "Claude is reading the quotes · 40%". */
export function stripDoing(job) {
  if (job.kind === 'locate') return `Claude is checking the values against the files · ${job.progress || 0}%`;
  if (job.kind === 'issue') return `Building the proposal files · ${job.progress || 0}%`;
  if (job.kind === 'turn') return job.status === 'queued' ? 'Claude will answer after the job ahead' : 'Claude is answering a message';
  if (job.kind === 'rank') return `Claude is ranking plans against the client guidance · ${job.progress || 0}%`;
  const where = job.status === 'queued' ? 'waiting to start' : `${job.progress || 0}%`;
  return `Claude is reading ${job.documents.length === 1 ? 'the file' : 'the files'} · ${where}`;
}

/** Whole seconds since an ISO time (D21's "thinking seconds"). */
export function secondsSince(iso, now = Date.now()) {
  const at = Date.parse(iso || '');
  return Number.isNaN(at) ? 0 : Math.max(0, Math.floor((now - at) / 1000));
}

export const SLOW_NOTE = 'a big request can take a minute'; // after 30 s (D21)

/** The toast after files are attached (D16, D17): what was filed and what Claude now reads. */
export function sentToast(count, sent) {
  const files = `${count} file${count === 1 ? '' : 's'}`;
  const jobs = sent?.jobs || [];
  const notRead = sent?.not_read?.length || 0;
  if (!jobs.length) return `Filed ${files}. Claude does not read files of ${notRead === 1 ? 'that' : 'those'} kind here.`;
  const queued = jobs.some((job) => job.status === 'queued' && job.queue_position);
  const filed = notRead ? ` ${notRead} of them ${notRead === 1 ? 'is' : 'are'} only filed.` : '';
  return `Attached ${files} — ${queued ? 'Claude reads them after the job ahead' : 'Claude is reading them'}.${filed}`;
}

/** "Read 2 files into the table" (D14). */
export function readButton(count) {
  return `📥 Read ${count} file${count === 1 ? '' : 's'} into the table`;
}
