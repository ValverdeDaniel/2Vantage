# Part H — Commissions

[← Porting plan](README.md)

**What it is:** Commissions tracks three things for each sold deal. First, what the carrier pays the agency on each line: a Comp (a percent of premium, flat dollars a year, or PEPM) applied to the sold premium. Second, who shares that revenue: the house, a primary producer, other producers and outside partners. Third, in the ledger, whether the carriers actually paid, month by month. In the old app it is a separate Django app (`commissions`: 20 models, 60 routes, about 17,800 lines with tests). It also adds a Commission tab to the deal, a card on the Overview, the `/commissions` back office and a client statement.

## H.1 Files read, in order (one line each)

V = Vantage (old), 2V = 2Vantage (new).

**Specs and READMEs**

| File (lines) | What it is / what it taught |
|---|---|
| V/commissions/README.md (432) | Module map, routes, seams, house rules, walkthrough beats |
| V/commissions/CLAUDE.md (85) | Invariants; three known defects (rebook, apply-scan lock, agreement tiers) |
| V/PlanningDocs/Commissions/commissions-module.md (244) | Phases 1–4; payouts and bonuses were never built |
| V/PlanningDocs/Commissions/commissions-build-spec.md (295) | Findings 1–13. §3.2: row terms (renewal amount, expiry, pool or gross). §9: open questions (referral basis; the own tier stays self-only) |
| V/PlanningDocs/Benefits/decisions.md (D-011–021, D-032–038, D-066, D-073) | Typed Comp; agreements; the CAA disclosure is required at close (D-020); statement reading; aliases; folds; a lost deal never books (D-037); split terms are visible to every producer (D-066 item 6) |
| V/PlanningDocs/Platform/efficiency-upgrade.md; items/5-security.md | Infrastructure copied three times; the 5-01 agreement leak, "decided, not built" |
| V/benefits/README.md (394) 306–340 | The six benefits→commissions seams |
| 2V/CLAUDE.md (42); 2V/plan.md (3,432) §1.2, 1.4, 3.3, 3.6–3.9, 4.7, 5.5–5.6, 5.10, 6.2, 6.4, 6.6–6.7, 7.8, 8.5, 8.10, 10, 12.3, 13, 15, 16 | Conventions; the app chain; Activity; carriers in `rfp`; the basis package and the 3,805 example; `summary.py`; "one home for carrier"; the ai Job and registry; ledgers listed out of scope (§1.4 :117–119, §15 :3323) |

**Models**

| File (lines) | What it is / what it taught |
|---|---|
| V/commissions/models.py (1,249) | 20 models (H.2) |
| V/commissions/lines.py (33), permissions.py (28), signals.py (31), apps.py (9), admin.py (71) | Lines per LOB; tiers (split capture is open to producers "on their own case", :3–5); file unlink; admin |
| V/commissions/migrations/0001–0012 | Schema history |
| V/benefits/models/case.py, models/radar.py | `commission_rates`, `CoverageLine.commission` and its source, `client_fold`, `referral`; `Client.owner`, `service_owner` |
| V/users/models.py (229) 29–92 | `commissions_access` |
| 2V/deals/models.py (94), activity.py (47), values.py (47), services.py (143), stages.py (23), lines.py (291), downloads.py (28) | `AgencySettings.default_commission`; `Client.relationship`; Activity needs a deal; `create_client` always makes a deal; `delete_client` cascades; `forward` keeps a deal lost |
| 2V/quotes/marks.py (162), services.py, math.py (176), packages.py (155), selectors.py (155) | `set_sold` has no lost check; `update_plan` and `delete_plan` ignore sold; `round_money` returns an int or a float; `line_packages`; `line_state` costs about 4 queries |
| 2V/documents/models.py, kinds.py (44), backend/meta.py (28), backend/urls.py (23) | A Document needs a deal and is stored per deal; kinds; /api/meta/; URL roots |

**Rules and services**

| File (lines) | What it is / what it taught |
|---|---|
| V/commissions/services.py (1,694) | `comp_amount`, resolver, validation, `compute_shares` (gross rows first), owner sync, `book_case` (fills nulls only), year number, freeze, rebook, holes, rollups |
| V/commissions/reconcile.py (667) | Month grid, gaps, `norm_name`, scorer, `auto_match_ok`, post, reverse |
| V/commissions/aliases.py (221); agreements.py (384); book_split.py (128); disclosure.py (151) | Spellings and the contested rule; agreement snapshot, hash and redaction; the book split, grouped by account manager; CAA data |
| V/benefits/pipeline/sale.py 94–162 | `mark_plan_sold` swallows booking errors |
| V/benefits/pipeline/plan_math.py; enrollment.py (194) | `tier_counts_with_source` never reads `Plan.enrollment`; `group_premium` does |
| V/benefits/market/validation.py 127–173 | `parse_comp` stores `%g`; `comp_label` |
| V/benefits/radar/reminders.py 294–316, 901–963, 1595–1621; radar/lineage.py 55–90 | `commission_gap` (off by default, its own grace setting, a $25 floor); `confirm_client_link`; `case_type_as_of` counts hand-added years |
| V/benefits/pipeline/closeout.py (193) 32–53; renewal.py (947) 95–133, 748–772 | Disclosure seam; rate and in-force carry |
| V/benefits/market/rfp.py (608); pipeline/quote_request_form.py (385); rfp_cover_pdf.py (276); rfp_bundle.py (243) | The commission request text |
| V/benefits/archive.py (188); versions.py (2,589) 571–585, 2072–2081 | Archiving never touches the ledger; commission data inside snapshots |
| V/users/access.py (530) 61–168 | Producers default to `own`; admin is forced to `all`; COI and fail-closed are `none` |
| V/referrals/models.py 78–125, views.py 165–186; V/jointventures/ledger.py (910) 37–40 | The P&C and JV readers of the ledger |
| V/commissions/management/commands/ (seed_practice 58, seed_story 75, seed_commissions 253, seed_commissions_walkthrough 603, seed_statement_docs 341, audit_plan_year_lineage 270) | Demo seeds; lineage audit |

**Views and payloads**

| File (lines) | What it is / what it taught |
|---|---|
| V/commissions/views.py (1,207) | Parties, agreements, schedules (`IsProducer`), records, splits, rebook (409), summary, changes, settings |
| V/commissions/views_reconcile.py (729); views_statements_scan.py (718) | Statements, receipts, an alias taught on each manual match, gaps, packet; upload, scan, chat, apply (job checked outside the lock), versions, file |
| V/commissions/views_agreements.py (228), views_aliases.py (166), views_disclosure.py (89), views_export.py (148) | Agreements (the list returns tokens to any producer) and the signer; aliases; CAA; XLSX |
| V/commissions/serializers.py (838), urls.py (87) | Hand-built payloads; 60 routes |
| V/commissions/workbooks.py (347), dispute_packet.py (140), agreement_pdf.py (144), disclosure_pdf.py (189) | XLSX exports; three reportlab PDFs |
| V/benefits/serializers/overview.py 1484–1638 | `commission_payload`: basis plan, float preview, the ledger read in a guarded try and sent to every user |
| V/benefits/serializers/case.py (261); status_report.py (420); pipeline/status_report_pdf.py (728); status_report_text.py (223) | Ledger data reaches every user |
| V/benefits/serializers/radar.py 615–624; client_overview.py (540) 308–354; primitives.py (360) 340–352; market.py (980); pipeline.py 1366–1380 | Work Queue owner; in-force column; agency default; coverage-line commission |
| V/benefits/views/cases.py (1,256) 315–347, 1118–1180; market.py (2,148) 802–855; portal.py (2,609); closeout.py (146); radar.py (687) 120–130; V/users/views.py (455) | Rate PATCH; agency profile; in-force write; portal exclusion; disclosure preview; archived clients; access edits |

**AI**

| File (lines) | What it is / what it taught |
|---|---|
| V/commissions/statement_reader.py (779) | Prompt, forced `record_statement` tool, chunking, normalising, dedupe across the whole statement |
| V/commissions/statement_offline.py (405) | A real keyless XLSX/CSV read (header row, synonym columns); `demo-` PDFs |
| V/commissions/statement_jobs.py (149); statement_chat.py (578); statement_versions.py (554) | Daemon-thread jobs; a chat with two tools; snapshots and diffs |
| V/docscan/kinds.py (195), chunking.py (461), client.py (320), jobs.py (189), serving.py (75) | Statement kind; 28 pages with 2 overlap; 5 MB images; serving |
| V/backend/settings.py (489) 223–254, 372–387 | `COMMISSIONS_STATEMENT_MODEL`, keyless fallback, `AGENTS_ENABLED` |

