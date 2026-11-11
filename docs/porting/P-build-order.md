# Part P — Build order

[← Porting plan](README.md)

> **Superseded for building by [plan.md §13](../../plan.md#13-build-order)** (slice 1, 2026-11-11), which is this part
> with Daniel's answers applied: the client lifecycle and client page (slices 6, 67, 68; OQ2, OQ101), staging (slice
> 69; OQ105), stop-loss reordering (OQ13) and slice 50 waiting (OQ6). Slice numbers 1–66 are unchanged.

**How to read this part**
- A slice is one app or one shared framework, rarely two. Daniel reviews and commits each slice before the next one is reviewed (plan.md §13).
- Every slice builds only in Part O's apps and folders and imports only to the left.
- **Needs** lists the slices that must be committed first; each points to an earlier slice. **Done when** is walked in the browser on a golden deal, after the slice's tests and lints pass (V.1). **Answer first** names the questions whose answers change the slice; every other question keeps its default, built in one place.
- Item ranges cover only Keep, Simplify and New rows. Sizes are relative (S, M, L, XL); an XL slice is reviewed in two sittings, backend first. Each slice's tests are in Q.9.

## P.1 Before slice 1
- **Commit the baseline.** Every 2Vantage app is untracked today, so no slice's change could be read on its own. Daniel commits M0–M6 first.
- **Fix the old commit the port follows: 891f1b3.** Two old-repo commits landed on 2026-11-11 while this plan was written. 7385bb3 committed the need-9 code (`plan_slots.py`, `plan_slot_tests.py`, `PlanPicker.jsx`, `ProposalPages.jsx`, `keyRows.js`) and D-224, so J.5 B20's rescue step is void and slice 14 ports from that commit. 891f1b3 added D-225, which turned the member-data screen off for every Claude read (OQ22). Later old-repo decisions are listed for Daniel before the slice that ports their area.
- **Scope and conventions.** Daniel answers OQ1–OQ9, or accepts their defaults.

## P.2 Golden deals
`seed_golden` lives in the `golden` app from slice 3 and builds every deal through services, with synthetic data only, from one JSON spec per deal. Slices extend these deals; no slice adds a private fixture. Each spec has a parity profile for the old app (Q.5). Stephanie signs a key before the slice that prices its deal: GD1 and GD2 before slice 7.
- **GD1 Golden Manufacturing** (built): three current medical plans with renewals; alternates from two carriers; a consolidation; plans bought together; two picks for one plan; dental and vision. Slice 15 adds a synthetic quote PDF, workbook and SBC; slice 33 a Florida Blue pair; slice 49 a variant, GD1-sold, with two sold medical plans (OQ12).
- **GD2 Golden Small Shop** (built): a one-plan small group.
- **GD3 Quote-first** (slice 13): no intake answers and no census. Medical starts with typed whole-line tier counts and ten alternates; a PEPM line prices from typed lives (F92). From slice 18 it carries unread synthetic files: a renewal packet that brings two current plans with renewals and printed per-plan counts, an alternate quote and an SBC. Its script has two checkpoints:
  - **A**: typed counts only; the packet lands and the counts are split; from slice 42 the Florida Blue 51+ form is started (52 enrolled); from slice 49 a sale is booked.
  - **B**: a 48-person census arrives, its elections naming both current plans, so the census takes over (F91), the band notice shows (G133) and the booking reads "Out of date" (H120).
- **GD4 Census by plan name** (slice 12): about 150 people with dependents and waivers; elections naming three current plans, one alias and an unmatched variant; a copy on Warner's template.
- **GD5 Stop-loss** (slice 36): level-funded medical with stop-loss and TPA quotes and lasers; the SIIA disclosure from slice 43.
- **GD6 Get to Market** (slices 38–59): full intake, contacts, coverage with in-force commission, BOR, a 60-person census, Florida Blue 51+ signed, the Warner route, and a client link answered and approved.
- **GD-Big** (tests only): 600 plans, 2,000 members, 200 links, 200 notes, 100 documents and 5,000 Activity rows.

