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
//   pick      (in old or new) a file tab, by its visible name, to click before the capture (Documents; optional)
//   storage   localStorage entries both apps read as the page loads, e.g. a layout kept per browser (optional)
//   styles    key selectors whose computed font, colours, borders, radius, padding and box are compared
//
// Order of work: the screens that exist in both apps today first, then the old-only states later slices match.

const SHELL = ['body', '.navbar', 'h1', '.btn-primary', '.btn-secondary'];
const WORKSPACE = [...SHELL, '.bb-nav', '.bb-nav-item.active', '.bnf-nav-group-label', '.bb-tab-title', '.bb-panel'];
const AGENDA = [...WORKSPACE, '.bb-panel-title', '.bnf-event-title', '.bnf-ag-toggle', '.bnf-ag-count', '.bnf-ag-section-sub', '.bnf-ag-row', '.bnf-cal-label', '.bnf-agenda-detail', '.bnf-agenda-open', '.bnf-ag-btn'];

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
  { key: 'archived', title: 'Archived: archived clients with their status and stage, Restore (slice 38; A13, M105)', old: { path: '/benefits/archived' }, new: { path: '/archived' }, ready: '.bnf-archived-section', styles: [...SHELL, '.bb-eyebrow', '.bb-title', '.bb-subtitle', '.bnf-archived-title', '.bnf-archived-table th', '.bnf-archived-table td'] },
  { key: 'commissions.book', title: '/commissions: the tiles and the Book (slice 49; H42–H51)', old: { path: '/commissions' }, new: { path: '/commissions' }, ready: '.bnf-com-tiles', styles: [...SHELL, '.bb-dash-header', '.bnf-com-tiles .bb-stat-card', '.bnf-com-tabs', '.bnf-com-tab.active', '.bnf-com-filters'] },
  { key: 'commissions.people', title: '/commissions By person (slice 49; H68)', old: { path: '/commissions?tab=people' }, new: { path: '/commissions?tab=people' }, ready: '.bnf-com-tabs', styles: [...SHELL, '.bnf-com-tiles .bb-stat-card', '.bnf-com-tab.active', '.bnf-com-filters'] },
  { key: 'gd1.overview', title: 'GD1 Overview', deal: 'GD1', widths: 'workspace', old: { tab: 'overview' }, new: { pending: 62, why: 'the Overview' }, styles: WORKSPACE },
  { key: 'gd1.agenda', title: 'GD1 Agenda: the steps by section, Add a task, Done collapsed (slice 60; I1–I14, I27)', deal: 'GD1', old: { tab: 'agenda' }, new: { tab: 'agenda' }, ready: '.bnf-ag-block', styles: AGENDA },
  { key: 'gd3.agenda', title: 'GD3 Agenda at checkpoint A: quote-first, the intake steps listed and not leading (slice 60; I44, I50, OQ90)', deal: 'GD3', old: { tab: 'agenda' }, new: { tab: 'agenda' }, ready: '.bnf-ag-block', styles: AGENDA },
  { key: 'gd1.review', title: 'GD1 Review & requests: the Board, its readiness strip, the Waiting and To review lanes (slices 53, 55; L1, L2, L7, L9)', deal: 'GD1', widths: 'workspace', old: { tab: 'review' }, new: { tab: 'review' }, ready: '.bnf-board-lanes', styles: [...WORKSPACE, '.bnf-viewtab', '.bnf-board-head', '.bnf-board-ready', '.bnf-board-lane-head', '.bnf-board-empty'] },
  { key: 'gd1.intake', title: 'GD1 Intake (slice 11: the coverage card, current coverage, lines to quote; the form in 39)', deal: 'GD1', widths: 'workspace', old: { tab: 'intake' }, new: { tab: 'intake' }, ready: '.bnf-cvg', styles: [...WORKSPACE, '.bnf-cvg-head', '.bnf-cvg-badge', '.bnf-cvg-table th', '.bnf-cvg-box', '.bnf-cvg-foot', '.bnf-subcard', '.bnf-chip'] },
  { key: 'gd6.intake', title: 'GD6 Intake: the four question cards answered (slice 39); contacts, checklist and BOR in 40', deal: 'GD6', widths: 'workspace', old: { tab: 'intake' }, new: { tab: 'intake' }, ready: '.bnf-intake-section', styles: [...WORKSPACE, '.bnf-intake-section', '.bb-account-row', '.bb-account-label', '.bb-account-value', '.bnf-qb-star', '.bnf-intake-row .bb-badge', '.bnf-note-line', '.bnf-viewtab'] },
  { key: 'gd6.advisor', title: "GD6 Advisor: the filter card with the client's budget hints (F139)", deal: 'GD6', old: { tab: 'advisor' }, new: { tab: 'advisor' }, styles: [...WORKSPACE, '.bnf-advisor-filtercard'] },
  { key: 'gd6.questionnaire', title: 'GD6 Questionnaire: Florida Blue 51+ by the band, its plans row, the signatures (slice 42)', deal: 'GD6', widths: 'workspace', old: { tab: 'questionnaire' }, new: { tab: 'questionnaire' }, ready: '.bnf-q-paper', styles: [...WORKSPACE, '.bnf-q-toolbar', '.bnf-q-title', '.bnf-q-paper', '.bnf-q-secthead', '.bnf-q-field', '.bnf-q-label', '.bnf-q-rowchip', '.bnf-q-sign'] },
  { key: 'gd3.advisor', title: 'GD3 Advisor at checkpoint A: ten quotes priced from the medical line’s typed counts, ✎ counts (slice 13; F85–F88)', deal: 'GD3', old: { tab: 'advisor' }, new: { tab: 'advisor' }, styles: [...WORKSPACE, '.bnf-pc-mark', '.bnf-advisor-boardhead .btn-secondary'] },
  { key: 'gd1.pages', title: 'GD1 Advisor ▦ Pages, “What the client will see”: medical, a page per current plan (slice 14; F37–F39, J49, J50)', deal: 'GD1', widths: 'workspace', old: { tab: 'advisor' }, new: { tab: 'advisor' }, storage: { 'vantage.bnf.advisor': '{"layout":"pages","line":"medical"}' }, ready: '.bnf-pg-page', styles: [...WORKSPACE, '.bnf-pg-pagehead', '.bnf-pg-count.is-full', '.bnf-pg-col.is-option', 'button.bnf-pg-name', '.bnf-pg-title', '.bnf-pg-table tbody th', '.bnf-link-picker select'] },
  { key: 'gd1.builder', title: 'GD1 Advisor ▸ Proposal builder: medical, the Plans card with Key rows and the rows card (slice 25; J17, J18, J23, J47–J62)', deal: 'GD1', widths: 'workspace', old: { tab: 'advisor' }, new: { tab: 'advisor' }, storage: { 'vantage.bnf.advisor': '{"view":"build","line":"medical"}' }, ready: '.bnf-build-toolbar', styles: [...WORKSPACE, '.bnf-build-toolbar', '.bnf-build-progress', '.bnf-lineswitch .bnf-linetab', '.bnf-bcard-head', '.bnf-pg-rowswitch', '.bnf-pg-rec .bnf-pg-recbtn', '.bnf-build-rec-why textarea', '.bnf-build-enroll'] },
  { key: 'gd1.export-excel', title: 'GD1 Advisor ▸ Export viewer, the Excel chip: the file opens on Dynamic Medical Compare (slice 28; F3, J105, J112, J116, J118)', deal: 'GD1', widths: 'workspace', old: { tab: 'advisor' }, new: { tab: 'advisor' }, storage: { 'vantage.bnf.advisor': '{"view":"export","exportFile":"excel","line":"medical"}' }, ready: '.bnf-xw[data-render="ready"]', styles: [...WORKSPACE, '.bnf-xv-toolbar', '.bnf-xv-formats .bnf-viewtab', '.bnf-xv-status', '.bnf-xw-checks', '.xg-colhead', '.xg-rowhead', '.xg-cell', '.bnf-xw-tab-on', '.bnf-xv-about'] },
  { key: 'gd1.export-deck', title: 'GD1 Advisor ▸ Export viewer, the PowerPoint chip: the slides open on the first Medical plan set, with the fit report and speaker notes (slice 30; J108–J112)', deal: 'GD1', widths: 'workspace', old: { tab: 'advisor' }, new: { tab: 'advisor' }, storage: { 'vantage.bnf.advisor': '{"view":"export","exportFile":"powerpoint","line":"medical"}' }, ready: '.bnf-xv[data-render="ready"]', styles: [...WORKSPACE, '.bnf-xv-toolbar', '.bnf-xv-formats .bnf-viewtab', '.bnf-xv-status', '.bnf-xv-jump .bnf-xv-chip', '.bnf-xv-ledger .bnf-xv-chip', '.bnf-xv-thumb', '.bnf-xv-thumb-on', '.bnf-xv-fit', '.bnf-xv-slide', '.bnf-xv-nav', '.bnf-xv-notes', '.bnf-xv-about'] },
  { key: 'gd1.export-paper', title: 'GD1 Advisor ▸ Export viewer, the Paper chip: each page on its US Letter sheet at 75%, with the printed type (slice 30; J114, J115)', deal: 'GD1', widths: 'default', old: { tab: 'advisor' }, new: { tab: 'advisor' }, storage: { 'vantage.bnf.advisor': '{"view":"export","exportFile":"paper","line":"medical"}' }, ready: '.bnf-xv[data-render="ready"]', styles: [...WORKSPACE, '.bnf-xv-toolbar', '.bnf-xv-paperline', '.bnf-xv-slide.bnf-xv-paper', '.bnf-xv-nav', '.bnf-xv-about'] },
  { key: 'gd5.stop-loss', title: 'GD5 Advisor ▸ Stop-loss analysis: the basis and its source, the contract in force, the verdict ranked lowest first, the option table and the laser detail (slice 36; F98–F105)', deal: 'GD5', widths: 'workspace', old: { tab: 'advisor' }, new: { tab: 'advisor' }, storage: { 'vantage.bnf.advisor': '{"view":"stop-loss","line":"stop_loss"}' }, ready: '.bnf-sl-board .bnf-sl-table', styles: [...WORKSPACE, '.bnf-viewtab-on', '.bnf-sl-basis', '.bnf-sl-section-title', '.bnf-sl-card', '.bnf-sl-card-verdict', '.bnf-sl-rank', '.bnf-sl-rank-best', '.bnf-sl-rank-badge', '.bnf-sl-punchline', '.bnf-sl-seg-on', '.bnf-sl-table th', '.bnf-sl-verdict-row td'] },
  { key: 'gd5.advisor', title: 'GD5 Advisor ▸ Quote comparison on the Stop-Loss line: ▲▼ on every quote (slice 36; OQ13)', deal: 'GD5', old: { tab: 'advisor' }, new: { tab: 'advisor' }, storage: { 'vantage.bnf.advisor': '{"view":"quotes","line":"stop_loss"}' }, ready: '.bnf-viewtab', styles: [...WORKSPACE, '.bnf-viewtab-on', '.bnf-lineswitch .bnf-linetab'] },
  { key: 'gd1.census', title: 'GD1 Census: the empty roster (slice 12; C10)', deal: 'GD1', old: { tab: 'census' }, new: { tab: 'census' }, styles: WORKSPACE },
  { key: 'gd4.census', title: 'GD4 Census: the roster grid, outside ✎ Edit (slice 41; C1–C10, C25)', deal: 'GD4', widths: 'workspace', old: { tab: 'census' }, new: { tab: 'census' }, ready: '.bb-grid-card', styles: [...WORKSPACE, '.bnf-cobra-check', '.bb-sov-toolbar', '.bb-legend-item', '.bb-sov-page .bnf-line-chips .bb-chip.active', '.bb-col-header', '.bnf-census-person', '.bb-grid-row .bb-cell', '.bnf-census-empid'] },
  { key: 'gd4.documents', title: 'GD4 Documents: the census file beside its whole roster (slice 65; E43, OQ97)', deal: 'GD4', widths: 'workspace', old: { tab: 'documents' }, new: { tab: 'documents', pick: 'census (synthetic).xlsx' }, ready: '.bnf-scan-panel', styles: [...WORKSPACE, '.bb-doc-tab', '.bnf-doc-bucket', '.bnf-file-bar', '.bnf-scan-head', '.bb-col-header', '.bb-grid-row .bb-cell'] },
  { key: 'gd1.rfp', title: 'GD1 RFP: the census line, the coverage card, What we’re requesting, the checklist (slice 44; K1–K33), the packet (slices 45–46; K34–K56) and the emails (slice 46; K57–K68)', deal: 'GD1', widths: 'workspace', old: { tab: 'carriers' }, new: { tab: 'rfp' }, ready: '.bnf-rfp-request', styles: [...WORKSPACE, '.bnf-rfp-census-status', '.bnf-build-progress', '.bnf-bcard-head', '.bnf-rfp-group-label', '.bnf-rfp-chip', '.bnf-rfp-chip-on', '.bnf-rfp-chip-tag', '.bnf-rfp-fields input', '.bnf-rfp-notes textarea', '.bnf-rfp-grid th', '.bnf-rfp-section-title', '.bnf-rfp-doc', '.bnf-export-fmt', '.bnf-rfp-variants .bnf-rfp-chip', '.bnf-rfp-packet .bnf-export-name', '.bnf-rfp-drafts .bb-panel-sub'] },
  { key: 'gd1.commission', title: 'GD1 Commission: the rates grid with Expected / yr, Producers & splits with the live preview, How this books (slice 48; H1–H24); the booked block in 49', deal: 'GD1', widths: 'workspace', old: { tab: 'commission' }, new: { tab: 'commission' }, ready: '.bnf-com-grid', styles: [...WORKSPACE, '.bnf-com-grid-head', '.bnf-com-grid-row', '.bnf-com-comp', '.bnf-ov-comm-total', '.bnf-com-source .bb-badge', '.bnf-com-kind', '.bnf-com-preview', '.bnf-com-addrow .btn', '.bnf-com-howlist'] },
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