**Frontend** (V/frontend/src unless noted)

| File (lines) | What it is / what it taught |
|---|---|
| services/api/commissions.js (311) | 83 API functions |
| components/commissions/: CompInput 76, PartySelect 54, ExportButton 42, MonthStrip 100, GapsTab 194, BookingSummaryModal 209, RecordDrawer 300, BookTab 300, ByPersonTab 139, BookSplitTab 149, PartiesTab 346, PartyProfileDrawer 383, SettingsTab 134, SplitAgreementCard 226, SignAgreementPage 195, StatementScanReview 378, StatementHistory 305, StatementScanChat 381, StatementDocumentsTab 803, StatementsTab 516, CommissionsDashboard 191 | Every back-office screen. BookTab: a flat list with a group toggle and no paging. The statement tabs call `getCarriers` and `getReceipts` |
| components/benefits/shared/: CommissionTab 92, overview/CommissionPanel 173, overview/CommissionSummaryCard 81, overview/SplitsPanel 552, CaseWorkspace 1,346, CaseOverviewTab 333, overview/ClientHeader 238, ExportReportModal 333, PdfViewer 586 | Deal tab (open to all; the inline basis line); split terms (renewal, ladder, expiry, gross); nudge badge; Overview; status report; viewer |
| components/benefits/radar/client/: ClientCommissionsTab 415, ClientCommissionSnapshot 76, clientMath.js, ClientWorkspace.jsx, ClientHeaderCard 242, ClientOverviewTab 471 | Client statement (with "Comp disclosure ⤓" per plan year) and snapshot |
| benefits/close/ComparisonGrid.jsx, AdvisorTab.jsx; market/IntakeTab.jsx (1,638) 1484–1538; close/HubTab.jsx (349) | The booking modal opens on every Sold toggle; star; in-force input; agency default |
| Navbar.jsx 210, utils/home.js 24, utils/format.js 198, contexts/UserContext.jsx, services/api/benefitsRadar.js 88, UserManagementPage.jsx 302, users/RoleFields.jsx 257, CreateUserModal.jsx 136, App.jsx | Nav link, landing page, `compLabel`, `canSeeCommissions`, the access field, `/commissions` and `/s/:token` |
| guides/commissions.js (715), compAgreements.js (318) | Walkthroughs (sizes only) |
| 2V/frontend/src: ui/, deal/advisor, deal/proposal, pages/DealPage | Where the port fits |

**Styles**

| File (lines) | What it is / what it taught |
|---|---|
| styles/commissions.css (975) | `bnf-com-*` families; undefined `--accent` and `--accent-bg` (:957–961); a `.btn` patch; Manage Users badges; kept screens use `.bnf-com-histpane` (:804), `.bnf-com-workcols` and `-workstack` (:907–913), `.bnf-com-docactions` (:946–951) |
| styles/benefits-overview.css (1,020) 437–470, 652 | `bnf-ov-comm-*` |
| styles/benefits-radar.css (744) 647–733 | `bnf-cw-stmt-*`, `bnf-cw-snap-*` |
| styles/jointventures.css (389) 284–285; main.jsx 24; App.css 1–42, 256 | JV reuse; import order; `:root` tokens; the global `.btn-primary` |

**Tests:** V/commissions/tests.py (5,628): share math, resolver, booking, records API, reconcile, statements, scan, versions, chat, aliases, agreements, exports, book split, disclosure, access. Also V/users/tests.py (`CommissionsAccessTests`) and V/benefits/tests_pkg/: `case_tests` (`CommissionTests`, `RenewalCarryForwardTests`), `market_tests` (`CoverageLineCommissionTests`), `existing_client_tests` (`CarriedCoverageTests`), `pipeline_tests` (`CloseoutTests`, `QuoteRequestFormTests`, `StatusReportPayloadTests`), `portal_tests` (`ClientIntakePayloadLeakTests`), `radar_tests` (`CommissionGapRuleTests`, `ClientFoldTests`), `versions_tests`, `big_deal_speed_tests`.

## H.2 Old data model, in brief

- **Comp** is `{type: pct|flat|pepm, value}` everywhere. It is stored as `%g`, which keeps only 6 significant digits.
- **Settings** is a singleton: the producer % for year 1 (40) and for renewals (30); `default_external_split` (dead); gap grace (45 days); a P&C rate; a visibility default; a confirmed flag.
- **People:**
  - `Party`: producer, house, COI org or rep, or external broker; optional login, NPN, appointed, default split, payee and W9 fields.
  - `PartyLicense`, `PartyAppointment`.
  - `ProducerAgreement`: the producer's % by date and LOB.
- **Terms:**
  - A `SplitSchedule` is scoped to exactly one of client, case, referral or firm default (plus LOB, line and dates).
  - Its `SplitLine` rows hold party, role, amount, renewal amount, year ladder, expiry, basis (pool or gross) and a works-it flag.
- **Ledger:**
  - `CommissionRecord`, frozen per (case, line): client, plan year, carrier text and a registry link, rate and its source, premium and its source, enrolled count, dates, first-year flag, year number, status (booked, active, renewed, terminated, lost_bor) and `edited_by`.
  - `CommissionRecordSplit`: a frozen share % per party; the shares sum to 100.
- **Money in:**
  - `Carrier` registry.
  - `CarrierStatement`: header, file, `scan_state`, draft or posted.
  - `CommissionReceipt`: the printed fields, provenance, match and reversal; locked once posted.
  - `GapResolution`: one per record and month.
  - `ClientAlias`.
- **Machinery:** `ChangeLog`, `StatementScanJob`, `StatementVersion`, `StatementMessage`, and `SplitAgreement` with its signers (snapshot, hash, tokens).
- **On the benefits side:**
  - `BenefitsCase.commission_rates`: a bare % string or a Comp.
  - `AgencyProfile.default_commission`.
  - `CoverageLine.commission` and its source.
  - `Client.owner` and `service_owner`.
  - `UserProfile.commissions_access`.
- **Derived on read:** expected revenue, house share, split dollars, holes, the month grid, gaps, rollups, statement totals, agreement drift and payee readiness.

## H.3 Functionality inventory and verdicts

**Slices:**
- **C1:** the deal tab, booking, the Book, By person, Producers & partners, Settings, the exports and the CAA disclosure.
- **C2 (the ledger):** statements typed by hand or imported from a spreadsheet, aliases, reconciliation, Gaps, the dispute packet and the client statement.
- **C3:** the Claude statement read.

plan.md rules ledgers and statements out of version 1. D-012 and the owner's module list put them in. So the C2 and C3 verdicts below hold only if Daniel answers Q1 yes; if he says no, each of them becomes Defer (outside version 1).

New items are numbered from H120, so the draft's numbers stay the same.

**Review outcome.**
- **Accepted:** challenges 3, 4, 5, 7, 9, 10, 12, 16, 19, 21, 22, 23, 25, 26, 27, 29, 30, 32 and 33.
- **Accepted with changes:**
  - 1: the verdicts stay; C2 and C3 wait for Q1.
  - 2: every producer sees every split row; saving stays with the all tier or the deal's owner, as permissions.py:3–5 intended.
  - 6: the chip shows on the tab and in the drawer, not on Book rows.
  - 8: such deals book at the renewal % with a "year unknown" hole.
  - 11: the primary stays on the split and sets `Deal.owner`.
  - 13: one starred plan, never a sum of options.
  - 14: the year ladder stays deferred.
  - 15: as proposed, with the largest line as the PEPM fallback.
  - 17: the download is kept; the close-out card stays deferred.
  - 18: the import goes into draft lines after a mapping step.
  - 20: a Document with no deal was chosen.
  - 24: the Agenda plan places the app.
  - 28: no paging (see 32).
  - 31: moving carrier names to `deals` is a request to the RFP plan.
- **Rejected:** none.

### Rates and expected revenue (deal Commission tab, C1)

