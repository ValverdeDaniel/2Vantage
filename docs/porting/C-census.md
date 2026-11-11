# Part C — Census

[← Porting plan](README.md)

**What it is:** the employer's roster of employees and dependents. It feeds pricing (enrollment by tier, volumes,
headcounts), the carrier census files in the RFP packet, the questionnaire's employee counts, the size band and the
checklist.

## C.1 Files read, in order (one line each)

**Specs and READMEs**

| File (lines) | What it is / what it taught |
|---|---|
| `benefits/README.md` (394) | Module map. Census is counted in SQL; rows are paged by employee; snapshots key rows by a derived key because every rebuild changes primary keys. |
| `benefits/market/README.md` (461) | Census files, the renewal loop, and D-152 `upsert_roster` replacing delete-and-rebuild. |
| `benefits/CLAUDE.md` (120) | Layered values (edited ?? client ?? extracted), the confirmation layer, layer stamps, "requiredness implemented several times". |
| `PlanningDocs/Benefits/census-client-request.md` (439) | D-047: the gap panel, ask scopes, the employer adds people, the rebuild guard. |
| `PlanningDocs/Benefits/carrier-census-templates_20260917.md` (501) | The seven export formats and their per-column translation tables. |

**Models and rules**

| File (lines) | What it is / what it taught |
|---|---|
| `models/market.py` (706) | `CensusRow`, `CensusCell` (about 30 columns per cell), `CensusImport`, the client request/link census fields, `CensusFieldRequirement`. |
| `models/case.py` (1,878) | `BenefitFieldDef`, `census_counts`, the deal's census methods (required keys, scope queries, `census_metrics`), `ConfirmableValue`, `LocatedValue`, `LayerStamps`, `CarrierTemplate`. |
| `registry.py` (632) | The 45 census fields in four append-only lists seeded by migrations; per-line required tiers; in-force rules; three legacy demo carrier templates. |
| `market/validation.py` (501) | Tier aliases, waive words, coded choices, `validate_case` (every census rule). |

**Import and services (`market/`)**

| File (lines) | What it is / what it taught |
|---|---|
| `census_reader.py` (507) | Parses CSV/XLSX, finds the header row, synonym mapper, `apply_import` → `import_people` → upsert. |
| `census_upsert.py` (271) | `upsert_roster`: matches people by identity and keeps worked-on people; dry run. |
| `census_pivot.py` (629) | Detects one-row-per-benefit files and pivots them to one row per employee; refuses rather than guesses. |
| `census_request.py` (844) | Ask scopes, gap report, help text, the rebuild guard and ask re-pointing, masked SSNs. |
| `field_request.py` (913) | Per-deal Required/Waived overrides, the one requiredness fold, the review board, column drill. |
| `value_origin.py` (231) | Nine "origin" words, implemented twice (Python and SQL); `write_hand_edit`. |
| `census_lens.py` (437) | Per-carrier format lens: list, detail, real-fill check. |

**Pricing and other readers of the census**

| File (lines) | What it is / what it taught |
|---|---|
| `pipeline/plan_math.py` (1,440) | Tier counts, `group_premium` by basis, volumes, enrolled counts, stop-loss headcount, FTE, family order, `census_rows_for_template`, derived age, county and out-of-area. |
| `lines.py` (197) | `TIER_FIELD_FOR`, `VOLUME_FIELD_FOR`. |
| `pipeline/enrollment.py` (194) | Typed per-plan counts and their precedence. |
| `pipeline/medicare.py` (52) | `census_ages`. |
| `pipeline/plan_links.py` (174) | Confirms the old app never matched census plan names to plans. |
| `serializers/pipeline.py` (1,958, lines 240–365) | Counts per line in `comparison_payload`. |
| `pipeline/advisor.py` | Census notes in Claude's context. |
| `market/marketing_checklist.py` | The COBRA row; `enrolled_headcount`. |
| `market/rfp.py` | `group_facts` (FTE). |
| `questionnaires/service.py` | Prefills eligible employees. |
| `radar/reminders.py` | Plan-year snapshot. |
| `renewal.py` | Census carry. |
| `market/intake.py` | `census_ok`, `approve_client_values`. |
| `serializers/journey.py` | Census next actions. |

**Views, payloads, files, AI**

