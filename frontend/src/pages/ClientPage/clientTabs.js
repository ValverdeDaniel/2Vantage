// The client page's nav (plan.md §8.5; CL13; old ClientWorkspace.jsx at 891f1b3): Overview, then the old groups Upkeep
// (Agenda), Revenue (Commissions) and Relationship (Notes), in the old order, with the old badges and the sidebar's
// agenda rollup chip. A pure module: ClientSidebar draws it and clientTabs.test.js pins it. A tab not built is left out
// with its group's label; the old Plan years, Notifications and Deals & history wait with renewals (CL27). An unknown
// or unbuilt tab opens the Overview, as the deal page does.

export const CLIENT_NAV = [
  { label: null, tabs: [{ key: 'overview', label: 'Overview' }] },
  { label: 'Upkeep', tabs: [{ key: 'agenda', label: 'Agenda' }] },
  { label: 'Revenue', tabs: [{ key: 'commissions', label: 'Commissions' }] },
  { label: 'Relationship', tabs: [{ key: 'notes', label: 'Notes' }] },
];

// The tabs built (slices 67–68).
export const CLIENT_TABS = ['overview', 'agenda', 'commissions', 'notes'];
export const CLIENT_DEFAULT_TAB = 'overview';

/** The groups to draw, in order, keeping only tabs in `built`; a group with none left is dropped with its label. */
export function clientNavGroups(built = CLIENT_TABS) {
  const keep = new Set(built);
  return CLIENT_NAV.map((group) => ({ ...group, tabs: group.tabs.filter((tab) => keep.has(tab.key)) })).filter(
    (group) => group.tabs.length > 0,
  );
}

/** The tab the path asks for when it is built, else the Overview. */
export function clientTabFor(asked, built = CLIENT_TABS) {
  return built.includes(asked) ? asked : CLIENT_DEFAULT_TAB;
}

/** `/clients/12/overview` */
export function clientPath(clientId, tab = CLIENT_DEFAULT_TAB) {
  return `/clients/${clientId}/${tab}`;
}

/** "← Prospects" for a prospect, else "← Clients", each to its home view (§8.5). */
export function backLink(relationship) {
  return relationship === 'prospect' ? { to: '/', label: '← Prospects' } : { to: '/?view=book', label: '← Clients' };
}

/**
 * The nav's badges (old `navItem(key, label, badge, tone)`): Agenda wears the overdue count in rose; Commissions an amber
 * 1 while no primary producer is set (the client's owner is the client split's primary, H22). `counts` is the client
 * Agenda's rollup ({overdue, soon, total}). {key: {count, tone}}; a count of 0 draws nothing.
 */
export function navBadges(client, counts) {
  return {
    agenda: { count: counts?.overdue || 0, tone: 'rose' },
    commissions: { count: client?.owner ? 0 : 1, tone: 'amber' },
  };
}

/** The sidebar's agenda rollup chip (old `rollupChip`): "N overdue" rose, else "N due soon" amber, else "on track". */
export function rollupChip(counts) {
  if (counts?.overdue > 0) return { label: `${counts.overdue} overdue`, className: 'bb-badge bb-badge-rose' };
  if (counts?.soon > 0) return { label: `${counts.soon} due soon`, className: 'bb-badge bb-badge-amber' };
  return { label: 'on track', className: 'bb-badge bb-badge-green' };
}