| # | Functionality (what the user sees -> how it worked) | Verdict | New implementation |
|---|---|---|---|
| H1 | Comp value: %, flat $ a year or PEPM; a bare number means %. → `parse_comp` stored `%g` | Simplify | `deals/comp.py` (`parse_comp`, `comp_label`), because intake and AgencySettings also take Comps. Exact decimal strings; the errors from plan §5.6 |
| H2 | CompInput: a type toggle with a unit suffix (/yr, /EE/mo). Blur or Enter commits; a blank clears; switching type commits; Escape was meant to revert | Keep | `src/ui/CompInput.jsx`. Escape reverts without committing (fix, bug 23) |
| H3 | Grid rows: the requested lines (else lines with plans, else medical), plus lines with a rate, plus in-force lines not being quoted (muted) | Keep | `selectors.line_rows(deal)`, which also adds lines with sold plans |
| H4 | In-force column: Comp label and carrier, with the source in a tooltip; "set on Intake" or "no incumbent"; "Edit in-force on Intake ↗" | Keep | The carrier comes from the shared incumbent read: current plans, else the intake coverage row (plan §6.4). The Comp comes from intake `CurrentCoverage`. Review 25: on quote-first deals the old column said "no incumbent" |
| H5 | Agreed-rate column: one CompInput per line, with an "agency default" or "not set" note. → the PATCH replaced the whole map | Keep | Any deal user may edit (D-011: producers set it at RFP time; CaseWorkspace.jsx:694 showed the tab to everyone). `PATCH deals/{id}/commission/` merges one line under a row lock; one `sources` entry per line |
| H6 | Expected/yr, with its basis on a line under the amount ("$X/yr premium · carrier — plan" or "premium not known yet"). → basis = sold, then starred, then current, then the first plan; float `round()` | Simplify | Before the sale: Renewal, then Current (plan §5.6), then the first starred plan as a one-plan package labelled "estimate". Once a line has a sold plan, only Sold counts, or its reason shows. Summed per carrier; rounded with `round_money`. The basis line stays inline (old look); the plans show on hover |
| H7 | Deal total and the note "Based on N enrolled (entered on the proposal / counted from the census)". → the medical headcount was used for every line | Simplify | Each line uses its basis package's enrollment: typed Advisor counts, then the linked current plan, then the census by plan name, then the census by line. The note names the source |
| H8 | Agency default rate as the fallback | Keep | `AgencySettings.default_commission`, also edited on the Settings tab (H100); a "confirm rate" hole once booked |
| H9 | A "No primary producer" nudge and a "1" badge on the sidebar item | Keep | One computed `needs_primary`. After the sale it stays, as "Booked with the house at 100% — set the primary and Rebook". Review 10 reversed the draft, which cleared it at the sale |

### Who gets what (splits editor, C1)

| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| H10 | Which split applies, with a source badge: deal or client (per line), carried forward, referral, firm default, client owner 100%, house 100% | Simplify | Deal split, then client split, then `Deal.owner`'s producer party, then `Client.owner`'s producer party, then the house at 100%. The line-scoped, firm-default and referral tiers had no screen |
| H11 | Primary picker: producers only; "(not appointed)" disabled; live % and $ | Keep | Also lists producer users who have no Party yet; saving creates the Party (review 23) |
| H12 | Other rows: ＋Secondary, ＋Split, ＋Referral agent. Each role limits the party kinds; PartySelect is grouped and hides parties already used; a pick fills in the party's default split; CompInput; live share; × remove | Keep | The roles are labels only; one share math serves them all |
| H13 | "works it" checkbox → created a partner-agent contact | Simplify | Stored on the row; the Overview contacts card lists these partners (computed) |
| H14 | "⚠ no W9" payee flag | Defer | Comes back with payee profiles (H99) |
| H15 | Terms on renewal: the same, or a different amount | Simplify | One optional `renewal_amount` per row, from year 2; 0 is allowed ("first year only") |
| H16 | Terms: "changes by year…" ladder | Defer | It differs from `renewal_amount` only from year 3, and renewals are open (Q3). Its CSS (`.bnf-com-ladder*`) comes back with it |
| H17 | Terms (advanced): basis pool or gross (taken off the top) | Keep | `basis` on each row; a short branch in `compute_shares`. Changed after review 14: build-spec §3.2 and §9.1 say some referral deals are quoted gross, and terms are captured at the sale |
| H121 | Terms: expires after N years | Keep | `expires_after_years` on each row; one comparison in `year_terms`. Changed after review 14: it is captured at the sale and costs one integer |
| H18 | Live preview, debounced 350 ms: "House X% · pool Y% (first year/renewal, firm default) · on $R"; errors keyed `lines.<i>.<field>` | Keep | `POST …/split/preview/` runs the same validation and math as save (fixes bug 7). The body carries the revenue and headcount the GET returned, so `line_state` is not rebuilt on each keystroke (review 28a) |
| H19 | Validation: exactly one appointed primary; role and kind rules; % ≤ 100 | Keep | Pure `rules.validate_rows` |
| H20 | Scope "this client (all deals) / this deal only", Save, Discard. → a client save took two calls | Simplify | One `PUT …/split/ {scope, rows}` in one transaction; one client split per client. All-tier users or the deal's owner may save (Q6); every producer sees every row (D-019, D-066 item 6) |
| H21 | "Carried forward from <year>" banner; "Confirm for this client" | Defer | Renewals only (Q3) |
| H22 | The primary's login was synced one way into `Client.owner`; the Work Queue owner came from a batched resolver | Simplify | When the deal split's primary has a login, it sets `Deal.owner` (the agent the RFP prints). A client split sets `Client.owner`. Both go through `deals.services.set_owner` with one Activity row (review 11, Q8). The batched resolver goes |
| H23 | After the sale, the booked split shown frozen (per line when lines differ), with "edit in Commissions" | Keep | Read from each record's terms |
| H24 | "How this books" explainer | Keep | Static text |

### Sale and booking (C1)

| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| H25 | Mark as sold → `book_case` inside a try that swallowed every error | Simplify | `quotes` sends `sold_changed` through `transaction.on_commit(…, robust=True)` and `send_robust`, so a booking error is logged and never turns the saved sale into a 500 (review 7). Commission books in its own transaction. The tab works out "Sold — not booked · Book now" on read |
| H26 | Which lines booked: every requested line (unsold lines priced from the starred, current or first quote) plus unrequested in-force lines as rate holes | Simplify | Lines with sold plans (one record per line and carrier), plus Intake "Keep" lines with an in-force Comp (rate source `in_force`). A lost deal books nothing (H124) |
| H27 | Frozen facts: client, plan year, carrier (cut from the label, then registry containment), plan label, rate and its source, premium (null = hole), enrolled, effective date, first-year flag, year number | Simplify | `values` and `sources` (origin `sale`). Carrier copied from `Plan.carrier`; premium = the Sold package's annual; employees per line; the deal's effective date |
| H28 | A later booking only filled nulls; premium and rate never refilled once edited | Simplify | A change to the sold set, or Rebook, refreshes every `sale` key; `typed` keys never change. Records are found by `plan_ids` first, then by (deal, line, carrier), so a carrier rename updates the record instead of orphaning it (review 5) |
| H29 | Shares frozen once as %; flat and PEPM shares froze at 0% when revenue was unknown | Simplify | Only the terms are frozen (rows and house %). Shares and dollars are computed on read, once per deal, and applied to each record |
| H30 | First-year flag and year number, worked out from deal lineage | Simplify | Use the typed "year with us". Otherwise, 1 + the number of distinct earlier effective years among the client's non-void records, hand-added ones included. A deal opened for an existing client with no earlier record books at the renewal % with a "year unknown" hole. No effective date gives a hole. `Deal.opened_as` snapshots the relationship when the deal is created, because `set_sold` flips it (review 8) |
| H31 | Earlier records flip to `renewed`; a year that sells late flips itself | Simplify | Booking year N flips the client's earlier booked or active records on that line to renewed and sets their term end |
| H32 | Un-selling a plan (2V allows it) | New | A line left with no sold plan turns its record `void`: never deleted, hidden from the Book by default, brought back if the plan is sold again. Un-selling the deal's last sold plan voids its Keep-line records too. Changed after review 9: deleting broke archive-never-delete |
| H120 | Census or Advisor counts arriving after the booking | New | On the deal tab and in the record drawer, `rules.stale_keys` compares the `sale` keys with today's Sold package and shows "Out of date: $X → $Y · Update" (a one-click rebook). Typed keys are untouched. Not shown on Book rows, because of the cost |
| H124 | A lost deal never books (D-037) | Keep | `set_sold` refuses on a lost deal (2V lacks this check, marks.py:41–60); `lines_to_book` returns nothing for a lost deal (review 4) |
| H33 | Late-year re-derivation (D-102/D-107); the lineage audit command | Drop | Machinery for a year rule that H30 replaces |
| H34 | Floating referral record, COI lines, fold gates, `rebook_after_link`, service-owner fill | Drop | P&C referrals, folds and the service owner are not in 2V |
| H35 | BookingSummaryModal: tiles; a table with hole badges; inline fixes (rate, premium as billed, enrolled); who gets what by role; Open in Commissions; Fix later / Done; text for a 403 or an empty result | Keep | It opens when the deal first becomes sold (2V has a Sold checkbox per plan), then from a "Booked · view" link on the Advisor, the Proposal and the tab. The all tier edits; the own tier sees it read-only through `visible_shares`; the none tier never sees it, as before (ComparisonGrid.jsx:558; BookingSummaryModal.jsx:20–21). The fold banner goes |
| H36 | Rebook a deal (from the Book) or one record (409 once edited; deleted the splits first) | Simplify | One atomic `rebook(records)` that never answers 409. It refreshes the `sale` keys and works out the terms again, unless someone typed the shares |
| H37 | Holes: premium, rate (none or agency), enrolled (PEPM), year, client link | Simplify | Pure `holes(record)`: premium, rate (none or agency), employees (PEPM), year unknown, effective date, and no sold plan (skipped when the rate came from in-force) |

