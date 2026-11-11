# Part K — RFP

[← Porting plan](README.md)

**What it is:** The RFP tab turns a deal into a request to carriers. It records what is shopped, who is asked and which files go with each email. It fills Warner Pacific's request forms and each carrier's own census workbook in place, and builds a cover page, a packet zip and Outlook drafts. It records who was asked, which the Proposal's "Markets checked" reads. The app never sends anything itself.

## K.1 Files read, in order (one line each)

Path shorthand: `V/` = old `Vantage/`, `B/` = `V/benefits/`, `F/` = `V/frontend/src/`, `2V/` = `2Vantage/`. "Re-checked" marks files the finaliser re-opened to decide the challenges.

**Specs and READMEs**

| File (lines) | What it is / what it taught |
|---|---|
| B/README.md (394) | Module map. RFP sits in Get to Market; `marketing_checklist()` runs on most payloads |
| B/market/README.md (461) | `rfp_config` is sparse and merged. D-045, D-068, D-114. Carriers advise, never gate |
| B/templates_xlsx/README.md (99) | Seven bundled workbooks with hashes; the Warner census is cut from the 2–50 form |
| V/PlanningDocs/Benefits/rfp-cover-and-drafts.md (54) | The D-068 spec. Owed: rep list, returns inbox, Mark's cover |
| …/carrier-census-templates_20260917.md (501) | Final column maps of the four formats; they override 0054 |
| …/decisions.md (5,528) | D-045, D-053 #6, D-063 #5–#6, D-068, D-113, D-114, D-115, D-143, D-146 #6 (re-checked) |
| B/pipeline/README.md (716) | RFP outputs. D-069: Markets checked reads `asked` |
| …/GetToMarketRoadmap.md, V/PlanningDocs/focus-list.md (grep) | Still open: rep list, returns inbox, BAA before sending, "Benefit Central or email only" |
| …/experience-review/experience-review.md (5,142) | X-02, X-09, X-40, X-150, X-163, X-180–X-201; triage rows for X-182, X-184, X-186 (re-checked) |
| …/tab-load-speed.md (108), proposal-polish.md (75) | RFP load cost (41 queries on staging); the `asked` snapshot |
| 2V/CLAUDE.md (43), 2V/plan.md (3,432) | Chain and write rules; §3.3, §4.7, §5.3.3, §5.5, §5.7, §6.9, §7.10, §8.9, §9.8–9.11, §13 (re-checked), §15, §16, Appendix A |

**Models and migrations**

| File (lines) | What it is / what it taught |
|---|---|
| B/models/case.py (1,878) | `rfp_config`, `marketed_at`, `requested_lines`, `commission_rates`, agent names; `CarrierTemplate`; `AgencyProfile.rfp_returns_email` |
| B/migrations 0052 (16), 0053 (73), 0054 (375), 0055 (132), 0061 (100), 0065 (107), 0066 (74), 0067 (43), 0073 (18) | Layouts seeded as data, patched five times. 0054 maps CURRENT PLAN ELECTION to `medical_plan`/`dental_plan`/`vision_plan`. 0055: PAY MODE "Annual"; Warner 500 = its row counter; Angle 213 = pre-styled rows (re-checked) |
| B/stages.py (118) | `quoting` is set only by an AI quote read |
| 2V/deals/models.py (94), activity.py (47), values.py (47), services.py (143), stages.py (23), lines.py (291), clock.py (25), downloads.py (28), views.py (151) | `owner` nullable, `created_by` required; AgencySettings has no producer name; coalescing merges rows by key; `advance`, `locked`, `clock.today`; `file_response` types files with `mimetypes` (re-checked) |
| 2V/documents/models.py (46), services.py (120), kinds.py (44) | Kinds; optional roles current/renewal/alternates on quote, renewal and sbc; `carrier`; PHI kinds (re-checked) |
| 2V/quotes/models.py (73), selectors.py (155), math.py; 2V/proposals/selection.py (44); 2V/backend/meta.py (28), urls.py (23); 2V/Dockerfile | Plan roles, `carrier`, `created_at`; `enrollment_for` (typed beats census); meta and URL style; `python:3.12-slim` |

**Rules and services**

| File (lines) | What it is / what it taught |
|---|---|
| B/market/rfp_carriers.py (357) | 25 carriers, `COLUMN_LINES`, three-tier matcher; Cigna/Gravie notes (re-checked) |
| B/implementation/carrier_change.py (138) | `norm_carrier`, `_SUFFIXES`, used by the matcher |
| B/market/rfp.py (608) | Config clean and merge, band, route, `resolve_rfp`, `group_facts` (`group.enrolled` prints intake first, re-checked), commission text, summary, audience |
| B/market/rfp_review.py (59) | The only writer of card marks; stores a display name |
| B/pipeline/xlsx_fill.py (864) | Fills workbooks by patching XML; Excel-like CSV |
| B/pipeline/quote_request_form.py (385) | Warner forms: cell maps (D15 = enrolled), label guard, matrix, notes, inline census |
| B/pipeline/plan_math.py (1,440; 60–200, 700–1440) | Tier counts with source (typed config beats census), row builder, `column_required`, notes, overflow warning (re-checked) |
| B/pipeline/enrollment.py | Typed per-plan counts (`own_counts`, `effective_counts`) |
| B/pipeline/workbooks.py (2,056; 488–776) | Drift guard, fill, CSV formula count, `headcount_warnings`, `saved_by`, cap cut (re-checked) |
| B/pipeline/geo.py (154) | ZIP prefixes and county crosswalk |
| B/reports/census_mapping.py (1,741), census_mapping_workbook.py (376), census_compare.py (155); V/reports/compare.py (62), registry.py (199), urls.py (26) | Mapping report; the lens borrows `kind_of`, `DERIVE_INPUTS`, `GAP_HOMES`; `sheet_grid` |
| B/templates_xlsx/recut_warner_census.py (176) | Offline zip surgery for the Warner census |
| B/market/marketing_checklist.py (615), coverage.py (577), serializers/market.py (980; 746–819) | `enrolled_headcount` (intake declared first; re-checked), form keys, coverage intent |
| B/pipeline/rfp_bundle.py (243), rfp_cover_pdf.py (276), rfp_email.py (426), export_check.py (449) | Packet (exception text in warnings), cover, drafts (`_for_carrier`, content-type map, `mark_draft_sent`), check (client states) (re-checked) |
| B/market/census_lens.py (437) | Lens list, detail, real-file check (re-checked) |
| B/pipeline/pdf_kit.py (134), branding.py (227); B/pipeline/workbook_preview.py; V/docscan/sheet_format.py | Theme, letterhead, logo; `look()`, the Export viewer's sheet window |
| B/questionnaires/service.py (701), wp_lg.py (388), export.py (42) | `_split_address`; forms name RFP carrier keys; a GET creates rows |
| B/market/validation.py (501) | Loose `parse_date`; `parse_comp`, `comp_label` |
| B/market/client_request.py (1,617), serializers/client_overview.py (540), serializers/overview.py (1,703) | `is_historical`; 10-day follow-up |
| B/pipeline/markets.py (313), proposal_presentation.py (2,005), presentation_workbook.py (2,166), proposal_pdf.py (1,703), composition.py (843); F/…/close/MarketsChecked.jsx (59) | Consumers of `asked` |
| B/review/items.py (1,544), board.py (724), request_page.py (1,569), tasks/steps.py (677), pipeline/proposal_review.py (123), serializers/primitives.py | `chosen_format_columns` shape, board ranking, `due_date`, follow-up only with no plans (re-checked), `review_stamp` |
| B/management/commands/seed_benefits.py (1,134), seed_gtm.py (318), seed_stop_loss.py (329); V/devtools/checks/benefits_checks.py (763); V/usage/features.py (136); B/admin.py; V/backend/settings.py | Seeds, live checks, usage events, `CarrierTemplate` editable in admin (re-checked), `TIME_ZONE='UTC'` |

