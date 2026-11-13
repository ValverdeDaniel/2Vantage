// The request tray's pure helpers (plan.md §8.8; L49, L50, L52, L53; old 891f1b3 `ReviewTrayDock.jsx` destinationOf,
// `FollowUpSnippet.jsx` SECTIONS, `FollowUpCart.jsx` groups). The server says where each item goes and why it cannot;
// these only group and word it. The sections' labels come from /api/meta/ `review.tray_sections` (rule 1).

/** "Dana" from "Dana Diaz"; an address as it is. */
export function firstName(name) {
  const text = String(name || '').trim();
  if (!text || text.includes('@')) return text;
  return text.split(/\s+/)[0];
}

/** "Dana’s", "Dana’s and Joe’s", "their". */
export function possessive(names) {
  const firsts = [...new Set((names || []).map(firstName).filter(Boolean))].map((name) => `${name}’s`);
  if (!firsts.length) return 'their';
  if (firsts.length === 1) return firsts[0];
  return `${firsts.slice(0, -1).join(', ')} and ${firsts[firsts.length - 1]}`;
}

function monthDay(iso) {
  if (!iso) return '';
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? '' : date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

/**
 * Where the tray's items go, for its bar (old W4): "→ Dana’s link (expires Oct 30)", "→ Dana’s and Joe’s links",
 * "→ needs a new link", or both halves when some have a link and some do not. A gone item goes nowhere.
 */
export function destinationOf(items, now = new Date()) {
  const live = (items || []).filter((item) => !item.gone);
  const targets = new Map();
  live.forEach((item) => {
    if (item.target && !item.why) targets.set(item.target.key, item.target);
  });
  const nowhere = live.filter((item) => !item.target || item.why).length;
  const list = [...targets.values()];
  const names = list.flatMap((target) => target.names || []);
  const parts = [];
  if (list.length === 1 && names.length <= 1) {
    const end = list[0].expires_at;
    let left = '';
    if (end) left = new Date(end).getTime() <= now.getTime() ? ' (lives again when sent)' : ` (expires ${monthDay(end)})`;
    parts.push(`→ ${possessive(names)} link${left}`);
  } else if (list.length) {
    parts.push(`→ ${possessive(names)} links`);
  }
  if (nowhere) parts.push(list.length ? `${nowhere} need${nowhere === 1 ? 's' : ''} a new link` : '→ needs a new link');
  return parts.join(' · ');
}

/** The tray's items by section, in the sections' order, empty ones left out: [{key, label, list}]. */
export function bySection(items, sections) {
  return (sections || [])
    .map((section) => ({ ...section, list: (items || []).filter((item) => item.surface === section.key) }))
    .filter((group) => group.list.length);
}

/**
 * The cart's destinations (L37, L53): one group per link the items go on, in the order they first appear, then the
 * items no open link can take ("needs a new link"), then the gone ones (dropped on send).
 */
export function byDestination(items) {
  const groups = new Map();
  const nowhere = [];
  const gone = [];
  (items || []).forEach((item) => {
    if (item.gone) gone.push(item);
    else if (!item.target || item.why) nowhere.push(item);
    else {
      if (!groups.has(item.target.key)) groups.set(item.target.key, { key: item.target.key, target: item.target, list: [] });
      groups.get(item.target.key).list.push(item);
    }
  });
  return { links: [...groups.values()], nowhere, gone };
}

/** "Sent 3 to Dana’s link" / "Sent 4 on 2 links" for the toast after a send. */
export function sentWords(answer) {
  const sent = answer?.sent || 0;
  const targets = answer?.targets || [];
  if (!sent) return 'Nothing went: no open link could take it';
  const what = `${sent} item${sent === 1 ? '' : 's'}`;
  if (targets.length === 1) return `Sent ${what} on ${possessive(targets[0].names)} link`;
  return `Sent ${what} on ${targets.length} links`;
}