### Other deal and client surfaces (C1)

| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| H38 | Overview CommissionSummaryCard: expected, received this year and months short, booked block, chips, link | Keep | `commission/summary.py` (plan §5.10). Every deal user sees the expected figure and the split chips; received, months short and holes follow the tier |
| H39 | Overview "Expected revenue" tile | Keep | The same summary, fed by line states computed once per request (review 28b) |
| H40 | Status report "Expected revenue" section (copy text, phone and letter PDF) | Simplify | The same summary, called with the viewer (fixes bug 4). Whether the report stays is the Overview plan's call |
| H41 | Client header "In-force commission" chips; a read-only "Primary producer" with "set ▸" | Keep | Intake data; `Client.owner`, linking to the client split |

### /commissions dashboard

| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| H42 | Route and tier gate; the title "Commissions" or "My commissions" | Keep | `pages/CommissionsPage` |
| H43 | "Show me how ▸"; the home page lands on Commissions for users who have only that module | Drop | Walkthroughs and the roles matrix |
| H44 | Top-nav "Commissions" link | Keep | Shown when the tier is not none |
| H45 | Tiles: Expected (annual), House*, Pool*, Next 12 months, Booked records, Received YTD, Open gaps ($, months in a tooltip) | Keep | Expected counts booked and active records only (bug 5). Received YTD goes by arrival date (Q12). The received and gap tiles come in C2 |
| H46 | "Owed to producers" placeholder tile | Drop | Always empty; payouts were never built. H123 meets the need |
| H47 | Unconfirmed-defaults banner | Keep | Same |
| H48 | Tabs through `?tab=`; an own-tier user who asks for an all-tier tab gets the Book | Keep | The Book split tab stays hidden until it is built |

### Book and record drawer (C1)

| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| H49 | Filters: search, person*, LOB, status, year, clear; deep links for client, deal, party, record and group | Keep | LOB goes; search waits 300 ms; void records show only when the status filter asks for them |
| H50 | A flat list with a "Group by client" toggle and group sums; no paging | Keep | The same toggle and look. One response per filter change carries the rows and totals; a server cap shows "narrow the filter" (reviews 28c and 32) |
| H51 | Columns: client (yr N), line, carrier, effective, premium, rate, expected, received, gap, house*, chips, status; a row click toggles the drawer | Keep | Same |
| H52 | Export: a Book sheet (16 columns) and a Totals sheet | Keep | XlsxWriter; injection guard; the same filters and visibility |
| H53 | Drawer header: year chip, booked by, edited by, "comp agreement vN", open deal, holes explained | Keep | The agreement chip returns with H107 |
| H54 | Facts edit: premium as billed, rate, carrier, policy #, effective date, enrolled, status | Keep | Edited keys get `typed` sources; a term end is added; statuses include `void` |
| H55 | Splits list; Edit splits (%, add, remove, must total 100, a reason) | Keep | Stored as typed shares with the reason; `party_ids` is updated with them (review 16) |
| H56 | Notes | Keep | `Record.notes` |
| H57 | History from ChangeLog | Simplify | Activity rows with before and after values; all tier only |
| H58 | Manual booking: an API with no screen, although the empty Book promised it | New | An "Add to book" dialog. It searches existing clients first; a new outside client is created without a deal (`create_client(first_deal=False)`, review 22). It uses the same booking service |

### Reconciliation and gaps (C2)

| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| H59 | Month strip: one cell per term month, "received of expected", 7 colours, tooltips | Keep | `reconcile.py` |
| H60 | Totals: received (and this year), expected to date, open $ and months, paid through | Keep | Same |
| H61 | Month detail: Explain…/Change (reason and note), Reopen | Keep | Only on short months inside the term (fix) |
| H62 | List of the receipt lines applied | Keep | Posted lines only (fix) |
| H63 | Dispute packet PDF | Keep | `packet.py` |
| H64 | Month rules: term months (up to 36, else 12); expected ÷ n with the residual on the last month; statuses paid (within $1), not due (inside grace), open, explained, disputed, future, unknown | Keep | Pure functions; a renewal, a termination or a void sets the term end |
| H65 | Batched received and gap rollups | Keep | One selector, two queries |
| H66 | Gaps tab: filters; "N open months · $X short · grace"; export; a table with Explain, Reopen, Packet and a record link | Keep | The tab badge and the list use one filter (fix) |
| H67 | `commission_gap` reminder (off by default; its own grace setting; a $25 floor) | Simplify | An Agenda rule over `open_gaps(viewer)`, using the one grace setting and the floor as a constant. Agenda sits to the right of commission; amounts follow the tier; gaps on manual records show on the Gaps tab only (review 24) |

### By person and Book split

| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| H68 | By person: year filter; person, kind, records, expected, share of book; drill-down; book ↗; export (a pivot plus a sheet per person) | Keep | C1. The own tier sees only its own row |
| H123 | Received share per person | New | C2. A column of received money × each person's share, per person. Review 33: D-012 says the module exists to pay producers; payouts themselves stay deferred |
| H69 | Book split worksheet and export | Defer | It groups the book by account manager (`service_owner`), which 2V does not have (book_split.py docstring), and it sits outside the deal workflow. Reason corrected after review 33 |

### Statements by hand (C2)

| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| H70 | Filters (search, carrier, status); "＋ New statement" form | Keep | The carrier comes from a pick list: the shared carrier names (moved to `deals`, review 31) plus the carriers on booked records |
| H71 | List columns: carrier, period, received, method·ref, lines, entered, declared (+Δ), unmatched, status | Keep | 25 per page; the list never includes the read job's result (review 28d) |
| H72 | Drawer: file ⬇, posted by, Delete draft, Post, tiles, a declared total editable while draft | Keep | The file is a firm-level Document |
| H73 | Each line shows what it is applied to (auto or manual), or "Unmatched — pick…" with up to 8 scored candidates | Keep | `matching.py` |
| H74 | ⟲ unmatch, × remove, Reverse (reason through `window.prompt`) | Keep | A ConfirmDialog with a reason; guarded (bug 19) |
| H75 | Re-pointing a posted line moved money silently | Simplify | It writes a reversal and a new line in one transaction |
| H76 | Add-lines editor: the client list includes archived clients; ＋Row copies the month; all or nothing; auto-match | Keep | Same |
| H77 | Post: auto-match the remaining lines, lock, toast "N still unmatched" | Keep | Same |
| H78 | Matcher: name 0–3, policy +2, carrier +1, line +1, period +1. Auto-match needs a client or policy anchor, a score of 3 or more, and no tie | Keep | Pure functions; the book is loaded once per statement; an alias counts as an exact name |
| H79 | Standalone receipts route; carriers API | Drop | Duplicate paths. The statement payload carries its lines, which replaces `getReceipts({statement})` (StatementDocumentsTab.jsx:184). The H70 pick list replaces `getCarriers` (StatementsTab.jsx:55; StatementDocumentsTab.jsx:356). Creating carriers goes with H99. Reason corrected after review 31: the draft said nothing called them |
| H80 | Lock rules; a reversal cannot be reversed; a posted statement cannot be deleted | Keep | Plus a unique `reverses` |
| H81 | ⟲ History on statements: versions rail and "What we corrected" | Simplify | An Activity list inside `.bnf-com-histpane`; confirm records "N lines, K corrected" |