| File (lines) | What it is / what it taught |
|---|---|
| `views/market.py` (2,148) | Census view classes: grid, import, apply, rows, cells, requests, exports, template, links, approve, review, requirements, batch. |
| `views/lens.py` (68) | Three lens GETs, no-store. |
| `views/review.py` (628) | Census parts. |
| `review/items.py` (1,544) | Census client / AI / questions items; chosen-format columns. |
| `serializers/market.py` (980) | `census_payload`, COBRA block, paging. |
| `pipeline/workbooks.py` (2,056) | Carrier census workbook fill, bundled fill, template drift check, blank template. |
| `ai/extraction.py` (846) | Census read job; auto-chain after a quote read. |
| `views/ai.py` | Starts the census job. |
| `ai/claude_readers.py` (4,127) | Census parts: Claude column mapping, shape classifier, PDF reader, de-duplication of people read twice, staged apply. |
| `ai/census_agent.py` (605) | Work with Claude census agent (`CensusTurn`) and its tools. |
| `urls.py` | Census routes. |

**Frontend (`frontend/src/…`)**

| File (lines) | What it is / what it taught |
|---|---|
| `services/api/benefitsMarket.js` (455) | Census API calls. |
| `CarryNotice` (43), `CobraCheck` (85), `CensusReformatBanner` (97), `MappingReview` (159) | Small panels; `MappingReview` takes over the tab while a mapping awaits review. |
| `CensusRequestPanel` (435), `CensusGrid` (1,215), `CensusTab` (948) | Gap panel; the roster grid; the tab shell with its views and URL aliases. |
| `censusreview/censusReviewRows.js` (340), `CensusReviewFieldRow` (202), `CensusReviewDrill` (307) | Board rows and the column drill. |
| `CensusSendPanel` (263), `ExportReadiness` (102), `CensusReviewView` (483) | Send to assignees, export cards, the board. |
| `CensusFormatLens` (685), `CensusAiReview` (495), `CensusClientReview` (619), `CensusRequestsView` (602) | Format lens and the review and waiting queues. |
| `shared/useGridKeys.js` (435) | The grid keyboard contract. |
| `benefits-census-review.css` (928), `benefits-grid.css` (200), about 41 census rules in `benefits.css` | Census styling. |

**Tests (names only):** `market_tests` (about 40 census classes), `pipeline_tests`, `portal_tests`, `wwc_targets_tests`,
`plan_counts_tests`, `tab_speed_tests`, `intent_outputs_tests`, `presentation_tests`, `builder_polish_tests`,
`review_*_tests`.

## C.2 Old data model, in brief

- **Columns:** 45 census columns from `BenefitFieldDef(domain='census')`.
  - **Identity:** employee id, first, last, relationship, subscriber SSN, middle.
  - **Demographics:** DOB, SSN, gender, address, phone, email, county.
  - **Employment:** division, class, hire date, salary, title, work state, term and rehire dates, status, hours per week.
  - **Enrollment by line:** medical, dental and vision plan, tier and effective date; life and disability amounts.
- **Requiredness, computed on read:** a column is required if it is statically required, or it is a quoted line's tier
  column, or it is `medical_plan` when medical is quoted and in force. Then:
  - the per-deal override applies (waived beats forced);
  - then a dependent is exempt from employment, enrollment and ZIP.
- **Rows:** `CensusRow` (employee or dependent, parent link) plus one `CensusCell` per row × field. That is about
  60,000 cells for 1,000 employees, each with three value layers, confirmation, review mark, origin stamps and source
  location.
- **Imports and templates:**
  - `CensusImport` stores the mapping (with three sample values per column — PHI kept forever) and the pivot recipe.
  - `CarrierTemplate` holds each carrier file's columns, translations and workbook geometry.
- **Derived on read:** effective value, status, confirmation, origin word, validation issues, and metrics — readiness %
  (capped at 99 while errors remain), counts by status, error and warning counts, employees and dependents.

## C.3 Functionality inventory and verdicts

**Verdicts:** **Keep** = rebuild as it works now; **Simplify** = keep the user-visible behaviour, change how it's
built; **Drop** = not rebuilt; **Defer** = later; **New** = not in the old app.

### Roster grid

