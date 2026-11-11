# Part O — Architecture of the new codebase

[← Porting plan](README.md)

This part fixes where every piece lives. O.6 resolves each conflict between Parts A–M, and O.1–O.5 already follow those rulings. Where a part's own design says otherwise, this part wins, and slice 1 corrects plan.md. Changes to Daniel's conventions are asked once, as OQ9.

## O.1 The app chain

```
accounts → deals → documents → ai → intake → census → quotes → questionnaire
         → commission → rfp → proposals → review → agenda → overview → golden
```

- An app imports only from apps to its left. An import-linter "layers" contract fails the Lint lane on any import to the right; each app joins the contract in the slice that creates it.
- `backend/` (settings, URLs, `/api/meta/`) is the composition root and may import any app.
- `golden` is not a tab. It holds `seed_golden`, the golden deal specs and their keys, and seeds through every app's services, so it sits last. Only the seed command and the root `conftest.py` import it.

**Why the non-obvious apps sit where they do.**
- **ai** holds jobs, the worker, the Claude client, chats, change sets and landing, but no business data: owners register into it (D.6).
- **quotes** (the Advisor) prices from census rollups and owns `facts.py`, which questionnaire and rfp share.
- **questionnaire** prefills from `quotes.facts` and ties rows to current medical plans (G134).
- **commission** books from quotes' packages and `sold_changed` (H.6).
- **rfp** prints questionnaire files and commission's requested rates (K.6).
- **proposals** prints "Markets checked" from `rfp.asked_by_line` (J63, K117).
- **review** writes through every owner, and later hosts `/p/`, which imports proposals (J156).
- **agenda** reads every app's facts and review's rules, and sets nudges through review. **overview** assembles one deal; nothing imports it.

**Crossing to the right.** A left app never imports a right app. It owns a seam that the right app fills in `AppConfig.ready()`:
- a **provider slot**: one function with a default answer, so the left app runs and passes its tests before the right app exists;
- a **registry**: many entries of one shape;
- an **on-commit signal**, sent with `transaction.on_commit(..., robust=True)` and `send_robust`.

A left app's pure rules take the right app's fact as an argument, for example `checklist.tier(headcount)`; only its services and payloads call the provider. Agenda, overview and golden import each app's `summary.facts` directly; `deals` has no summary registry.

| Seam | Filled by | Shape | Used for |
|---|---|---|---|
| `intake.providers.headcount` | quotes | `{count, source, estimate}` | checklist tier and address rule (B25), readiness |
| `intake.providers.census_state` | census | `{has_roster, employees, errors, ok}` | "Census OK" (B33, C23) |
| `intake.providers.questionnaire_items` | questionnaire | `{item: {form, source, armed, started, progress, signed, done}}` | form rows (B22, B26, G11) |
| `intake.providers.quote_lines` | quotes | `{line: {presented, sold}}` | `line_states` (B24) |
| `census.providers.carrier_required` | rfp | `{key: {employee: [carrier], dependent: [carrier]}}` | requiredness and blanks (K.6) |
| `quotes.providers.disclosure_state` | questionnaire | signed, started or not started | stop-loss Binding Notes (G117) |
| `rfp.checks.providers` | review | `fn(deal) -> [check line]` | the export check and its `?ack=` digest |
| `ai.registry` | intake, census, quotes, questionnaire, commission, proposals, review | O.3.3 | reads, turns, tools, page context |
| `deals.activity.reverters` | every app that writes | `revert(activity, user) -> changed` | Undo and Revert |
| `quotes.signals.sold_changed` | commission | `(deal_id, lines, user_id)` | booking (H.6) |
| `quotes.signals.plans_changed` | proposals | `(deal_id, lines)` | clearing Plans card marks (J.6.4) |

## O.2 The apps

Every app has `models.py`, `services.py` (or a `services/` package re-exported from its `__init__`), `selectors.py`, `summary.py`, `views.py`, `urls.py` and `tests/`. `summary.facts(deal_ids) -> {deal_id: dict}` runs in a fixed number of queries and returns counts, dates and flags only. One-to-one rows are created on the first write, never by a GET. Each app's API sits under `/api/deals/{id}/<area>/`, plus firm-level roots: `/api/auth/`, `/api/clients/` (DELETE answers 405), `/api/activity/{id}/revert/`, `/api/archived/`, `/api/documents/{id}/`, `/api/ai/jobs/{id}/`, `/api/plans/{id}/`, `/api/saved-views/`, `/api/commissions/`, `/api/proposal/`, `/api/links/{id}/`, `/api/portal/{token}/`, `/api/tasks/{id}/` and `/api/work-queue/`.