### Statement documents and the Claude read (C3 unless marked)

| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| H82 | Upload: drop zone, several files, pdf/xlsx/csv/png/jpg, a note; the read starts; status polled every 900 ms | Simplify | The shared upload validator stores a firm Document (kind `commission_statement`, no deal), then an `ai.Job` of the same kind runs; the shared polling |
| H83 | Toolbar: show confirmed, history, hide document, chat; document tabs with state badges; `?statement=` link | Simplify | The chat toggle goes; `.bnf-com-docactions` stays |
| H84 | Document pane: PDF with page, highlight, OCR fallback and neighbour-page sweep; spreadsheet grid preview; remove an upload | Keep | The shared Documents viewer. Remove = `DELETE statements/{id}/` on a draft |
| H85 | Read states: running, failed with retry, not read, read again, reviewed with ⌖ | Keep | Computed from the Job; `POST statements/{id}/read/` starts a read or repeats it |
| H86 | Review table: header fields; totals check ("Off by $X" / "Matches ✓"); rows with ⌖; a match chip equal to what confirm will do; low-confidence shading; × drop; Discard; "Confirm N lines" | Keep | Same, in `.bnf-com-workcols` and `.bnf-com-workstack` |
| H87 | Confirm: all or nothing; header and carrier; receipts with provenance; auto and manual matches | Keep | Through ai's `apply`, which calls commission's registered handler. It locks the statement and the job; a second confirm answers 409 (bug 18) |
| H88 | Discard keeps the file | Keep | ai's `discard` |
| H89 | Reader: 28-page chunks with 2 pages of overlap; images up to 5 MB; row windows halved on truncation; forced tool; normalising; at most 2,000 rows | Simplify | Registered on the shared `ai` chunking, client and worker; the prompt is a data module; dedupe only across overlap pages (bug 20) |
| H90 | One gate for starting a read: file present, not posted, nothing running, no lines yet | Keep | `reader.can_read`; one running read per statement |
| H92 | Keyless spreadsheet reader (finds the header row, maps columns by synonyms) | Simplify | C2 "Import spreadsheet": the census importer's generic parser, moved to `documents/tables.py`, maps the columns. A mapping step shows them, then "Add N lines" writes draft lines, all or nothing. Changed after review 18: under Q13's default it is the only way to import a statement |
| H93 | Client aliases: learn, retire, the contested rule, teaching on a match | Simplify | C2. A manual match stores the normalised printed name against the client. A name claimed by two clients is ignored (the contested rule). No retire screen (Django admin) and no lessons. Changed after review 19: without it every odd spelling is picked by hand every month |
| H91 | Statement chat rail: Read button, attach, transcript, teach-lesson flags, saved-reader picker | Drop | A second chat whose only actions were "read" (kept as the Read button) and alias proposals (H93) |
| H94 | Statement version engine, saved readers, lessons, `AGENTS_ENABLED` | Drop | Snapshots and agents (plan §15) |

### Producers & partners, Settings, access (C1)

| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| H95 | Roster (the GET created rows); the own tier sees the roster only; show inactive | Keep | Nothing is written on a GET. Producer users with no Party are listed (computed); their Party is created on the first split save or booking (review 23) |
| H96 | ＋ Add a partner, or a producer without a login | Keep | Same |
| H97 | Producers table: appointed, NPN, year-1 and renewal producer/house % inline, book ↗, deactivate | Keep | The %s live on `Party`; Activity keeps the history |
| H98 | Partners table: kind, default split, contact, deactivate | Keep | Same |
| H99 | Profile drawer (licenses, carrier codes, payment and W9, history); payee readiness | Defer | Payouts were never built; W9 files need their own storage rules. `.bnf-com-profile-*` comes back with it |
| H100 | Settings: producer %s, gap grace, confirm; external-split default (dead), P&C rate, visibility default | Simplify | Keeps the %s, grace and confirm, and adds the agency default rate (stored on AgencySettings, written by a deals service). All commission defaults sit on one screen (review 33). The dead fields go |
| H101 | Per-person access: Follow role / None / Own / All, with a badge | Simplify | `commissions_access` on the accounts user-flags row (Django admin); the badge shows in the roster |
| H102 | Access tiers and own-tier scoping | Simplify | `accounts.commission_tier(user)`: admin is all; a producer defaults to own. The deal tab (rates, expected revenue, split terms, preview) is open to every deal user (D-011, D-066 item 6). Ledger figures and ledger writes need a tier. The own tier sees the records it is a party to (`party_ids`), with the other shares collapsed by `visible_shares` |

### Client statement (C2 unless marked)

| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| H103 | Client commissions section: export, Open in Commissions, "Your share" banner, tiles | Keep | `ClientStatement` (Q10) |
| H104 | Start renewal | Defer | Renewals (Q3) |
| H105 | Statement table: person chips; plan-year groups (▲▼ vs the prior year, holes, received and short); line rows with a ▸ month strip; print stylesheet; "Comp disclosure ⤓" per plan year | Keep | Same; the disclosure is H108 |
| H106 | Client-scoped splits editor; the client overview snapshot, tiles and in-force column | Keep | C1. The same editor with client scope |

### Agreements, disclosure, seams, machinery

| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| H107 | Comp agreements: card, versions, signers, resend, countersign, PDFs, public `/s/:token` page | Defer | Pay paperwork outside the deal workflow, and the riskiest public surface (bug 1). When it returns: all tier only, and tokens are never listed |
| H108 | CAA comp disclosure PDF (medical, dental and vision; per plan year) | Keep | C1. `disclosure.py` and `disclosure_pdf.py`, all tier. "Comp disclosure ⤓" sits on the tab's booked block, and in C2 on each plan year of the client statement, with the old tooltip "send it only inside the close-out packet". Changed after review 17: D-020 says the law requires it at every close |
| H122 | The close-out card that bundled the disclosure | Defer | Close-out is not in scope; the back office downloads H108 and sends it inside its own close-out email (Q14) |
| H109 | Commission request sent to carriers (form cell, cover, packet, email) | Keep | `rfp` reads `selectors.requested_rates(deal)` |
| H110 | The portal never shows or writes commission | Keep | Allowlist, plus a test |
| H125 | Client-facing proposal files never carry commission | Keep | A proposals test pins it for the workbook, the deck and the PDF |
| H111 | Renewal carry of rates and of a switched line's in-force commission | Defer | Renewals (Q3) |
| H112 | Archiving never touches the ledger; archived clients appear in pickers | Keep | `Record.client` and `Record.deal` use PROTECT. Deleting a client that has ledger rows answers 409 "archive instead". Needs Wave 1's `Client.archived_at` (review 21) |
| H113 | ChangeLog on every write; GET `changes/` | Simplify | Activity rows with before and after values; firm rows have `deal` null and a `subject`. Rates, splits and record facts register a revert handler; posted money never reverts, it only moves by reversal (review 26) |
| H114 | Vocabularies shipped inside the settings and summary payloads | Simplify | `/api/meta/` |
| H115 | File unlink on delete | Keep | Statement files are Documents; the documents app deletes the file in `on_commit` (review 33) |
| H116 | Shared UI: Tile, ExportButton, SplitChips, PartySelect, CompInput | Keep | `src/ui/` |
| H117 | Seeds, guides, `data-guide` anchors, practice and story resets, `demo-` fixtures | Drop | Demo and walkthrough code |
| H118 | Daemon-thread job runner; `scan_state` reaper | Drop | The shared `ai` worker |
| H119 | P&C lines, COI kinds, the JV and referral readers | Drop | Not in 2V |

## H.4 Data flow (in and out, by model, field or function)

**In:**
- `deals`:
  - `Deal.client`, `owner`, `effective_date`, `stage` (including lost), `requested_lines`, `opened_as`
  - `Client.name`, `owner`, `archived_at`
  - `AgencySettings.default_commission`
  - `comp.py`, `carriers.py`
- `intake`: `CurrentCoverage` per line (the in-force Comp and its source; the carrier until current plans exist) and the coverage intent ("Keep" lines book).
- `quotes`:
  - the sold set per line (`Plan.sold`, `carrier`, `name`, `plan_number`)
  - `selectors.line_state` → `package()` for Sold, Renewal, Current and the first starred plan (annual, enrollment, reason, enrollment source)
  - the incumbent read
  - `math.round_money` and `round_decimal`
  - `sold_changed`