## P.3 Phase 0 — Ground

| # | Slice | Needs | Builds | Done when | Answer first |
|---|---|---|---|---|---|
| 1 | PLAN · M | P.1 | plan.md rewritten from Parts A–Q: scope (§1.4), chain (§3.3), models, API, screens in the old look, the old file formats (§9), AI with the chat (§10), this part as §13, a shorter §15, and every open question in §16 with its default and slice. CLAUDE.md: the chain, the conventions OQ9 changes, the worker and Vitest commands, under 80 lines. No code | Daniel agrees with §1.4, §13, §15 and §16; the suite passes | OQ1–OQ9 |
| 2 | LOOK-1 · L | 1 | O.5's port: the class sweep, the cut into ≤300-line files and one manifest, the token pins, the two button fixes, Plex fonts, stylelint and the port-proof script | The port proof shows each sheet's files equal the old sheet minus the listed edits; every M1–M6 flow still works | OQ10 |
| 3 | PAR-1 · L | 2 | The `golden` app (seed, specs with parity profiles, keys with signature fields, root-conftest fixtures; moved from proposals). `tools/parity/`: the old app as its own Compose project, the tools image (LibreOffice, poppler), `old_loader.py` for GD1 and GD2. `browser/` with the Look lane and the generated hide list | GD1 and GD2 load into both apps from one spec, and the Look lane captures the old app's GD1 screens | — |
| 4 | LOOK-2 · L | 3 | AppShell (A6). DealShell with path tabs and an error boundary per tab (A20, A21, A26). The home header and Clients view (A7, A13), New client dialog, deal header with a `proposal` stage pill, Activity drawer and Documents v1. 2V's simplified Advisor and Proposal move onto old classes until slices 9 and 25 replace them. Every `*.module.css` and 2V's tokens go | The sign-in page, top bar and GD1's built screens pass Look with labelled differences only; every M1–M6 flow still works | — |

## P.4 Phase 1 — The Advisor without Claude

