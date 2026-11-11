# Part F — Advisor

[← Porting plan](README.md)

**What it is:** The Advisor is the deal's quote board. It shows every plan quoted on one line. The user searches, filters, sorts and stars plans, links each quote to the plan it replaces, and sets the order the client will see. A stop-loss verdict board sits beside it. Its view pills also hold the Proposal builder and the Export viewer, which the Proposal section specifies. It is the `quotes` app. 2V's simplified screen (an editable table with plans as columns) is closer to the old Proposal grid, so its parts are reused inside the board.

## F.1 Files read, in order (one line each)

Paths: R = c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage (old, read-only) · 2V = c:/Users/fooba/OneDrive/desktop/Vantage_all/2Vantage

**Specs and READMEs**
| File (lines) | What it is / what it taught |
|---|---|
| R/benefits/README.md (394) | Module map. Line 206 says 85 plan fields; there are 95 |
| R/benefits/pipeline/README.md (716) | One paragraph per module; its `rank_case_plans` note is stale |
| R/frontend/src/components/benefits/README.md (421) | Advisor views, the board bridge, `landClaude` |
| R/PlanningDocs/Benefits/decisions.md (5,528; D-027, D-049, D-083, D-094/095, D-119, D-136, D-149, D-160, D-167, D-169, D-174, D-210–D-223) | Several current plans; rules and pick; transpose cap; summary tiers; links. ★ means "on the proposal" and a separate list was declined (D-210). Pairs (D-219); one order (D-220); six a slide (D-221). Picks replace, modelled on the client spreadsheet's Compare drop-downs (D-222, D-083). Pages (D-223); the viewers (D-119, D-167); a duplicate copies every value (D-049) |
| R/PlanningDocs/Benefits/proposal-pages-and-picker.md (114), plan-order-everywhere.md (74) | Pages and PlanPicker; one order on three screens; the `deck_sequence` page shape |
| R/PlanningDocs/Benefits/big-deal-speed.md (parts) | 624 plans × 83 rows = 6.33 MB, of which sources are 3.21 MB; target ≤ 3 MB and ≤ 2.5 s |
| 2V/CLAUDE.md (43), README.md (43) | App chain, write rules, the 300-line limit, behavioural tests, "deal-tab queries use staleTime 0" |
| 2V/plan.md §1, §3 (§3.3), §4.1, §4.3, §4.5, §5.3.6, §5.4–5.5, §6 (§6.4), §7.7, §7.9, §8.11–8.17, §9.3, §10, §12–13, §15–16 | Roles and links; enrollment precedence ("typed always wins"); packages; one home for carrier and funding; the AI registry; required tests; non-goals |

**Models**
| File (lines) | What it is / what it taught |
|---|---|
| R/benefits/models/pipeline.py (621) | Plan (`bundling_state`: '', included, unbundled; `option_number`), PlanValue, AdvisorFilterSet, BundleTemplate, share links |
| R/benefits/models/case.py (parts; 791–845) | Field definitions; ConfirmableValue; LocatedValue (`located_where`: page, or sheet and cell, found after the read) |
| R/benefits/registry.py (632) | 95 plan-field definitions |
| R/benefits/lines.py (197) | 27 lines, field sets, rate bases, tier and volume fields, `PROXY_TIER_FIELD` |
| 2V/quotes/models.py (73), proposals/models.py (26), deals/models.py | Plan, Package, ProposalConfig (`lines` is a stored presented list); Activity holds only a summary and a count |

