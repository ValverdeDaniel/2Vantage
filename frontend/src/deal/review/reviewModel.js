// The Review tab's pure helpers (plan.md §8.8; L1, L7, L8): its views and pills, and the sentences a request card
// says about a link (old Vantage 891f1b3 `DealReviewTab.jsx`, `RequestCard.jsx`, `LinkStatus.jsx`). The labels of
// states, levels and close reasons come from /api/meta/ `review` (rule 1); the server says each link's state.

// The View row (D-171): Board · Request · N to send · Review · N. The Review queue is slice 55's.
export const VIEWS = [
  {
    key: 'board',
    title: 'The board: everything this deal is missing, waiting on and has to review, in three lanes',
  },
  {
    key: 'request',
    title: 'The request page: what to do next, what to ask, the form and what waits on you, in one place',
  },
  {
    key: 'queue',
    title: 'The review queue: every section’s client answers and AI reads, one section at a time, approve or send back',
  },
];
export const BUILT = new Set(['board', 'request', 'queue']);
export const LATER = 'arrives in a later version';

/** The view `?view=` asks for, when built; else the Board. */
export function viewOf(params) {
  const asked = params.get('view');
  return BUILT.has(asked) ? asked : 'board';
}

/** The section `?section=` names for a section's own Board (L12, L45), else '' (the whole deal). */
export function scopeOf(params) {
  const asked = params.get('section');
  return asked === 'intake' || asked === 'census' ? asked : '';
}

/** A pill's words: "Request · 2 to send", "Review · 3". */
export function pillLabel(key, counts) {
  if (key === 'board') return 'Board';
  if (key === 'request') return `Request${counts?.to_send ? ` · ${counts.to_send} to send` : ''}`;
  return `Review${counts ? ` · ${counts.to_review}` : ''}`;
}

// Classes by state (reviewrequest.css), the old cards' own.
export const REQUEST_CLASSES = {
  draft: 'rr-link-draft',
  partly_sent: 'rr-link-waiting',
  waiting: 'rr-link-waiting',
  answered: 'rr-link-answered',
  expired: 'rr-link-expired',
  closed: 'rr-link-covered',
};
export const LINK_CLASSES = {
  answered: 'rr-link-answered',
  off: 'rr-link-expired',
  closed: 'rr-link-covered',
  covered: 'rr-link-covered',
  draft: 'rr-link-draft',
  lapsed_draft: 'rr-link-expired',
  expired: 'rr-link-expired',
  opened: 'rr-link-opened',
  waiting: 'rr-link-waiting',
};

/** A [{key, label}] vocabulary's label, or the key. */
export function labelIn(list, key) {
  return list?.find((item) => item.key === key)?.label ?? key ?? '';
}

/** "just now", "12 min ago", "3h ago", "2d ago", then the date (old `agoWords`). */
export function agoWords(iso, now = new Date()) {
  if (!iso) return '';
  const seconds = Math.round((now.getTime() - new Date(iso).getTime()) / 1000);
  if (seconds < 60) return 'just now';
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  if (days < 31) return `${days}d ago`;
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

/** "Oct 30" */
export function monthDay(iso) {
  if (!iso) return '';
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? '' : date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

/** What a link has done, said of the link, never of a person (old `linkDetail`; D-057). */
export function linkDetail(person, now = new Date()) {
  switch (person.state) {
    case 'answered':
      return person.submitted_at ? `sent back ${agoWords(person.submitted_at, now)}` : '';
    case 'off':
      return 'a person turned it off, so it no longer opens';
    case 'closed':
      return 'its request was closed, so this link no longer opens';
    case 'covered':
      return 'the request was answered — this link still works until it expires';
    case 'draft':
      return 'nobody has this URL yet';
    case 'lapsed_draft':
      return 'it expired before anyone sent it';
    case 'expired':
      return person.opened ? `this link was opened ${person.opens || 1}×, then expired` : 'not opened before it expired';
    case 'opened': {
      const times = person.opens > 1 ? ` ${person.opens}×` : '';
      return `this link was opened${times} · last ${agoWords(person.last_opened_at, now)}`;
    }
    default:
      return person.sent_at ? `sent ${agoWords(person.sent_at, now)} · not opened yet` : 'not opened yet';
  }
}

/** "Runs out in 2 days" / "in under a day" on a Waiting card (old board chip). */
export function runsOutWords(days) {
  if (days <= 0) return 'Runs out in under a day';
  return `Runs out in ${days} day${days === 1 ? '' : 's'}`;
}

/** The Waiting lane's head count: its requests, and the links whose person is still answering. */
export function waitingCount(board) {
  return (board?.lanes?.waiting?.length || 0) + (board?.in_progress?.length || 0);
}

/** The full URL to copy: the browser's own origin in front of the server's `/portal/<token>`. */
export function linkUrl(path, origin) {
  return path ? `${origin}${path}` : '';
}
