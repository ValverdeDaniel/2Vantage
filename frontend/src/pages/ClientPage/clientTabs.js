// The client page's nav (plan.md §8.5; CL13; old ClientWorkspace.jsx at 891f1b3): Overview, then the old groups Upkeep
// (Agenda), Revenue (Commissions) and Relationship (Notes), in the old order. A pure module: ClientSidebar draws it and
// clientTabs.test.js pins it. Tabs not yet built are left out with their group's label (Agenda and Commissions arrive
// with slice 68); the old Plan years, Notifications and Deals & history wait with renewals (CL27). An unknown or
// unbuilt tab opens the Overview, as the deal page does.

export const CLIENT_NAV = [
  { label: null, tabs: [{ key: 'overview', label: 'Overview' }] },
  { label: 'Upkeep', tabs: [{ key: 'agenda', label: 'Agenda' }] },
  { label: 'Revenue', tabs: [{ key: 'commissions', label: 'Commissions' }] },
  { label: 'Relationship', tabs: [{ key: 'notes', label: 'Notes' }] },
];

// The tabs built so far (slice 67); slice 68 adds 'agenda' and 'commissions'.
export const CLIENT_TABS = ['overview', 'notes'];
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