**Rules and services**
| File (lines) | What it is / what it taught |
|---|---|
| R/benefits/pipeline/plan_math.py (1,440; read 55–235, 381–664) | `round_money`, count sources, `stop_loss_enrolled` (medical tally only), `group_premium`, `proposal_plans`, `_proposal_layout` (versions behind originals, `behind_current`), move/swap/last. Lines 709–1440 are census export code |
| R/benefits/pipeline/enrollment.py (194) | Typed counts; the "version" step; one switch per line; each save is the line's whole typed set |
| R/benefits/pipeline/current_plans.py (212), plan_links.py (174), stars.py (108) | Current plans; links (`compared_to`); the 16 cap counts current and starred plans only |
| R/benefits/pipeline/plan_slots.py (177) | The slot rule; its `on()` ignores recommendations |
| R/benefits/pipeline/plan_line.py (141), plan_remove.py (193), plan_copy.py (429), plan_merge.py (434) | Move-to-line refusals; delete, clear and merge; one copy rule over every value; pairs |
| R/benefits/pipeline/option_numbers.py (61), renewal_pairs.py (57), plan_codes.py (152) | Numbers stamped once; a renewal copies design, not rates; codes as a plan's identity |
| R/benefits/pipeline/packages.py (438; 100–141), presentation_model.py (1,031; 600–880) | `leading_ids`, `carrier_groups`; `DECK_COLUMNS`, `line_pages`, `deck_sequence` |
| R/benefits/pipeline/claude_edits.py (684; 95–110, 320–360) | `editable`; `record_value_correction` skips copies and priced versions |
| R/benefits/pipeline/stop_loss_math.py (214) | Maximum annual liability (MAL), lasers, attachment floor, level-funded split |
| R/benefits/pipeline/concessions.py (1,002) | Priced versions, bundle templates, auto-star (898–905) |
| R/benefits/pipeline/advisor_filters.py (351), sale.py (162), workbook_import.py (378) | Saved setups, budget rungs, the `total` rule key; selling; template import |
| R/benefits/pipeline/advisor.py (715) | Rank (clears the line's stars, 521–530), `board_plans_block`, `case_context_text`, `rank_after_read` |
| R/benefits/pipeline/composition.py (240–275), presentation_math.py, exec_summary.py (1,448) | The order capped at 200 ids; `cost_summary`; a second copy of the membership rule |
| R/benefits/market/coverage.py (577), pipeline/markets.py (313), market/value_review.py, market/validation.py, market/intake.py (1,055; 155–163) | Line states and lines kept off the proposal; marketing block; review marks; `normalize_tier`; the goals questions (budget target, acceptable increase, priorities) |
| 2V/quotes/math.py (176), packages.py (155), services.py (224), marks.py (162), selectors.py (155), fields.py (205), values.py | Built pricing, packages, writes (design-only `_copy`, per-role order, hard delete) and payloads (the whole `sources`) |
| 2V/deals/values.py (47), activity.py (47); proposals/selection.py (44), selectors.py (90) | A changed value replaces its whole source; coalescing; a second presented list and a carrier sort |

**Views and payloads**
| File (lines) | What it is / what it taught |
|---|---|
| R/benefits/serializers/pipeline.py (1,958), serializers/primitives.py | `comparison_payload` (deal-wide `shortlist_count`, 517); `_source_payload` keeps the document under an edited value |
| R/benefits/views/pipeline.py (2,581), urls.py, views/shared.py | Plan routes; `ClearShortlistView` already takes a line (122–144); `_hand_edit_target`; `_get_case` |
| R/benefits/views/versions.py (552), views/ai.py (1,316), views/cases.py (1,256) | Edit sessions; lock, flag check, job status, rank; review views |
| R/backend/settings.py (489) | Rank needs `ANTHROPIC_API_KEY`; `BENEFITS_ADVISOR_MODEL` is undeclared |
| 2V/quotes/views.py (140), urls.py (20) | The 14 built routes; PATCH accepts role, links and the star |

**AI**
| File (lines) | What it is / what it taught |
|---|---|
| R/benefits/ai/scan_chat.py, quote_reconcile.py (843–855), pipeline/claude_writes.py | `set_board`, `board_patch`, `_tool_pick`; new plans numbered in reading order |
| R/benefits/ai/table_agent.py (922; tool list) | `merge_plans`, `pair_plans`, `set_table_note` and the other table tools |
| R/benefits/ai/table_lock.py (109), flag_check.py (304), extraction.py (846; 124–134), plan_checks.py (186) | The table lock; the re-check job; the job runner (rank after a read is skipped without guidance); `verify()` |
| R/benefits/ai/source_check.py (374), docscan/locate.py (579), docscan/sheet_preview.py (288), docscan/sheet_format.py (353) | Where each value is printed; a sheet value stores only its snippet (sheet_preview 6–8); the viewer's Excel look |

**Frontend**
| File (lines) | What it is / what it taught |
|---|---|
| R/frontend/src/components/benefits/close/AdvisorTab.jsx (3,924) | The whole board in one component |
| …/close/StopLossAnalysis.jsx (758), PlanCountsCard.jsx (295), EnrollmentStrip.jsx (145) | Stop-loss board; summary tiers ("Off sends every plan back to the census"); the builder's line counts ("Borrowed from the medical census") |
| …/close/SavedFilterBar.jsx (291), PlanTemplateImport.jsx (89), AddQuotes.jsx (137), App.jsx | Saved setups; import; the orphan page |
| …/close/ProposalPages.jsx (487), PlanPicker.jsx (298), keyRows.js, proposalRows.js | Pages and the slot picker |
| …/close/PricedVersionComposer.jsx (1,542), pricedKinds.js (180) | The priced-version composer |
| …/close/useComparisonStore.js, planOrder.js, OrderArrows.jsx, PlanLinkPicker.jsx, compliance.js, planFinder.js, sourceDocs.js, ComparisonStatus.jsx | Small helpers |
| …/benefits/planGroups.js (119), lines.js (40) | Groups for the transposed layout |
| …/shared/useGridKeys.js (435), useWriteQueue.js, useFreezePanes.js, useWindowedPlans.js (224), useGridSizes.js (251) | Grid keys, write queue, frozen panes, windowing, sizes |
| …/shared/EditModePrompt.jsx, ReviewBulkBar.jsx, valueReview.js, findText.js, claudePages.js, ClaudeLockSwitch.jsx (44), useDealJobStore.js (239), flashPlans.js (35) | Edit prompt, bulk review (its Undo is the `clear` action), find, lock chip, job store, flash |
| …/shared/CaseWorkspace.jsx (mounts 876–925, drop 992), ScanChat.jsx (DROP-1), close/WorkWithClaude.jsx, ComparisonGrid.jsx (1,365; "＋ Add quotes" 856), ProposalBuilder.jsx (2,131) | Mounts and file drops, `refresh`, Rank and "Add client guidance first", the Proposal grid, the builder |
| …/close/useExportPreview.js (137), ExportViewer.jsx (892), useUnleashedCopy.js (327), UnleashedView.jsx (558) | Previews built only while shown and only when the deal moved; the Unleashed sandbox |
| …/shared/home/PlanTray.jsx (96) | The only drag-and-drop reorder in the app |
| R/frontend/src/contexts/EditSessionContext.jsx (205), UserContext.jsx (114), GuideContext.jsx (338) | Edit sessions, `claudeDirect`, guide switches |
| R/frontend/src/utils/format.js (198), download.js, pageView.js, usage.js; services/api/core.js, benefitsClose.js (422), benefitsShared.js; guides/library.js (313), guides/concessions.js | Number display, downloads, API (`current-order` and `mergePlans` unused); the only callers of `/add-quotes` and `?concession=` |
| 2V/frontend/src/deal/advisor/* (AdvisorTab 182, PlanTable 161, EnrollmentCard 152, …), api/quotes.js (136), api/meta.js, api/deals.js, main.jsx | The simplified screen and its hooks; staleTime 0 on deal tabs |

**Styles**
| File (lines) | What it is / what it taught |
|---|---|
| R/frontend/src/styles/benefits.css (6,275; 1,473–2,200 and 4,026–5,100) | Board classes; `--muted` is undefined (used four times, first at 1503) |
| R/…/styles/benefits-grid.css (200), benefits-freeze.css (104), benefits-grid-sizes.css (92) | Grid, frozen panes, sizes |
| R/frontend/src/App.css (4,357), main.jsx (45) | Root tokens and the `bb-*` building blocks; import order |
| R/…/styles/benefits-export.css (479) | `bnf-xv-*`, the Export viewer the Advisor hosts |
| R/…/styles/benefits-unleashed.css (877), benefits-census-review.css (928) | The gold pill. Census-review reuses `.bnf-advisor-filtercard` and `.bnf-review-bar` without restyling them (header; line 125), so the Advisor does not need it |
| 2V/frontend/src/styles/tokens.css (81) | The current tokens, to be replaced |

**Tests**
R/benefits/tests_pkg: current_plans_tests, plan_links_tests, plan_slot_tests, plan_counts_tests, board_filters_tests (RuleFieldParity, SavedSetRules, BoardChat, BatchStar), template_import_tests, compare_slots_tests (belongs to Proposal), multiline_tests (StopLoss×3, RateBasis, PerLineCardinality, QuoteReaderLine, LineAwareRequiredness, clear scoped to one line), pipeline_tests (Comparison through ZeroEnrollment, ClearShortlist, RankPlans, FilteredRank, ShortlistPayload, PlanComplianceField, MarkCaseLost), wwc_accuracy_tests (PlanRemove, PlanChecks), plan_type_tests, claude_lock_tests, flag_check_tests, builder_polish_tests, presentation_tests, reread_tests, work_with_claude_tests, existing_client_tests. Management commands seed_stop_loss, seed_plan_links, locate_sources. 2V/quotes/tests: test_math, test_plans, test_template.

## F.2 Old data model, in brief

- **Plan**: one row per column. Fields: `carrier`, `plan_name`, `line`, `is_current`, `is_sold`, and `is_shortlisted` (the star) with `shortlist_reason`. `sort_order` is the slot order among current plans and "as added" for quotes.
- **Plan links**: `renewal_of` and `compares_to` ("Replacing:").
- **Priced versions and copies**: a priced version has `concession_of` and a `concession` JSON (pct, rates, formulas, bundle or premium holiday). A copy has `duplicate_of` and `duplicate_spec`.
- **Other Plan fields**: `bundling_state`; `enrollment` `{counts, on}`; `option_number` (stamped once, D-175); `client_name`; `plan_codes` (identity, D-149); `read_key` and `read_state`.
- **PlanValue**: the EAV store, one row per plan and field. A value is `edited ?? extracted`, with confirmation and review layers and a source document, page and snippet. A later check stores `located_where` (page, or sheet and cell). Status is derived.
- **BenefitFieldDef**: 95 fields seeded by migrations, in 13 groups.
- **AdvisorFilterSet**: name, view (quotes, stop-loss or census-review), line, config JSON, owner, shared flag. **BundleTemplate**: discounts per line.
- **Deal `proposal_config`**: `composition.lines[line]` holds `plan_order` (at most 200 ids), `merged` (pairs, D-219) and `table_note` (D-216). It also holds `tier_counts_by_line` and a legacy deal-wide `tier_counts`. The deal itself has `claude_table_lock` and `client_guidance`.
- **Derived on read**: the comparison payload (cells, line blocks, totals, stop-loss figures, `proposal_order`). The client works out Δ%, closeness, incomplete, flags and compliance itself.

## F.3 Functionality inventory and verdicts

F1–F134 keep the draft's numbers. F135–F144 were split off or added after the challenges, and each sits in its sub-area. "Changed (Cn)" marks a verdict or design that challenge n changed, and says why.

### A. Shell, header and views
| # | Functionality (what the user sees -> how it worked) | Verdict | New implementation |
|---|---|---|---|
| F1 | Five pills: Quote comparison, Stop-loss analysis, Proposal builder, Export viewer, Unleashed. The choice is kept per browser (`vantage.bnf.advisor`); `?view=` wins; an unavailable view falls back to quotes | Keep | Pills in `deal/advisor/AdvisorTab.jsx`; `useAdvisorPrefs.js` keeps the key. Four pills while F4 is deferred |
| F2 | The Stop-loss pill shows only when the deal has a stop_loss line, even with no plans | Keep | From `plans/lines/` (one grouped query) |
| F3 | Builder and Export viewer pills; both previews kept warm in AdvisorTab | Simplify | Components from `deal/proposal/`. Changed (C22): each preview is a React Query entry keyed on the deal's change stamp, `staleTime: Infinity`, enabled only while its format is on screen, last copy kept on screen, built after the builder's queued saves. 2V's staleTime 0 would rebuild PowerPoint, PDF and Excel on every pill switch |
| F4 | Gold Unleashed pill, shown only with `claudeDirect` | Defer | Changed (C21): not an owner need, not in the module list, and a 2V §15 non-goal (sandbox copies). Follows the Work with Claude section's verdict on Unleashed (Q7) |
| F5 | Line tabs with plan counts; kept per browser; `?line=` wins; switching drops the draft, counts card, ticks and Move-to pick | Keep | `bnf-lineswitch`, `bnf-linetab` |
| F6 | First load "Loading N quoted plans…" with Retry; later loads a RefreshChip; a hand-made store keeps the newest read | Simplify | React Query `isPending` and `isFetching` |
| F7 | Empty board: "No quoted plans yet — read the carrier quotes first" with "Go to the proposal tab ▸"; a line with only current plans still shows its pinned rows | Keep | The button becomes "＋ Add quotes" (F96) |
| F8 | Title "Quote advisor" and its subtitle | Keep | |
| F135 | "Show me how ▸" beside the title | Drop | Walkthroughs are dropped (split from F8) |
| F9 | Count line "Showing N of M quoted plans · K shortlisted · current plan (carrier) $X/mo", then a note about several or no current plans | Keep (fixed) | K counts this line only (bug 1); $X is the Current package total |
| F10 | Amber notes in the filter card | Keep | Wording follows F18 and F140 |
| F11 | "View shortlist in proposal ▸" | Keep | Opens the Proposal tab |
| F12 | Deep links `?concession=` and `?bundle=` (two passes), `?r=` | Drop | Changed (C21): only the dropped guides link to them (guides/concessions.js); no `?priced=` replaces them |
| F136 | `?file=` picks the Export viewer's file | Keep | URL state like `?view=` and `?line=` (split from F12) |
| F13 | A line the coverage intent keeps off the proposal looks like any other line | New (fix) | Chip "Off the proposal" on the line tab, from intake's coverage intent |

### B. Finder (need 4)
| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| F14 | Every typed word must match the name, plan number, carrier, network or plan type, ignoring case or using letters and digits only; current plans never count as hits | Keep | `board/finder.js` (pure), saved as `find`. Changed (C15, C26): also matches `Plan.codes` and carrier aliases ("UHC") from `deals/carriers.py`, which moves left of intake and quotes (2V §4.7 put it in rfp) |
| F15 | "Also matches N on Dental" chips switch the line and keep the query | Keep | `GET plans/find/?q=` returns every line's hits in one query |
| F16 | A single match scrolls into view and flashes 1.5 s; Enter jumps to the first match; Esc clears | Keep | `bnf-find-flash` |
| F17 | The empty board says why nothing shows | Keep | `bnf-nofilter-row` |

### C. Filters and budget (need 5)
| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| F18 | Budget select: Any; within 5, 10 or 15%; at least 5, 10 or 15% cheaper. It tested Δ ≤ N against the line's only current plan | Simplify | Same select, steps and meaning ("no more than N% above"). Tests the server's `change.pct` (each plan against what it replaces), so it works with several current plans; saved as `budget_pct` |
| F19 | No typed cap on the monthly total; only a Claude rule had one | New | "Monthly total ≤ $" input. Changed (C7): stored as the rule `{key: total, op: <=, value, line}`, the same predicate and saved key as Claude's `total` rule, kept per line |
| F139 | Intake's Monthly Budget Target and Acceptable Increase reach no screen | New | Changed (C7): hints on the filter card, "Client target $X/mo · Apply" and "Client accepts up to N% · Apply". Not prefilled as C7 proposed: the target may cover every line (Q4) |
| F140 | A budget or total filter hides plans with no total without saying so | New | Changed (C7): "N have no price yet — enter enrollment" |
| F20 | Sliders in steps of 50, bounded by the line's quotes: medical deductible and OOP max; dental deductible and annual max; vision exam copay and frame allowance | Keep (fixed) | Lists in `quotes/board_presets.py`; annual max and frame allowance become "at least" sliders (bug 16) |
| F21 | "EE-only rate ≤ $" and "PCP copay ≤ $" (strict parser); a blank fails an active cap | Keep | Numbers parsed once on the server (`facts`) |
| F22 | Hide incomplete, Hide non-compliant, ★ Starred only, ⚑ Needs checking, ⚠ To review | Keep (fixed) | A missing total no longer counts as incomplete |
| F23 | Carrier chips, shown with two or more carriers | Keep | |
| F24 | Claude rule chips `{key, op, value}` (at most 8); a blank never meets a rule; a rule on a missing column rests greyed; the user can only remove them | Keep | Cleaned by `board.clean_config`; applied only in `board/filter.js` |
| F25 | Pick chip "✦ Claude: label (n) · k not judged"; one line only; never saved | Keep | |
| F26 | "N active · Clear" | Keep | |
| F27 | Filters carry across line switches | Keep | Except a rule that names a line (F19) |

### D. Saved setups
| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| F28 | Saved bar: Mine, then Shared; ＋ Save current (name, description, this line or any line, Share); Update and Delete for the owner or an admin; applying never switches the line | Simplify | Changed (C20): `quotes.SavedView` cleaned by `board.clean_config`, with no cleaner registry in deals; others' private sets answer 404. Kept for the "entire Advisor", though 2V §15 called saved filter templates a non-goal (Q6) |
| F29 | Stop-loss settings can be saved; the bar shows only when there are summaries | Keep | Same model, `view='stop-loss'`. Not dropped as C20 proposed: it is visible, uses the same bar and costs one cleaner |
| F30 | Census-review sets live in the same model | Keep | The Review section (right of quotes) reuses `quotes.SavedView` with its own cleaner, or drops the kind |

### E. Columns, sort and layouts (needs 3, 10)
| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| F31 | Column presets: Primary (per field set), Cost sharing, Rx, Rates & contributions, All columns. ★, ☐ and Plan are pinned; a column used by the sort, a rule or the pick stays | Keep | Lists in `board_presets.py`, served by `/api/meta/` |
| F32 | Clicking a header sorts and flips direction; the select offers Proposal order (default), Sort by column, Closest to current | Keep | Server order (`order.layout`) and closeness score |
| F33 | In Edit with a column sort, the row order holds until a sort or filter changes | Keep | |
| F34 | ⇄ Transpose; kept per browser; blocked above 60 plans with a tooltip | Keep | `TRANSPOSE_MAX` 60 |
| F35 | Transposed: frozen header and label column | Keep | `useFreezePanes.js` |
| F36 | Excel-style sizes per user: one column width, row heights, double-click a grip to reset, "↺ Reset sizes", three-line clip | Keep | `useGridSizes.js`, key `vantage.bnf.gridsizes.<user>` |
| F37 | ▦ Pages "What the client will see": each column has a place, CURRENT k or RENEWAL, ‹ ›, ✕, Today or Option n, the name and Replacing:; rows Monthly premium, Change vs current, then the preset's rows | Keep | `pages/PagesView.jsx`. Changed (C14): the split is the deck's own, not just six a slide: carrier breaks in the by-carrier layout, repeated current plans counted, pages by current plan, renewal pairs three a slide. `proposals` serves ids only (`GET proposal/pages/?line=`); the board joins them with its comparison cache. It ships with this view, and the PowerPoint uses the same function |
| F38 | "Page i of n · … · k of 6 columns · full"; with no stars, two pages plus "Show every page (N)"; a banner when a write adds a page | Keep | "Page 1 is full…" comes from the same split |
| F39 | Column chips PRICED, RENEWAL, "repeated"; the current column reads "What they have today"; current, priced and stop-loss names not clickable | Keep | The pair chip is F137 |
| F137 | "+ name (one column)" on a pair printed as one column (D-219) | Defer | Changed (C13): nothing stores pairs, and 2V §5.4 chose one plan "5182 / 5183" (each value still traces to its SBC through its source) or two plans bought together. That holds until Q5; if pairs return, `Plan.pair_of` in quotes, so the presented rule, slots, Pages and exports read one place |
| F40 | Above 150 plans the rows layout draws only rows in view; off while a draft is open | Keep | `useWindowedRows.js` (guide condition dropped) |
| F41 | Derived columns: Monthly total, Δ, network and type, Flags | Keep | Server `premium`, `change`, `facts` |
| F42 | Nothing rebuilds a scanned quote's plan order and printed rows; the Documents viewer only shows the file | New | "As quoted" layout. It has one chip per scanned document and shows that document's plans in its column order. Its printed rows come in printed order: mapped rows live and editable, unmapped rows greyed with their printed text. Changed (C1): no `QuoteLayout` model and no third order store. The reader writes `Document.read_rows` and a `col` in each value's source, and the selector finds and orders plans from those. Not deferred as C1 proposed, because need 3 says "recreate", which a file viewer does not do. Built by default; Q2 confirms |
| F138 | A scanned quote's plans arrive in its column order (`quote_reconcile` numbers them in reading order; D-220 "as added") | Keep | The reader's apply numbers new plans in reading order under the deal lock. Nothing sorts on a value, so board, Pages and exports open in the quote's order (need 3) |

### F. Order and slots (need 9)
| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| F43 | ▲▼ and ◀▶ in Proposal order; a move passes hidden plans; a priced version moves with its quote; stored as at most 200 ids | Simplify | One order: `Plan.sort_order`, one sequence per line. Rule in `quotes/order.py` (pure), writes in `services/ordering.py`. Changed (C12): replaces 2V's per-role `plans/order/` (which needs every id and runs one UPDATE each) with move, swap and reset, written by `bulk_update`. No second endpoint |
| F44 | Current plans have slot arrows; their groups follow | Keep | Same endpoint |
| F45 | Click a name in Pages to open PlanPicker: search, greyed rows that say why, at most 60 rows, page badge, ★, arrows, Enter, Esc. Picked plan X takes plan P's place, star and link; P takes X's | Keep | `quotes/slots.py` (pure), `ordering.put_in_slot`. Changed (C3, C19): "on the proposal" is `presented()`; a pick over a recommended plan clears its recommendation (D-222 item 5); a swap trades whole `replaces` sets |
| F46 | "＋ Add a plan" beside a current plan, with Replacing: when there are several; "Page 1 is full…" | Keep | Same service |
| F47 | Drag and drop to reorder (proposed by the draft) | Drop | Changed (C2): not added. Need 9 is D-222's click-a-name drop-down, modelled on the client spreadsheet's Compare drop-downs (D-083); Daniel chose Replace over Insert. A drop calling `move_before` is Insert. It would be a third ordering path, could not reach windowed rows (F40) and would fight the grid keys |
| F48 | Order reset, in the builder only | Keep | `POST plans/order/ {reset}` |
| F49 | Stop-loss keeps the order its quotes were added in | Keep | A rule in `order.layout` |

### G. Stars, current plans and links (needs 7, 8)
| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| F50 | ★ per row: cap of 16 per line counting current plans; current plans take no star; reason "Hand-picked" | Keep | `services/marks.star`, `star_reason`. Changed (C3, C24): the cap counts every presented column (current, recommended, starred) through `presented.room()`, under the deal-row lock |
| F51 | A fresh star links to the nearest current plan (client score, second POST) | Simplify | Server, same write (`closeness.py`), on lines with two or more current plans |
| F52 | "Replacing:" only beside starred or linked quotes, with two or more current plans | Simplify (fixed) | Beside every presented quote (bug 18); "Several…" makes a consolidation |
| F53 | In Edit with ticks: Mark current and Remove current; sold plans and priced versions refused; a plan turning current loses its star and link | Keep | `POST plans/role/`. Changed (C12): PATCH no longer takes `role`. Turning current clears the star, recommendation and links (bug 30) |
| F54 | Replace mode on the Proposal grid menu | Keep | Proposal section |
| F55 | "Clear shortlist" clears every line (tooltip "Remove every star") | Simplify (fixed) | Changed (C16): this line only, as stars are per line and the server already took a line; tooltip "Remove every star on this line"; Activity with revert |
| F56 | The star PATCH accepts a reason; no screen sends one | Drop | No caller |

### H. Ticks and batch actions
| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| F57 | ☐ ticks in every mode; select-all takes the filtered quotes, never current plans | Keep | `board/SelectBar.jsx` |
| F58 | Batch ★ Star and ☆ Unstar, all or nothing | Keep | One star call |
| F59 | Move to another line; refusals; stars, links and option numbers clear | Simplify | Changed (C10): moved in place with the same id, because a rebuild would orphan Activity, sources and labels. `move_line` changes the line, drops values outside the new line's fields (kept in Activity), and clears star, links, enrollment and packages. A current plan joins the end of the target's current plans. Refused: sold plans; priced versions and copies; originals that have them; plans a bundle requires. Labelled plans may move, against C10's proposal: 2V labels are per deal and never renumbered |
| F60 | Delete N; sold plans and client picks kept and named | Keep | Changed (C11): soft delete (`Plan.removed_at`). Delete-time side effects (its renewal becomes an alternate; it leaves `replaces` lists) are real writes in the same Activity entry, and revert with it. C11 proposed computing them on read; real writes keep every reader simple. Restore refuses in words when a rule now blocks it. Sold plans are kept and named (2V has no client carts) |
| F61 | Clear all plans on the line; current, sold and picked plans stay | Keep | Same soft delete; current and sold plans stay |

### I. Cells, flags and sources
| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| F62 | Plan chips: CURRENT k, BUNDLED, priced, superseded, "⚠ MV · Part D", star reason, "requires…", "updated · who" | Keep | From plan fields and `derived` |
| F63 | Flags chip "⚠ N to review · ⚑ k" with Approve, Ignore, Needs checking, "View in document ▸" | Keep | Marks live in `sources`; `POST plans/review/` |
| F64 | ↗ opens the document at the page or cell; cell classes show each mark | Keep | Documents review station. Changed (C8, C23): the link survives a hand edit (F141); the full source is fetched on ↗ |
| F141 | A typed number sits over the carrier's: ↗ stays and the read value is kept (the old edited layer) | Keep (fixed in 2V) | Changed (C8): when a typed value replaces a read one, the new source keeps doc, page, cell and `read`. `read` is only written on plans the reader produced, never on copies or priced versions, as `record_value_correction` did |
| F65 | Bulk review strip: ticked plans, else filtered plans, else the line | Keep | Same endpoint |
| F66 | "✦ Ask Claude to re-check" | Keep | Seam; AI section |
| F67 | Undo an Ignore | Keep | Changed (C17): the review endpoint's own `clear` action ("Undo"), which Overview's Data confidence list also uses |

### J. Edit mode and grid keys
| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| F68 | ✎ Edit took a per-deal lock; a second editor got 409; Done filed a version; a banner linked to "change history ▸" | Simplify | A screen mode only, same button and banner; the link opens Activity |
| F69 | Keys: F2 or typing edits; Enter and Shift+Enter move down and up; Tab and Shift+Tab right and left; arrows; Home and End; Delete and Backspace; Esc; no write when unchanged; no save on blur | Keep | `grid/gridKeys.js` (pure), `useGridKeys.js` |
| F70 | Ctrl+Z and "↶ Undo", 50 deep | Keep | `useUndo.js` |
| F71 | Two write doors; null reverts; optimistic; a write queue | Simplify | One door, `PATCH plans/{id}/`, for carrier, name, plan_number, notes and values; per-cell queue; one refetch per burst. Changed (C12): role, links and stars only through their own endpoints |
| F72 | Double-click outside Edit asks to enter edit mode | Keep | |
| F73 | Edit-only buttons; outside Edit: ＋ Add SBCs, Import, ✎ Edit | Keep | |
| F74 | Lesson-book correction signal | Drop | Activity before/after and the source's `read` (F141) keep the evidence D-027 asked for |
| F75 | No range copy or paste | Defer | Not in the old app; not on the owner's list |

### K. Priced versions
| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| F76 | ＋ draft row with the "Excel stack", live total and Δ; ✓/Enter and ✕/Esc; the composer can dock above the table | Simplify | Same look; preview from `POST plans/priced/ {dry_run}` |
| F77 | Concession: % or $ off or up, or set to, on all rates, with per-rate overrides | Simplify | Changed (C9): `copy_plan(with_rates=True)`, then the ops, with `derived_from` and a `derived` record. 2V's design-only copy would drop the rates the ops change |
| F78 | Bundling: per-line op, value and the quote that must sell; scope; conditional; `bundling_state` | Simplify | One copy per quote with `derived.requires`. `Plan.bundling` ('', included or unbundled) refuses a bundled copy of a quote whose rates already include the bundle |
| F79 | Bundle templates | Defer | Saving never worked for typed bundles; no screen edits them (Q1) |
| F80 | Premium holiday: a $ credit a year or free months, shown net after credit | Simplify | `derived.credit`; `math.net_after_credit` |
| F81 | Duplicate a plan and name the copy | Simplify | Changed (C9): the same `copy_plan` with rates (D-049: a standalone peer with every value), then named |
| F82 | Several commit routes, validated on the server | Simplify | One create, recompute and delete; same refusals except the lost-deal one |
| F83 | Auto-star a new version when there is room; ✎ reopens; ✕ removes | Keep (fixed) | No auto-star on a line with no stars (bug 17) |
| F84 | Superseded chip | Keep | From `derived_from` and `derived.at` |

### L. Enrollment (need 6)
| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| F85 | "＋ Add summary medical tiers" opens PlanCountsCard: switch, plan chips, EE/ES/EC/FAM, Save | Keep | 2V `EnrollmentCard` restyled `bnf-pc-*`; inputs follow the rate basis; "Copy first row to all"; Save writes the line's whole typed set |
| F86 | "✎ counts" marker on a total priced by typed counts | Keep | `enrollment_source`. Changed (C6): every source named in words, including "Borrowed from the medical census" (worksite) and "From medical enrollment" (stop-loss) |
| F87 | Typed counts pass from a plan to its priced versions, renewal or linked quotes | Simplify | 2V `enrollment_for`. Changed (C9): adds a step for a priced version's original, so "5% off" prices the same people |
| F88 | Three count sources on two screens | Simplify | Changed (C5): per-plan counts, plus one whole-line figure (`LineEnrollment`) typed only in this card. The card offers the line figure where the line has no current plan: one current plan's counts already price every quote, and with two a line figure cannot split. A stored figure keeps applying if a current plan arrives later, so no price vanishes. One switch per line (`LineEnrollment.on`). `Plan.enrollment_on` and the builder's EnrollmentStrip counts go |
| F89 | Census count per line (employees only, waivers skipped) | Keep | `census.rollup`, once per line per request (C23) |
| F90 | No census count per current plan | New | Census by plan name (`Plan.census_names`) |
| F91 | Typed counts silently beat a later census | New | Changed (C4): typed counts saved before the latest census import give way to the census wherever it can price the plan. The card shows "Priced from the census now · Keep my typed counts". Counts typed after the import win. Uses `LineEnrollment.typed_at` and the census's last import time. 2V §5.5's "typed always wins" changes; the owner's "pick up the census when it arrives" answers the draft's Q3 |
| F92 | PEPM lines could not use typed counts | Keep (fixed) | 2V `{lives}` and `{volume}` shapes |

### M. Import and export
| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| F93 | ⤓ Export the board as it stands | Keep (fixed) | `quotes/board_export.py` (bug 5) |
| F94 | Import from template, staged as a job | Simplify | 2V plan template (built) |
| F95 | ＋ Add SBCs | Keep | The workspace Claude door |
| F96 | No "Add quotes" on the board | New | Changed (C21): "＋ Add quotes" opens the same Work with Claude door as the Proposal grid's button (ComparisonGrid.jsx:856). The board gets no drop zone of its own; files still drop on the drawer and Documents (DROP-1) |
| F97 | `/add-quotes` page (orphan) | Drop | Linked only from the guide library |

### N. Stop-loss analysis
| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| F98 | Basis "N enrolled employees × 12 months", warning at 0 | Keep (fixed) | Changed (C6): lives typed on the stop-loss plan, else on its current contract, else the medical enrolled employees (the current medical plans' enrollment from any source, else the medical line figure, else the census). The basis names its source, so a quick quote no longer reads 0 |
| F99 | In-force cards and contract terms row | Keep | `selectors/stop_loss.py` over `math/stop_loss.py` |
| F100 | Verdict cards ranked lowest first; ★; ±$ vs current | Keep | Ranked on the server |
| F101 | Punchline sentence | Keep (fixed) | Always compares the lowest premium with the lowest MAL (bug 20) |
| F102 | Controls: Rank by, PEPM or Annual, Contract terms, Hide unscored, Reset lasers | Keep | Four are saveable (F29) |
| F103 | Option table with vs-current rows, partly computed on the client | Simplify | All differences on the server |
| F104 | Laser what-if, never saved | Keep | By laser position, never claimant id; never in Activity |
| F105 | Read-only board; empty and unscored messages | Keep | |
| F106 | Five-tab workbook; refuses two or more current contracts | Keep | `quotes/stop_loss_workbook.py` |
| F107 | Level-funded split (% to claims) | Keep | `math.lf_split` |

### O. Work with Claude seams (needs 1, 2)
| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| F108 | Board bridge: getBoard, getPage, applyBoard | Keep | `board/useBoardBridge.js` |
| F109 | Patch cleaning; picks limited to `<board-plans>` (at most 150 plans, 60k characters) | Keep | `board_plans_text`, registered with `ai`, without lasers |
| F110 | Tool text describes `network` and the medical caps wrongly | Simplify (fixed) | Config keys named after the field (bug 15) |
| F111 | Rank, and rank after a read | Keep (fixed) | Needs a line; writes through `marks.star`. Changed (C18): reads intake's goals (budget target, acceptable increase, network priorities, contribution philosophy, pain points) plus one free-text Client guidance answer in that card. Shows "Add client guidance first" when it is empty. Claude's `update_client_guidance` writes through intake's services, registered with `ai` |
| F112 | Landing flash; ClaudeStrip actions | Keep | `flashPlans`; strip in the Work with Claude section |
| F113 | Claude table lock | Keep | Owned by the AI section |
| F142 | Merge the rate page's row and the SBC's column of one plan (`merge_plans`) | Keep | Changed (C15): a quotes service registered as an `ai` tool, because `ai` sits left of quotes and cannot write Plan |
| F143 | A plan's codes identify it for re-reads and SBCs (D-149) | Keep | Changed (C15): `Plan.codes` (a list) from the pure codes parser, which lives left of quotes; searched by the finder |
| F114 | The deal context prices every plan with the medical count | Simplify (fixed) | Reads the comparison's own figures (bug 12) |
| F115 | "Earlier chat" messages | Drop | Work with Claude keeps its own history |

### P. Rules behind the board
| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| F116 | `group_premium` by rate basis | Keep | `math.monthly_premium` |
| F117 | Δ%, `cost_summary`, `concession_net` | Simplify | `math.change`, `math.net_after_credit` |
| F118 | `compared_to` | Simplify | 2V `base_ids` |
| F119 | Membership rule, plus its copy in `exec_summary` | Simplify | Changed (C3): one `presented()` in `quotes/presented.py`: current plans, recommended plans, and the starred plans, or every plan when none is starred (★ = on the proposal, D-210, which answers the draft's Q2). The cap, slots, Pages, exports and proposals all call it. `ProposalConfig.lines` retires as a presented list, agreed with the Proposal section |
| F120 | Order layout: current plans first; quotes grouped by the plan they replace; values never sort | Keep | `order.layout`. Changed (C19, C9): a consolidation groups under the first plan it replaces, in slot order. Priced versions ride right behind their original on every screen, a current plan's too. Duplicates stay peers: C9 asked for every copy, but D-049 makes a duplicate a standalone plan |
| F121 | Closeness score on the client | Simplify | `quotes/closeness.py` |
| F122 | Incomplete, flags and compliance on the client | Simplify | `quotes/facts.py` |
| F144 | No rule says whether the board's current plans or intake's CurrentCoverage name the carrier in force | New | Changed (C26): `facts.incumbent(deal, line)` gives the current plans' carrier and funding once they exist, else CurrentCoverage's (2V §6.4). RFP, commission and Overview read it |
| F123 | Mark sold (not on the Advisor) | Keep | 2V `marks.set_sold` |
| F124 | Lost-deal checks on some writes only | Simplify | Lost never blocks a write (2V §3.6) |

### Q. Machinery and waste
| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| F125 | EAV PlanValue (95 seeded rows per new column) | Drop | JSON values |
| F126 | Field registry seeded by migrations | Drop | `quotes/fields.py` |
| F127 | Versions, edit sessions, `note_write_or_409`, `settleRef` | Drop | Activity before/after and revert |
| F128 | `merge-plans` endpoint | Drop | Changed (C15): no screen calls it (`mergePlans` in benefitsClose.js is never imported); the merge itself is F142 |
| F129 | `current-order` endpoint | Drop | No caller |
| F130 | `reread` block | Drop | Read by no screen |
| F131 | Guide anchors | Drop | Walkthroughs dropped |
| F132 | Tests that read source | Drop | 2V §12.4 |
| F133 | Usage events | Drop | Out of scope |
| F134 | 2V's simplified Advisor screen | Simplify | Its parts are reused; the Proposal section places + Plan and Packages |

## F.4 Data flow (in and out, by model, field or function)

**In (read):**
- `quotes`: live `Plan` rows (values, sources, role, renews, replaces, starred, star_reason, recommended, sold, sort_order, enrollment, census_names, codes, derived_from, derived, bundling, option_label); `LineEnrollment`; `Package`; `SavedView`.
- `census`: `rollup(deal, line)` (tier counts by line and by plan text, lives, volumes), computed in one aggregate per request; `last_import_at(deal)`; medical enrolled employees.
- `intake`: requested_lines; the coverage intent (lines off the proposal); `CurrentCoverage`; the goals answers (budget_target, acceptable_increase_pct, network_priorities, contribution_philosophy, pain_points, client_guidance).
- `documents.Document`: name, kind, `read_rows`.
- `ai`: table lock and job state. `deals`: Activity (change stamp, revert), `claude_direct`, `carriers` (aliases).
- `proposals` (frontend only): page split ids.

**Out (written, only through quotes services, each with Activity before/after):**
- `Plan`: values and sources (marks, `read`); starred and star_reason; role and links; recommended (cleared by a pick); sort_order; enrollment; derived_from, derived, bundling; codes; removed_at.
- New `Plan` rows: copies, priced versions, and reader plans in reading order.
- `LineEnrollment`; `SavedView`; `Package` membership (cleared by a move).
- `ai` jobs, through the AI section (Rank, re-check).

**Read downstream:**
- proposals: `presented()`, `order.layout`, premiums, packages, recommendation, `derived`.
- commission: the sold set and `facts.incumbent`. rfp: `facts.incumbent`.
- overview: `plans/lines/` and the line facts.
- ai: `board_plans_text` and the registered tools. review: `SavedView`, if it keeps census-review sets.

## F.5 Bugs and pain points found (with file evidence)

1. The shortlist count is deal-wide (serializers/pipeline.py:517). Fix: this line only (F9).
2. Bundle parts are read as numbers in two places (PricedVersionComposer.jsx:1283–1311; AdvisorTab.jsx:1562–1584). Fix: one `math/pricing.bundle_parts`.
3. Lost-deal checks are inconsistent (views/versions.py:44–59). Fix: F124.
4. ✕ on Pages fails past 16 plans (AdvisorTab.jsx:1284–1292). Fix: disable it with a tooltip.
5. The export does not match the screen (AdvisorTab.jsx:1181–1183; workbooks.py:323, 412, 419). Fix: F93.
6. Δ rounding can differ by 0.1 (AdvisorTab.jsx:736–737, 1971). Fix: the server's `change.pct`.
7. The draft preview clamps a negative bundle result to 0, while the server refuses it. Fix: a dry run (F76).
8. Each click builds the payload two to four times (CaseWorkspace.jsx:256; views/pipeline.py:1389–1391). Fix: one invalidation per burst.
9. The budget filter is relative only (AdvisorTab.jsx:2159–2160). Fix: F18, F19.
10. The quick-quote path is fragile (AdvisorTab.jsx:765; plan_math.py:75–82). Stop-loss headcount reads only the medical tally, never per-plan counts (plan_math.py:181–194). Fix: F87–F91, F98.
11. Rank clears every star on the line, hand-picked ones too, even for a filtered subset (advisor.py:521–530; ComparisonGrid.jsx:194–196). Fix: F111, Q3.
12. The Claude context prices every plan with the medical count (advisor.py:263–341). Fix: F114.
13. Orphan code: `current-order` and `mergePlans` (benefitsClose.js:85–86, 145–146; urls.py:290) and `/add-quotes`. Fix: F97, F128, F129.
14. New columns seed every field, and `sort_order` can collide after deletes (views/pipeline.py:214–219; claude_writes.py:83). Fix: JSON values; numbering under the deal lock.
15. The `set_board` tool wording is wrong (scan_chat.py:367–376). Fix: F110.
16. Two sliders work backwards (AdvisorTab.jsx:163–167). Fix: F20.
17. The first priced version on a line with no stars hides every other quote (concessions.py:903–905). Fix: F83.
18. "Replacing:" shows only for starred or linked quotes (AdvisorTab.jsx:1851). Fix: F52.
19. Lines kept off the proposal are not flagged (serializers/pipeline.py:249–252). Fix: F13.
20. The stop-loss punchline can be false (StopLossAnalysis.jsx:152–159). Fix: F101.
21. The hand order is capped at 200 ids (composition.py:250, 270). Fix: F43.
22. Mark sold is not atomic and cannot be undone (views/pipeline.py:339). Already fixed in 2V.
23. Only `merge_plans` locks the deal row. Fix: the deal-row lock for every rule over several plans.
24. AdvisorTab is 3,924 lines long. Fix: the F.6 frontend split.
25. `--muted` is undefined (benefits.css:1503, used four times). Fix: F.6 styles.
26. The finder ignores `client_name` and carrier aliases. Fix: F14.
27. 2V has two orders, and a second presented list that sorts alternates by carrier (quotes/selectors.py:13–15; proposals/selection.py:4–44). Fix: F43, F119.
28. 2V `marks.star` has no cap and no reason (marks.py:16–22). Fix: F50.
29. 2V `set_enrollment` locks rows in request order, which can deadlock (marks.py:89–97). Fix: the deal-row lock.
30. 2V keeps the star when a plan turns current (services.py:127–140). Fix: F53.
31. 2V PATCH accepts `starred`, `role`, `renews_id` and `replaces_ids` (quotes/views.py:59). Fix: F71.
32. 2V numbers and reorders `sort_order` per role; the reorder needs every id and runs one UPDATE each (services.py:92–101, 217–224). Fix: F43.
33. 2V `set_enrollment` saves unchanged figures and keeps no time (marks.py:86–102). Fix: F88, F91.
34. 2V drops ↗ and the read value on a hand edit (deals/values.py:5, 42–46). Fix: F141.
35. 2V `_copy` drops rates (services.py:168–171), and `enrollment_for` has no step for a version's original (math.py:89–102). Fix: F77, F81, F87.
36. 2V hard-deletes plans, so package and `replaces` rows cascade. Its Activity keeps only a summary and a count (services.py:158–165; deals/activity.py). Fix: F60.
37. 2V `lines_summary` runs `line_state` and about eight queries per line (selectors.py:132–155). Fix: one grouped query.
38. 2V sends every source entry (selectors.py:82). On the old staging deal, sources were 3.21 of 6.33 MB (big-deal-speed.md). Fix: compact flags.
39. The old slot rule ignores recommendations (plan_slots.py:89–90), and the old cap counts only current and starred plans (stars.py:38–50). Fix: F45, F50, F119.
40. "Clear shortlist" sends no line, so it clears every line (AdvisorTab.jsx:3380–3394; views/pipeline.py:122–144). Fix: F55.
41. Intake's budget answers reach no filter (intake.py:155–158; AdvisorTab.jsx:2158–2161). Fix: F139.
42. A sheet value keeps only its snippet (sheet_preview.py:6–8), and no printed row labels are stored, so nothing can rebuild a quote's layout. Fix: F42's reader output.

Not carried over as a bug: there is no per-deal access scoping. 2V decided that every signed-in user sees every deal (plan.md §1.2).

## F.6 New design

**App.** No new app: the Advisor is `quotes`. `SavedView` lives in quotes (C20). The Pages split comes from `proposals` (C14). Claude hooks register with `ai`, including the merge tool (C15).

**Models (quotes).**
- `Plan` gains:
  - `star_reason`;
  - `derived_from` (a self FK, SET_NULL) and `derived` `{kind: concession, bundle, holiday or duplicate; label, note, ops: [{key, op, value}], credit: {annual} or {months}, requires: [plan ids], conditional, by, at}`;
  - `bundling` ('', included or unbundled);
  - `codes` (a list);
  - `removed_at`.
- `sort_order` becomes one sequence per line. `enrollment_on` goes (C5).
- The default manager hides removed plans. The one-renewal constraint adds "not removed". Option labels stay unique across removed rows, so a label is never reused.
- `LineEnrollment` `{deal, line, enrollment: {} or the basis's figures, on, typed_at}`, unique per deal and line.
- `SavedView` `{owner, shared, view: quotes or stop-loss (census-review if Review keeps it), line ('' = any), name, description, config, sort_order}`, unique per owner, view and name. The quotes config is `{find, budget_pct, rules: [{key, op, value, line?}], sliders, ee_rate_max, copay_max, hide, starred_only, needs_check, to_review, carriers, preset, sort, layout}`.
- Elsewhere: `documents.Document.read_rows` `[{label, key or null, cells: {col: text} for unmapped rows}]`. Each source entry may carry `col` and `read` (Foundation).

**Pure modules.**
- `quotes/math/` holds all money math, under 300 lines a file:
  - `premium.py` (today's math.py);
  - `enrollment.py` (`enrollment_for` with the census rollup and its import time; `medical_employees`);
  - `pricing.py` (version ops, bundle parts, `net_after_credit`);
  - `stop_loss.py` (MAL, lasers, attachment floor, `lf_split`).
- `presented.py` (`presented`, `room`, 16 columns); `order.py` (`layout`, `move`, `swap`, `last`, `reset`); `slots.py` (`prepare` returns a placement).
- `facts.py` (incomplete, flags, compliance, `incumbent`); `closeness.py`; `board.py` (`clean_config` for saved views and Claude patches); `board_presets.py` (data: presets, sliders, budget rungs).
- Enrollment order: own typed figures; a priced version's original; the renewal's or replaced plans' typed figures; census by plan; stop at two or more current plans; the whole-line figure; the census line rollup (stop-loss: medical employees); none. A typed source saved before the latest import yields to a census source for the same plan.

**Services** (`quotes/services/`, one file each):
- `plans.py` (create, values, `copy_plan`, delete, restore, `move_line`, merge, clear line);
- `marks.py` (star, clear shortlist, recommend, sold);
- `roles.py` (role and links);
- `ordering.py` (move, swap, reset, `put_in_slot`);
- `priced.py`; `review.py` (approve, ignore, check, clear); `enrollment.py`; `saved_views.py`.

`quotes/revert.py` is the reverter quotes registers with the Activity revert.

Service rules:
- A rule over several plans locks the Deal row and writes only its own columns, with `bulk_update` (C24). This covers the cap, order, slot, role, links, enrollment, create, delete and move. A value edit locks only its plan.
- An unchanged write changes nothing and records nothing.
- Every write records Activity with before/after of the keys it changed (never member values or lasers), and returns only the plans that changed.
- Revert (C11) works per key and is refused when a later write changed the same key. It is multi-row for order, stars, slots and delete.

**Selectors** (`quotes/selectors/`): `comparison` (compact sources), `lines_summary` (one grouped query), `find_index`, `stop_loss`, `as_quoted`, `board_plans_text`, `source`.

**Endpoints.**
- Changed:
  - PATCH `plans/{id}/` takes only carrier, name, plan_number, notes and values.
  - `plans/star/` gains the cap, the reason, the auto-link and the lock.
  - `plans/enrollment/` takes the line's whole typed set `{line, plans, whole_line, on}`.
  - `plans/order/` takes `{line, move}`, `{line, swap}` or `{line, reset}`.
- New:
  - plan lists and links: `plans/find/`, `plans/shortlist/clear/`, `plans/role/`, `plans/links/`;
  - moving and removing: `plans/move-line/`, `plans/delete/`, `plans/clear/`, `plans/slot/`;
  - priced versions and review: `plans/priced/` and `plans/{id}/priced/`, `plans/review/`;
  - reads and files: `plans/stop-loss/` and its `workbook/`, `plans/board-export/`, `plans/as-quoted/?doc=`, `plans/{id}/source/?key=`;
  - `saved-views/`.
- From proposals: `proposal/pages/?line=` (ids only). There is no merge endpoint.
- Payload (C23): cells carry compact flags (status, mark, origin, document index). Documents are listed once, and the full source comes on ↗. Budget: 600 plans in ≤ 3 MB raw and ≤ 2.5 s.

**Frontend** (`frontend/src/deal/advisor/`, files ≤ 300 lines):
- Top: `AdvisorTab.jsx`, `useAdvisorPrefs.js`, `LineTabs.jsx`.
- `board/`: QuoteBoard, FilterCard, BudgetHints, SavedBar, SelectBar, PlanCell, FlagsChip, ReviewBulkBar, ReplacingPicker, AsQuotedTable, `finder.js`, `filter.js`, `sort.js`, `useBoardBridge.js`.
- `pages/`: PagesView, PlanPicker, `pageRows.js`.
- `grid/`: `gridKeys.js`, `useGridKeys.js`, `useUndo.js`, `useWriteQueue.js`, `useFreezePanes.js`, `useGridSizes.js`, `useWindowedRows.js`.
- `priced/`: PricedComposer, DraftRow, `pricedKinds.js`. `enrollment/`: EnrollmentCard, CensusNotice. `stoploss/`: StopLossBoard, VerdictCards, OptionTable, LaserWhatIf.
- React Query hooks live in `api/quotes.js`, split by area as it nears 300 lines.

**Styles.**
- Copy verbatim, with the same class names, in the old import order: App.css (tokens, `bb-*`), benefits.css (board ranges), benefits-grid.css, benefits-freeze.css, benefits-grid-sizes.css and benefits-export.css (`bnf-xv-*`, C25). Copy benefits-unleashed.css only if F4 returns.
- Not benefits-census-review.css: it reuses the Advisor's classes without restyling them.
- Files over 300 lines follow the Foundation's rule. Failing one, split them at their own section comments into consecutive files imported in order, so the cascade cannot change.
- Families: `bnf-advisor-*`, `bnf-viewtab*`, `bnf-ux-*`, `bnf-lineswitch`, `bnf-linetab*`, `bnf-filter-*`, `bnf-find-*`, `bnf-nofilter-row`, `bnf-rule-chip*`, `bnf-saved-*`, `bnf-preset-tab*`, `bnf-sort*`, `bnf-freeze`, `bnf-plan-*`, `bnf-chip-*`, `bnf-flag-*`, `bnf-review-*`, `bnf-shortlist-reason`, `bnf-pv-*`, `bnf-conc-*`, `bnf-pc-*`, `bnf-pg-*`, `bnf-pk-*`, `bnf-sl-*`, `bnf-xv-*`, `gk-cursor`, `bb-*`.
- Point `--muted` at the muted ink (#5b6573).

**Tests** (behavioural, synthetic data).
- Pure:
  - `presented` and `room`: none starred, recommended plans counted, the cap at 16.
  - `order.layout`: groups, consolidations, versions behind originals, stop-loss as added, a rate edit moves nothing.
  - `slots`: replace, swap, add beside, refusals; a recommended plan picked over loses its recommendation; `replaces` sets traded.
  - `enrollment_for`: every step, the census-arrival rule both ways, the switch off, the stop-loss medical default.
  - `facts` (incomplete without a total; `incumbent`), `closeness`, `board.clean_config`.
- Services:
  - stars: the cap and reason, the auto-link; a role change clears the star; clear shortlist touches one line;
  - order and lines: one order per line; `move_line` keeps the id and refuses in words;
  - delete: soft delete and revert, refused after a later write;
  - review `clear`; a priced dry run equals the commit and keeps rates;
  - an unchanged enrollment save writes nothing; private saved views answer 404;
  - PATCH ignores role and star keys; a hand edit keeps doc, page, cell and `read`.
- Selectors and files:
  - as-quoted order from `col`; stop-loss figures and workbook; board export equals the screen;
  - queries do not grow from 10 to 600 plans; a synthetic 600-plan payload stays within budget;
  - two concurrent stars at the cap leave 16.
- Frontend: Vitest, a developer decision under "tested and easy to test", for `filter.js`, `finder.js`, `sort.js`, `gridKeys.js` and `pageRows.js`.

## F.7 Open questions for Daniel

1. Should the priced-version composer (concession, bundle, premium holiday) stay, making ordinary plan copies marked "made from"? 2V §15 lists priced versions as a non-goal, but "the entire Advisor" keeps them. Can bundle templates wait?
2. Need 3 says "recreate the exact order and rows of the scanned quote in the viewer". Did you mean (a) the Documents viewer showing the carrier's file as in Excel, (b) an "As quoted" layout on the Advisor rebuilt from the read, or (c) the client files in the quote's order? We build (a) and (b). (c) holds for plan order only, because the client files keep the house rows.
3. Should Rank on a filtered board clear hand-picked stars outside the filter? Today it clears the whole line.
4. Does intake's Monthly Budget Target mean the medical premium, or all lines together?
5. Florida Blue 5182 / 5183: two plans printed as one column (D-219), or one plan "5182 / 5183" (2V §5.4, the default)?
6. Should saved setups (Mine and Shared, plus stop-loss settings) stay? 2V §15 listed them as a non-goal.
7. Is Claude Unleashed (the sandbox copy and its gold pill) in scope?
8. Once a line has stars, should its renewal need its own star to print (the old rule and our default), or always print (2V's draft default)?
