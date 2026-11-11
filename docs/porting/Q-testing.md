# Part Q — Testing approach

[← Porting plan](README.md)

## Q.1 What counts as proof
- **Figures** are right when they equal an answer key worked out outside the app and signed by Stephanie (plan.md §12.6). Every other test is regression.
- **Screens and client files** are right when they match the old app on the same synthetic deal (its parity profile). Any other difference is listed, tied to the plan item that causes it, in a register Daniel signs.
- **Rules** are right when a table-driven test of the pure function covers every row, and one service test shows that the screens and files call that function, not a copy.
- **Behaviour only.** Tests call services, endpoints and pure functions, and read generated files back. No test reads source, CSS or docs; lint scripts may (the chain contract, stylelint, the CSS port proof).

## Q.2 Lanes

| Lane | What it proves | Command | When | Budget |
|---|---|---|---|---|
| Fast | rules, services, endpoints, the Q.3 contracts, golden keys, recorded AI reads, canaries, query scaling | `docker compose exec backend pytest` (one app: `pytest quotes`) | every change | ≤60 s in all; ≤10 s per app |
| Front | Vitest on pure modules, ESLint, build | `npm test`, `npm run lint`, `npm run build` | frontend changes | Vitest ≤10 s |
| Lint | ruff, `makemigrations --check`, the import-linter chain, stylelint, the CSS port proof | `ruff check .`, `lint-imports`, `npx stylelint` | every change | ≤30 s |
| Recalc | a LibreOffice recalculation equals the keys | `pytest -m recalc` (LibreOffice from the tools image) | workbook slices; each release | ≤3 min |
| Fidelity | old and new files compared (Q.5) | `python tools/parity/files.py --deals all`, in the tools image | painter slices; each release | ≤10 min |
| Look | old and new screens compared, by pixels and computed style (Q.5) | `npm --prefix browser run look -- --screens <key>` | UI slices; each release | ≤15 min |
| Walk | each need and each "done when", scripted in Chrome | `npm --prefix browser run walk -- --need <n>` | UI slices; nightly | ≤10 min |
| Perf | time and size budgets on GD-Big (Q.7) | `pytest -m perf` | slices that touch hot reads; weekly | ≤5 min |
| Eval | live reads of the synthetic corpus, scored against keys (Q.6) | `manage.py reader_eval --set all` | model, prompt, schema or merge changes; monthly | ≤30 min, about $20 |

- Add pytest-xdist when the serial Fast run passes 45 s; the 10 s per app still holds.
- Golden deals are built once per test module by root-`conftest.py` fixtures, under `django_db_blocker`; app tests never import `golden`. Tests that write use factory deals.
- A socket guard lets tests open only the database socket; `settings_test.py` blanks the API key. Artifacts go outside the OneDrive-synced repository.

## Q.3 Contracts every app passes
Shared helpers live in the root `conftest.py`; each app supplies a small table.
1. **Write path.** A changing call locks its row, writes one Activity row with before and after, and returns only what changed. The same call again changes nothing: not the value, the source, `updated_at` or Activity. Revert restores the earlier value and is refused after a later write to the same key. Each app lists its key-only areas (census rows, sensitive questionnaire slots, lasers); their Revert refuses with a sentence.
2. **GETs write nothing.** A sweep walks Django's URL registry at runtime, calls every GET with golden ids and captures the SQL. Only the portal's first open and the `downloaded` and `viewed` rows may write. A URL with no sample arguments fails the sweep.
3. **Permission matrix.** Each app keeps a table of endpoint × actor → status code. Actors: signed out, producer, deal owner, admin, `claude_direct`, commission tiers none, own and all, a portal link with and without a PIN, and a staff session on the portal. An endpoint with no row fails; a write without CSRF answers 403.
4. **Query scaling.** Every list or summary read runs the same number of queries at two sizes (1 and 10 deals, or 10 and 600 plans). It never pins a number.
5. **Quote-first.** Every module that reads enrollment, headcount or readiness has a GD3 test at checkpoint A (typed counts only, including a line split across two current plans) and at B (the census arrives).
6. **Canaries** as in Q.8.
7. **Clock.** Date rules hold at 21:00 Eastern.
8. **Concurrency.** Each family of locking services has a two-thread test: writes to different keys both survive; racing at a cap leaves the cap; a review beside an apply never deadlocks.
9. **Stored counts.** `CensusFacts` and `flags` equal a fresh rebuild after every service.
10. **Existing 2V tests.** `deals/tests/test_platform.py` pins 27 lines and 96 fields, against rule 9; it should check membership instead. `proposals/tests/test_proposal.py` pins the carrier sort that slice 7 retires; slice 7 rewrites it.