| App | Models (new or changed) | Owns, and what other apps call |
|---|---|---|
| accounts | `Profile(user, claude_direct, commissions_access: none, own or all)` | `can_direct`, `commission_tier`; admin and producer users (A2) |
| deals | `Client` (+ archive fields), `Deal` (+ `deal_size`, `opened_as`, `agent_of_record`), `Contact`, `Note` (soft delete), `Activity` (O.3.2), `AgencySettings` (+ `producer_name/npn`) | `values`, `carriers`, `comp`, `clock`, `stages`, `rules` (`refuses`, `deal_type`, `agent_name`, `is_past`, `client_asks_open`), `contacts.primary`, `downloads`, `pdfkit`. Services: `advance` (reload, lock, forward only), `set_lines` (called only by intake), `mark_lost`, `archive_client`, `set_owner`, notes, contacts, revert |
| documents | `Document` (+ `page_labels`, `page_count`, `screen`, `protected`, `link_id`, `slot`, archive fields; `deal` null only for firm statements) | `kinds`, `review_rules`, `screening`, `pages`, `sheets` (`look`), `locate/`, `images`, `xlsx_safe`. `upload` is the only door; archive and purge refuse protected files; bytes go only after commit (E96) |
| ai | `DealAi(locked_by/at, budget_usd, next_chat)`, `Chat`, `ChatMessage`, `Job`, `CarrierNote` | `registry`, `client` (the only importer of `anthropic`), `reading`, `turn`, `land`, `ranges`, `budget`, `pricing`, `worker`; services `jobs`, `chats`, `landing`, `deal_ai` |
| intake | `Intake(answers, sources, client, rules, checklist, intent_confirmed, bor_*, marketed_*, flags)`, `CurrentCoverage` | `form` (data), `values`, `validation`, `coverage`, `checklist` (COBRA included), `providers`; `set_intent`, `set_form_choice`, `mark_values`, the review contract |
| census | `Member(kind, employee, position, values, sources, client, added_by_link, removed_at)`, `CensusImport` (no sample values; `job` from slice 51), `CensusSettings(rules)`, `CensusFacts` | `fields`, `importer`, `pivot`, `matching`, `validation`, `rollup`, `template`; soft remove, `refresh_facts`, the review contract |
| quotes | `Plan` (+ `star_reason`, `starred_by/at`, `codes`, `read_ref`, `client_name`, `derived_from`, `derived`, `bundling`, `pair_of`, `option_number`, `flags`, `removed_at`; one `sort_order` per line; `option_label` and `enrollment_on` go), `Package`, `LineEnrollment`, `SavedView`, `QuoteLayout` | `math/` (`premium`, `enrollment`, `pricing`, `stop_loss`, `round_decimal`), `presented`, `order`, `slots`, `labels`, `facts` (`group_facts`, `enrolled_headcount`, `enrollment_check`, `incumbent`), `providers`, the reader modules, `revert`, the board exporter. Services for plans (merge, pair, clear line), marks (rank), roles, ordering, priced versions, review, enrollment, saved views, `read_apply`, `set_sold`, `stamp_option_numbers`. Selectors `comparison`, `deal_state`, `find_index`, `as_quoted`, `stop_loss`, `sources` |
| questionnaire | `Questionnaire` (G.6, with L's `client` shape) | `forms/`, `engine/`, `values.effective`, `prefill`, `choice`, `checks`, `rfp_rules`, `pdf/`; services `answers`, `rows`, `signing`, `client`, `reads`, `picks` |
| commission | `Party`, `Settings`, `Commission`, `ClientSplit`, `Record`; `Statement`, `Receipt`, `GapNote` and `Alias` only if OQ6 says yes | `math` (rounds only through `round_decimal`), `rules`, `visibility`, `booking`, `requested_rates`. `summary.facts` is the same for every viewer; `summary.card(deal, viewer)` adds what a tier may see |
| rfp | `RfpRequest` (K.6) | carrier data and formats, forms, `cover`, `packet`, `drafts`, `eml`, `check/`; services `update`, `set_done`, `mark_sent`; selectors `asked_by_line`, `required_columns` |
| proposals | `ProposalConfig` (J.6.2; `lines` holds per-line settings, never membership or pairs), `ProposalIssue`, `ProposalTemplate`, `FirmPages`, `TeamMember`, `CoverImage` | `catalog`, `config`, `marks`, `pages` (the one splitter; a pair is one column), `client_facts/`, `ready`, `checks`, `story/`, `layout/`, `paint/`, `workbook/`, `viewer/`, `packet`; services `set_config`, `set_mark`, `clear_marks`, `issue`, firm pages, templates |
| review | `ClientRequest`, `ClientLink` (+ `nudge {on, by, at, done_at, done_by}`), `ReviewNote`, `Seen` | `rules/` (`items`, `requests.carries`, `policy.floor`, `next`, `badges`, `form_plan`, `tray`), `owners.py`, `portal/`; services `mark_document`, `set_nudge`, `finish_nudge`, `portal/save`; selectors for the tab's counts, `confidence`, `outreach` |
| agenda | `StepMark`, `Task` | `catalogue`, `rules`, `steps/`, `marks`, `rows`, `queue/`; services `marks`, `tasks`. It never writes a module value or a stage |
| overview | none | `payload.overview(deal, viewer, today)` and `rules`; no services |

## O.3 Shared frameworks

**O.3.1 Values, sources and marks**
- Plan, LineEnrollment, Intake, Member, Questionnaire, Commission and Record keep values (or answers) as JSON with a parallel `sources` dict.
- `deals/values.py` defines one source entry: `{origin, by, at, doc, page, cell, line, link, low, loc, mark: {state, by, at}, confirmed: {by, at, via}, read_value}`. `origin` is typed, relay, client, ai, import, prefill, sale, in_force or agency. `line` (≤300 characters) is never kept on census or questionnaire values; `read_value` only on plans the reader made (F141); `low` is a reason, or null; `loc` is the locator's result `{state, page or sheet and cell, hits, via, why, printed, v, at}`.
- `deals/values.apply()` is the only writer of these dicts. An unchanged value writes nothing. An empty string clears a value, and `null` reverts a typed value to the one that was read. Any change drops `mark` and `confirmed`, so marks lapse in one place. A typed value over a read one keeps `doc`, `page`, `cell`, `line` and `read_value`, and drops `low` and `loc` (E66, F141).
- `documents/review_rules.py` is pure: `apply_mark`, `is_approved`, `open_warning` (the one rule; no SQL copy), `potential_error`, `shows_approval`, `review_bucket`, `origin_bucket`, `quality_headline`.
- Each value owner serves `GET …/sources/?documents=&bucket=&page=` and `POST …/marks/`, and registers `locate_queries` and `save_locations` with ai. Review's `mark_document` marks one file across all owners in one transaction.
- A client's answer waits in the row's `client` JSON `{value, confirm, link, at, status, by, decided_at}`; status is pending, approved, rejected or replaced, and census and questionnaire entries add `prior`. Only approval moves an answer into `values`. Rollups, readiness, exports and printed PDFs read approved values only.

**O.3.2 Activity and revert**
- One `Activity` row holds `deal` (null for firm rows, which carry a `subject`), `area`, `action`, `actor`, `actor_kind` (user, client, claude or system), `summary`, `changes`, `document_id`, `coalesce_key`, `count`, `reverts` and `reverted_at/by`. It is indexed on (deal, created_at) and (area, created_at); list selectors defer `changes`.
- `changes` holds before and after per key, for example `[{"t": "plan:41", "k": {"rate_ee": ["612.50", "640.00"]}}]`. Census rows, sensitive questionnaire slots and lasers record keys only; commission values are hidden below the all tier.
- A burst of writes merges into one row that keeps the first "before" and the last "after". Review, marks, imports, issues, sales and stage changes never merge.
- `POST activity/{id}/revert/` calls `reverters[area]` in one transaction, in the lock order. It answers 409, naming the keys, when a later write changed them; writes the old values through the owner's services; records a new row with `reverts` set; and works only once. Sold plans, signed forms, issued proposals, posted statements and rows that kept keys only refuse it with a sentence. For key-only rows the grid's in-session undo, which holds the old value in the browser, still works.
- A job's Undo reverts the job's row; the reader's keep rule (D73) lives in `quotes/revert.py`.
- `deals.activity.log_access(deal, user, action, what, document_id)` writes `downloaded` and `viewed` rows for PHI kinds and for files whose `screen.lists_members` is true. "Last updated" and the feed skip them.

**O.3.3 Jobs, the worker and the ai registry**
- One `ai.Job` (D.6's fields; `deal` null for firm statements). Kinds: `read`, `turn`, `recheck`, `rank`, `locate`, `issue`; `target` names the reader (quotes, sbc, intake, census, questionnaire, commission_statement). Lanes: `work` (read, recheck, rank), `chat` (turn) and `system` (locate, issue), so a locate or an Issue never waits behind a long read. A partial unique constraint allows one running job per (deal, lane), or per (document, lane) with no deal.
- `manage.py run_worker` runs as its own Compose service: it claims jobs with `select_for_update(skip_locked=True)`, beats on stream events, times out silent calls, and its reaper takes jobs silent for 10 minutes (D105). Tests run jobs inline with a fake client.
- Registry entries, each registered from `apps.ready()`:
  - **readers** `{target, kinds, prompt, schema, build_changes, must_review, apply, undo, discard, can_access, on_client_upload}` from quotes (`quotes`, `sbc`), intake, census, questionnaire and commission (only with OQ6);
  - **job kinds** `{lane, run, access}`: `rank` (quotes) and `issue` (proposals);
  - **context providers** `fn(deal, page_state) -> text` from quotes, intake, census (counts only), questionnaire, proposals and review;
  - **chat tools**, strict (D81), whose writes stage through `propose_changes`: quotes' `set_board`, `rank_plans`, `check_values`, `merge_plans`, `clear_line` and `pair_plans`; intake's `add_lines` and `update_client_guidance`; proposals' `set_table_note` and `set_rows`;
  - **locate hooks** from quotes, intake and questionnaire.
- Every reader runs through `ai/reading.py`: Messages API only, structured outputs, streamed, page ranges from `ranges.py`, no forced tool calls. The change set is D.6's, with `line` on each value.
- **Files are read whole,** as the old app reads them since D-225. `ranges.py` always leaves out pages that carry only the running header and footer, and leaves out pages the screen flags only while `AI_MEMBER_DATA_SCREEN` is on (OQ22). The SSN scrub, counts-only census context and the questionnaire's answered-or-blank sensitive slots stay. PHI readers (census, intake, questionnaire, statements) register only when the PHI-gate setting is on.
- **Landing (D71).** A quote read lands at once only for admins and direct people, and even then waits when the table is locked, the deal is lost, the read is partial, the file is an SBC, or the read removes a plan. Intake, census and questionnaire reads always wait in their owner's review. A person applies every re-check (D-119).

**O.3.4 Asks, links and the portal**
- Review owns requests, links, notes and the public portal (`review/portal/`). Intake, census, questionnaire and the document upload slots expose one owner contract: `save_client`, `approve_client`, `reject_client`, `revert_approval`, `client_entries`, `portal_payload` and `spec`; `review/owners.py` is a plain table of these modules.
- `rules/requests.carries(asks, ref)` is the only rule for what a link asks, and `rules/policy.floor(asks)` the only second-factor rule. Questionnaire forms use `sensitive_slots()` and `gate_slots()`; a census ask needs a PIN only when the page shows people.
- `rules/badges` is the one count rule. The Review tab and tray get their counts in their own payload (L1, L2, L28, L49); agenda's `journey/` calls the same rule for the sidebar.
- The portal is AllowAny, with per-token throttles, `no-store` and allowlisted payloads. A GET writes only the open stamp; staff sessions get 403 on writes; saves lock the owners' rows in the lock order.

**O.3.5 Viewers and the printed quote layout (need 3)**
- documents holds the server helpers: `sheets.py` with the pure `look(workbook, sheet, start, rows, cols)`, `locate/` (pypdf, visible cells only, D-122), `screening.py`, `pages.py`, `images.py` and `xlsx_safe.py`. Downloads go through `deals.downloads.file_response`.
- The browser's `src/viewer/` takes a URL or a blob, uses the legacy `pdfjs.js` build shared with the Export viewer, serves tesseract from `/static`, and draws `look()` payloads in SheetTable. `src/grid/` (selection, keys, sizes, freeze panes, windowed rows, the write queue and a 50-step per-cell undo that writes with `expect`) serves the Advisor, Proposal, Documents and Census grids.
- **`quotes.QuoteLayout`** stores one printed table of a scanned quote: `deal`, `document`, `line`, `where` (`{"page": 3}` or `{"sheet": "Medical"}`), `columns` (`[{"col": 0, "plan": 41, "head": "Gold PPO 1500"}]`), `rows` (each `{label, keys}`, and for an unmapped row `{"label": "Chiro visits", "keys": [], "printed": ["20/yr"]}`), `job` and `written_at`. `read_apply` writes it while landing, a re-read replaces it, and `printed` is never kept for PHI kinds.
- One endpoint, `GET deals/{id}/plans/as-quoted/?document=&line=`, serves the Advisor's "As quoted" view (F42) and the Documents view (E42). Mapped rows show live values; unmapped rows show the printed text, greyed.
- The layout orders nothing. The read numbers new plans in reading order (F138), so the board, Pages and client files open in the quote's order.

**O.3.6 Outputs and the export viewer**
- Client files live in proposals. The workbook is a pure sheet model written by XlsxWriter through `xlsx_safe`. `story/` builds the content; `layout/` fits it and records every frame; `paint/pdf.py` draws the PDF, `paint/pptx/` replays the frames and `paint/paper.py` places pages at 75%. The Letter PDF is made from the stored PDF. Fonts, colours and letterhead come from `deals/pdfkit.py`. Internal files stay with their owners.
- 2V pins the old app's writers (reportlab 4.2.5, python-pptx 1.0.2, XlsxWriter 3.3.0) in the slices that add them, so Fidelity compares our code, not library versions.
- A pair prints as one column under the first plan's id and option number; each row is worked out by code, as D-219 does, and the column is priced again by `package()`.
- The export viewer (J105–J120) writes nothing. The deck view is one build; the Excel view serializes the sheet model, one tab per call, into `look()`'s payload; preview keys hold J's `files` and `firm` stamps (J107).
- Client files print only `client: True` fields, and never the items on J.4's "never" list.

**O.3.7 Rules every app shares**
- **Lock order.** A write that spans rows or owners locks the Deal row first, then owner rows in chain order, each by id. A single-row edit locks only its row.
- **Lost deals.** `deals.rules.refuses(deal, action)` lists what a lost deal refuses: send to market, sign, mark sold, book, portal writes, client asks and automatic AI landing. Internal edits pass (A19).
- **Removed rows.** Plan, Member, Task, Note and Document hide removed rows in their default manager; `all_objects` serves links and history. Archived clients are filtered by `live()` in list selectors only, so their pages still open.
- **Protected files.** Issue and signing set `Document.protected`; archive and purge refuse those files with a sentence. The kind cannot tell a signed copy from a client upload, and documents cannot read questionnaire.
- **Stored counts** are the one exception to "status is worked out on read" (OQ9): `census.CensusFacts`, and `flags` (open warnings) on Plan, Intake and Questionnaire. Owners rewrite them in the same transaction; `manage.py rebuild_facts` and a test rebuild and compare them.
- **Money.** Premium math and all rounding live in `quotes/math/` (Decimal, half up, `round_decimal`). Commission's share arithmetic rounds through it. The browser does no money math.
- **PHI** never reaches Activity, logs, error text, file names or URLs. Downloads and views of PHI files are logged.

## O.4 Frontend

- **Routes.** Tabs live in the path; in-tab state lives in the query string (`?view=`, `?line=`, `?file=`, `?doc=&ref=&page=&back=`, `?focus=`, `?form=`, `?claude=read&docs=…`). Pages: `/login`; `/` (New clients, Clients or Work queue, by `?view=`); `/archived`; `/commissions` (needs a commission tier); `/deals/:id/:tab` (overview, agenda, review, intake, census, questionnaire, rfp, commission, advisor, proposal, documents), where `/deals/:id` opens the Advisor until slice 62 and the Overview after; `/deals/:id/documents/:docId/window`; `/portal/:token`; `/preview/links/:linkId`; `/b/:token` ("This link has moved").
- **Shell.** AppShell holds the 56 px navy bar. DealShell holds the 232 px sticky sidebar (grouped nav, badges, readiness meters, journey stepper), the header strip, one error boundary per tab, the Claude button, drawer and strip, the review tray and toasts. It runs two queries: `['deal', id, 'header']` from deals and `['deal', id, 'journey']` from agenda. The Advisor's view pills mount the builder, Pages and the Export viewer from `deal/proposal/`.
- **React Query.** Deal keys are `['deal', id, area, …]` with `staleTime: 0`. Heavy keys (the station, sheet windows, previews) skip refetch on focus; previews use `staleTime: Infinity`, keyed on the stamps and enabled only while shown. A write's answer holds only what changed; the hook writes it with `setQueryData` and invalidates its own area; `invalidateDeal(id)` refetches only the header and journey. Two pollers only: `useAiState` (2 s, slowing to 10 s while jobs run; a finished job invalidates its `landed.areas`) and review's `usePollStamp`.
- **Folders.** `frontend/src/` holds `api/` (client.js with CSRF, keys, one file per app), `auth/`, `pages/`, `deal/<tab>/` (plus `claude/` and `shared/`), `portal/` (its own axios instance), `viewer/`, `grid/`, `valuereview/` (lists, bulk bar, `useReviewHotkeys`, `keys.js`, `useMarks`), `exportcheck/`, `voice/`, `ui/`, `lib/` and `styles/`. A tab folder's `index.js` exports only what other tabs mount. Shared: `FieldInput` (intake, questionnaire, portal), `CellInput` (census), `deal/shared/BuilderCard` (proposals, rfp). Vitest covers pure modules only. `tools/parity/` and `browser/` hold the parity and walk harnesses (Q.5).

## O.5 The stylesheet port

**One port, in slice 2.** Every in-scope old sheet is copied whole, in the old `main.jsx` order, except the ranges listed below: App.css, navbar, benefits, benefits-coverage, benefits-overview, benefits-journey, benefits-radar (agenda rows, `bnf-cat-chip`, `bnf-cal-*` and `bnf-cw-*` only), benefits-workqueue, benefits-tasks, benefits-questionnaire, benefits-census-review, benefits-grid, benefits-freeze, benefits-grid-sizes, benefits-history, benefits-export, commissions, reviewrequest, assistant (`hlp-mic*` only) and linkguard (`lg-*` only): about 19,300 lines.

**Left out:** whole sheets of out-of-scope modules (taskmode, implementation, guide, unleashed, jointventures, workflows, lessons, reports, walkthroughs, pnc*, platform, roles, formbuilder, dev-usage), and the ranges the parts name for dropped or deferred features (`bnf-ver-*`, `agt-*`, `lsn-*`, print and `/p/` styles, the commission version rail and chat column, the edit lock). Deferred ranges return at their old position with their feature.

**Rules kept screens borrow.** Before the cut, a sweep lists every class the in-scope components use. A rule for such a class found only in a left-out sheet is ported at that sheet's old position in the manifest. Example: `.bnf-scan-drawer-sub`, the Work with Claude drawer's subtitle, lives only in benefits-unleashed.css.

**Cut, never merged.**
- Each sheet is split at its own section comments into consecutive files of at most 300 lines, under `src/styles/<old file>/NN-topic.css`. One manifest, imported once from `main.jsx`, lists every file in order.
- No CSS modules and no per-route sheets, because either would change the cascade. Module parts list the classes they use; they never copy CSS.
- A lint script (not a test) proves that each sheet's files, joined, equal the old sheet minus the listed edits.

**Fixes that keep the look.**
- App.css's `:root` block replaces 2V's tokens.
- Each use of an undefined property (`--muted`, `--accent`, `--ink-soft`, `--ink-3`, `--line`, `--red`, `--accent-bg`, `--border-strong`) is rewritten to what it rendered: its fallback or the inherited value (OQ10). A stylelint rule refuses unknown properties.
- `.btn-primary {width: 100%}` (App.css line 256) moves to the selectors that rely on it, and every rule that undid it goes. The first `.btn-sm` (line 483) goes, because the second wins.
- Markup bugs are fixed in the markup: C3's `warn`/`warning` mismatch and the unstyled `bnf-ag-section-title`.

2V's CSS modules are deleted in slice 4. At Milestone 2, a class-usage sweep deletes the rules no component uses.

## O.6 Resolved conflicts

| # | Conflict (parts) | Ruling |
|---|---|---|
| 1 | Chain order (A.6, I.6, L.6, H.6 vs G.6, J.6, K.6) | O.1's chain, the only order in which every stated import points left. OQ9 asks Daniel |
| 2 | Intake reads census, questionnaire and quotes (B.4, B25, C25, G11, K31, M) | Four `intake.providers` slots; the COBRA tick moves into `Intake.checklist`; B25's own headcount cascade goes |
| 3 | Header, next action, journey, badges, dashboard (A.4, A9, A10, A24, A29 vs I, M, L13) | The header carries deals facts only; agenda's `journey/` carries the journey, next step, sidebar badges and meters; the dashboard uses `work-queue/` and `stats/`. The Review tab and tray carry their own counts from the same pure `review.rules.badges` (L1, L2, L28, L49), so they work before slice 61. A29's registry and review's separate `badges/` endpoint go |
| 4 | Florida Blue pair (J3, J15, J161 vs F50, F137, D116) | D-219 by default: two plans in the data, one column in client files, both on working screens. `Plan.pair_of` lives in quotes so `room()` counts a pair once; proposals only print it; `pair_plans` is a quotes tool. `lines[line].merged` and `oversize()` go; F137 is built. OQ42 asks only how the deductible prints |
| 5 | Firm documents (H82 vs E.6) | `Document.deal` becomes nullable, with files under `firm/`; commission serves statement bytes by tier; the generic download refuses rows with no deal |
| 6 | Proposals' Job (J.6.1, J.6.7 vs D, E, A36) | Job stays in ai; proposals call `ai.services.start` |
| 7 | Chain cautions (I.4, J11, J156) | "Log a call" is a browser POST to agenda; "Page 1 is full…" comes from the pages payload; `/p/` lives in review |
| 8 | Printed layout (D66, E42, F42, F138) | `quotes.QuoteLayout` (O.3.5), one endpoint; no `Document.read_rows`, no `col` in sources; it never orders the board |
| 9 | Plan fields (D.6, D96, E40, F.6, F141, F143) | `star_reason`; top-level `codes`; `read_ref` and `read_value`; `starred_by/at` as fields, so E40's hover fits the compact payload |
| 10 | Typed enrollment (F85–F92, J48, D67, G5) | One `LineEnrollment` and one service; the Advisor card and the builder strip (J48) are two doors; `Plan.enrollment_on` goes. Claude's printed counts land unticked, per plan when printed per plan. A line figure that a second current plan stops is named and split, never dropped silently (OQ20) |
| 11 | Job model (A36, D.6, E59, G, H, J, M) | O.3.3: six kinds, `target`, three lanes, one running job per deal (or document) and lane |
| 12 | Document fields and kinds (E.6 vs D, F, G, H, J, L) | E owns the model and adds every field the others need; kinds add `stop_loss`, `commission_statement` (firm only) and `proposal` |
| 13 | Census members (C.5, C7 vs L.6, L90, L112) | L's design with C's `values`; soft removal; the default manager hides removed and pending people; `ReviewNote.member` is PROTECT |
| 14 | Client entry shape (G.6 vs L.6) | L's shape for every owner (`replaced`, `decided_at`, `prior`) |
| 15 | Option labels (F59 vs J159) | Per-line `option_number`, stamped at Issue in page reading order, never reused; `option_label` goes |
| 16 | Client guidance (D6, D98 vs F111, J.4) | The intake answer `client_guidance`, written by the drawer through intake; `DealAi` keeps only lock and budget |
| 17 | What archive covers (A18, I.6, L.4, M.6) | The client (M), with a computed `deal.archived` |
| 18 | Default managers (E, F, I, L vs M, A18) | O.3.7 |
| 19 | Activity and undo (A34, D.6, D73, E54, I, M) | O.3.2: one row with `changes`; one reverter registry; a job's Undo reverts its row |
| 20 | Firm pages (A22, A39 vs J155) | An in-app drawer; logo and colour stay in Django admin |
| 21 | Agent and producer name (G.4, H.6, J145, K.6, M.6) | One `deals.rules.agent_name` |
| 22 | Smaller fields (A3; I.6 vs L.6; G135) | `commissions_access` is H's tier; review owns `ClientLink.nudge`; signing and Issue set `Document.protected`, which archive checks (O.3.7) |
| 23 | Stored counts (C.5 vs I, K, L, M) | `CensusFacts` and row `flags`, an exception to "computed on read" (O.3.7, OQ9), because the Work queue reads every open deal |
| 24 | Enrollment precedence and headcount (C40, D67, F87–F91, G5, H7, J48, K17, B25, F86) | `enrollment_for` takes the first that exists: the plan's own typed counts; a priced version's original; the renewal's or replaced plans' counts; census by plan name; then, on a line with two or more current plans, nothing (the Advisor asks for the split or the link); else the line's typed figure; the census line rollup (stop-loss: medical employees); medical counts borrowed by worksite tier-rated lines; none. Counts typed before the latest import give way to the census (F91). `facts.enrolled_headcount` is that medical enrollment, else intake's enrolled count, else eligible or total as "estimate"; every band, tier, printed count, commission basis and Overview figure calls it |
| 25 | Rules with two homes (K19 vs M67; G.4, K.4 vs M30; L.5 B21; I.6, J22, H.6 vs M; F144) | `quotes.facts.enrollment_check`; `deals.contacts.primary`; `deals.rules.deal_type` over `opened_as`, frozen at the sale; `group_facts` calls `incumbent` |
| 26 | Plan order (G134 vs F43, E37; F49 vs J7) | Everyone uses `order.layout`; stop-loss keeps the order added (F49) until OQ13 |
| 27 | The 16-column cap (F50, F119, J3, D96) | One `room()`, counting a pair once; Rank goes through the star rule |
| 28 | Ask follow-ups (L4 vs I.6) | Review owns the ask predicates and wait; agenda imports them and keeps the carrier and decision waits |
| 29 | Counting open warnings (E91 vs M) | No SQL copy: stored counts, or the owner's one-query pass |
| 30 | Marking a whole document (E58, E86 vs M.6; L.6) | Owners keep `mark_values`; review adds `mark_document` and `confidence`, one transaction, in the lock order |
| 31 | Past deals (A28 vs G.4, L.6, K64, M.6) | `deals.rules.is_past` and `client_asks_open`; A28's deferral covers only the read-first screen |
| 32 | Two columns become one (D116, D87 vs F142, F61, J161) | One quotes merge service, also called by the reader's `combine`; `merge_plans` and `clear_line` are tools. Pairing is not merging: halves stay two plans (D-219) |
| 33 | Grid undo (F70, J74, E54, F71) | One undo stack in `src/grid/`; every value PATCH takes `expect` |
| 34 | Helpers built twice (C12, E29, H, K, J116; D114, J153; G, J, K PDFs; E99, K, G63; F93, J167) | One `documents/sheets.py`, `xlsx_safe.py`, `deals/pdfkit.py`, `log_access` and board exporter |
| 35 | Source entries (A31 vs D, E, F, G) | O.3.1's one spec; marks lapse inside `values.apply`; D's change set gains `line` |
| 36 | AI registry (D81 vs E, G, H, B39, C20) | O.3.3: every reader through `reading.py`; G drops forced tool calls; H's chunking is `ranges.py`; owner tools stage through `propose_changes` |
| 37 | Review asks (G-Q2, L.6, M; D44, G-Q9; B27; C.5, G34; B38, C33, L10, D29) | One `policy.floor`; an `on_client_upload` flag per reader (OQ89); review owns custom asks and the board; waiting change sets go to the owner's review |
| 38 | Shared frontend (D, E, F, J, L) | E's shared folders; Pages and pickers in `deal/proposal/pages/`; one bulk bar, key hook and undo stack |
| 39 | Stylesheets and tokens (A, D–M) | O.5: one port; parts list classes only; tokens pinned as L does (OQ10) |
| 40 | Lock order (M.6 vs L.6) | O.3.7; the portal save locks intake, census and questionnaire, then the link stamps |
| 41 | Caching (A27, E, I, M, F3, J107) | O.4; previews key on J's stamps; F3's stored deal stamp goes |
| 42 | Lost deals (A19, F124 vs B34, D71, G, H, K, L, M) | O.3.7's list; B34 changes to match |
| 43 | Facts (A.4, G, H, I–M) | `summary.facts(deal_ids)` everywhere; commission's viewer figures in `summary.card`; G's batched `summaries` waits for OQ2 |
| 44 | Quotes API (F.6 vs D, E, G–M) | O.2's quotes row, with `set_sold` (refuses lost deals) and `delete_plan` (refuses sold plans) |
| 45 | Member-data screen (D49, D52 vs the old app's D-225) | `screening.py` still runs at upload and stores `Document.screen`; reads leave flagged pages out only while `AI_MEMBER_DATA_SCREEN` is on, off by default (OQ22) |
| 46 | Census sends by contact (C27, C29 vs L67) | Dropped by default with L67 (OQ88); if kept, `CensusSettings.rules` stores each column's contact and slice 57 sends one link per contact |
| 47 | Stop-loss Binding Notes (G117 vs the chain) | The workbook lives in quotes (J166), left of questionnaire, so it reads the SIIA disclosure through `quotes.providers.disclosure_state` |

**Names** (the owner's name wins, else the one most parts use): `QuoteLayout`, `star_reason`, `Plan.codes`, `read_ref`, `read_value`, `pair_of`, `order.last` (not `next_sort_order()`), kind `stop_loss`, origin `relay`, `low` as a reason, `decided_at`, `Member.values`, `option_number`, `summary.facts`, `deal_state` (one grouped read), `asked_by_line`, `run_worker`, `recheck`, `DealAi.locked_by/at`, `useReviewHotkeys` with `keys.js`, `src/lib/findText.js`, `DocumentWindowPage`, `deal/shared/BuilderCard`, `FieldInput`, `CellInput`, one `advance(deal, user, stage, reason)`, quotes' `sold_changed`, proposals' `client_facts/`. Part letters are fixed in C32, C33 and C35 (Part L) and C36 (Part K).

**Endpoints** live under their owning app, one door per action: `ai/reads/`, `ai/recheck/`, `ai/locate/`; `<owner>/sources/` and `<owner>/marks/`; `review/marks/` and `confidence/`; `plans/as-quoted/` and `plans/pair/`; `questionnaires/` (plural); agenda's `journey/`; J's pages payload with formatted cells and `others`; `work-queue/` and `stats/`; the reader deep link `?claude=read&docs=…` (D3, I53).

**Dropped in one part, needed by another.** Priced versions stay, and the reader's matching skips copies and versions (F141). D94's automatic audit goes, with E's `via: "audit"`. D41's census door waits for the PHI gate, and C20's census turn tools become Defer (D111). The mapping assist sends column shapes only (D109 over C14). Documents shows the census roster (E-Q3 over D130). The quote-first door creates the deal first and lands on the Advisor (D43 over A14). Curation reads `quotes.presented()`, not `ProposalConfig.lines`. Per-deal Required and Waived stay (OQ17). Saved census filters reuse `SavedView` if OQ7 keeps it. Plan my day waits (I over A12); sparklines show real figures (I over A10); quote-first deals are never "skipped" (M over A24). `review_rules.origin_bucket` is added for M.

**Questions the parts answered differently** are asked once: OQ7, OQ8, OQ9, OQ13, OQ17–OQ22, OQ28, OQ32, OQ41, OQ42, OQ45–OQ47, OQ52, OQ53, OQ80, OQ86, OQ88–OQ90 and OQ97.