- `census`: only through the package's enrollment order, and as employees per line where a basis has no tier counts (Wave 1's fixed rollup: waivers skipped, client answers counted).
- `documents`: firm Documents; `tables.py`.
- `ai` (C3): Job, registry, chunking, client.
- `accounts`: `commission_tier(user)`.

**Out:**
- `Deal.owner` and `Client.owner`, through `deals.services.set_owner`.
- `Activity` rows in area `commission`, with before and after values and revert handlers.
- `Party` rows, created on first use.
- Firm Documents, and `ai.Job` rows resolved through the registered handlers.
- Not ported: partner-agent contacts (now computed), `service_owner`, lesson signals.

**Read by others:**
- `rfp` → `requested_rates(deal)`: one label, or a grouped one.
- `overview` → `summary(deal, viewer, states)`.
- `agenda` → `open_gaps(viewer)` (C2).
- Advisor and Proposal → BookingSummaryModal and "Booked · view".
- `review` and `proposals` → nothing.

**Client- and carrier-facing files:**
- No split, house-share or ledger figure ever appears on one.
- The RFP carries the requested rate on purpose.
- The CAA disclosure carries the commission on medical, dental and vision to the client, because the law requires it.
- Proposal files carry none (H125).

## H.5 Bugs and pain points found (with file evidence)

1. **P0 privacy (agreements).** The agreement list, detail, resend, create and PDF views check only `IsProducer`. The list returns every signer's live `/s/` token, and the PDF is unredacted (views_agreements.py:38–141; only countersign checks the tier). Fixed by deferring H107; when it returns it is all-tier only and never lists tokens.
2. **Split saves are unscoped.** Any producer can rewrite any client's split (views.py:682–836; only firm-default writes check the tier, :775). permissions.py:3–5 says capture is meant for a producer's own case. Reading every split is a decision (D-066 item 6), not a bug. Fix: the all tier or the deal's owner saves.
3. **Own-tier redaction is uneven.** Several payloads return every party's share (serializers.py:294–295; services.py:1449–1457; views.py:470–478). D-066 item 6 makes the redaction presentation only, so this is not a leak. Fix: one `visible_shares` for ledger payloads and exports.
4. **Ledger figures reach every user.** Received, gaps and holes go out through the case GET and the status report (serializers/case.py:251; overview.py:1626–1637), and `summary/` embeds the firm settings (views.py:1139). Fix: one summary that takes the viewer; the pre-sale expected figure and split terms stay open to all.
5. **"Expected (annual)" counts every status** (services.py:1433–1438), against its tooltip (ClientCommissionsTab.jsx:136). Fix: booked and active only.
6. **The gap tile and badge disagree with the Gaps list.** The tile counts terminated and lost-BOR records (reconcile.py:205–237); the list does not (views_reconcile.py:690). `term_end` is written only through the API. Fix: one selector, and a term end on renewal, termination or void.
7. **The draft preview drops ladders** (views.py:745–752 vs services.py:254). Fix: preview and save share one function.
8. **`%g` loses money.** $1,000,000 is stored as `1e+06`, and 12,345.67 becomes 12345.7 (validation.py:156; services.py:865). Fix: exact decimal strings.
9. **Two rounding rules.** The preview uses float `round()`; booking rounds half-even (overview.py:1547–1561; services.py:63, 67, 896). Fix: `quotes.math` everywhere.
10. **PEPM uses the medical headcount for every line, frozen** (overview.py:1538–1545; services.py:826, 898). It ignores the Advisor's typed counts, so quote-first deals show "unknown" (CommissionPanel.jsx:119–122). Fix: employees per line from the basis package.
11. **One premium plan per line** (overview.py:1484–1498). Fix: sum the sold set.
12. **The first sale books every requested line with guessed premiums, and later sales only fill nulls** (services.py:905–931). A plan sold on an unrequested line never books (:835). Fix: H26–H28.
13. **Flat and PEPM shares freeze at 0% without revenue.** Filling the premium in later sets `edited_by`, and then rebook answers 409 (views.py:1023, :1109). Fix: shares computed on read.
14. **A flat split is paid once per line.** `compute_shares` runs per record (services.py:605–609, 1134–1139), but the preview computes it once per deal (overview.py:1633–1635). Fix: per-deal shares (Q7).
15. **Writes that are not atomic.** Rebook deletes the splits, then calls a booking that swallows errors (services.py:1225–1241; views.py:1110–1118). The schedule, profile and statement-line loops have no transactions. The client save is two calls (SplitsPanel.jsx:194–204). Fix: atomic services and one PUT.
16. **Duplicate client schedules.** No scope is unique (models.py:308–313), and the newest silently wins. Fix: one row per client.
17. **Rate edits overwrite each other**, because the PATCH sends the whole map (CommissionPanel.jsx:37–49). Fix: a one-line merge under a lock.
18. **apply-scan can run twice.** The job is checked outside the atomic block (views_statements_scan.py:397 vs :459). Fix: lock the statement and the job.
19. **Posted money can move.** `record_id`, client and line pass the lock (views_reconcile.py:227–230, 532–558); reversals check neither posting nor the lock (:588–599). Fix: H74, H75, H80.
20. **Reader dedupe drops real rows.** Identical lines anywhere in a statement collapse (statement_reader.py:453–465; statement_offline.py:333–339). Fix: dedupe only across overlap pages.
21. **Small but wrong.**
    - Received YTD goes by the month paid for (reconcile.py:154–157).
    - Draft lines show as "applied" (views_reconcile.py:635).
    - The typed statement accepts any file (:332–336).
    - Junk ids give a 500.
    - Any month can be "explained" (:651–668).
    - There are two grace settings (reminders.py:308–311).
    - GET requests write: the parties list creates rows (views.py:338–344), and scan-status reaps jobs.
22. **Carrier linking by containment** matches 1–2 typed characters (models.py:722–728; services.py:785–795). Fix: copy the carrier from the plan; match statements on equal normalised names.
23. **Escape in CompInput commits** instead of reverting. It sets the text, then blurs, and the blur handler commits the stale text (CompInput.jsx:62–68). Found by reading the code; not tried in a browser.
24. **Dead or unwired code.**
    - `default_external_split` and `default_pnc_rate`.
    - The empty Book promises manual booking (BookTab.jsx:174–175).
    - `ProducerAgreement` dating is unused.
    - Carrier aliases and kind, and `owed`/`paid`, are never used.
25. **Performance.** `suggest_matches` loads the whole book per line, twice (views_reconcile.py:610–612); `record_payload` runs extra queries per row; the Book search refetches on every keystroke.
26. **Fragile lineage**: `_case_type`, D-036, D-102, D-107 and an audit command for misbooked years. Fix: H30.
27. **Frontend.** Hand-rolled fetch state; `window.prompt` and `window.confirm`; MonthStrip imports its controls from GapsTab; files of 803, 552 and 516 lines; inline styles; the booking modal reopens on every Sold toggle (ComparisonGrid.jsx:558).
28. **CSS.** `--accent` and `--accent-bg` are undefined (commissions.css:957–961); a local `.btn` patch (:117–119); the Manage Users badges live in this file (:10–13).
29. **Docs drift and copies.** The "two seams" docstrings; the README is wrong about Settings; the version engine, chat and job runner are copied across apps.

**In 2V today (found while porting):**

30. `set_sold` has no lost-deal check: the plan turns sold and the client turns existing while the stage stays lost (2V/quotes/marks.py:41–60; deals/stages.py:15–19). D-037 forbids booking on a lost deal.
31. `delete_plan` deletes a sold plan and leaves the stage at sold (2V/quotes/services.py:158–165). `update_plan` changes a sold plan's carrier, role and values with no refresh (:116–155).
32. `round_money` returns an int or a float, never a Decimal (2V/quotes/math.py:22–27).
33. Clients and deals:
    - `delete_client` cascades the client's deals (2V/deals/services.py:62–69).
    - `create_client` always creates a deal (:21–38).
    - `update_client` writes an Activity row on every deal (:57–58).
    - `create_client` makes the creator the owner, who may not be a producer.
34. A Document needs a deal and is stored per deal (2V/documents/models.py:12–17), and the ai Job is per deal (plan §10.2). Neither fits a firm-level statement.
35. 2V has no `ATOMIC_REQUESTS` and no signals yet, so `sold_changed` would be the first.

## H.6 New design

**App.** `commission` stays where the chain puts it (quotes → commission → proposals). Changes in other apps, each with its reason:

