/*
 * The words of "Check this file" (plan.md §8.16; E59, D-122), in the old app's voice: its button ("Check this file",
 * "Checking…"), its toast after the check ("Checked 12 values against the file — 2 not found in it", "Every value here
 * is already checked") and its strip while a job runs ("· 40% — Reading page 120 of 1,500", with Stop). Pure.
 */

export function checkLabel(count, busy) {
  if (busy) return 'Checking…';
  return count > 1 ? 'Check these files' : 'Check this file';
}

export const CHECK_TITLE = 'Look for every value in this file again, in code: no AI, no cost';
export const STOPPING = 'Stopping — values already checked are kept.';

/** The running strip's line: {text, line} for a queued or running locate job. */
export function runningWords(job, count) {
  const what = count > 1 ? 'these files' : 'this file';
  if (job.status === 'queued') {
    const line = job.queue_position > 1 ? 'another check on this deal runs first' : '';
    return { text: `Waiting to check ${what}`, line };
  }
  return { text: `Checking the values against ${what} · ${job.progress || 0}%`, line: job.step || '' };
}

/** What a finished check says: {tone: 'landed' | 'news' | 'failed', text}. */
export function finishedWords(job, count) {
  const files = count > 1 ? 'files' : 'file';
  if (job.status === 'failed') return { tone: 'failed', text: `The check stopped: ${job.error || 'it failed'}` };
  if (job.status === 'cancelled') return { tone: 'news', text: 'Stopped — values checked before Stop are kept.' };
  const checked = job.counts?.checked || 0;
  if (!checked) return { tone: 'landed', text: 'Every value here is already checked' };
  const absent = job.counts?.absent || 0;
  const noun = checked === 1 ? 'value' : 'values';
  return {
    tone: 'landed',
    text: `Checked ${checked} ${noun} against the ${files}${absent ? ` — ${absent} not found in it` : ''}`,
  };
}

// Why the file itself cannot settle a value (check by eye), as against a value with no printed form (say nothing).
const FILE_REASONS = new Set(['image', 'no_text', 'text_layer', 'unreadable', 'too_large', 'format', 'missing']);

/** What a value's locator answer says on the file bar, or null when it says nothing worth a word. */
export function locWords(loc) {
  if (!loc) return null;
  if (loc.state === 'absent') {
    return {
      tone: 'absent',
      text: 'Not in the file',
      title: 'Code looked for this value in the file and it is printed nowhere: the likeliest misread.',
    };
  }
  if (loc.state === 'weak' || (loc.state === 'nocheck' && FILE_REASONS.has(loc.why))) {
    return {
      tone: 'eye',
      text: 'Check by eye',
      title: 'The file cannot settle it in code: a common figure with no label beside it, an image, or a scanned page.',
    };
  }
  if (loc.state === 'derived') {
    return {
      tone: 'derived',
      text: 'Worked out',
      title: 'Not printed as read: the reader’s own rule turns a printed figure into it.',
    };
  }
  return null;
}
