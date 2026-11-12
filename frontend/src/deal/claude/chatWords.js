// What Work with Claude's chat says (plan.md §8.17, §10.6; D7, D19, D25, D90, D104; the old chatControls and ScanChat).
// Pure. The tab names come from the deal's tabs; the models from /api/meta/.

import { modelLabel } from './drawerWords';

/** "Oct 14" this year, "Oct 14, 2025" otherwise: short enough for an <option> (the old shortDate). */
export function shortDate(iso, now = new Date()) {
  if (!iso) return '';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '';
  const sameYear = date.getFullYear() === now.getFullYear();
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', ...(sameYear ? {} : { year: 'numeric' }) });
}

/** The tooltip's line for one chat: when a person last wrote in it, and who (the old lastUsedLine). */
export function lastUsedLine(chat) {
  if (!chat?.last_used_at) return '';
  const date = new Date(chat.last_used_at);
  if (Number.isNaN(date.getTime())) return '';
  const stamp = date.toLocaleString('en-US', { dateStyle: 'medium', timeStyle: 'short' });
  return `Last used ${stamp}${chat.last_used_by?.name ? ` by ${chat.last_used_by.name}` : ''}.`;
}

/** Chats ▾'s option: "Aetna fixes · Advisor · Oct 14" (D7): the title, the tab it started on, the day last used. */
export function chatOption(chat) {
  const parts = [chat.title || `Chat ${chat.number}`];
  if (chat.tab) parts.push(chat.tab.charAt(0).toUpperCase() + chat.tab.slice(1));
  const when = shortDate(chat.last_used_at || chat.created_at);
  if (when) parts.push(when);
  return parts.join(' · ');
}

const usd = (value) => `$${Number(value || 0).toFixed(2)}`;

/** A reply's run line (D90), for everyone: "This run $0.04 · Deal $1.20 of $25.00 · Sonnet 5.5". */
export function runLine(turn, spend, meta) {
  if (!turn || turn.status === 'queued' || turn.status === 'running') return '';
  const parts = [`This run ${usd(turn.cost_usd)}`];
  if (spend) parts.push(`Deal ${usd(spend.usd)}${spend.budget_usd ? ` of ${usd(spend.budget_usd)}` : ''}`);
  if (turn.model) parts.push(modelLabel(meta, turn.model));
  return parts.join(' · ');
}

/** The composer's placeholder (D19, D104). */
export function placeholder({ locked, busy }) {
  if (busy) return 'Claude is answering — Stop it on the card, or wait…';
  if (locked) return 'Locked: Claude reads and answers; its changes wait for your review…';
  return 'Ask Claude about this deal, or tell it what to change…';
}

/** Past the window Claude no longer sees the start of the chat (D25). */
export function windowHint(count, window = 30) {
  if (count <= window) return '';
  return `Claude reads only the last ${window} messages of a chat. For a new topic, start a new chat — the deal’s documents, plans and guidance carry over.`;
}

/** Where a turn's changes stand (D71, D73): '' while nothing was proposed. */
export function changesState(turn) {
  if (!turn || !(turn.items || []).length) return '';
  if (turn.landed?.undone || turn.resolution === 'undone') return 'undone';
  if (turn.resolution === 'applied') return 'applied';
  if (turn.resolution === 'discarded') return 'discarded';
  if (turn.status === 'queued' || turn.status === 'running') return 'proposing';
  return 'waiting';
}

/** The changes card's title: "Claude proposes 2 changes" / "Claude changed the table". */
export function changesTitle(turn) {
  const state = changesState(turn);
  const count = (turn?.items || []).length;
  if (state === 'applied') return turn.landed?.auto ? '✓ Claude changed the table' : '✓ Changes applied';
  if (state === 'undone') return 'Undone — the table is back the way it was before this run';
  if (state === 'discarded') return 'Discarded — nothing changed';
  return `Claude proposes ${count} change${count === 1 ? '' : 's'}`;
}