| # | Slice | Needs | Builds | Done when | Answer first |
|---|---|---|---|---|---|
| 5 | FND-1 · M | 1 | O.3.2's Activity, the revert endpoint and reverter registry, quotes' first reverter, Revert in the drawer (A34), `log_access`; O.3.1's source entry and `values.apply` (A31–A33) | On GD1, Revert restores a plan value; a second Revert says it was already undone; after a later edit, Revert is refused; a hand edit over a read value keeps ↗ | — |
| 6 | FND-2 · M | 5 | `advance` reloads and locks; `deals/rules.py` (`refuses`; `agent_name` as owner, then agency producer); `deals/carriers.py` (F14, K105); `AgencySettings.producer_name/npn`; `accounts.Profile` (A3, A4); the import-linter chain contract; Vitest | A lost GD1 refuses each `refuses` action with its sentence; the chain contract fails on an import to the right | — |
| 7 | ADV-1 · L | 3, 6 | quotes: O.2's Plan fields; `presented` and `room` (F119, J2, J3); `order.layout` (F120, J4); `slots`, `closeness`, `facts` (F121, F122). Services: stars with the cap, reason and auto-link (F50, F51); clearing the shortlist per line (F55); roles and links (F52, F53); move, swap, reset, `put_in_slot` (F43–F48); recommend within `room()`; `set_sold` refusing lost deals (F123). PATCH limited (F71). `quotes/math/` with `round_decimal`; both signals; `deal_state` in one grouped query. 2V's per-role order, membership list and carrier sort retire (F.5 #27–32) | On GD1 a 17th star is refused with a sentence; a starred quote made current loses its star and links; a rate edit moves nothing; GD1 matches its signed key | OQ11–OQ13 |
| 8 | ADV-2 · M | 7 | Soft delete and restore (F60); clear line (F61); `move_line` in place (F59); `copy_plan` with rates (F81); the one merge service (F142). A sold plan cannot be deleted | Deleting a current plan turns its renewal into an alternate, and Revert restores both; a plan moved to dental keeps its id; a copy keeps its rates | — |
| 9 | ADV-3 · L | 4, 8 | `src/grid/`. AdvisorTab with pills and line tabs (F1, F2, F5–F11); presets and sort (F31–F33, F36, F40, F41); ⇄ Transpose (F34, F35); chips (F62); edit mode (F68–F73); ticks and batch star (F57, F58); delete, clear and move on screen (F59–F61); the board exporter (F93, J98, J167) | GD1's board passes Look; Transpose keeps the header frozen and refuses above 60 plans; Excel keys and Ctrl+Z work; the export matches the screen | — |
| 10 | ADV-4 · M | 9 | Finder over name, plan number, carrier, network, type, codes and aliases, with "Also matches N on Dental" (F14–F17); budget select and "Monthly total ≤ $" (F18, F19); "N have no price yet" (F140); sliders, caps, hides and Claude's rule chips (F20–F27); saved board setups (F28) | On GD1 "UHC" finds UnitedHealthcare plans on every line; "Monthly total ≤ $45,000" hides the dearer plans and names those with no total | OQ7, OQ14 |
| 11 | INT-1 · M | 9 | intake: B.6's models, `form.py`, the one cleaner, `CurrentCoverage` (B14); `set_intent` as the only writer of `requested_lines`, with confirm and reopen (B16–B21, B23, B24, B32); `intake.providers` with defaults; `deals/comp.py`. quotes fills `quote_lines` and adds `facts.incumbent` (F144) and the "Off the proposal" chip (F13). The coverage card | On GD1, Shop it and Keep as-is show per line; a change after Confirm shows "Changed since confirmed"; the Advisor flags the kept line | OQ15 |
| 12 | CEN-1 · L | 11 | census: `fields.py`, `Member`, `CensusImport`, `CensusSettings`, `CensusFacts`. Read, reshape, map, apply and match with a dry run (C12–C17, C14's offline mapper only); validation (C21–C24); rollups by line and by plan name (C39–C46); fills `census_state`; the import door and MappingDialog (C15). Seeds GD4 | GD4's file imports through the mapping dialog; a re-import first lists who is added, changed, removed and kept; the Warner-template copy imports; tier counts equal a hand count | OQ16, OQ17 |
| 13 | ADV-5 · M | 9, 12 | `LineEnrollment`; `enrollment_for` (O.6 #24); source words (F86); the counts card with the split, and CensusNotice (F85, F88, F91); F87, F89, F90, F92, F98; `facts.enrolled_headcount` and `enrollment_check`; quotes fills `headcount`. Seeds GD3 | On GD3 every medical plan prices from typed counts; a second current plan names the plans that lost their price and opens the split; a census import re-prices them with "Priced from the census now · Keep my typed counts"; counts typed after the import win again | OQ18–OQ21 |
| 14 | ADV-6 · L | 13 | proposals: `pages.py` (the one splitter) and `GET proposal/pages/?line=`, with formatted cells and `others`. `deal/proposal/pages/` (PagesView, PlanPicker, PlanLinkPicker), ported from old commit 7385bb3 and mounted by the Advisor (F37–F39, F45, F46, F48, J5–J13) | On GD1, clicking a column name and picking a plan puts it in that slot with the slot's star and link; "Replacing:" groups a quote under its plans; "Several…" makes a consolidation | — |

## P.5 Phase 2 — Documents and Work with Claude

| # | Slice | Needs | Builds | Done when | Answer first |
|---|---|---|---|---|---|
| 15 | DOC-1 · L | 4, 5 | documents: kinds and buckets; O.2's fields, `protected` included; upload checks (30 MB cap, magic bytes, page count); archive and restore, refusing protected files; `screen` at upload (D52); `record_access`; deep links (E1–E8, E10–E18, E20–E24, E26–E32, E93–E99). `src/viewer/` without OCR; `sheets.py` and `look()`; `xlsx_safe.py` (D114). Synthetic files on GD1 | A value's ↗ opens the PDF page with the value boxed, or the cell in its Excel look; Remove archives a file, and "Show removed files" restores it | OQ22–OQ27 |
| 16 | DOC-2 · L | 15 | The ai core: `Job`, `DealAi`, the worker service, the reaper, the state endpoint and `useAiState` (A36, D105). `documents/locate/`, the `locate` job and quotes' hooks; "Check this file" (E59, E81–E84, D95) | "Check this file" runs with progress and Stop and survives `docker compose restart backend`; each ↗ then opens where the value was found, or says "not in the file" | — |
| 17 | DOC-3 · L | 9, 16 | `review_rules.py`; `Plan.flags`; quotes' `sources/` and `marks/`. The List view, file strip, bulk bar, keys and Undo (E34, E35, E47, E48, E52–E58, E85–E89, E92, D121, D122, D124, D126). The Advisor's flags chip and review strip (F63, F65, F67). Change history from Activity (E73, E74) | The strip reads "N AI values to review"; A, I and F mark values, and Undo restores them; the Advisor's amber agrees with the station | OQ28 |
| 18 | AI-1 · L | 13, 16 | `ai/client.py` (Messages API only); pricing, budgets and limits (D53, D99); `reading.py` and `ranges.py` (D46, D48–D51, D54–D62, D64, D65); quotes' reader modules, reading order (F138), codes (F143); the one read door (D39); the staged review card (D28, D31); the fake client, the corpus and the Eval lane | On GD3 a read of the renewal packet shows the staged card: two current plans and their renewals in printed order, with their per-plan counts unticked; nothing is written | OQ29, OQ30 |
| 19 | AI-2 · L | 18 | `read_apply` with Undo (D72–D75); counts landing (D67); D115, D117; the Re-read panel and staged banner (E75, E78, E79) | "Use this scan" lands GD3's packet and moves the deal to Quoting; accepting the counts prices both current plans; Undo removes the plans; an unchanged re-read writes nothing | — |
| 20 | AI-3 · L | 19 | The drawer and pill (D1, D3–D5, D8, D9); the File room and attach from anywhere (D13, D14, D16, D17); running and over-budget cards, strip and flash (D21–D24, D27, D34, D35, F112); landing by person (D71); Try again (D76); "＋ Add quotes" (F96, D37); the quote-first door (A14, D43) | From "I already have carrier quotes", dropped files create the deal and are read; an admin's read lands with Undo, a producer's waits for review; Stop keeps finished parts | OQ31 |
| 21 | AI-4 · M | 20 | `QuoteLayout` written at landing (D66, E94); the Advisor's "As quoted" (F42) and the Documents view (E42) | "As quoted" shows GD3's packet in the file's column order with its printed rows; unmapped rows are greyed, with their printed text | OQ32 |
| 22 | AI-5 · L | 17, 20 | SBC reads: design values only, never a new plan (D15, D38, D47). Re-checks applied by a person (D40, D93, E76, E77, E80, F66). `split.py` (D116; halves stay two plans); the merge tool (F142) | "Attach SBC…" stages design values; a value the SBC disagrees with is flagged; re-check approvals apply only when a person applies them | OQ33 |
| 23 | DOC-4 · M | 9, 17 | The station grid on `src/grid/` (E36–E41, E50, E51, D123); Find with aliases (E60–E64, D127); Review mode and edits (E65–E68, D125, D129) | In Review mode a click jumps the file to its value; Ctrl+F walks every match | — |
| 24 | AI-6 · L | 10, 11, 20 | Chats (D7, D19, D25); agent turns that stage plan changes (D77–D86, D88, D90–D92); `set_board` (D80, F108–F110, F114) and `clear_line`; GuidanceBox writing through intake (D6, D98); budget and lock (D100, D104, F113); carrier notes (D119) | "Show PPOs under $40,000 a month" sets the board; a direct person's "delete the duplicate Aetna plan" changes the table, with Undo | OQ34 |

## P.6 Phase 3 — The Proposal

| # | Slice | Needs | Builds | Done when | Answer first |
|---|---|---|---|---|---|
| 25 | PRO-1 · XL | 11, 14 | `ProposalConfig` reshaped; `set_config` merged by path under a lock; card marks (J18–J20); `ready` and `checks`. quotes' `option_number`, `labels.numbers`, `stamp_option_numbers` and `client_name` (J14, J159). The builder shell and line cards (J16, J17, J23, J27–J31, J47–J62), with the EnrollmentStrip (J48). 2V's selection and preview retire | On GD1 two picks for one current plan each show their own change; a kept line needs no pick; predicted option numbers match Pages | OQ35–OQ37 |
| 26 | PRO-2 · L | 25 | Output and page switches with their ledger (J38, J39, J41, J42); plan experience (J45); the coverage card (J46); summary and renewal blocks (J64–J66); next steps (J67). Markets checked (J63), through a new `rfp` app holding only `RfpRequest` and `asked_by_line()` | Every card saves and marks itself done; Markets checked lists the quoting carriers, with "no RFP sent" | OQ38 |
| 27 | PRO-3 · L | 15, 25 | The workbook: the sheet model with the old formulas, the tabs (J145–J154), the writer through `xlsx_safe` (XlsxWriter 3.3.0); downloads (J24, J97, J104); the Recalc lane | The file opens in Excel with the old look; totals match GD1's key three ways | OQ39–OQ41 |
| 28 | PRO-4 · L | 27 | The Export viewer in the Advisor (F3, F136, J105, J107, J112) with the workbook view (J116–J118); the Fidelity lane | The Excel chip pages through every tab as the file shows it; previews write nothing; Fidelity shows no unexplained difference | — |
| 29 | PRO-5 · XL | 26 | `story/`, `layout/` and `paint/pdf.py` (J122–J140 except J129; J142, J165; reportlab 4.2.5); the `FirmPages` and `TeamMember` models and stock covers, edited in Django admin until slice 34 | GD1's Client PDF has the old Presentation pages, type floors and "(continued)" pages | — |
| 30 | PRO-6 · M | 28, 29 | The deck view, slide rail, fit report, notes, Paper, downloads and Print… (J108–J111, J114, J115, J120) | The PowerPoint and PDF chips page through the slides; Paper shows the Letter frame; Print… opens the print dialog | — |
| 31 | PRO-7 · L | 29 | `paint/pptx/`, replaying the recorded frames (J141; python-pptx 1.0.2) | The .pptx opens with the old master, native charts and notes, slide for slide like the PDF | — |
| 32 | PRO-8 · L | 16, 30, 31 | The Proposal tab: the board in presented mode (J70–J94); the packet card (J96–J101); Issue as an `issue` job with stored, protected files (J102, J103) | Issue makes v1 with three stored files and moves the deal to Proposal; v2 leaves v1's bytes unchanged; an uncovered shopped line is refused with its sentence | — |
| 33 | PRO-9 · M | 32 | The D-219 fold: `Plan.pair_of`, `room()` counting a pair once, "⧉ One column with… · Split" on Pages (J15, F137), the fold in the three files, the `split_plan` check. Adds the pair to GD1 | On GD1, 5182 and 5183 print as one column on Pages and in the PDF, PowerPoint and workbook, and its total equals the pair's package; Split restores two | OQ42 |
| 34 | PRO-10 · M | 29 | `CoverImage` uploads, pictures, team, the firm-pages drawer and templates (J32–J35, J43, J68, J155); `documents/images.py` | An uploaded cover and a team member print on the PDF and the PowerPoint | — |
| 35 | ADV-7 · M | 9 | Priced versions (F76–F78, F80–F84) | "5% off" previews its total, and commits a copy behind its original that prices the same people | OQ7 |
| 36 | ADV-8 · L | 13, 27 | Stop-loss analysis (F98–F107) with saved settings (F29) and its five-tab workbook (J166), whose Binding Notes read `disclosure_state` (G117). Seeds GD5 | The verdict cards rank lowest first; the basis names its source; the laser what-if is never saved | OQ43 |
| 37 | AI-7 · M | 24, 33 | Rank through the star rule (D36, D96, D97, F111); the tools `set_table_note`, `set_rows` (J160, D120) and `pair_plans` (J161) | With guidance written, Rank stars 5–8 plans with reasons within `room()`, and without it says "Add client guidance first"; asked, Claude pairs two halves and writes a table note, each with Undo | OQ44 |

**→ Milestone 1 (P.10).**

## P.7 Phase 4 — Get to Market

| # | Slice | Needs | Builds | Done when | Answer first |
|---|---|---|---|---|---|
| 38 | FND-3 · M | 6, 25 | M's O1: `Contact` and `contacts.primary`; `Note` (A37); client archive and the Archived page (A13, A18); `deal_size`, `opened_as`, `agent_of_record` (first in `agent_name`), `set_owner`; `rules.deal_type`, `client_asks_open`, `is_past`; the builder's RENEWAL chip (J22). Client DELETE answers 405; `mark_lost` answers 409 on a lost deal | Archiving a client hides it everywhere, and Restore brings it back; deleting a pinned note can be undone; a deal opened as a renewal shows RENEWAL | OQ45–OQ49 |
| 39 | INT-2 · L | 11 | The intake form (B1–B11, B36); budget hints on the Advisor (F139) | On GD6 all four cards fill by keyboard; a bad FEIN shows its message; "Client target $X/mo · Apply" appears on the Advisor | OQ50, OQ51 |
| 40 | INT-3 · L | 38, 39 | Contacts, the checklist with COBRA, BOR, readiness and Mark as marketed (B13, B25–B31, B33–B35) | GD6 reaches "Ready to market"; Mark as marketed records the skipped items and can be undone | OQ52, OQ53 |
| 41 | CEN-2 · L | 12, 17 | The roster grid on `src/grid/` (C1–C10, C38); COBRA through intake (C25) | Flagged errors are fixed with Excel keys; the blank template re-imports cleanly | — |
| 42 | QST-1 · XL | 13, 40 | G's Q1 and Q2 (G1–G55, G124, G125, G133, G134, G136); `quotes.facts.group_facts`; questionnaire marks (E103); fills `questionnaire_items` | On GD6 Florida Blue 51+ is chosen by the band, with one plans row per current plan; the officer's signature locks the form | OQ54–OQ56 |
| 43 | QST-2 · L | 15, 42 | G's Q3 (G56, G57, G59, G61–G67, G110–G113); the signed copy filed as a protected Document (G135); fills `disclosure_state` (G117) | Stamped values sit inside their boxes; the signed copy is filed and refuses Remove; a stale check is refused; GD5's Binding Notes read "SIIA disclosure signed" | OQ57, OQ58 |
| 44 | RFP-1 · L | 26, 40 | K1–K33; the commission text from `AgencySettings.default_commission` | The band comes from the one headcount; the cross-check names the intake, census and Advisor counts; carrier picks save | OQ59, OQ60 |
| 45 | RFP-2 · XL | 41, 44 | K34–K42, K79–K98, K105–K108, K124; rfp fills `carrier_required` | The Warner, Aetna, Angle and UHC files open in Excel with each carrier's own formatting | OQ61–OQ64 |
| 46 | RFP-3 · L | 43, 45 | K43–K78, K99–K104, K109–K123 | A draft `.eml` opens in Outlook; the first Sent tick moves the deal to Quoting; Markets checked lists who was asked | OQ65–OQ69 |
| 47 | PHI · M | 46 | plan.md §11 and R3.9: Microsoft 365 sign-in; the access-log check; the key confirmed under the BAA; the staging canary scan | Staff sign in on staging with firm accounts; the §11 checklist is signed | OQ29 |

## P.8 Phase 5 — The rest

| # | Slice | Needs | Builds | Done when | Answer first |
|---|---|---|---|---|---|
| 48 | COM-1 · L | 11, 38 | H1–H24, H95–H102, H106, H113, H116, H121; rfp's request text switches to `requested_rates` | A 60/40 split previews and saves | OQ70, OQ71 |
| 49 | COM-2 · XL | 32, 48 | H25–H58, H68, H108–H112, H114, H115, H120, H124, H125; GD1-sold | Mark as sold opens BookingSummaryModal; un-selling voids the record; GD1-sold books both plans | OQ72–OQ77 |
| 50 | COM-3 · XL (only if OQ6 says yes) | 16, 49 | H59–H93, H103–H105, H123; firm statements on a nullable `Document.deal` | A statement is entered or read, posted, and reconciled against the records | OQ6, OQ78, OQ79 |
| 51 | AI-8 · L | 40, 41, 47 | D29, D41, D42, D109, D110, D112, D134, B39, B40, C11, C19; `CensusImport.job` | A synthetic PDF roster becomes a staged census import, handed to the Census tab; the mapper sends column shapes only | — |
| 52 | QST-3 · M | 43, 51 | G's Q6 (D113, G99–G102, G106–G109) | A synthetic filled form is staged, and never applied to a signed form | — |
| 53 | REV-1 · L | 40, 41 | L's V1: models, rules, link services, a minimal New link, the Waiting lane, `summary.facts` and the tab's own counts (L1, L2, L28) | A link is created, copied and revoked; the Waiting lane and the pills count it | OQ80–OQ83 |
| 54 | REV-2 · XL | 47, 53 | V2: the portal for intake, census and documents (B43, C35); "This link has moved" for old `/b/` links (L136) | A client fills answers and uploads files on a phone-sized screen | OQ84–OQ86 |
| 55 | REV-3 · L | 46, 54 | V3: queues, approvals, section bars, the rfp export-check provider (B38, C28, C32, C34) | An approved answer is stored with origin `client` | — |
| 56 | REV-4 · L | 55 | V4: the tray with its count and destination (L49), notes, threads, request page (B12) | Asks gathered in the tray go out on one link | OQ87 |
| 57 | REV-5 · L | 56 | V5: builder, Ask card, settings card, People & links, edit mode, comment margin (B37, C27, C30); census filter sets (F30) if OQ7 keeps them; the contact partition (C29) only if OQ88 keeps it | The Ask card changes an open link | OQ88 |
| 58 | REV-6 · L | 43, 57 | V6: questionnaires in review and on the portal (G68–G81, G83–G90, G92–G98) | The client answers the form and signs as the officer | — |
| 59 | REV-7 · M | 51, 58 | V7: reads started by client uploads, then the receipt (D44, D45, L125, L135) | A client's census file becomes a staged import that staff apply | OQ89 |
| 60 | AGD-1 · L | 38, 49, 59 | I's AG1: steps (the commission step included), marks, tasks and the deal's Agenda tab | GD3's next step reads "Add the census, or type enrollment in the Advisor"; Later holds a step until its day | OQ90–OQ93 |
| 61 | AGD-2 · L | 60 | I's AG2, with A9–A12, A23 and A24: the `journey/` read for the shell (badges and meters); the Work queue, New clients and stats | The shell shows the stepper and badges; the dashboard's numbers are real | OQ94, OQ95 |
| 62 | OVW-1 · L | 49, 61 | M's O2: the Overview shell, header, banners, tiles and stepper, with the renewal-offer chip (M20); deals open on the Overview | The block order matches the old Overview | OQ96 |
| 63 | OVW-2 · L | 58, 62 | M's O3 and O4: Card 1, Card 2, feed, notes, side cards | Every Card 1 control writes through its owning app | — |
| 64 | OVW-3 · M | 22, 63 | M's O5: review's `confidence` and `mark_document`; the re-check panel | Confirm all for one document can be undone | — |
| 65 | DOC-5 · M | 39, 41 | E43–E45, D130; the pop-out window (E69–E71, D128); browser OCR for scanned pages (E25) | The census file opens beside its roster; a scanned SBC page highlights its values; the pop-out follows the keys | OQ97–OQ99 |
| 66 | AI-9 · S | 20 | Voice input (D20) | The microphone dictates into the composer | — |

**→ Milestone 2 (P.10).**

## P.9 Parallel work and risks
**Parallel work.** Review stays one slice at a time. A slice may be built ahead on its own branch (a git worktree) and rebased when its Needs are committed. After a rebase, the branch deletes its unmerged migrations and makes them again, so migration numbers never clash.
- After slice 1: the look and parity (2–4) beside the foundation (5–6).
- After 4 and 6: the Advisor lane (7–10) and documents (15–16).
- After 9: intake and census (11–12), then the Documents and Claude lane (17–24) beside the Advisor lane (13, 14). Joins: 17 needs 9; 18 needs 13; 24 needs 10 and 11.
- Phase 3: the workbook (27–28) beside the PDF (29), then 30, 31 and 34; 35 and 36 whenever their Needs are in; FND-3 (38) once 25 is in.
- Phase 4: 38 beside 41; the questionnaire after 40; rfp joins both.
- Phase 5: commission (48–50), the readers (51–52) and review (53–59) in parallel. Agenda and Overview come last, because they read every app.

**Risks to this order.**
1. Real carrier files wait for OQ29. Slices 18–24 are built on synthetic files; the golden-deal trial (OQ31) runs once the key is confirmed.
2. Slices 27–31 port the largest old files, about 2,000 lines each.
3. Agenda (60) relies on the stored counts of slices 12 and 17.
4. The cascade breaks if a sheet is imported out of order: one manifest, the port proof, stylelint and the Look lane guard it.
5. Until slice 61 the shell has no stepper or sidebar badges; Milestone 1's Look labels mark them "pending slice 61". The Review tab has its own counts from slice 53.
6. The old app keeps changing: two commits landed while this plan was written. P.1 pins the commit the port follows.
7. The old loader is real work, because the old app stores one row per value. Each golden deal adds its part in the slice that seeds it.

## P.10 Milestones
**Milestone 1 — the Advisor and the Proposal (after slice 37).**
- Gates A and B (V.2) on slices 1–37: GD3, then GD1, walked once as an admin and once as a producer, need by need.
- Priced versions, stop-loss, Rank, the pair fold, the builder cards and templates work. The 600-plan budget and `-m recalc` pass.
- Not yet built: contacts and notes (38), intake budget hints (39), the questionnaire, the asked carriers on Markets checked (46), booking on a sale (49), the portal, and the stepper (61).
- Then Gate C, Stephanie's walk (the old M9), on plan data and typed counts.

**Milestone 2 — the full MVP (after slice 66).**
- GD6 works end to end: intake reaches Ready; the census is imported and fixed; the questionnaire is signed; the packet and drafts are sent (Quoting); a client answers on the portal and staff approve; quotes are read with Claude; the Advisor; the Proposal is issued; the plan is sold and booked.
- Agenda and Overview are right at every step. The quote-first deal is never shown as "skipped".
- Gates A, B and C run again, because slices 38–66 change shared code (headcount, booking, journey). The PHI gate is passed, so Gate C may use a census.
- The speed budgets and `-m recalc` pass. No file is over 300 lines except data modules, and no test reads source. The class-usage sweep removes unused CSS.
- Left out unless Daniel says otherwise: the ledger (50), renewals, the client page, the status report, Unleashed, the share link, task mode and Classic.
- Cutover follows OQ100.

**Critical files for the first slices:** c:/Users/fooba/OneDrive/desktop/Vantage_all/2Vantage/plan.md · c:/Users/fooba/OneDrive/desktop/Vantage_all/2Vantage/CLAUDE.md · c:/Users/fooba/OneDrive/desktop/Vantage_all/2Vantage/deals/activity.py · c:/Users/fooba/OneDrive/desktop/Vantage_all/2Vantage/deals/values.py · c:/Users/fooba/OneDrive/desktop/Vantage_all/2Vantage/quotes/models.py · c:/Users/fooba/OneDrive/desktop/Vantage_all/2Vantage/proposals/golden.py