## Q.4 Golden deals and keys
- The deals are in P.2 and live in the `golden` app.
- A key is a spreadsheet or a hand count, never the app's own output. It carries `checked_by`, `checked_on` and `method`, and changes only with Stephanie's agreement. GD1's and GD2's keys, built in M3–M6 but never signed, are signed before slice 7; each later key before the slice that prices its deal.
- What the keys pin:
  - GD1: per-plan monthly, annual and change; packages; the recommendation; the presented set; the page split; option numbers; finder and budget results; the slot order after scripted picks; the pair's column; expected revenue and shares; GD1-sold's two booked plans.
  - GD2: one-page outputs; PEPM commission; the small-group band.
  - GD3 A: totals from typed counts; the PEPM line from typed lives; the split's per-plan totals; borrowed counts; both bands; Agenda's lead step; QuoteLayout's columns and rows.
  - GD3 B: the census takeover, Keep or Switch (G133) and "Out of date" (H120).
  - GD4: tier counts per plan, by hand; counts inherited by renewals and quotes; the consolidation sum; the 65+ count.
  - GD5: MAL, attachment, laser liability, % to claims, the verdict order, the five-tab workbook, Binding Notes.
  - GD6: readiness; band and route; printed counts; the packet's file list; carrier-file cells; questionnaire PDF values; Agenda and Overview at each step.
- Checked three ways: the app's figures, the workbook's stored results and `-m recalc` each equal the key. The PDF and PowerPoint, read back as text, print each key figure in its plan's row.
- Before the slice that prices a deal, the old app runs the deal's parity profile once; a disagreement is fixed in whichever app is wrong.

## Q.5 Parity with the old app
**Setup (slice 3).**
- `tools/parity/` runs the old app (Django 4.2) as its own Compose project: code mounted read-only, its own database and media, an internal network and a dummy AI key.
- One tools image (LibreOffice, poppler and the Python readers) recalculates, rasterizes and reads back both apps' files.
- 2V pins the old writer versions (reportlab 4.2.5, python-pptx 1.0.2, XlsxWriter 3.3.0) in the slices that add them.
- Each golden spec has a parity profile that leaves out what the old app cannot express, such as census by plan name (C41). 2V loads it with `seed_golden`; the old app loads it with `tools/parity/old_loader.py` through `manage.py shell`, writing its one-row-per-value model. Slice 3 builds the loader for GD1 and GD2; each slice that seeds a deal extends it.

**Files (from slice 27).**
- Compared: the old `presentation-workbook/`, `proposal-pdf/`, `proposal-deck/` and `proposal-paper/` downloads against 2V's `proposal/files/{xlsx,pdf,pptx,letter}/`, plus carrier files, questionnaire PDFs and the stop-loss workbook. Dates, version and Draft stamps, ids and authors are masked on both sides.
- Exactly equal: workbook sheets, merges, panes, validations, print setup, and per cell the value, formula, number format, font, fill and border; PowerPoint slides, layouts, every run's text and font, charts and their series, notes; PDF pages, fonts and words in reading order.
- Tolerances: column width ±0.5 character; row height ±0.75 pt; shapes and word boxes ±0.5 pt; page images ≤0.05% of pixels at 110 DPI.

**Screens (from slice 3).**
- `browser/` drives the installed Chrome through `playwright-core`, as `devtools/e2e/_lib.mjs` does. It captures about 70 screen states (each tab on GD1 and GD3, empty states, PlanPicker, BookingSummaryModal, the check modals, the four export views, the portal at 390×844, the dashboard) at 1440×900, plus 1280 and 1920 for the workspace.
- Determinism: a fixed clock, no animation, fonts ready before capture, masked dates; AI states come from staged recorded jobs.
- A harness-only sheet hides what the plan drops on the old screens. It is generated from `browser/look/dropped.yaml`: one entry (item ID and selector) per Drop or Defer row with visible UI, seeded from the X.3 tables (for example the walkthrough buttons F135, J82, K5, E49 and M12; Classic and Share, J25, J26 and J36; the status-report button, M95; Plan my day, A12).
- Comparison: pixelmatch at threshold 0.1, where "same" means at most 0.02% of pixels differ; plus the order of `bnf-*`, `bb-*`, `gk-*` and `rr-*` classes, and the computed font, colours, borders, radius, padding and box (±1 px) of key selectors.