**Views and payloads**

| File (lines) | What it is / what it taught |
|---|---|
| B/serializers/pipeline.py (1,958; 1205–1893) | `export_cards`, default ticks (re-checked), reasons, `carrier_export_payload` |
| B/views/pipeline.py (2,581; 1700–1937), views/market.py (2,148), views/lens.py (68), views/review.py, views/cases.py (1,256), urls.py | Every endpoint; unlocked PATCH merge; stale-ack 409; `MarkMarketedView` resets the date (re-checked) |

**AI:** none. The RFP has no reader and no job.

**Frontend**

| File (lines) | What it is / what it taught |
|---|---|
| F/components/benefits/market/CarriersTab.jsx (1,366) | The RFP page; `clearMarkAfterEdit`, `afterPanelEdit`, form chip clears `packet` (re-checked) |
| F/services/api/benefitsMarket.js (455), benefitsReview.js (217), benefitsShared.js (423), benefitsClose.js (422) | API calls |
| …/close/ComparisonStatus.jsx (62), shared/CompletedMark.jsx (46), close/BuilderCard.jsx (79), shared/useExportCheck.jsx (151), shared/useDealTabStore.js (191), shared/SheetViewer.jsx | Load panel, card mechanics, check modal, cache, server-windowed sheet viewer |
| …/market/useMarketingChecklist.js (82), MarketingChecklist.jsx (577), CoverageIntentPanel.jsx (1,112), CoverageDocPicker.jsx (265), IntakeTab.jsx (1,638) | Shared intake panels; Mark as marketed |
| …/censusreview/CensusFormatLens.jsx (685), ExportReadiness.jsx (102); market/CensusTab.jsx (948), CensusGrid.jsx (1,215) | Lens; readiness cards read `client_in_progress` and `going_back` (re-checked); export picker |
| …/shared/CaseWorkspace.jsx (1,346), trayRefs.js (36), agenda/agendaRows.js (72); F/components/reviewrequest/ReviewQueue.jsx (474), shared/useReviewHotkeys.js (73); F/components/reports/CompareModal.jsx (146), CensusMappingReport.jsx (1,794); close/HubTab.jsx (349) | Nav, warm-up, tray, gap-queue engine, real-file grid, mapping report, returns-inbox field |
| F/utils/download.js (88), usage.js (212), fileDrag.js (55); F/guides/rfp.js (350), rfpToProposal.js (302) | Downloads, usage events, walkthroughs |
| 2V/frontend/src (tree), styles/tokens.css (81), package.json | The 2V shell; no xlsx parser in the browser (re-checked) |

**Styles**

| File (lines) | What it is / what it taught |
|---|---|
| F/styles/benefits.css (6,275): 766–770, 2974, 3028–3332, 3540–3591, 3905–3911, 4052+, 4411+, 5185–5326, 6104–6143 | Export rules, override link, chips (incl. `bnf-rfp-chip-off`, re-checked), cards, drafts, checklist rows, load panel, builder card, toolbar, packet grid, check modal, readiness cards |
| F/styles/benefits-census-review.css (928; 576+), benefits-coverage.css (527), reviewrequest.css (1,667), reports.css (1,158), benefits-workqueue.css (253) | Lens; coverage panel; `rr-change-chip`; `rpt-compare-actions`/`rpt-close`; `bnf-wq-chip` |

**Tests read:** B/tests_pkg/rfp_review_tests.py (199), export_check_tests.py (204), market_tests.py (4255–4999, 541–694), pipeline_tests.py (852–1266, 2535–2632, 5511–6160, 6889–7747, 8707–8800), review_board_tests.py, tab_speed_tests.py, export_guard_tests.py, presentation_workbook_tests.py, review_hub_tests.py, tasks_tests.py, existing_client_tests.py, questionnaire_tests.py, multiline_tests.py, agency_logo_tests.py, reports_tests.py, V/devtools/tests.py; 2V/quotes/tests/test_math.py.

## K.2 Old data model, in brief

- **`BenefitsCase.rfp_config` (one JSON blob).**
  - Settings: `carriers`, `other_carriers`, `funding`, `form`, `route`, `due_date` (raw text), `notes`, `include` (per-card overrides). Merged per key; `null` means "back to the default".
  - Writer-owned keys: `review` (card marks), `sent`, `asked`, `sent_with` (version numbers).
  - A legacy `lines` key is refused.
- **Deal fields it reads:** `marketed_at` (written by Intake), `requested_lines`, `commission_rates`, `agent_name`/`producer_name`, `renewal_date`, `stage`.
- **`CarrierTemplate`:** four live rows (`warner_census`, `aetna_gateway`, `angle`, `uhc`), seeded and patched by migrations, editable in admin, found by `name` because `key` is not unique. Each holds geometry, `columns` (header, hint, canonical_field, source, transform, value_map, required, employee_only, line, dependent_inherits), `group_info`, formats, `max_rows`, `size_band`, `row_scope`, `tier_codes`.
- **`AgencyProfile`:** returns inbox, agency name, producer, email, address, phone, default commission, brand colour, logo.
- **Constants:** 12 medical and 13 ancillary carriers, `COLUMN_LINES`, the Warner inbox, `VARIANTS`, packet reasons, `RFP_CARDS`, check scopes.
- **Computed on read:** `resolve_rfp`, `export_cards`, `group_facts`, drafts, summary, check report, lens payloads.

## K.3 Functionality inventory and verdicts

Rows marked **Changed** moved after the challenge review; the reason is in the row.

### Page shell