1. **`quotes`:**
   - Add `signals.sold_changed(deal, lines, user)`, sent with `on_commit(robust=True)` and `send_robust`. Quotes cannot call commission.
   - `set_sold` refuses a lost deal.
   - `delete_plan` refuses a sold plan ("unmark sold first").
   - Add `round_decimal` (Decimal, half up); `round_money` wraps it.
   - Add an `incumbent(deal, line)` read, unless the Advisor plan already has one.
2. **`deals`:**
   - `comp.py`.
   - `carriers.py`: carrier names and spellings, moved from `rfp/carriers.py`. rfp keeps its per-carrier data under the same keys.
   - Activity firm rows (`deal` null, with a `subject`) and a registry of revert handlers.
   - Commission before/after values hidden below the all tier.
   - `Deal.opened_as`: a snapshot of the client's relationship when the deal is created.
   - `set_owner(deal or client)`, writing one Activity row.
   - `create_client(first_deal=False)`.
   - Wave 1's `Client.archived_at`.
   - `delete_client` answers 409 when protected rows exist.
   - `set_default_commission`.
3. **`documents`:**
   - `Document.deal` becomes nullable for firm documents (kind `commission_statement`). They are stored under `firm/`, never appear in a deal's list, and are served only after the kind's registered access check.
   - `tables.py`: the generic part of the census importer (rows, header row, synonym mapping).
4. **`ai`:**
   - `Job.deal` becomes nullable.
   - A per-kind access check on `GET ai/jobs/{id}/`, apply and discard.
   - One running job per deal, or per document when there is no deal.
5. **`accounts`:** `commissions_access` ('' / none / own / all) on Wave 1's user-flags row, and `commission_tier(user)`.
6. **`backend/meta.py`:** serves `commission/vocab.py`.
7. **plan.md, in the same change:**
   - §1.4, §6.7, §7.8, §8.10 and §15.
   - §5.6: exact decimals instead of `%g`, and the Row shape.
   - CLAUDE.md rule 4 becomes "rounding lives only in quotes/math.py".

**Models.**

Dropped: ProducerAgreement, SplitSchedule/SplitLine, CommissionRecordSplit, ChangeLog, Carrier, StatementScanJob, StatementVersion, StatementMessage, SplitAgreement and its signers, PartyLicense, PartyAppointment.

- **`Party`:**
  - `kind`: producer or partner. The house is implicit, not a row.
  - `name`, `user` (one-to-one, null), `email`, `phone`, `npn`, `appointed`.
  - `default_split` (Comp).
  - `first_year_pct`, `renewal_pct` (null = the firm default).
  - `active`.
- **`Settings`** (pk 1): `first_year_pct` 40, `renewal_pct` 30, `gap_grace_days` 45, `confirmed_by`, `confirmed_at`.
- **`Commission`** (one per deal; the deal is the primary key):
  - `rates` `{line: Comp}`, `sources` `{line: source}`.
  - `split` `{rows: [Row]}`, or null.
  - `year_number` (typed, null), `updated_by`, `updated_at`.
- **`ClientSplit`** (the client is the primary key): `rows`, `updated_by`, `updated_at`.
- **Row:** `{party, role (primary, secondary, split or referral), amount: Comp, renewal_amount: Comp or null, basis (pool or gross), expires_after_years: int or null, works_it}`.
- **`Record`:**
  - `client` (PROTECT), `deal` (null, PROTECT), `line`, `carrier`, `effective_date`, `term_end`.
  - `year_number` (null = unknown), `is_renewal`.
  - `status`: booked, active, renewed, terminated, lost_bor or void.
  - `values` `{premium_annual, rate, employees, plan_label, plan_ids, policy_number}`.
  - `sources`: origin `sale`, `typed`, `in_force` or `agency`.
  - `terms` `{house_pct, rows, from, shares: null or [{party, role, pct}], reason}`.
  - `party_ids`: an integer array with a GIN index, written together with the terms and shares.
  - `notes`, `booked_by`, `booked_at`.
  - Unique (deal, line, carrier) when the deal is set.
- **`Statement`:**
  - `carrier`, `period_start`, `period_end`, `received_on`, `method`, `reference`, `declared_total`.
  - `status`: draft or posted; `posted_by`, `posted_at`.
  - `document` (null), `printed` `{agency_name, agency_code}`, `read_job` (null), `notes`.
- **`Receipt`:**
  - `statement`, `record` (null), `client` (null), `line`, `kind`, `period` (the first of the month).
  - `raw` `{client, policy, line, plan}`.
  - `premium_paid`, `lives_paid`, `amount`.
  - `source` `{page, snippet, sheet, low}`.
  - `match`: none, auto or manual; `matched_by`, `matched_at`.
  - `reverses` (a unique one-to-one to itself), `notes`.
- **`GapNote`**: record, period, reason, note, by, at; unique (record, period).
- **`Alias`** (C2): a normalised `name`, `client`, `by`, `at`; unique (name, client).

**Numbers.**
- Money is a Decimal at cents, rounded half up by `quotes.math.round_decimal`.
- Shares are integer millionths (100% = 1,000,000), so they always total exactly 100%. The residual goes to the primary, else the house.

**Pure modules** (plain data in, plain data out):
- `math.py`:
  - `comp_amount`.
  - `year_terms`: the renewal amount from year 2, and the expiry.
  - `compute_shares`, in the old order: gross rows off the top; the house takes its % of the rest; flat and PEPM rows come off the pool; % rows take their share of what is left; the primary keeps the rest; every row is capped.
  - `deal_shares`: computed once on the deal's total revenue. A split PEPM row counts the deal's medical employees, else its largest line's, never a sum. A manual record is its own group. Typed shares override only their own record.
  - `dollars`: sums to the revenue exactly.
- `rules.py`: `validate_rows`, `resolve`, `year_number`, `lines_to_book`, `holes`, `stale_keys`.
- `reconcile.py`, `matching.py`.
- `visibility.py`: `visible_shares(rows, tier, viewer)`, used only by ledger payloads and exports.

**Services.** Each one is atomic, locks its row with `locked()`, writes Activity and returns only what changed.
- `services.py`: `set_rates`, `set_year`, `save_split` (creates a missing Party; sets the owners), `save_party`, `save_settings`.
- `booking.py`: `on_sold_changed`, `book_deal`, `rebook`, `void_lines`, `add_to_book`.
- `records.py`: `edit_record`, `set_shares`, `set_gap_note`.
- `ledger.py`: statement create, edit and delete-draft; `add_lines`; `post`.
- `receipts.py`: `match` (learns the alias), `unmatch`, `move_posted_line`, `reverse`.
- `importer.py` (C2): the spreadsheet import.
- `reader/` (C3): `prompt.py` (a data module), `read.py` (registration, normalising, staging, `can_read`), `apply.py` (the apply and discard handlers).

**Selectors.**
- `selectors.py`: the deal payload, `line_rows`, the preview, `requested_rates`.
- `summary.py`: the Overview summary; it takes precomputed line states.
- `book.py`: rows and totals in one pass, the people rollup with the received share, the client statement, `open_gaps(viewer)`. The statement list never includes a job's result.
- `exports.py`, `packet.py`, `disclosure.py`.
- Each list costs a fixed number of queries, pinned by query-count tests.

**Views.** A `views/` package (deal, clients, records, people, statements, receipts, gaps) and a `payloads/` module per area. Every file stays under 300 lines.

