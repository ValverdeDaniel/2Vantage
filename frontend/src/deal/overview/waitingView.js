// The Overview's "Waiting on" banner (M33, M34; I119; old Vantage 891f1b3 `overview/WaitingBanner.jsx`), worked out
// from the shell's journey read (`waiting` and `next_step`, agenda's one answer), so the banner, the stepper's current
// dot and the Agenda agree. Pure: OverviewTab draws it, waitingView.test.js pins it.

const plural = (n, word) => `${n} ${word}${n === 1 ? '' : 's'}`;

/**
 * The banner, or null when there is none (a lost deal: "whose court is the ball in" is nobody's, M34):
 *   {done, side: 'us' | 'them' | null, label, detail, next, link, severity}
 * - waiting on the client or a carrier: its step's words, with how long, and the next step when it says something else;
 * - the ball in our court: the next step's words (the old headline), "The ball is in our court";
 * - nothing left, or only the sale's "Sold": Status · the step's words, with no Go ▸.
 * `link` is the next step's own (its tab and params, M33's Go ▸).
 */
export function waitingView(journey) {
  const waiting = journey?.waiting;
  if (!waiting) return null;
  const next = journey.next_step || null;
  if (waiting.state === 'waiting') {
    return {
      done: false,
      side: waiting.owner === 'us' ? 'us' : 'them',
      label: waiting.label,
      detail: waiting.days != null ? `Waiting ${plural(waiting.days, 'day')} so far.` : '',
      next: next && next.label !== waiting.label ? next.label : '',
      link: next?.link || null,
      severity: waiting.severity || 'info',
    };
  }
  if (!next || next.state === 'done') {
    return {
      done: true,
      side: null,
      label: next?.label || 'Complete',
      detail: 'Nothing outstanding on this deal.',
      next: '',
      link: null,
      severity: 'done',
    };
  }
  return {
    done: false,
    side: 'us',
    label: next.label,
    detail: waiting.label ? `${waiting.label}.` : '',
    next: '',
    link: next.link || null,
    severity: next.severity || 'info',
  };
}