| # | Functionality (what the user sees → how it worked) | Verdict | New implementation |
|---|---|---|---|
| C1 | Roster paged by employee (100 per page, up to 500); families kept together; orphan dependents on the last page | Keep | `census/selectors.grid_page` over `Member` rows |
| C2 | Line chips (Person & employment always on; medical, requested lines and lines with data shown by default); headers size the columns; frozen Person column ("↳ Spouse" for dependents) | Keep | Same markup and classes |
| C3 | Cell colour by status or review mark; red or amber underline for validation; ⓘ hint on coded columns; tooltip (mark → issues → note); ↗ pin opens the source document at the value | Keep (fix the "warning" vs "warn" bug that hides duplicate-person warnings) | Status computed from `values` + `sources` |
| C4 | ✎ Edit mode backed by a server edit session; double-clicking a locked cell offers edit mode; a "From the client" toggle tags edits as relayed | Simplify: Edit is a client-side toggle; no server session; "From the client" becomes `sources.origin = 'client_relay'` | — |
| C5 | Keyboard: click selects; typing or F2 edits; Enter, Tab, arrows, Home/End move; Esc cancels; Delete clears; Ctrl+Z undoes up to 50 edits | Keep (port `useGridKeys`) | `frontend/src/deal/census/useGridKeys.js` |
| C6 | Datalist suggestions on coded columns; a blur that changed nothing writes nothing; optimistic writes, one at a time, then one reload | Keep, plus Simplify: the PATCH returns only the changed member and its issues, not the whole roster | `census/services.edit_values` |
| C7 | ＋ Add employee; ＋ Dep menu (Spouse / Child / Domestic Partner, cursor lands in First Name); × delete person (dependents go too) | Keep | `add_member`, `remove_member` |
| C8 | ☑ Select cells / "Select all missing"; Approve / Ignore / Needs checking marks; ＋ Ask N into the request tray; bulk approve or ignore every open warning | Simplify: marks live in `sources[key].mark`; asks go through the Review app's tray | `census/services.mark_values` |
| C9 | Banners: validation error count; "a census file is mapped and waiting"; "a census file is waiting for review" (staged PDF) | Keep | — |
| C10 | Empty roster: three doors (scan with Claude, add by hand, ask for the file); Work with Claude opens itself once | Keep | — |

### Getting a file in

| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| C11 | Start a census read (producer upload; auto-chained after a quote read; portal upload, staged when a roster exists) | Keep | A job through the AI app (Part D) |
| C12 | Parse CSV (UTF-8 with BOM, else Latin-1) and XLSX/XLSM/XLS; header is the first of the top 10 rows with 3+ label-like cells; sheet row numbers kept | Keep | `census/importer.py` |
| C13 | One-row-per-benefit reformat: score the file's shape; pivot automatically at ≥ 0.80; 0.55–0.80 asks Claude or flags "needs attention"; refuse rules (> 40% rows without a person key, > 20% unknown benefits, > 10% conflicting identity, no employee); first duplicate kept; only the recipe stored, rows rebuilt from the file | Keep (it is deterministic and well tested) | `census/pivot.py` |
| C14 | Column mapping proposal: Claude (each key used once, header plus 15 sample rows) or the offline synonym mapper (exact 0.95; a bare "Effective Date" takes the previous column's line at 0.70; fuzzy 0.60 with a line-word guard); low = below 0.85 | Keep; **never store sample values** (PHI) | `census/importer.propose_mapping` |
| C15 | Mapping review screen: three samples per column, field select (picking a key takes it from the other column), Mapped / Check n% / Unmapped badge; reformat banner (before → after, lines found, things to check, "use the original file instead") | Keep | `MappingDialog.jsx`, same look |
| C16 | Apply: masked SSNs replaced by the number on file (last-4 check, else blank); an employee's SSN copied from the subscriber SSN; dependents linked by subscriber SSN, then employee id, then the last employee above; tiers normalised; source cell recorded | Keep | `census/importer.apply` |
| C17 | Identity matching on re-import: employees by employer id, then SSN, then name + DOB; dependents only inside their family (SSN, name + DOB, relationship + order); a shared identity is ignored; only the extracted layer moves; a dropped person someone worked on is **kept and reported** | Keep (better than plan.md's "delete unmatched"; plan.md is corrected) | `census/matching.py`, with a dry run that lists added, changed, removed and kept people |
| C18 | Rebuild guard: a 409 and confirm when open asks or unreviewed client values exist; asks re-pointed to new cell keys | Drop: asks are keyed by member id + column, which survive a re-import | — |
| C19 | PDF census read in page chunks; people read twice de-duplicated; dependents placed under their printed employee; tiers normalised; direct or staged apply | Keep | Through the AI reader framework (Part D) |
| C20 | Work with Claude census agent tools: get roster, find people (SSN last 4 only), read roster (dry-run preview), set mapping, apply, edit cells, add / remove person (refuses a person with dependents or an open ask), verify | Keep (Daniel wants Work with Claude), built on the shared agent framework (Part D) | `census/agent_tools.py` registered with the AI app |

### Validation and readiness

| # | Functionality | Verdict |
|---|---|---|
| C21 | Validation rules: SSN format, invalid, duplicate; duplicate person (warning); DOB unparseable, future, over 110, employee under 14 (warning); ZIP and state (warnings); unknown tier (Waived is valid); dependent relationship, orphan; tier against listed dependents (EE with deps, EC without child, ES without spouse, FAM without deps — warnings); hire after effective (warning) | Keep all; **one severity word** |
| C22 | Readiness % (100 when nothing is required; 99 cap while errors remain); counts by status | Keep |
| C23 | "Census OK" for intake readiness | Keep, **fixed**: it also requires zero errors (old bug) |
| C24 | Metrics and missing cells deal-wide whatever page is shown | Keep metrics; Drop the deal-wide `missing_cell_ids` list from every payload (fetched when Select-missing is used) |

### COBRA, renewal, review and requests

| # | Functionality | Verdict |
|---|---|---|
| C25 | COBRA check: tickbox with who/when; Waived reads "Marked not needed"; shared with the marketing checklist row | Keep (stored on `CensusSettings.cobra`; the checklist reads it) |
| C26 | Renewal carry (last year's census copied with origin `carry`, CarryNotice states, revalidation link from Overview, journey nag) | Defer with the renewal workflow (see open questions) |
| C27 | Review board per column: help or client note, band tone, filled / total, 5-segment status bar, origin bar, "differs from the client" chip, ▸ drill, assignee, Auto / Required / Waived toggle; filters (band, status, origin, search, required only, hide complete, only quoted, hide waived, assignee); saved filter setups | Keep (the Review app hosts the board; census supplies selectors) |
| C28 | Column drill: names for blanks; value, origin chip and layers side by side for filled; approve their answer; revert our edit; undo approval | Keep |
| C29 | Send to assignees: one link per contact from stored assignments (unassigned columns skipped or sent to the primary contact); copy, preview, PIN | Simplify: keep one link per contact; drop the disabled per-employee mode |
| C30 | Gap panel: scopes (just missing / whole census / cells I pick), by person or by field, recommends asking for a file when over 400 cells | Simplify: becomes a "by person" lens on the Board; same asks |
| C31 | Format lens per carrier file: summary, gap queue (A fill, X ask, R later), "make these required", warnings, column table, what they ask that we don't store, first 50 rows exactly as the carrier receives them, downloads, "check the real file" | Keep; it moves to the RFP app (census cannot import RFP); the Census tab links to it |
| C32 | Waiting panel (what we'd send now; links out with opened, progress, nudge, extend; contacts never asked) and the client-answers queue (grouped by column × change, approve all, A / X / R keys, keep ours, correct, notes, replies) | Keep in the Review app (Part J) |
| C33 | AI-read queue (absent / eye / review buckets; low-confidence and unused mapping columns first; viewer at the value) | Keep in the Review app (Part J) |
| C34 | "Approve N ready" section bar | Keep |
| C35 | Employer side: the portal writes only the cells asked about; adds people (50 per link, names required); downloads a blank template with masked SSNs; an uploaded file starts the reader | Keep (Part J portal) |

### Exports and outputs

| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| C36 | Carrier census exports: Warner, Aetna, Angle (+ CSV), UHC; filled in the carrier's own workbook; code translation with "no carrier code" notes; derived age, county and out-of-area; family order; employee-only columns; dependent-inherited values; row-cap warning; template drift check; export check (warn, then acknowledge) | Keep | Moves to the RFP app (Part H); one row builder |
| C37 | Warner request forms with the census inside | Keep (RFP) | — |
| C38 | Blank template: columns = registry minus unquoted lines plus forced columns; prefilled from the roster in family order; guide sheet second; portal copy masks SSNs | Keep | `census/template.py` |

### Rollups for pricing and the other modules

| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| C39 | Tier counts per line from employee rows (waivers and unknown words skipped); lines without their own tier column use the medical tier | Keep | `census/rollup.tier_counts(line)` |
| C40 | Precedence: typed per-plan counts (plan switch on) → a priced version's root → the linked current plan → the line's config counts → census tally | Keep the idea, Simplify the chain: plan enrollment typed → linked current plan's → census by plan name → census by line (2Vantage §5.5) | `quotes/math.enrollment_for` + `census/rollup` |
| C41 | Census plan-name matching to current plans (several current plans each priced from their own members) | **New** (the old app could not do it; it showed no dollar total for a multi-current line without typed counts) | `Plan.census_names` + `census/rollup.by_plan` |
| C42 | Volume sums (life per $1,000, STD weekly, LTD payroll) over employees | Keep (with the other rate bases) | `census/rollup.volume` |
| C43 | Enrolled count for flat per-employee (PEPM) pricing | Keep, **fixed**: count non-waived tiers from effective values (old bug counted Waived and ignored client answers) | `census/rollup.enrolled` |
| C44 | Stop-loss headcount (medical EE+ES+EC+FAM, else employees) | Keep | — |
| C45 | FTE (employees at or above the hours threshold, default 30) and the headcount warning against intake | Keep | `census/rollup.fte` |
| C46 | Ages at the effective date; Medicare-eligible count (dependents on their own DOB) | Keep | `census/rollup.ages` |
| C47 | Age-banded rating | Not in the old app; keep plan.md's "quoted premium" path | — |

**Not rebuilt:**
- the cell-per-row storage;
- the confirmation, stamp and location columns;
- census version snapshots and edit sessions;
- the many-to-many between asks and cells, with its re-pointing;
- the URL alias layer kept for guides;
- the legacy demo carrier templates;
- tests that read source or docs.

## C.4 Data flow

- **In:**
  - spreadsheet import (origin `import`) and PDF read (`scan`);
  - portal answers (pending until approved);
  - hand edits (`typed`, or `client_relay`);
  - Claude agent edits (`ai`), always staged for review;
  - renewal carry (deferred).
- **Out:**
  - **Pricing:** tier counts by line and by plan name, volumes, enrolled and stop-loss headcounts, feeding the Advisor and Proposal.
  - **RFP:** carrier census rows, FTE, headcount warnings.
  - **Questionnaire:** eligible employees.
  - **Intake and checklist:** census OK, COBRA, enrolled headcount, which sets the size band.
  - **Review:** client answers and AI reads to review.
  - **Overview and Agenda:** readiness and next actions.

## C.5 New design

- **Django app `census/`** (sits after intake and before quotes in the app chain):
  - `fields.py`: 45 columns, groups, choices, help, synonyms, `is_required`.
  - `models.py`:
    - `Member` (deal, kind, employee FK, position, `values`, `sources`, `pending`, `added_by_client`, timestamps);
    - `CensusImport` (document, sheet, header row, data row, mapping without samples, pivot recipe, status);
    - `CensusSettings` (deal 1:1, rules, COBRA).
  - Logic modules: `importer.py`, `pivot.py`, `matching.py`, `validation.py`, `rollup.py`, `template.py`.
  - `selectors.py`: grid page, summary, board, drill.
  - `services.py`: `edit_values`, `add_member`, `remove_member`, `apply_import(dry_run)`, `set_rules`, `approve_pending`, `mark_values`, `set_cobra`. Each locks the deal's members and records an Activity summary with no member values.
  - `agent_tools.py`.
- **Frontend `frontend/src/deal/census/`:**
  - `CensusTab` (Roster | Board), `RosterGrid`, `AddDependentMenu`, `MappingDialog`, `CobraCheck`;
  - Board components, which the Review app reuses.
- **Look:** the `bnf-census-*`, `bnf-map-*`, `bnf-reformat-*`, `bnf-cobra-*`, `bnf-dep-*` and `gk-*` rules are copied verbatim (Part N, styles).
- **Performance:** one query loads a deal's members as JSON. Readiness and validation are Python loops over at most a few
  thousand people, about 1,000 rows/ms, so no SQL twins and no parity tests.

## C.6 Open questions for Daniel

1. **Renewals:** are they in this build's scope? If yes, the census carry and revalidation (C26) come back.
2. **SSNs:** should SSN stay optional? The old app required it for every person, dependents included; plan.md made it
   optional and never asked on the portal.