**Endpoints** (under `/api/`):
- **Deal** (any deal user unless noted):
  - `GET` and `PATCH deals/{id}/commission/` (`{rates, year_number}`)
  - `POST …/split/preview/` (the rows plus the basis the GET returned)
  - `PUT …/split/` (all tier or the deal's owner)
  - `POST …/book/` and `GET …/disclosure.pdf` (all tier)
- **Client:**
  - `GET` and `PUT clients/{id}/commission/split/` (PUT: all tier or the client's owner)
  - `GET clients/{id}/commission/statement/`, with `export/` and the disclosure (own or all tier)
- **Records** (own or all tier reads; all tier writes):
  - `GET` and `POST commissions/records/` (POST is Add to book); `GET …/export/`
  - `GET` and `PATCH …/{id}/`; `PUT …/shares/`; `POST …/rebook/`
  - `GET …/months/`; `PUT` and `DELETE …/months/{YYYY-MM}/`
  - `GET …/dispute-packet/`
- **People and settings:**
  - `GET commissions/people/` (with `{id}/` and `export/`)
  - `GET` and `POST commissions/parties/`; `PATCH …/{id}/`
  - `GET` and `PATCH commissions/settings/`
- **Statements** (all tier):
  - `GET` and `POST commissions/statements/`
  - `GET`, `PATCH` and `DELETE …/{id}/`
  - `POST …/lines/`, `…/import/` (a preview, then add), `…/post/`, `…/read/` (C3); `GET …/file/`
  - Confirm and discard go through `ai/jobs/{id}/apply/` and `…/discard/`.
- **Receipts:** `PATCH` and `DELETE commissions/receipts/{id}/`; `POST …/reverse/`; `GET …/matches/`.
- **Gaps:** `GET commissions/gaps/` (with `export/`).
- A bad id answers 400.

**Frontend.**
- `src/deal/commission/`: CommissionTab, RatesGrid, SplitEditor, SplitRow, SplitTerms, SplitPreview, BookedBlock, StaleChip, HowThisBooks, BookingSummaryModal.
- `src/pages/CommissionsPage/`:
  - CommissionsPage, Tiles
  - BookTab, BookTable, AddToBookDialog, RecordDrawer, RecordFacts, RecordShares
  - MonthStrip, GapControls
  - ByPersonTab, GapsTab
  - StatementsTab, StatementDrawer, StatementLines, AddLines, ImportStatement, MatchPicker
  - DocumentsTab, ScanReview, ReviewHeader, ReviewTable
  - PartiesTab, ProducersTable, PartnersTable, SettingsTab
  - ClientStatement, PlanYearGroup, StatementLineRow
- `src/ui/`: CompInput, Tile, ExportButton, SplitChips, PartySelect.
- `src/api/commission/`: deal.js, book.js, statements.js and people.js, as React Query hooks. Keys are `['deal', id, 'commission']` (staleTime 0) and `['commissions', area, filters]`.
- No math in the browser.

**Stylesheets** (the same class names, so the screens look the same):
- Copy from commissions.css now:
  - lines 15–552 (including `.bnf-com-terms*` and `.bnf-com-grid-basis`), 651, 667–798 and 953–970;
  - `.bnf-com-histpane` (:804), `.bnf-com-workcols` and `.bnf-com-workstack` (:907–913), `.bnf-com-docactions` (:946–951).
- Copy `.bnf-com-viaalias` (971–975) with C2.
- Also copy `bnf-ov-comm-*` (benefits-overview.css 437–470, 652) and `bnf-cw-stmt-*` / `bnf-cw-snap-*` (benefits-radar.css 647–733).
- Bring later, with their features: 553–607 (profiles), 608–621 (ladder and agreements), 622–649 (`bnf-sign-*`), 652–661 (`bnf-com-bs-*`), 663–666 (payee).
- Drop: 10–13, the version rail (`.bnf-com-vhist*`, the rest of 799–900) and the chat column (`.bnf-com-chatcol`).
- Fixes: `--accent` becomes `--blue` and `--accent-bg` becomes `--blue-bg`. Remove the patch at :117–119 once Wave 1 fixes `.btn-primary`.

**Slices.**
- **C1:** H1–H58, H68, H95–H102, H106, H108–H125 (except H123).
- **C2:** H59–H67, H69–H81, H92, H93, H103–H105, H123.
- **C3:** H82–H91, after the `ai` app exists and the BAA question is answered.

**Tests** (behavioural, synthetic data):
- **Comp:** `parse_comp` and `comp_label`, with 1000000 and 12345.67 kept exact. `comp_amount` per type, rounding half up.
- **The §5.6 example (3,805) and the old share examples:**
  - house 60 / $1,000 flat → 10% / a 50% split → 15% / primary 15%;
  - a flat amount capped at the pool;
  - no primary → the house keeps the rest.
- **Gross and expiry:** a gross row comes off the top; `renewal_amount` 0 pays nothing from year 2; a row past its expiry pays nothing.
- **Per-deal shares:**
  - a flat split on a three-line deal pays its amount once in total;
  - a split PEPM uses the medical employees;
  - a manual record is its own group;
  - shares settle when the premium arrives later.
- **Basis:**
  - after the sale, Sold only, with its reason;
  - before the sale, Renewal, then Current, then the starred plan as "estimate";
  - PEPM uses the line's own employees;
  - typed Advisor counts beat the census.
- **Booking:**
  - idempotent;
  - "Keep" lines book;
  - an unrequested sold line books;
  - a lost deal books nothing, and Sold is refused on it;
  - a sold plan cannot be deleted;
  - a carrier rename updates the record found by `plan_ids`;
  - un-selling voids, and selling again brings the record back;
  - typed keys survive Rebook, and Rebook works the terms out again unless shares were typed;
  - a failing receiver leaves the sale saved, with no 500 (`captureOnCommitCallbacks`), and the tab shows "not booked".
- **Stale chip:** shown after a census or count change; Update rebooks.
- **Year rule:** typed; earlier records, manual ones included; a deal opened as existing books at the renewal % with "year unknown"; the renewed flip.
- **Owners:** the resolver order; saving a primary sets `Deal.owner` with one Activity row; a Party is created on the first save.
- **Visibility** on every endpoint family and in exports:
  - any deal user edits rates;
  - only the all tier or the deal's owner saves a split;
  - the own tier sees its own records, `party_ids` included;
  - none-tier users get no ledger figures in the summary.
- **Reconcile:** every month status; drafts excluded; reversals net out; YTD by arrival date; the badge equals the list.
- **Statements:**
  - match → post → lock → reverse; reversing twice, or reversing a draft, is refused;
  - a posted line moves only by reversal;
  - a junk id answers 400;
  - a spreadsheet import is all or nothing;
  - an alias is learned on a match and ignored when two clients claim it.
- **Matcher:** tiers, ties and anchors; the review chip equals what confirm does.
- **Reader:**
  - no network without a key;
  - nothing is written until confirmed;
  - confirm is all or nothing, and a second one answers 409;
  - dedupe only across overlap pages;
  - truncation retries;
  - firm documents and jobs are refused below the all tier.
- **Records and clients:** deleting a client with records answers 409; Add to book creates no deal.
- **Disclosure:** medical, dental and vision only; all tier only.
- **Exports:** the injection guard; proposal files carry no commission.
- **Activity:** before and after values only; the revert handlers work for rates and splits.
- **Concurrency and cost:** concurrent edits to two lines' rates both survive; the preview runs no `line_state` queries.

## H.7 Open questions for Daniel

1. Is the commission ledger (statements, reconciliation, gaps, statement reading) part of 2V's first build? plan.md §1.4 and §15 rule it out; D-012 makes it a top-three priority and dates it to the first carrier checks (about 2027-02-01). **Default:** C1 in the MVP; C2 and C3 wait for your answer.
2. Should the ledger start with the existing book of business (a spreadsheet of in-force lines), or with the old app's parties, client splits and booked records? Without one, most statement lines will be unmatched. **Default:** "Add to book" by hand; a one-off import if you ask for it.
3. Are renewals in scope: carrying last year's split and rates, Start renewal, year ladders? **Default:** no carry.
4. For clients the agency served before the app, which year applies? **Default:** earlier records decide, hand-added ones included; else a typed "year with us". A deal opened for an existing client with neither books at the renewal % as "year unknown".
5. Do producers keep the "own" tier on the ledger, seeing only their own share? **Default:** yes; admins see everything; a per-person override in Django admin. Every producer still sees every split on the deal tab (D-066).
6. Who may save a split? **Default:** all-tier users and the deal's owner. The old code let any producer save.
7. Is a partner's flat or PEPM amount per deal (spread across the lines) or per line? Is a referral % taken from the producer pool or from gross revenue? **Default:** per deal; the pool, with gross selectable per row.
8. Is the deal owner always the primary producer? The RFP prints the deal owner as the agent. **Default:** yes; saving a split's primary sets the owner.
9. Should the pre-sale estimate use Renewal, then Current, then the starred plan? **Default:** yes; after the sale only Sold counts.
10. Is the client workspace page being rebuilt? **Default:** the client statement lives at `/commissions?client=…`.
11. When two carriers are sold on one line, is that one record per carrier? **Default:** yes.
12. Should Received YTD go by the date the money arrived, or by the month it pays for (as before)? **Default:** the arrival date.
13. May carrier statements be sent to Claude before the BAA is signed? **Default:** no (plan §10).
14. The law requires the CAA disclosure at every close (D-020). Who sends it while the close-out bundle is out of scope? **Default:** the back office downloads it and sends it inside its own close-out email.
15. When do comp agreements with e-sign, producer profiles and W9s, payouts and the Book split come back? **Default:** after the MVP.
