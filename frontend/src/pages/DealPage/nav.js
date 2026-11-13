// The deal sidebar's nav (A21; plan.md §8.4; OQ9): old Vantage's order and groups exactly, never the app chain's.
// A pure module: DealNav renders it and nav.test.js pins it. Tabs not yet built are left out, and a group with no
// built tab loses its label too; an unknown or unbuilt tab opens the default tab.

export const NAV = [
  {
    label: null,
    tabs: [
      { key: 'overview', label: 'Overview' },
      { key: 'agenda', label: 'Agenda' },
    ],
  },
  {
    label: '1 · Get to Market',
    tabs: [
      { key: 'review', label: 'Review & requests' },
      { key: 'intake', label: 'Intake' },
      { key: 'census', label: 'Census' },
      // Shown only while the deal has a form that is armed or started (G7).
      { key: 'questionnaire', label: 'Questionnaire' },
      { key: 'rfp', label: 'RFP' },
      { key: 'commission', label: 'Commission' },
    ],
  },
  {
    label: '2 · Quote to Close',
    tabs: [
      { key: 'advisor', label: 'Advisor' },
      { key: 'proposal', label: 'Proposal' },
    ],
  },
  {
    label: 'Shared',
    tabs: [{ key: 'documents', label: 'Documents' }],
  },
];

// The deal's default tab: the Overview, where deals open from slice 62 (O.4; plan.md §8.1).
export const DEFAULT_TAB = 'overview';

/** The groups to draw, in order, keeping only tabs in `built` (a list or Set of keys); empty groups are dropped. */
export function navGroups(built) {
  const keep = new Set(built);
  return NAV.map((group) => ({ ...group, tabs: group.tabs.filter((tab) => keep.has(tab.key)) })).filter(
    (group) => group.tabs.length > 0,
  );
}

// Tab names an older link may carry in `?tab=` (old Vantage called the RFP tab `carriers`).
const RENAMED = { carriers: 'rfp' };

/** The tab a path or an old `?tab=` link asks for when it is built, else the default tab. */
export function tabFor(asked, built) {
  const key = RENAMED[asked] || asked;
  return new Set(built).has(key) ? key : DEFAULT_TAB;
}

/** The label of a tab key, or the key itself. */
export function tabLabel(key) {
  for (const group of NAV) {
    const found = group.tabs.find((tab) => tab.key === key);
    if (found) return found.label;
  }
  return key;
}