| # | Functionality (what the user sees → how it worked) | Verdict | New implementation |
|---|---|---|---|
| K1 | "RFP" in the sidebar under Get to Market → tab key `carriers` | Keep | Route `/deals/:id/rfp`; same label and place |
| K2 | `Loading...`, a load panel with "Try again", a "Refreshing…" chip → `useDealTabStore` | Simplify | React Query states drawn with the same `bnf-load-panel*`/`bnf-refresh-chip*` classes |
| K3 | The workspace warms the RFP payload when the browser is idle (D-115) | Simplify | **Changed** from Drop: Daniel chose "warm in background" so the first click is instant (D-115). Once the deal header loads and the browser is idle, the workspace calls `prefetchQuery(['deal', id, 'rfp'])` beside Intake and Census page 1. Same cache, no second store |
| K4 | Title "RFP", subtitle "The request that goes out for <account>…" | Keep | Legal name, else client name (X-150) |
| K5 | "Show me how ▸" | Drop | Walkthrough code |
| K6 | "✓ N of M completed" | Keep | Counted from the five marks |
| K7 | Collapse all / Expand all, this visit only | Keep | Component state |
| K8 | Census line: employees, dependents, readiness % (green ≥90, amber ≥70, else rose), errors, "Check it on the Census tab ▸" | Keep | Census facts. With no census, it names where the band's count came from (K17) |
| K9 | Collapsible cards; "✓ Mark completed"; "✓ Completed · name, date" with Undo; a completed card starts collapsed | Keep | `done[card] = {by: user id, at}`; the name is rendered from the user |
| K10 | An edit inside a completed card clears its mark (D-114 #3) through a second request | Simplify | rfp's own writes clear the owning card's mark in the same transaction through one `CARD_OF` map: settings → request; ticks, Select all, Reset, form chip → packet; Sent → emails. **Changed**: coverage and checklist edits are intake writes that rfp never sees, so after one saves, the page sends `done: false` for that card, only when it is marked (the old page's rule). Intake stays unaware of rfp |
| K11 | A browser promise queue orders every write | Drop | Server row lock and per-key changes |
| K12 | Coverage card shows both "Confirmed" and "Mark completed" (X-182) | Keep | **Changed** from Simplify: X-182 was triaged as deliberate. Confirmed is D-030's marketing gate; Mark completed is D-114's bookkeeping. Card 1 also holds the document picker. Asked in K.7 |

### Card 1: What we're shopping

| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| K13 | Intake's coverage-intent panel, controlled mode (intent, confirm/reopen, add lines) | Keep | Intake's component; its writes invalidate `['deal', id, 'rfp']` |
| K14 | Per-line document picker (kind, lines, upload, drag-drop) | Keep | Documents service |
| K15 | Questionnaire and stop-loss form pickers on the medical line and in the checklist, worded differently (X-184) | Simplify | **Changed**: both pickers stay (D-053 #6: "I would keep it in both spots"), over one intake service and one wording. The packet's "Not set up" row links to the checklist picker |
| K16 | The RFP's lines are the requested lines; no line list (D-045) | Keep | `Deal.requested_lines`; drop plan.md §6.9 `lines` |

### Card 2: What we're requesting

| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| K17 | "<band> · N enrolled" | Simplify | **Changed** (the draft gave two orders and lost two fallbacks). N comes from `quotes.facts.enrolled_headcount(deal)` → `{count, source}`. Order: first the medical enrollment the Advisor prices with: typed per-plan counts, the line's summary tier counts on a quote-first deal, the census by plan name or by line (employees only, waivers skipped). Then intake `enrolled_count`. Then intake eligible or total, marked "estimate". The same number drives the band, the checklist tier, the printed count and the questionnaire band (bug 5) |
| K18 | Band: 51 or more enrolled is large | Keep | `request.band(count)` |
| K19 | Cross-check "Enrolled: intake 42 · census 40 · Advisor 41" | New | plan.md §5.7. It also names the source used, and says so when it is an estimate. The same warning is a deal problem in the check of every file that prints the count |
| K20 | Route chips "standard under 51" / "standard at 51+"; clicking the default sends `null` | Keep | `route=''` follows the band until the first send pins it (K64) |
| K21 | Funding chips send the full list | Simplify | Add/remove changes. An empty list is kept, with "Pick at least one funding type" (bug 4) |
| K22 | Default funding: the medical coverage row, else fully insured plus level-funded | Keep | Current medical plans (`quotes.facts.incumbent`), then `CurrentCoverage`, then both |
| K23 | Carrier chips grouped Medical/Ancillary; a misfit is dimmed and dashed but clickable; tooltip; "own census" tag | Keep | Same markup and classes, `bnf-rfp-chip-off` included |
| K24 | Eligibility reasons "Not on the 2–50/51+ form", "None of the lines you picked" | Keep | Pure function; advice only |
| K25 | Carrier toggles send the whole list from stale props | Simplify | `{carriers: {add, remove}}` (bug 2) |
| K26 | Other carriers (≤300), Quotes due back, Notes (≤2,000); save on blur when changed | Keep | Never disabled while saving (bug 3); `due_date` is a Date |
| K27 | A bad value answers 400 by field: "That value was not accepted" | Keep | DRF field errors |
| K28 | Collapsed summary "Route · N carriers · due date" | Keep | |
| K29 | Commission request text is never shown (X-192) | New | Show the text the form prints, with "Commission ▸" |
| K30 | Override the band by hand near 50 | Defer | Open question. When built it lives on Deal, because intake's tier and the questionnaire band read it too |

### Card 3: Marketing readiness checklist

| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| K31 | Intake's checklist, controlled mode: tier, enrolled, meter, "Sent to market <date>" | Keep | Intake's component. **Changed**: intake is left of quotes, so quotes registers its headcount with an intake hook at start-up and the tier uses K17's number |
| K32 | Row actions: attest, waive, still needed, upload, ask through the tray, census Ask, custom asks | Keep | Intake and review services |
| K33 | Mark as marketed exists only on Intake; the Emails card points to a "checklist above" without it (X-02) | New | The Emails card footer offers intake's Mark as marketed once a draft is sent: same service, same 409 gate, "Send to market anyway?". **Changed**: intake's service keeps the first `marketed_at`; a repeat changes nothing; Undo through Activity (bug 13) |

### Card 4: RFP packet

| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| K34 | One table in sections: In packet · Document · Format · For · Rows · Check · Download | Keep | `bnf-rfp-grid` markup as is |
| K35 | "The whole RFP" three-state box, "N of M in packet · K off on purpose", Select all, Deselect all, a box per section | Keep | The server keeps only overrides that differ from the default |
| K36 | Census format rows: carrier, name, columns, scope, For (Warner shows "Any carrier"), Rows | Keep | From the format definitions |
| K37 | Row notes "your pick", "Off on purpose — …", "Ticked by hand — …" | Keep | |
| K38 | "Usually a 2–50 format" note; employee-only row scope | Drop | No live format uses either after 0055 and 0066 |
| K39 | With carriers picked, Warner's universal census is always ticked (D-063 #6) | Simplify | Ticked when nothing is picked, the route is Warner, a picked carrier has no format of its own, or "Other carriers" is filled (bug 29). **Changed**: the "Other carriers" draft carries the universal census, so filling it ticks the file. Asked in K.7 |
| K40 | Angle CSV row, off on purpose, own download | Keep | |
| K41 | A census card is offered with an empty census | Simplify | Unavailable, reason "No census yet" |
| K42 | Warner form + census rows (Simplified, 2–50, 51+): download only, version, "standard", band reason, cap warning | Keep | |
| K43 | Questionnaire PDF and stop-loss disclosure rows; "Not signed by the employer yet"; default ticks follow who takes the form and the funding asked | Keep | `questionnaire.rfp_files`, `copy_to_send` (warns when two copies would go), `takes`, `disclosure_needed`. Lands with the questionnaire slices |
| K44 | Acrobat original questionnaire, off on purpose | Defer | The questionnaire plan defers the XFA copy |
| K45 | "Not set up" row with "Open Overview ▸" | Simplify | Links to the checklist picker (K15) |
| K46 | Request form card with variant chips ("standard", misfits dimmed); a pick writes `form` | Keep | |
| K47 | Cover page card; the route decides which cover leads, the other is off on purpose | Keep | |
| K48 | Comparison workbook, client proposal, benefit guide, contribution model, stop-loss workbook, all off on purpose | Drop | They duplicate the Proposal export viewer and show competitors' pricing. Dropping them fixes X-186 and lets rfp sit left of proposals. Reverses D-063 #5: asked in K.7 |
| K49 | Attachments: renewal, claims, invoice, SBC, paper questionnaire or disclosure. Defaults: invoice off; paper copy off once the in-app form is signed; claims on at 100+ enrolled or level/self-funded; paper disclosure follows funding | Keep | Live documents only. **Fix for 2V roles**: renewal = kind renewal, or kind quote with role renewal. An SBC is ticked when its role is current or renewal. Alternates are off on purpose ("Another carrier's plan"). No role: listed, unticked, "Role not set" |
| K50 | Attachment Download has no check, busy label, toast or error handling (X-185) | Simplify | Through rfp's file door (K51): same modal, busy label, toast and error; PHI kinds logged |
| K51 | Row downloads go through the check | Keep | **Changed**: one door, `files/{key}/`, for every row, the packet and each draft. Questionnaire and attachment bytes are read from their owners |
| K52 | Check pills Ready / N problems; questionnaire rows never get one (bug 12) | Simplify | One `checks/` call, re-run only when `checks_stamp` changes (K.6). Every row gets a pill, "Unsigned" included |
| K53 | "Check ▸" opens the lens | Keep | |
| K54 | Footer member list; "Recommended" (X-183) | Keep | Renamed "↺ Reset to recommended" |
| K55 | "Download packet (N) ⬇" | Keep | Built once. A failing member refuses the download with a 409 naming its label only (bug 36) |
| K56 | Stale `attachment_<id>` overrides pile up | Simplify | Ignored on read, pruned on the next write |

### Card 5: Emails to send

| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| K57 | Sub-line explains the route | Keep | |
| K58 | Table To · Subject · Attached · Draft · Sent | Keep | |
| K59 | Warner draft: quoting inbox, request summary, the whole packet | Keep | |
| K60 | Direct drafts: one per carrier plus "Other carriers"; blank To; never names another carrier | Keep | The subject lists that carrier's own lines (bug 20) |
| K61 | Which attachments go to which carrier (`_for_carrier`) | Simplify | `audience.receives()`: the paper questionnaire follows `takes`; PHI files follow the lines they cover (bug 10) |
| K62 | Copy puts "Subject: …" and the body on the clipboard | Keep | |
| K63 | Open in Outlook: `.eml` with `X-Unsent: 1`, no From | Keep | A failing member answers 409 by label (bug 9). Attachments are typed from an explicit map and served chunked (bug 39) |
| K64 | Sent tick stores date, `asked` and `sent_with`; refused on lost and past deals; untick removes them | Simplify | Row lock; agency-zone date; stores `{on, at, by, route, asked}`. **Changed**: no `files` snapshot (nothing reads it; `at` serves a later "changed since"). The first send pins an empty route. Un-marking works for any stored key |
| K65 | Sent date shown as raw ISO | Simplify | Shown as "Nov 11" |
| K66 | "Marked sent X of Y" | Keep | |
| K67 | "Changed since sent" (computed, never shown) | Defer | Later: compare each owner's last change with `at` |
| K68 | Stage after sending | New | The first send runs `advance(quoting)`, forward only |
| K120 | A send whose draft no longer exists (route or picks changed) vanishes from the table but still counts as asked | New | "Sent earlier" rows: label, date, Undo (bug 35) |
| K121 | Attachments too large to email | New | A check problem when a draft's files pass about 20 MB; base64 adds about 37% |

### Export check modal

| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| K69 | "Before you download: <label>", count or "All checks passed", rows (⚠, where, text, up to 20 names, "Fix ▸"), "Not now", "Download (anyway) ⬇" | Keep | Fix links use 2V routes |
| K70 | Download sends `ack=<digest>`; a stale one gets 409 with the fresh report and "Something changed…" | Keep | |
| K71 | "File" depth builds the file to learn fill-only problems | Drop | Row-level checks; build once; template drift answers 500, guarded by tests. **Changed**: the one fill-only warning (CSV values carried as text) moves to row level (K74); exception text never reaches a report (bug 36) |
| K72 | Seven scopes | Simplify | `check(deal, key)` plus `checks(deal)` over one key space |
| K73 | Deal problems: AI value not in file, AI open, client waiting, client still typing, sent back | Simplify | `documents.review_rules.open_warning` and pending-count selectors. **Changed**: "client still typing" stays, because Export readiness builds its sentence from it. Counts by state come from census and questionnaire; if review keeps those states, it registers a counter with rfp's check |
| K74 | Census problems: validation, required blank, overflow, blank tier, translation notes (names in the app only), group-tab blanks | Keep | Blank tier counted once per employee (bug 17); one overflow line (bug 16); the CSV formula-like count at row level |
| K75 | `unknown_field` problem | Drop | Definitions are code; a test proves every field exists |
| K76 | Questionnaire problems (empty, incomplete, unsigned, check codes, waiting) | Keep | Questionnaire selectors; lands with its slices |
| K77 | Cigna and Gravie "census needs" warning | Drop | False (bug 11). Carrier-declared census needs are not added: `medical_plan` is already required whenever medical is in force (plan.md §5.3.3 rule 4), the only time a plan election exists |
| K78 | `blocking` codes (always empty) | Drop | Nothing is refused |
| K122 | Broker fields print blank on a deal with no owner | New | Agent from the owner, else `created_by`; deal problem "No owner on this deal" (bug 19) |

### Census format lens

| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| K79 | Export readiness cards: status, client-waiting sentence, "⬇ Export", click or Enter opens | Keep | Enter also closes; Export offers every format; "Unsigned" says so |
| K80 | Lens chips: "Our census", formats (badge; rows · columns · gaps · in packet; CSV/XLSX), Warner forms + census | Keep | One list payload |
| K81 | Lens head with Download | Keep | One label everywhere: "⬇ Export" (X-163) |
| K82 | "Check the real file ▸": a server fill drawn by `sheet_grid` in CompareModal | Simplify | **Changed** (2V has no xlsx parser in the browser): `files/{key}/look/?sheet=&start=` builds the file once and returns windows from documents' shared `look()`, the path of the document viewer and the Proposal export viewer. Angle's CSV is one sheet. Logged as a PHI view |
| K83 | Stats: Rows (of max), Columns, Filled % (floored), We don't store, Warnings | Keep | |
| K84 | Gap queue: A fill in, X ask, R later; up to 200 items | Keep | Review's queue engine; census service write. A derived column asks for its inputs (`describe.py`) |
| K85 | "＋ Ask N" | Keep | Review tray |
| K86 | "Make these required on this deal" | Drop | Duplicate path: the request's formats already feed required-ness (K124) |
| K87 | Column-by-column section; first 50 rows (up to 200), missing cells highlighted, legend | Keep | Fills, rules and translation text from `describe.py` |
| K88 | "What they ask that we don't store" plus unwritten columns with formula counts | Simplify | `gaps` and `not_sent` stored per format; drop the physical-sheet reader |
| K89 | Census grid export picker (formats plus three form + census options) | Keep | Same check modal |

### Builders

| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| K90 | `fill_xlsx`: rewrites only sheetData, merges, dimension; styles explicit, nearest row, row, column; text cells stay text; formulas untouched; inline strings; cloned styles; recalc flag only when a formula reads a written column; `lastModifiedBy`; drops Aetna's thumbnail; Excel-like zip entries | Keep | Ported unchanged, split into `rfp/xlsx/` |
| K91 | `sheet_to_csv` like Excel's Save As CSV UTF-8 | Keep | |
| K92 | Census row builder: family order; line gating; inherit; vocabulary translation; age at effective date; county (typed wins); IN_AREA; notes; missing cells; typed cells | Keep | Pure function over Member JSON |
| K93 | Warner (B–X, 500, PAY MODE "Annual"), Aetna (A–I, 485, J1 selector), Angle (B–I, 213, xlsx + csv), UHC (A–X, 350, 19 group facts) | Keep | Generated from the final migration state, then diffed against the 2026-09-17 doc **and** the live rows, since admins could edit them |
| K94 | Templates as rows, admin editing, a fresh-openpyxl path | Drop | Vocabulary is code; every format ships its own file |
| K95 | Unused `case:`/`const:` sources, `row:waive_all`, `date_mdy`, `upper`, SSN and `tier_code` transforms, `tier_codes` | Drop | No caller after 0055/0066 |
| K96 | Drift guard by column letter, plus group-tab labels | Keep | |
| K97 | Rows past the cap are cut; the warning promises a second file that doesn't exist | Simplify | **Changed** from New: splitting is Daniel's call, and Angle's 213 is styling, not a carrier limit. The warning says how many people did not fit and shows in the check. Angle's CSV is written from the rows and carries everyone. Split or extend waits for K.7 |
| K98 | UHC "employees applying" vs roster warning | Simplify | **Changed**: merged into K19. The group tab prints K17's count, so the old comparison repeats the cross-check (duplicate path) |
| K99 | Warner request form: label guard, header facts, funding boxes (2–50 has no ASO box: warns), matrix only where a box exists, wrapped Notes, Additional Carriers, inline census (500), header-only in the packet | Keep | `VARIANTS` copied as is |
| K100 | Simplified form carries only the header and commission box | Keep | Deliberate fidelity |
| K101 | `group_facts`: about 6 queries, rebuilt in every fill | Simplify | `quotes.facts.group_facts` plus `rfp/printed.py`, built once per request. `group.enrolled` = K17's count (bug 38) |
| K102 | Cover PDF: letterhead, group, size, coverage requested with what is in force, funding boxes, broker, return-to, BOR, commission by line, notes; names no carrier | Keep | Agent from the owner, else the creator (K122); agency fields; agency-zone date (bug 22) |
| K103 | Packet zip: README plus `Quote request summary.txt` | Keep | Summary only on the Warner route (bug 23); agency name in README (bug 21) |
| K104 | Drafts, `asked_for`, other-carrier name splitting | Keep | |
| K105 | Three-tier carrier matcher and identity | Keep | `deals/carriers.py` holds the one identity list. rfp's attributes are keyed by the same keys; a test proves they match |
| K106 | Commission request text (one label, or grouped) | Keep | Pure builder in `deals/comp.py`. Rates come from commission once built; `AgencySettings.default_commission` until then |
| K107 | Formula guard (CSV apostrophe, XLSX text) | Keep | Foundation's guard |
| K108 | `recut_warner_census.py` | Keep | Offline tool in `rfp/tools/`, never imported |
| K109 | Census-mapping report, its workbook, its compare page | Drop | Developer-only. The lens's helpers (`kind_of`, `DERIVE_INPUTS`, `GAP_HOMES`, unwritten columns) move to `rfp/formats/describe.py` |

### Rules, records, other modules

| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| K110 | Every signed-in benefits user; COI partner gets 403 | Simplify | Admins and producers |
| K111 | Lost deal: sends refused (409); edits allowed | Keep | |
| K112 | Past or closed year: only the Sent tick is disabled | Defer | Waits on the renewals question |
| K113 | No PHI download log (bug 26) | New | `downloaded` Activity rows |
| K114 | `private, no-store` missing on two downloads | Keep | Every file goes through `file_response` |
| K115 | No Activity for RFP writes | New | Before/after per key, with Undo; notes get a summary only. **Changed**: coalesced settings rows merge first-before and last-after; sends and marks never coalesce |
| K116 | Usage events, Data Hub footer, demo seeds, live checks, dead endpoints (`census-export-check/`, `?check=1`, `carrier-templates/`) | Drop | Machinery with no product caller |
| K117 | Markets checked consumers (screen, client workbook tab, PDF/PowerPoint page, `market_notes`) | Keep | `selectors.asked_by_line` |
| K118 | Review board "blocks a chosen carrier" | Keep | Reads K124's columns: only formats the request sends (bug 24) |
| K119 | Agenda `build_rfp`/`follow_up_carriers`; journey "Sent to market" opens Intake (X-09) | Keep | Those steps open the RFP tab |
| K123 | Carrier follow-up counts from `marketed_at` and fires only when the deal has no plans | New | `summary.facts` adds `first_sent_on` (used when `marketed_at` is blank) and `awaiting`: asked carriers with no plan from them since the send |
| K124 | A column a picked carrier's file requires shows as required in the Census tab | Keep | `required_columns(deal)` → `{key: {employee: [names], dependent: [names]}}`, registered with census. **Changed** from the draft's set over every ticked format: pure (request, definitions, requested lines; no census read). Scope: picked carriers' own formats, hand-ticked formats, and the universal format when a picked carrier or "Other carriers" takes it |

## K.4 Data flow (in and out, by model, field or function)

**In:**
- **deals:** `Deal` client name, `effective_date`, `requested_lines`, `owner` else `created_by`, `stage`. `Contact`: primary, else HR admin, else first. `AgencySettings`: name, address, phone, email, brand colour, logo, `rfp_return_email`, `default_commission`. Helpers: `carriers`, `comp`, line `short` labels, `clock.today()`, `locked`, `advance`, `file_response`.
- **documents:** live `Document` rows of kinds renewal, quote (role renewal), claims, invoice, sbc (role, carrier), questionnaire, stop_loss (label, lines, file); `review_rules.open_warning`; `look()` sheet windows.
- **intake:** `legal_name`, `address_physical`/`mailing` (`split_address`), `locations_list`, `sic_code`, `fein`, `enrolled_count`, `waiting_count`, `employee_count`, `total_employees`, `atne`, `years_in_business`, `waiting_period`, `hours_threshold`; `CurrentCoverage` (carrier, funding, in force); BOR on file; intent confirmed; `marketed_at`; form choices.
- **census:** members in family order (one query), one validation run, the facts row, FTE, age at a date, ZIP, pending counts by state, `last_import_at`.
- **quotes:** `facts.enrolled_headcount` (and batched), `facts.group_facts`, `facts.incumbent`; Plan `carrier`, `created_at` for `awaiting`.
- **questionnaire:** `rfp_files`, `copy_to_send`, `takes`, `disclosure_needed`, `pdf.build`, problems, pending counts.
- **commission:** requested rates.
- **review (registered):** client in-progress and sent-back counters, if review owns those states.

**Out:**
- `RfpRequest` writes; Activity rows with before/after; `downloaded` rows.
- `deals.services.advance(quoting)` on the first send.
- Intake's mark-marketed, called from the Emails card through intake's endpoint.
- A refresh of census's stored facts when the provider's answer changes.
- Files never stored: census xlsx/csv, form xlsx, cover PDF, zip, `.eml`.

**Read by others:**
- **proposals:** `asked_by_line(deal)`.
- **census:** the `required_columns(deal)` provider.
- **review:** `required_columns`, `checks`, `due_date`.
- **agenda and overview:** `summary.facts(deal_ids)` → route, carriers, drafts sent/total, `first_sent_on`, `last_sent_on`, cards done/total, due date, `awaiting`.

## K.5 Bugs and pain points found (with file evidence)

1. **Lost updates on `rfp_config`.** The PATCH merges without a lock (`views/cases.py:501-514`); `mark_draft_sent` has no lock or transaction (`rfp_email.py:373-396`); only marks lock (`rfp_review.py:44-57`); ordering relies on a browser queue (`CarriersTab.jsx:521-529`). PATCH, mark-sent and mark-marketed never move `updated_at`.
2. **Two quick chip clicks drop the first pick:** the list is built from stale props and replaced whole (`CarriersTab.jsx:151-162, 181-193`).
3. **Notes typed during another save vanish:** inputs are disabled while saving (`CarriersTab.jsx:280,290,299`; X-180).
4. **Funding can never be cleared:** a stored `[]` falls back to the default (`rfp.py:196`).
5. **The band is not medical enrolled:** intake, else every employee row including waivers; typed Advisor counts never count (`marketing_checklist.py:228-252`, `rfp.py:470-472`).
6. **Every download builds its file three times** (`useExportCheck.jsx:42`, `export_check.py:395-400`, `views/market.py:412-423`, `views/pipeline.py:1920-1926`).
7. **Pills reload the roster per format and refire on every change**, including Mark completed and Sent (`export_check.py:152-157, 291-306`; `CarriersTab.jsx:576-583`; `ExportReadiness.jsx:30-40`; `review/board.py:587-597`).
8. **2–4 requests per control.** Mark-sent returns the whole payload (`views/pipeline.py:1873`); the PATCH builds an unused Overview payload (`views/cases.py:552`).
9. **`.eml` silently drops failing members** (`rfp_email.py:400-408`, `export_check.py:401-411`), against the spec (`rfp-cover-and-drafts.md:31`).
10. **PHI leak:** a paper medical questionnaire and claims go to every direct draft (`rfp_email.py:92-94`).
11. **False "census needs" warning for Cigna and Gravie** (`export_check.py:318-331`): 0054 maps CURRENT PLAN ELECTION to `medical_plan` (lines 122–128).
12. **The "unsigned" pill never shows:** pills render only on census rows (`CarriersTab.jsx:1094, 832-878`).
13. **A dead-end hint and two "sent" facts.** The hint points to a control the page lacks (`CarriersTab.jsx:385-390`; X-02; the control is at `IntakeTab.jsx:865-885`). Sends never set `marketed_at`. Every mark-marketed call resets it, restarting the 10-day follow-up (`views/market.py:1232`).
14. **Past years stay editable; the server refuses nothing on PATCH** (`CarriersTab.jsx:172-307`).
15. **Rosters past a cap are cut** while the warning promises a second file (`workbooks.py:725`; `plan_math.py:1428-1432`; `quote_request_form.py:282`).
16. **Form + census warns twice about overflow** (`plan_math.py:1428-1432`, `quote_request_form.py:280-283`).
17. **Blank-tier warning counts by header:** Warner's three tier columns share one header, so 9 employees read "18" (`plan_math.py:1385-1392, 1410-1414`; X-201).
18. **The UHC headcount warning counts waived employees** (`workbooks.py:674-702`).
19. **The cover prints "—" for agent, email, phone and return-to**, and "Full-time employees 0" when hours are blank (`rfp_cover_pdf.py:249-257`, `plan_math.py:1009-1054`; X-194). In 2V it persists when `Deal.owner` is empty (`2V/deals/models.py:32`; AgencySettings has no producer name).
20. **Direct subjects list every requested line** (`rfp_email.py:145-147, 180`).
21. **Hard-coded firm name** (`rfp_email.py:106`, `rfp_bundle.py:145`, `workbooks.py:670-671`); README uses the account name, not the legal name (`rfp_bundle.py:131`).
22. **Dates stamped in UTC:** Sent (`rfp_email.py:383`), README (`rfp_bundle.py:132`), cover (`rfp_cover_pdf.py:210`) (X-40).
23. **The packet summary names every carrier asked**, even in direct packets (`rfp.py:560-571`, `rfp_bundle.py:204-206`).
24. **The review board flags formats nobody picked**, and its test mocks the report (`review/board.py:587-597`, `review_board_tests.py:650-667`).
25. **Two roster downloads are cacheable** (`views/market.py:462-465`, `views/pipeline.py:1765-1770`).
26. **No PHI access log** on census, zip or `.eml` downloads.
27. **A GET writes:** packet and `.eml` builds create questionnaire responses (`rfp_bundle.py:16-17`, `serializers/pipeline.py:1598-1603`).
28. **Card marks store a display name** (`proposal_review.py:45-52`).
29. **Universal census ticked whenever carriers are picked** (`serializers/pipeline.py:1398-1401`, recorded in D-063 #6), even when nobody on the request receives it.
30. **Dead code:** `census-export-check/`, `?check=1`, `carrier-templates/`, unused payload keys, never-set busy states, CSS `.bnf-rfp-note` and `.bnf-export-chev`.
31. **Undefined tokens:** `--accent` without fallback (`benefits.css:3273`); `--ink-soft` at 2282, 2298, 2338, 2352, 2367, 3561–3576.
32. **Templates are migration-seeded, admin-editable rows** found by `name` (`admin.py:93-96`); `rfp._SHORT_LINES` repeats line labels with other spellings.
33. **Corrections to earlier claims:** `is_historical` = complete, lost, or a renewal over 365 days old; archived deals still accept RFP writes; "Deselect all" sends `null` for cards already off; `due_date` is raw text; each off-on-purpose document has its own message; readiness cards open on Enter only, export only the primary format, and read "unsigned" as "N things to fix".
34. **2V plan.md is out of date:** §9.8 PAY MODE and cap 587 (0055 made them "Annual" and 500); §9.8 keeps UHC "Waive all" (0066 removed it); Appendix A omits 0055; §9.10's README lists warnings (D-143 forbids); §9.11 sends direct carriers the universal census too; §4.7's matcher is one tier; §5.3.3's provider is a set; §5.7 prints intake counts and defaults the route to Warner.
35. **Sends vanish from view** when the route or picks change: un-marking works "for any stored key" (`rfp_email.py:348-360`), but the table lists only current drafts.
36. **Exception text reaches the screen:** `build_failed` (`export_check.py:202`) and packet warnings (`rfp_bundle.py:162-166`) print `({exc})`, which can carry a member's value.
37. **Angle's CSV inherits the workbook's 213-row cap** (0055 header), though the portal CSV has no limit.
38. **The printed enrolled count and the band disagree:** `group.enrolled` prints intake first (`rfp.py:470-472`) on Warner's D15 (`quote_request_form.py:67`), the cover (`rfp_cover_pdf.py:230`) and UHC's tab (0054:317).
39. **2V risks found while porting:** `file_response` types `.xlsx` as octet-stream (`2V/deals/downloads.py:16-17`; Python's built-in map lacks `.xlsx`; the slim image has no mime.types), which is why the old `.eml` kept a map (`rfp_email.py:52-62`). `FileResponse` sets Content-Length, so a large zip or `.eml` meets Cloud Run's 32 MiB limit on non-streamed responses. Porting "every SBC" (`serializers/pipeline.py:1465-1467`) onto 2V roles (`2V/documents/kinds.py:19-25`) would send alternate SBCs to every carrier.

## K.6 New design

**App and chain.** One `rfp` app, moved left of `proposals`: `accounts → deals → documents → ai → intake → census → quotes → questionnaire → commission → rfp → proposals → review → agenda → overview`. Proposals reads who was asked, and once K48 is dropped rfp needs nothing from proposals.

**Start-up registrations** (the ai-registry pattern; an app registers with one to its left):
- rfp → census: `required_columns` as the `carrier_required` provider.
- quotes → intake: the headcount for the checklist tier.
- review → rfp check: client in-progress and sent-back counters, only if review owns those states.
- rfp → deals: the Activity reverter for Undo.

**Moved left (needs):**
- `deals/carriers.py` (data): key, name, group, aliases; `match`, `identity`, `display_name`, `norm`, `split_names`.
- `deals/comp.py`: `parse_comp`, `comp_label`, the request-text builder (shared with intake's in-force commission).
- `quotes/facts.py`: `enrolled_headcount(deal)` → `{count, source}` (K17), `enrolled_headcounts(deal_ids)`, `group_facts`, `incumbent`.
- `documents/sheets.py`: `look(xlsx_bytes, sheet, start, rows)`, shared with `documents/{id}/sheet/` and the Proposal export viewer.
- `deals/downloads.py`: an explicit content-type map (xlsx, xlsm, docx, csv, pdf, zip, eml) and a chunked option.
- `deals/pdfkit.py`: theme, letterhead, `date_long`; reportlab joins `requirements.txt`.

**Model** `RfpRequest`, one per deal:

| Field | Shape |
|---|---|
| `deal` | OneToOne, primary key |
| `route` | `''` (follow the band), `warner` or `direct` |
| `carriers` | JSON list of carrier keys, registry order |
| `other_carriers` | Char(300) |
| `funding` | JSON list, or null for the default; `[]` is a real pick |
| `form` | `''` (Simplified), `small_group` or `large_group` |
| `due_date` | Date, null |
| `notes` | Text, ≤ 2,000 |
| `include` | `{file_key: bool}`, only differences from the default |
| `done` | `{coverage, request, checklist, packet, emails: {by: user_id, at: iso}}` |
| `sends` | `{draft_key: {on: 'YYYY-MM-DD', at: iso, by: user_id, route, asked: [{key or null, name, lines}]}}` |
| `updated_at` | DateTime |

**One key space** for include, pills, checks, downloads and the lens: `census-warner`, `census-aetna`, `census-angle`, `census-angle-csv`, `census-uhc`, `form`, `form-census-<variant>`, `cover`, `questionnaire-<form>`, `disclosure-<form>`, `doc-<id>`; checks and downloads add `packet` and `draft-<key>`.

**Data modules:** `rfp/carriers.py` (Warner columns per carrier per band, census format, `on_form`, note, inbox; keyed like `deals/carriers.py`); `rfp/formats/definitions.py` (four formats: geometry, columns `{header, hint, field or source, transform, value_map, required, employee_only, line, inherits}`, `group_info`, `gaps`, `not_sent`, derived inputs), generated once from a migrated old database, diffed against the 2026-09-17 doc and the live rows, Warner S and X checked against the workbook; `rfp/forms/maps.py` (`VARIANTS`); seven workbooks (hash-checked) and `zip_county.csv.gz`.

**Pure modules** (no database access):

| Module | Job |
|---|---|
| `request.py` | Band, route, defaults, eligibility, cross-check, summary text |
| `printed.py` | What files print on top of `quotes.facts.group_facts`: due date, broker (owner else creator; agency), return-to (`rfp_return_email` else owner email), funding flags, UHC tokens, Aetna selector, enrolled (K17) |
| `cards/` | `census.py`, `forms.py`, `docs.py`, `defaults.py`: the one card list |
| `audience.py` | `receives(card, carrier or None, band)` |
| `drafts.py` | Drafts by route, subjects, body, sign-off, `asked_for` |
| `formats/` | `rows.py`, `translate.py`, `county.py`, `describe.py`, `lens.py` |
| `xlsx/` | `refs.py`, `sheet.py`, `package.py`, `csv.py` |
| `forms/fill.py`, `cover.py`, `packet.py`, `eml.py` | Builders |
| `check/` | `census.py`, `questionnaire.py`, `deal.py`, `digest.py` |

**Services** (`rfp/services.py`). Each runs in a transaction: `get_or_create` the row (Django re-reads after an IntegrityError), then `select_for_update`. An unchanged value writes nothing.
- `update(deal_id, user, changes)`: settings; `carriers`/`funding` as `{add, remove}`; `include` true/false/null or `reset`. Clears the owning card's mark. Activity per key, coalesced as `rfp:request` with first-before/last-after. When carriers, other carriers or include change, refreshes census's stored facts on commit. Returns `{changed, request, cards, drafts, checks_stamp}`.
- `set_done(deal_id, user, card, done)`: never coalesced.
- `mark_sent(deal_id, user, key, sent)`: lost → 409; marking an unknown draft → 404; un-marking any stored key works. Pins an empty route. Stores the send. First send → `advance(quoting)`. Never coalesced. Returns `{draft, stage, sent_count}`.
- `log_download(deal, user, what)`.

**Selectors:** `page`, `checks` (one roster load, row level), `check(deal, key)`, `formats`, `format_detail`, `look`, `asked_by_line`, `required_columns`, `summary.facts(deal_ids)` (fixed query count: stored census facts, batched headcounts, one plans query; never cards per deal).

**`checks_stamp`:** a hash of the census, questionnaire, intake and documents change times plus `funding`, `carriers`, `other_carriers`, `route`, `include`. Marks, sends and notes do not change it.

**Endpoints** (under `/api/`):

| Method | Path | Purpose |
|---|---|---|
| GET | `deals/{id}/rfp/` | Page payload with `checks_stamp` |
| PATCH | `deals/{id}/rfp/` | Settings, toggles, include |
| POST | `deals/{id}/rfp/done/` | `{card, done}` → `{done}` |
| GET | `deals/{id}/rfp/checks/` | Pills and deal problems |
| GET | `deals/{id}/rfp/check/?file=` | One report and its digest |
| GET | `deals/{id}/rfp/files/{key}/?ack=` | Every row, `packet` (zip), `draft-<key>` (`.eml`) |
| GET | `deals/{id}/rfp/files/{key}/look/?sheet=&start=` | Real-file windows |
| POST | `deals/{id}/rfp/drafts/{key}/sent/` | `{sent}` |
| GET | `deals/{id}/rfp/formats/`, `formats/{key}/?rows=` | Lens |

`/api/meta/` gains `rfp`: carriers, funding, forms, routes, format keys and labels only. No query parameter is named `format`.

**Downloads and PHI.** Every file goes through `file_response`; names follow `<Client> - <Carrier> census.xlsx`. The zip and `.eml` stream chunked (confirm at deployment). `downloaded` rows for census files, form + census, a packet or `.eml` carrying a census or PHI documents, attachments of PHI kinds and real-file views. A failing member answers 409 naming its label only.

**Frontend** (`frontend/src/deal/rfp/`):
- `RfpTab.jsx`, `useRfp.js`: `['deal', id, 'rfp']` with `staleTime: 0`, optimistic toggles, PATCH answers written with `setQueryData`; `['deal', id, 'rfp', 'checks', checks_stamp]` with `staleTime: Infinity`; the workspace's idle prefetch.
- `cards/RequestCard.jsx`, `CarrierChips.jsx`, `PacketCard.jsx`, `DraftsCard.jsx`, `SentEarlier.jsx`.
- `packet/PacketSection.jsx`, `PacketRow.jsx`, `TriTick.jsx`, `FormVariants.jsx`, `CheckPill.jsx`.
- `lens/CensusFormatLens.jsx`, `LensChips.jsx`, `LensColumns.jsx`, `LensGaps.jsx`, `LensPreview.jsx`, `GapQueue.jsx`, `ExportReadiness.jsx`, mounted by the census review view.
- Shared: `src/exportcheck/`, `src/viewer/` (server windows), `src/deal/shared/BuilderCard.jsx`, `CompletedMark.jsx`. Intake's coverage card and checklist mounted as they are. Every file under 300 lines.

**Styles.** Port unchanged: `styles/rfp.css` (benefits.css 3028–3332, 5185–5326); `styles/export.css` (766–770, `bnf-export-*`, 6104–6143); `styles/lens.css` (benefits-census-review.css from 576); `styles/buildcard.css` (4052+, 4411+). Shared files keep 2974, 3905–3911, `rr-change-chip`, `bnf-wq-chip`; checklist rows (3540–3591) stay with intake. Class names to copy:
- **Page:** `bb-tab-page`, `bb-tab-title`, `bb-subtitle`, `bb-panel-sub`, `bnf-rfp-toolbar`, `bnf-build-toolbar`, `bnf-build-progress(-done)`, `bnf-rfp-census-status`.
- **Cards:** `bnf-bcard`, `-head`, `-title`, `-toggle`, `-summary`, `-done`, `-mark`, `-badge`, `bnf-build-panel`, `bnf-card-toggle`, `bnf-req-chevron`, `bnf-rfp-card`.
- **Request:** `bnf-rfp-request`, `-group`, `-group-label`, `-chips`, `-chip`, `-chip-on`, `-chip-off`, `-chip-tag`, `-fields`, `-notes`, `-sub`.
- **Packet:** `bnf-rfp-packet`, `-packetcard`, `-gridcard`, `-gridbar`, `-gridscroll`, `-grid`, `-section`, `-section-title`, `-section-count`, `-section-sep`, `-tritick`, `-tritick-label`, `-col-tick`, `-include`, `-include-off`, `-doc`, `-row-in`, `-row-alt`, `-row-notice`, `-rownote`, `-rownote-deliberate`, `-pick`, `-for`, `-for-chip`, `-num`, `-pill`, `-pill-ok`, `-pill-warn`, `-variants`, `-download-only`, `bnf-export-name`, `-fmt`, `-actions`.
- **Drafts:** `bnf-rfp-drafts`, `-drafts-grid`, `-draft-actions`, `-draft-sent`.
- **Check modal:** `bnf-xcheck`, `-row`, `-icon`, `-text`, `-where`, `-people`, `-stale`, `-footer`, `bnf-export-ok`, `bnf-export-warnings`, `bnf-review-drillerror`, `bb-modal*`.
- **Readiness and lens:** `bnf-xready*`, `bnf-lens*`, `bnf-export-preview-*`, `-cell-missing`, `-legend*`, `-rownum`, `-meta`, `-empty`, `-warning`, `bb-acord-*`, `bb-stat-*`, `rr-change-chip`, `rr-change-cleared`, `rr-hint`, `bnf-wq-chip(-on)`.
- **Shared:** `bnf-override-link`, `bnf-review-note`, `bnf-marketing-guide-link`, `bnf-load-*`, `bnf-refresh-*`, `bb-badge`, `bb-amber`, `bb-rose`, `bb-green`, `bb-muted`, `bb-mono`, `btn`, `btn-primary`, `btn-secondary`, `btn-sm`.
- **Not ported:** `.bnf-rfp-note`, `.bnf-export-chev`, `bnf-export-handoff`, `rpt-compare-actions`, `rpt-close`. Define `--accent` and `--ink-soft` in the tokens.

**Tests** (pytest, behavioural):
- **request:** band at 50 and 51 from summary counts alone (quote-first), from the census, and from "120 eligible" (estimate, large); route default, override, reset; eligibility; funding order, `[]` kept; commission text; cross-check names all three and its source.
- **services:** two concurrent toggles both survive, also as the first writes on a new deal; unchanged writes record nothing; five chip clicks make one row whose Undo restores the first state; edits clear their own card's mark; `include` keeps differences and prunes stale `doc-` keys; lost deal: edits allowed, sends 409; 21:00 Eastern is still today; `asked` per route; the first send pins the route and moves the deal to Quoting; a later band change keeps the Warner row; "Sent earlier" lists a vanished draft and Undo removes it; Activity never carries notes or member data.
- **cards and audience:** default ticks; the "Other carriers" draft gets the universal census; alternate SBCs unticked and never attached by default; a renewal filed as quote/renewal is offered; `copy_to_send`; disclosure follows funding; direct drafts never name another carrier; questionnaire follows `takes`; PHI follows lines.
- **drafts and `.eml`:** subject per carrier; sign-off from the owner, else the creator; CC; `X-Unsent: 1`, no From; xlsx typed explicitly; chunked; failing member → 409 whose text holds no member value; size problem over 20 MB.
- **formats:** each source and transform; gating; inherit; family order; age; county; IN_AREA; translation notes; blank tier once per employee; overflow warns once and says how many did not fit; Angle's CSV carries everyone; CSV formula count at row level; printed enrolled equals the band's count on form, cover and UHC tab.
- **xlsx:** port `XlsxFillTests` and `ExportTypingTests`; every format matches its bundled file; a moved column raises; every field is a census key; rfp carrier keys exist in `deals/carriers.py`.
- **forms, cover, packet:** labels per variant, typed facts, boxes, matrix, notes, header-only copy, inline cap 500; one-page cover naming no carrier, return-to fallback, no logo; exactly the ticked files, summary only on Warner, README free of carrier names, 400 when nothing is ticked.
- **check and provider:** stable digest; stale ack 409; pills include "Unsigned"; "client still typing" listed; "No owner" listed; `checks_stamp` unchanged by marks, sends, notes, changed by a census edit; `required_columns` reads no census, has the dict shape, is empty on an untouched deal; census marks a picked carrier's blanks; proposals read `asked_by_line`; `summary.facts` uses as many queries for ten deals as for one; `awaiting` drops a carrier once its plan arrives.
- **downloads and lens:** headers, `downloaded` rows, no PHI in names; the list builds no rows; lens rows equal file rows; unknown key 400; `look` windows match the built file.
- **frontend:** Vitest for the three-state box and include-map builders.
- **Not ported:** `RfpPageSourceTests`, `CensusFormatDocTests`, `PdfRenderStateGuardTests`, seed tests, devtools checks.

**Build order** (fits plan.md §13):
1. R3.6: request and carriers; headcount from `quotes.facts`; commission text from `AgencySettings.default_commission`.
2. R3.7: formats, lens, provider; `documents/sheets.look()` built here if R4.7 has not landed.
3. R3.8: forms, cover, packet, drafts, sends, checks and pills, without questionnaire rows.
4. Later: questionnaire rows (K43, K76) with the questionnaire slices; commission rates at R4.2; review's counters at R4.5.

**Corrections to plan.md:** §3.3 chain; §4.7; §5.3.3 (provider shape and scope); §5.7 (headcount, band route, printed count); §6.9; §7.10; §8.9 (old look); §9.8–§9.11 and Appendix A, per K.5 #34.

## K.7 Open questions for Daniel

1. At exactly 50, does enrolled or ATNE decide the band, and how should a hand override work? Until answered: 51 or more enrolled is large; no override.
2. When intake's "currently enrolled" disagrees with the census or the Advisor's counts, which wins? The old app used intake. Until answered: the Advisor's medical enrollment, then intake, with a warning naming all three.
3. The full carrier list with each carrier's rep (fills the To line). Should Aflac, Kaiser, the Blues or UMR join the 25?
4. The returns inbox address. Until set: the owner's email.
5. Should the last Sent tick set "Sent to market" automatically? Until answered: the button (K33).
6. Claims, paper questionnaires and disclosures: only to carriers quoting the document's lines; with no lines, only medical carriers; never "Other carriers"? Until answered: yes to all three.
7. When a roster passes a carrier template's rows (Warner 500, Aetna 485, UHC 350, Angle 213): split into a second file, keep writing below, or stop with a warning? Until answered: stop with a truthful warning; Angle's CSV carries everyone.
8. Warner's "Nature of Business": SIC code, or a short description question on intake? Until answered: SIC code.
9. Keep both the Export readiness cards and the lens chips, or merge them (X-163)? Until answered: both.
10. Benefit Central or email only? Can you supply Mark's cover sample, and should the cover offer funding boxes beyond fully insured, level-funded and ASO?
11. Should past years become read-only? Waits on the renewals decision.
12. The comparison, client proposal, benefit guide, contribution model and stop-loss workbook leave the RFP page (they stay in the Proposal export viewer). This reverses D-063 #5. Agreed?
13. When every picked carrier has its own census format and "Other carriers" is empty, the universal census leaves the packet. D-063 #6 kept it. Agreed?
14. Card 1 keeps both "Confirmed" and "Mark completed" (D-114; X-182 triaged as deliberate). Keep both, or should Confirmed complete the card?
15. SBCs filed with no role: send by default? Until answered: listed, not ticked, "Role not set".