**Judging.** Each difference is a match, within tolerance, intended, or unexplained. An intended difference is listed with its item in `tools/parity/intended.yaml` or `browser/look/accepted.json`; an unexplained one fails the lane. Daniel signs each label once; a changed image is judged again. These are acceptance lanes, not suite tests (plan.md §12.4). They end when the old app is switched off, and the last approved images seed J.6.11's optional `-m look` job.

## Q.6 AI reader tests
**In the suite.**
- `ai/testing.py` replays responses keyed by reader, file hash and page range. An unknown key fails with "record it"; it never calls out.
- The corpus generator writes each synthetic file with its perfect response, plus named faults: "$512.34*", a missed renewal link, an invented plan, a blank cell, truncation, refusal, a silent stream and a cancel mid-range. It includes a two-current-plan renewal with printed per-plan counts and a Florida Blue pair.
- Recorded reads carry their model, date and schema version; the recorder refuses files outside the corpus manifest.
- Request-side checks on the fake client's log: Messages API only, with no beta headers; structured output and 128k `max_tokens`; prompt and schema identical across deals; header-only pages absent, and flagged pages absent only with the screen switch on; the mapping assist sends shapes only, and census context counts only.

**Eval (opt-in).** `ai/eval/` invents carriers, plans and rates, so every key is known by construction. It has a tuning set and a held-out set; the report holds counts only, and the command exits 1 under any threshold. The first run, in slice 18, informs OQ31.

| Metric | Tuning | Held-out |
|---|---|---|
| Plans found (precision, recall) | 100% | ≥95% |
| Roles, renews, replaces | ≥98% | ≥98% |
| Printed column and row order exact (need 3) | 100% | ≥95% |
| Rate cells exact to the cent | ≥99.5% | ≥99.5% |
| Wrong rate with no flag | ≤0.2% | ≤0.2% |
| Design values after house formats | ≥97% | ≥97% |
| Value written where the key is blank | ≤0.5% | ≤0.5% |
| SBC creates a plan | never | never |
| Cost against the estimate | ±30%, never over the $3 cap | same |

## Q.7 Performance budgets

| Read | Fast-lane rule | Perf budget on GD-Big |
|---|---|---|
| Advisor comparison | same queries at 10 and 600 plans; compact flags | 400 plans: ≤2 MB, ≤1.7 s. 600 plans: ≤3 MB, ≤2.5 s (old: 3.78 MB) |
| `deal_state`, pages, plan lines | one grouped query | ≤300 ms |
| Export preview | writes nothing | one workbook tab ≤1.5 s on 236 plans (old: about 7 s); deck ≤4 s |
| Overview, confidence, journey | fixed queries | ≤300 ms; journey ≤100 ms |
| `summary.facts`, work queue | same queries for 1 and 50 deals | 300 open deals ≤1 s |
| Census page and rollup | one aggregate | ≤300 ms with 2,000 members |
| Issue job | — | xlsx ≤3 s, PDF ≤6 s, pptx ≤8 s |

In the browser, the Advisor's first table paint is ≤1.5 s with 400 plans, and rows are windowed above 150 plans (F40).

## Q.8 PHI and client safety
- **PHI canaries.** Unique strings go into every PHI field of GD4, GD6 and the portal flow: names, SSNs, birth dates, addresses, lasers, medical answers and PHI file names. None may appear in Activity (`changes` included), Job steps, errors and results, chat messages, DEBUG logs, error bodies, URLs, `Content-Disposition` names, non-PHI payloads, or AI requests sent before the gate. The tests take the PHI kinds from `documents/kinds.py`.
- **Logging.** Every PHI download writes one `downloaded` row with the document id and leaves "Last updated" alone. Portal paths are not logged. Responses are `no-store`, and payloads are allowlists.
- **Client-safety canaries** go into `star_reason`, `client_guidance`, internal notes, document names, review marks, lasers, commission figures and birth dates. Every client file is read back (xlsx cells, comments, names, validations, headers and properties; pptx shapes, notes, layouts and charts; PDF text, metadata and links), and none may appear. This pins H125 and J.4 together.
- **Staging gate (slice 47).** After a scripted walk with the canary census, a log query finds no canary.

