// The Look lane's screen states (Q.5): each key says how to reach it in each app. A data module.
//
//   title     what the screen is
//   deal      a golden deal key: the screen opens that deal, found in each app by its client's name
//   signedIn  false for screens seen before sign-in (default true)
//   widths    'default' (1440) or 'workspace' (1280, 1440 and 1920)
//   old       { path } or, on a deal, { tab }: /benefits/cases/<id>?tab=<tab> in old Vantage
//   new       the same for 2Vantage (/deals/<id>/<tab>), or { pending: <slice>, why } while the slice that builds
//             it has not landed: the old side is captured and the key is reported "pending slice N"
//   ready     a selector each app shows once the screen has drawn (optional; networkidle always applies)
//   styles    key selectors whose computed font, colours, borders, radius, padding and box are compared
//
// Order of work: the screens that exist in both apps today first, then the old-only states later slices match.

const SHELL = ['body', '.navbar', 'h1', '.btn-primary', '.btn-secondary'];
const WORKSPACE = [...SHELL, '.bb-nav', '.bb-nav-item.active', '.bnf-nav-group-label', '.bb-tab-title', '.bb-panel'];

export const SCREENS = [
  {
    key: 'signin',
    title: 'Sign-in page',
    signedIn: false,
    old: { path: '/login' },
    new: { path: '/login' },
    ready: 'input[type="password"]',
    styles: ['body', 'h1', 'h2', 'label', 'input[type="text"]', 'input[type="password"]', 'button[type="submit"]'],
  },
  {
    key: 'home',
    title: 'Home: Prospects, the landing view (old "New clients"; CL10, CL11)',
    old: { path: '/benefits' },
    new: { path: '/' },
    styles: [...SHELL, '.bb-dash-header', '.bb-transfers-head', '.bb-transfer-row'],
  },
  { key: 'gd1.advisor', title: 'GD1 Advisor', deal: 'GD1', widths: 'workspace', old: { tab: 'advisor' }, new: { tab: 'advisor' }, styles: WORKSPACE },
  { key: 'gd1.proposal', title: 'GD1 Proposal', deal: 'GD1', widths: 'workspace', old: { tab: 'proposal' }, new: { tab: 'proposal' }, styles: WORKSPACE },
  { key: 'gd1.documents', title: 'GD1 Documents', deal: 'GD1', widths: 'workspace', old: { tab: 'documents' }, new: { tab: 'documents' }, styles: WORKSPACE },
  { key: 'gd2.advisor', title: 'GD2 Advisor', deal: 'GD2', old: { tab: 'advisor' }, new: { tab: 'advisor' }, styles: WORKSPACE },
  { key: 'gd2.proposal', title: 'GD2 Proposal', deal: 'GD2', old: { tab: 'proposal' }, new: { tab: 'proposal' }, styles: WORKSPACE },

  // Old-only states: captured now, matched by the slice named.
  { key: 'home.clients', title: 'Home: Clients view (CL12)', old: { path: '/benefits?view=book' }, new: { path: '/?view=book' }, styles: [...SHELL, '.bb-dash-header', '.bb-transfers-head', '.bb-transfer-row'] },
  { key: 'home.queue', title: 'Home: Work queue', old: { path: '/benefits?view=queue' }, new: { pending: 61, why: 'the Work queue' }, styles: SHELL },
  { key: 'archived', title: 'Archived', old: { path: '/benefits/archived' }, new: { pending: 38, why: 'the Archived page' }, styles: SHELL },
  { key: 'gd1.overview', title: 'GD1 Overview', deal: 'GD1', widths: 'workspace', old: { tab: 'overview' }, new: { pending: 62, why: 'the Overview' }, styles: WORKSPACE },
  { key: 'gd1.agenda', title: 'GD1 Agenda', deal: 'GD1', old: { tab: 'agenda' }, new: { pending: 60, why: 'the Agenda tab' }, styles: WORKSPACE },
  { key: 'gd1.review', title: 'GD1 Review & requests', deal: 'GD1', old: { tab: 'review' }, new: { pending: 53, why: 'Review & requests' }, styles: WORKSPACE },
  { key: 'gd1.intake', title: 'GD1 Intake (slice 11: the coverage card, current coverage, lines to quote; the form in 39)', deal: 'GD1', widths: 'workspace', old: { tab: 'intake' }, new: { tab: 'intake' }, ready: '.bnf-cvg', styles: [...WORKSPACE, '.bnf-cvg-head', '.bnf-cvg-badge', '.bnf-cvg-table th', '.bnf-cvg-box', '.bnf-cvg-foot', '.bnf-subcard', '.bnf-chip'] },
  { key: 'gd6.intake', title: 'GD6 Intake: the four question cards answered (slice 39); contacts, checklist and BOR in 40', deal: 'GD6', widths: 'workspace', old: { tab: 'intake' }, new: { tab: 'intake' }, ready: '.bnf-intake-section', styles: [...WORKSPACE, '.bnf-intake-section', '.bb-account-row', '.bb-account-label', '.bb-account-value', '.bnf-qb-star', '.bnf-intake-row .bb-badge', '.bnf-note-line', '.bnf-viewtab'] },
  { key: 'gd6.advisor', title: "GD6 Advisor: the filter card with the client's budget hints (F139)", deal: 'GD6', old: { tab: 'advisor' }, new: { tab: 'advisor' }, styles: [...WORKSPACE, '.bnf-advisor-filtercard'] },
  { key: 'gd1.census', title: 'GD1 Census', deal: 'GD1', old: { tab: 'census' }, new: { pending: 12, why: 'the census tab' }, styles: WORKSPACE },
  { key: 'gd1.rfp', title: 'GD1 RFP', deal: 'GD1', old: { tab: 'carriers' }, new: { pending: 44, why: 'the RFP tab' }, styles: WORKSPACE },
  { key: 'gd1.commission', title: 'GD1 Commission', deal: 'GD1', old: { tab: 'commission' }, new: { pending: 48, why: 'the Commission tab' }, styles: WORKSPACE },
];

// `--screens all`, a key, a prefix ("gd1" picks every gd1.* key) or a comma list of those.
export function pick(wanted) {
  const asked = String(wanted || 'all').split(',').map((word) => word.trim().toLowerCase()).filter(Boolean);
  if (asked.includes('all')) return SCREENS;
  const chosen = SCREENS.filter((s) => asked.some((word) => s.key === word || s.key.startsWith(`${word}.`)));
  const unknown = asked.filter((word) => !SCREENS.some((s) => s.key === word || s.key.startsWith(`${word}.`)));
  if (unknown.length) throw new Error(`No screen ${unknown.join(', ')}. Keys: ${SCREENS.map((s) => s.key).join(', ')}`);
  return chosen;
}
