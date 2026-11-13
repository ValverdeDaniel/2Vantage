// How one Activity row looks on the Timeline (plan.md §8.6; M70, M71; old Vantage 891f1b3 `ActivityFeed.jsx`
// KIND_ICON and the feed's tones): its dot's tone and its icon, from the row's area and action. Pure: Vitest pins it.
// A row the client wrote through their link keeps the old violet "client" tone whatever it did.

const ICONS = {
  documents: '📄',
  notes: '✎',
  quote_read: '⟳',
  census: '⟳',
  commission: '$',
  archive: '🗄',
};
const ACTION_ICONS = {
  created: '◆',
  sent: '↗',
  client_opened: '◉',
  client_submitted: '↙',
  client_added: '↙',
  closed: '■',
  checklist: '✓',
  signed: '✒',
  marketed: '▶',
  issued: '↗',
  sold: '$',
  read: '⟳',
  proposed: '⟳',
  lost: '✕',
  reverted: '↶',
};
const GOOD = new Set(['signed', 'sold', 'booked', 'marketed', 'imported', 'converted', 'checklist', 'read', 'approved']);
const WARN = new Set(['lost', 'failed', 'removed', 'deleted', 'archived', 'reverted', 'revoked', 'rejected']);

/** {tone: 'info' | 'good' | 'warn' | 'client', icon} for an Activity row's area and action. */
export function activityLook(area, action, byClient = false) {
  let tone = 'info';
  if (byClient) tone = 'client';
  else if (WARN.has(action)) tone = 'warn';
  else if (GOOD.has(action) || (area === 'documents' && action === 'created')) tone = 'good';
  const icon = (area === 'deal' && action === 'created' ? '◆' : null) || ICONS[area] || ACTION_ICONS[action] || '•';
  return { tone, icon };
}