## Q.9 Tests for every slice
Every slice also passes the Q.3 contracts and the Fast, Front and Lint lanes.

| Slice | Tests must pin | Golden | Extra lanes |
|---|---|---|---|
| 1 | nothing new; the suite stays green | — | — |
| 2 | the port proof; stylelint refuses unknown properties | — | — |
| 3 | one spec loads the same deal into both apps; fixtures build each deal once | GD1, GD2 | Look |
| 4 | old tests find elements by role and text | GD1 | Look, Walk (M1–M6) |
| 5 | revert per key, once, 409 after a later write, refused for key-only rows; first-before and last-after; the `values.apply` table; no PHI in `changes` | GD1 | — |
| 6 | the `refuses` table; `advance` forward only, under a lock; the chain contract | GD1 | — |
| 7 | `presented`, `room`, `order.layout`, `slots` tables; concurrent stars leave 16; PATCH ignores role and star; lost deals refuse Sold | GD1, GD-Big | Perf |
| 8 | soft delete and revert; `move_line` keeps the id and refuses in words; copies keep rates; a sold plan cannot be deleted | GD1 | — |
| 9 | Vitest for `gridKeys`, `sort` and the undo stack; the export equals the payload; the transpose limit | GD1 | Look, Walk (need 10) |
| 10 | Vitest for `finder` (aliases) and `filter` (monthly total, no price); `clean_config`; another person's private setup answers 404 | GD1 | Walk (needs 4, 5) |
| 11 | intent round trip; confirmation lapses; `requested_lines` changes only through `set_intent`; provider defaults | GD1 | Look |
| 12 | importer, pivot, matching, validation and rollup tables; `CensusFacts` equals a rebuild; no samples stored | GD4 | — |
| 13 | every `enrollment_for` step; the arrival rule both ways; borrowing; the split prompt; the headcount order; an unchanged save writes nothing | GD3 A/B, GD4 | Walk (need 6) |
| 14 | splitter cases; replace, swap, add beside; the recommendation lapses; Vitest for `pageRows` | GD1, GD3 | Look, Walk (needs 8, 9) |
| 15 | accept lists, magic bytes, archive refusals by `protected`, bytes removed after commit, PHI rows; the screen stored, applied only with the switch; `look()`; `xlsx_safe` | GD1 | Look |
| 16 | the claim race; one job per deal and lane; the reaper; cancel; locator states; the state GET writes nothing | GD1 | — |
| 17 | every mark action × prior state; one row with no values, reverted once; `flags` equal a rebuild | GD1 | Look |
| 18 | D.6's reader list; reading order; per-plan printed counts proposed unticked; request-side checks | GD3 | Eval (first run) |
| 19 | typed values untouched; Undo refusals; an unchanged re-read writes nothing | GD3 | Walk (need 1) |
| 20 | landing by person, lock and lost deal; mixed-send order; cost cap and Run anyway | GD3 | Look, Walk (need 1) |
| 21 | order from `QuoteLayout`; unmapped rows never enter values; no printed text for PHI | GD3 | Eval, Walk (need 3) |
| 22 | SBC rules; re-check approvals carry the person; "5182 / 5183" halves stay two plans | GD3 | Eval, Walk (need 2) |
| 23 | Vitest for `findText`, `selectionRange`, `pdfFind` | GD1 | Look |
| 24 | `set_board` writes nothing; `clear_line` stages; string tool inputs parsed; guidance writes through intake | GD1 | — |
| 25 | concurrent config writes; marks cleared by their card; `ready` and `checks` tables; kept lines never block; predicted numbers equal stamped ones | GD1, GD3 | Look |
| 26 | summary-block tables; `why_for`; `asked_by_line` with no sends | GD1 | — |
| 27 | read-back equals the sheet model; stored results equal the key; the formula guard; client canaries | GD1–GD3 | Recalc, Fidelity |
| 28 | `look(write(model))`; previews write nothing | GD1 | Fidelity, Walk (need 11) |
| 29 | layout and story cases; type floors; firm pages print nothing until written; client canaries in PDF text | GD1 | Fidelity |
| 30 | previews write nothing; paper scale; Vitest for `printPdf` | GD1 | Fidelity, Walk (need 11) |
| 31 | each text box equals its recorded frame | GD1 | Fidelity |
| 32 | Issue refusals; stamping under the lock; the build job; protected files; v1's bytes unchanged | GD1, GD3 | Walk (need 12) |
| 33 | the pair's total equals `package()`; it counts once against 16 and keeps the first plan's number; working screens show both | GD1 | Fidelity, Walk (need 12) |
| 34 | images re-encoded, metadata stripped | GD1 | Look, Fidelity |
| 35 | the dry run equals the commit; no auto star on an unstarred line | GD1 | — |
| 36 | stop-loss math; the punchline; lasers never in Activity; Binding Notes from the provider | GD5 | Recalc, Fidelity |
| 37 | skips curated lines; stays within `room()`; needs guidance; tools write with Undo | GD1 | — |
| 38 | archive; 405; `mark_lost` 409; `contacts.primary`; note undo; `deal_type` frozen; agent of record first | GD1, GD6 | Look |
| 39 | visibility and validation tables; one cleaner; a GET creates no row | GD6 | Look |
| 40 | tiers from the headcount provider; the band at 50 and 51; waivers; skipped items recorded; BOR | GD3, GD6 | Look |
| 41 | a PATCH returns only the changed member; template round trip | GD4, GD6 | Look |
| 42 | engine, `effective()`, live prefill, band notice, signing locks; questionnaire marks | GD3, GD6 | Look |
| 43 | values inside boxes; row 2 prints; AcroForm read-back; stale ack 409; the signed copy is protected | GD5, GD6 | Fidelity |
| 44 | the band three ways; the cross-check; five clicks make one row with one Undo | GD3, GD6 | — |
| 45 | each carrier file matches its template; printed count equals the band; no member value in errors | GD6 | Fidelity |
| 46 | packet contents; `.eml` headers; first send moves to Quoting; PHI follows lines | GD6 | Walk |
| 47 | one access row per PHI download | GD6 | staging canary scan |
| 48 | `parse_comp` exact; shares in millionths; §5.6's 3,805 example | GD1 | — |
| 49 | booking idempotent; un-sell voids; a lost deal never books; the stale chip; the tier matrix; a failed receiver shows "not booked"; two sold plans book | GD1, GD1-sold, GD3 | — |
| 50 | match, post, lock, reverse; the reader writes nothing before confirm; firm files by tier | synthetic statements | Eval |
| 51 | shapes-only mapper; counts-only context; no values in logs; the import's job link | GD6 | Eval |
| 52 | stages only; never a signed form; protected slots untouched | GD6 | Eval |
| 53 | link rules; PIN shown once and locked after five tries; facts and counts in fixed queries | GD6 | — |
| 54 | 404, 410, 428; staff 403; allowlist; all-or-nothing save; no-store; the `/b/` moved page | GD6 | Look (390×844), Walk |
| 55 | approvals store origin `client`; pending entries feed nothing | GD6 | — |
| 56 | tray grouping (Vitest); two asks leave one draft | GD6 | Look |
| 57 | form plans and dry runs; the floor never lowered while sensitive | GD6 | Look |
| 58 | portal narrowing; the second factor both ways; officer signing | GD6 | Walk |
| 59 | staged client imports; the receipt | GD6 | — |
| 60 | the `steps()` table; quote-first leads; carrier wait from `marketed_at`; the commission step; Later at 21:00 | GD3, GD6 | — |
| 61 | queue rows and stats; journey and badges in fixed queries | GD3, GD-Big | Look, Perf |
| 62 | every block on an empty deal; quote-first states; the renewal-offer chip | GD3, GD6 | Look |
| 63 | each control writes through its owner; feed rows | GD6 | Look |
| 64 | `mark_document` in one transaction with one revert; `value: null` for PHI | GD1, GD6 | Perf |
| 65 | the roster view; the pop-out relays keys; OCR draws but never marks a value found | GD4 | Look |
| 66 | lint only | — | — |
