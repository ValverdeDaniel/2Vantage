# Part J — Proposal and export viewer

[← Porting plan](README.md)

**What it is:** The Proposal module turns the Advisor's plans into what the client receives. It has three screens. The proposal builder is an Advisor view where the producer picks plans, sets the slot order, writes the words and sets the pages and the look. The Export viewer is an Advisor view that previews Excel, PowerPoint, Paper and PDF exactly as each file downloads. The Proposal tab is the comparison grid with the packet card, where Issue and the sale start. The module rebuilds the three client files (the presentation PDF, the PowerPoint and the client spreadsheet) in the formats already built.

Roots: old `c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/`, new `c:/Users/fooba/OneDrive/desktop/Vantage_all/2Vantage/`. Tags: [C] = added by the critic, [A] = opened by the analysis, [F] = opened by the finaliser. Untagged = the deep report. "chN" marks a change made because of challenge N; J.6.12 lists every ruling.

## J.1 Files read, in order (one line each)

**Specs and READMEs**

| File (lines) | What it is / what it taught |
|---|---|
| `benefits/README.md` (394) | Module map; the client set is always `proposal_plans` |
| `benefits/pipeline/README.md` (716) | One entry per proposal module |
| `frontend/src/components/benefits/README.md` (421) | How the builder, ExportViewer, CoverPicker and import are wired |
| `PlanningDocs/Benefits/export-viewer.md` (327) | D-193/194/196: a preview equals the download and writes nothing |
| `PlanningDocs/Benefits/plan-order-everywhere.md` (74) | D-220: one order; nothing sorts on a value |
| `PlanningDocs/Benefits/proposal-plans-card.md` (89) | D-210–212: ★ means "on the proposal" |
| `PlanningDocs/Benefits/proposal-pages-and-picker.md` (114) | D-221–223: 6 plans a slide; a pick replaces. Untracked [C] |
| `PlanningDocs/Benefits/proposal-presentation-format.md` (83) | The Presentation format |
| `PlanningDocs/Benefits/proposal-presentation.md` (90) | Story order |
| `PlanningDocs/Benefits/proposal-packet.md` (72) | Packet rules |
| `PlanningDocs/Benefits/nov5-call-fixes.md` (34) | The latest call's fixes; Daniel's open calls on the pair fold [F] |
| `PlanningDocs/Benefits/decisions.md` (5,528) | D-079 to D-223, the proposal decisions |
| `PlanningDocs/Benefits/proposal-packages-and-outputs.md` | Headings only (backlog) |
| `PlanningDocs/Benefits/proposal-in-spreadsheet-out.md` (1,807) [F] | The stop-loss analysis workbook "remains the document" |

**Models**

| File (lines) | What it is / what it taught |
|---|---|
| `benefits/models/pipeline.py` (Plan 13–224 and three more) | Plan's proposal fields; ProposalShareLink, ProposalSelection, ProposalTemplate |
| `benefits/models/case.py` 1309–1402 | AgencyProfile, AgencyCoverImage, AgencyTeamMember; `proposal_config` JSON |
| `benefits/models/radar.py` | ClientPlanYear: history and the renewal letter's four facts |

**Rules and services**

| File (lines) | What it is / what it taught |
|---|---|
| `pipeline/composition.py` (843) | Config cleaner, `merge_config`, `write_plan_order`, `set_table_note`, card stats, highlights [A 96–200] |
| `pipeline/presentation_model.py` (1,031) | House row maps, page plan, `pair_slides`, `deck_sequence`, `negotiated`; `chunk` is the spreadsheet's page rule on counts [F 565–600] |
| `pipeline/proposal_tokens.py` (96) | Colours, type floors, 16:9 geometry |
| `pipeline/option_numbers.py` (61) | `ensure(persist)`: Max() plus bulk_update, no lock [A]; stamps at the first client build [F] |
| `pipeline/proposal_ready.py` (78) | Missing picks, Draft text; a current plan is an answer; kept lines need none [A][F] |
| `pipeline/proposal_review.py` (123) | Card marks; `cards_marked` costs no query (D-139) [A][F] |
| `pipeline/disclaimers.py` (71) | Disclaimer texts |
| `pipeline/plan_slots.py` (177) | The picker's swap and add rule; untracked [C][A][F] |
| `pipeline/plan_links.py` (174) | "Replacing" links |
| `pipeline/stars.py` (108) | Room and the 16 cap |
| `pipeline/plan_math.py` 55–100 [F], 370–710 | `tier_counts_with_source` (typed, census, proxy); membership, layout, move, swap |
| `pipeline/presentation_math.py` (236) | Formula twins; contribution modes, credit, slot and package change, `cost_summary` [F] |
| `pipeline/packages.py` (438) | `derive`/`publish`; `replacing_caption` reads `client_name` [F] |
| `pipeline/exec_summary.py` (1,448) | 13 line and 8 deal blocks; standard and new-business sets [A]; renewal blocks [F] |
| `pipeline/proposal_checks.py` (385) | 18 before-you-export checks |
| `pipeline/plan_merge.py` (434) | The pair fold: pure, client files only [F] |
| `pipeline/markets.py` (313) | Markets checked |
| `pipeline/value_format.py` (143) | Money format, `sbc_link` |
| `pipeline/sale.py` (162) | Mark sold → stage, client, `book_case` [C] |
| `pipeline/plan_remove.py` (193) | Guards on Remove column [C] |
| `pipeline/current_plans.py` (212) | Current-plan actions [C] |
| `pipeline/renewal_pairs.py` (57) | Add renewal [C] |
| `pipeline/plan_line.py` (141) | Move to line; renumbers [C] |
| `pipeline/enrollment.py` (194) | Typed per-plan counts [C] |
| `pipeline/concessions.py` (1,002) | Priced versions; auto-star [C] |
| `pipeline/medicare.py` (52) | Ages for the 65+ block [C] |
| `pipeline/contribution_math.py` (58) | Employee cost [C] |
| `pipeline/workbook_import.py` (378) | Plan template import [C] |
| `pipeline/advisor.py` (715) | `MAX_SHORTLIST`; the rank stars only within room [C][F 495–515] |
| `benefits/lines.py` 130–160 [F] | Worksite lines borrow the medical tally as source `proxy` |
| `market/coverage.py` (577) | Coverage intent, lines off [C] |
| `market/value_review.py` (492) | Review marks [C] |
| `docscan/export_guard.py` (114) | Formula-injection guard [C] |
| `commissions/services.py` (1,694) | `book_case` [C] |
| `benefits/signals.py` (71) | post_delete file cleanup [C] |

**Views and payloads**

| File (lines) | What it is / what it taught |
|---|---|
| `serializers/pipeline.py` 1–1168 [A 600–660; F 738–760, 1215–1235, 1545–1570] | `proposal_payload`; `strip_client_payload` blanks `shortlist_reason`, sources, marks; `_picks_by_current`; `builder_summary`; `client_selection_payload` reads only `selected_plan`; RFP cards off on purpose |
| `serializers/overview.renewal_offer_for` [F], `versions.live_number` | The letter's four facts on ClientPlanYear; "Version N" |
| `serializers/journey.py` (557) | Journey reads proposal state [C] |
| `views/pipeline.py` 800–1110, 1245–1380 [F], 1378–1566, 2015–2260, 2365–2479 | Star, order, slot, files, preview, share, templates; Advisor, stop-loss and contribution exports; firm-level cover tiles |
| `views/covers.py` (113) | Covers, stock images, share hero; any benefits user may upload [F] |
| `views/presentation_pages.py` (246) | Team endpoints, `page_ledger`; firm Fix ▸ goes to the Data Hub [F] |
| `views/cases.py` 376–466 | Case PATCH, `merge_config`, edit lock |
| `benefits/urls.py` | Routes |
| `docscan/serving.py`, `users/permissions.py`, `backend/settings.py` | Serving, partner refusal, anonymous throttle [C] |
| `usage/features.py` (136) | Usage keys [C] |
| `devtools/checks/benefits_checks.py` (763) | Smoke checks [C] |
| `management/commands/seed_plan_links.py` (92), `seed_renewal_story.py` (223), `prune_orphan_media.py` (163) | Data fix, demo, media sweep [C] |

**Painters, file builders and viewers**

| File (lines) | What it is / what it taught |
|---|---|
| `pipeline/proposal_pdf.py` (1,703) | Classic PDF; `build_from_payload`; `_Shape.fit`; `_why_for`, `KEEP_CURRENT_WORDS`, "Prepared by" [F 1038–1064, 1280–1300] |
| `pipeline/proposal_presentation.py` (2,005) | Presentation story; agenda and dividers only when framed [A 1972–2000]; recommendation pages [F 325–340, 1415–1530] |
| `pipeline/proposal_deck.py` (1,066) | Replays the platypus pass into python-pptx; Arial has Helvetica's metrics; imports `_processed_frags` [A][F] |
| `pipeline/presentation_content.py` (173) | `with_content`, `document_cover` |
| `pipeline/proposal_furniture.py` (750) | Cover, agenda, section, closing, chrome |
| `pipeline/proposal_covers.py` (340) | 7 designs; docstring says six |
| `pipeline/stock_images.py` (219) | Stock pictures, crops |
| `pipeline/branding.py` (227) | Logo and colour; `FieldFile.path` |
| `pipeline/presentation_workbook.py` (2,166) | Client spreadsheet [A]; guarded totals, "never SUMPRODUCT"; no Draft mark; no per-line reasons [F 360–380, 855–990] |
| `pipeline/presentation_bank.py` (1,533) | Quote list, Dynamic Compare |
| `pipeline/presentation_styles.py` (639) | Formats; `print_plan` breaks by width and carrier [F 485–530] |
| `pipeline/workbook_preview.py` (389) | Excel view; reads the look through `sheet_format.look` [A][F] |
| `pipeline/workbook_values.py` (704) | MiniBook; a closed list of 11 functions [A][F] |
| `pipeline/workbook_text.py` (298) | Number formats as Excel shows them |
| `pipeline/workbook_pages.py` (189) | Printed-pages model |
| `pipeline/proposal_preview.py` (185) | One PDF build plus a page log, sent as base64 [A] |
| `pipeline/proposal_paper.py` (67) | pypdf placement at 75% |
| `pipeline/proposal_packet.py` (138) | Zip |
| `pipeline/proposal_templates.py` (287) | Template cleaning |
| `pipeline/workbooks.py` (2,056) | Internal spreadsheet, blank template [C]; stop-loss analysis workbook, a live model [F 1670–1700] |
| `docscan/sheet_format.py` [C][F] | Viewer look reader: no number formats; skips files over 5 MB |
| `guide/layout.py` (511), `guide/render_pptx.py` (326), `guide/render_pdf.py` (229), `guide/typefaces.py` (58), `guide/fonts/*.ttf` | Benefit-guide painters reused by the furniture |
| `pipeline/rfp_bundle.py` 45–66 | The proposal PDF as an RFP card |

**AI**

| File (lines) | What it is / what it taught |
|---|---|
| `benefits/ai/page_context.py` (667) | `_proposal`, `_export_viewer`, `_export_workbook`; rebuilds the preview every turn [C] |

**Frontend** (under `frontend/src/`)

| File (lines) | What it is / what it taught |
|---|---|
| `services/api/benefitsClose.js` 85–334 | Proposal API calls; stop-loss, contribution and Advisor exports [F 190–230] |
| `services/api/benefitsShared.js` (423), `benefitsRadar.js`, `benefitsMarket.js` | Shared calls [C] |
| `utils/download.js` (88), `format.js` (198), `usage.js` (212), `chromeless.js` (13) | Downloads, JS money format, usage, print chrome [C] |
| `close/planOrder.js` (109) | Interleaved order on screen |
| `close/keyRows.js` (45) | `KEY_ROWS_BY_SET`; `sl_lasers` at line 22 |
| `close/proposalRows.js` (52) | `designText` twin |
| `close/planFinder.js` (25) | Search index |
| `close/OrderArrows.jsx` (36) | ◀ ▶ |
| `close/PlanLinkPicker.jsx` (44) | "Replacing:" |
| `close/PlanPicker.jsx` (298) | Slot picker; untracked; greyed reasons worked out in the browser [F] |
| `close/ProposalPages.jsx` (487) | "What the client will see"; untracked |
| `close/ProposalPlansCard.jsx` (441) | Plans card; ✕ |
| `close/BuilderCard.jsx` (79) | Collapse and mark |
| `close/EnrollmentStrip.jsx` (145) | Expected enrollment; "Borrowed from the medical census" [F] |
| `close/ExecutiveSummary.jsx` (59), `AtAGlance.jsx` (45), `PackageSummary.jsx` (97), `MarketsChecked.jsx` (59), `NextSteps.jsx` (20) | Client blocks |
| `close/NextStepsCard.jsx` (84) | Next steps editor |
| `close/OutputPanel.jsx` (182) | How the documents look |
| `close/CoverPicker.jsx` (256) | Cover tiles via pdf.js |
| `close/PicturesCard.jsx` (168) | Pictures per place |
| `close/TemplateBar.jsx` (284) | Saved templates |
| `close/PresentationPagesCard.jsx` (300) | Page switches, ledger |
| `close/FirmPagesPanel.jsx` (282) | About, calendar, team; `bnf-present-*`, `bnf-firm-*` [F] |
| `close/HubTab.jsx` (349) | Agency card: colour, logo, facts [C] |
| `close/ProposalBuilder.jsx` (2,131) | Builder; save queue 334–388; RENEWAL chip on `client_type` [F 1240–1250] |
| `close/useExportPreview.js` (137) | 900 ms rebuild; the stamp ignores `review` [A] |
| `shared/PdfPagesPreview.jsx` (125) | Page canvas |
| `close/ExportViewer.jsx` (892) | Chips and the deck viewer [A]; Paper's download is "Letter PDF" [F 60–110] |
| `close/WorkbookViewer.jsx` (531), `WorkbookPages.jsx` (160), `shared/WorkbookGrid.jsx` (447) | Excel view (`xg-*`) |
| `close/AdvisorTab.jsx` (excerpts) | VIEWS: Quote comparison, Stop-loss, Proposal builder, Export viewer, Unleashed [A]; copies the grid's `displayValue` [F 330–345] |
| `close/useComparisonStore.js` (101) | Hand-written store |
| `close/ComparisonGrid.jsx` (1,365) | The Proposal tab grid |
| `close/ComparisonStatus.jsx` (62) | Load panel and refresh chip [C] |
| `close/pricedKinds.js` (180), `compliance.js` (66), `sourceDocs.js` (16) | Chip sentences [C] |
| `close/PlanTemplateImport.jsx` (89) | Import [C] |
| `close/UnleashedView.jsx` (558) | Unleashed seam [C] |
| `close/StopLossAnalysis.jsx`, `implementation/ImplementationTab.jsx`, `market/CarriersTab.jsx` | Callers of the extra exports; located only [F] |
| `shared/useGridKeys.js` (435), `useWindowedPlans.js` (224), `useGridSizes.js` (251), `useFreezePanes.js` (40), `useWriteQueue.js` (60) | Grid mechanics [C]; per-cell undo, 50 deep [F 1–90] |
| `shared/EditModePrompt.jsx` (99), `ReviewBulkBar.jsx` (106), `valueReview.js` (160), `ClaudeLockSwitch.jsx` (44), `CompletedMark.jsx` (46), `findText.js` (49) | Grid and builder parts [C] |
| `benefits/planGroups.js` (119), `benefits/lines.js` (40) | Copies of vocabulary [C] |
| `market/CoverageIntentPanel.jsx` (1,112) | Intake's panel [C] |
| `commissions/BookingSummaryModal.jsx` (209) | Shown after a sale [C] |
| `contexts/EditSessionContext.jsx` (205) | Edit sessions [C] |
| `close/ProposalPacketCard.jsx` (353), `ProposalShareModal.jsx` (110), `ProposalShare.jsx` (809), `ProposalPrint.jsx` (642), `DocumentNotes.jsx` (25) | Packet, share, /p/, print page |
| `guides/proposalBuilder.js` (323) | Walkthrough anchors [C] |
| `App.jsx` | Routes |

**Styles**

| File (lines) | What it is / what it taught |
|---|---|
| `styles/benefits-export.css` (479) | `bnf-xv-*`, `bnf-xw-*`, `xg-*` |
| `styles/benefits.css` (6,275) | Builder 4026–4633 (merged pair 4336–4338, edit lock 4445–4452 [F]); grid 346–380; arrows 626–658; covers 5568–5625; `--bnf-doc-*` 989–1007 (print and /p/ only) [A] |
| `styles/benefits-grid.css` (200), `benefits-freeze.css` (104), `benefits-grid-sizes.css` (92) | The grid's look [C] |
| `styles/benefits-unleashed.css` (877) | Overrides the viewer classes [C] |
| `App.css` (4,357) | Base tokens, `.btn` [C] |

**Tests** (names only): `export_preview`, `workbook_preview`, `plan_slot`, `client_gate`, `proposal_packet`, `proposal_pdf`, `output_options`, `covers`, `cover_images`, `stock_images`, `plan_merge`, `plan_links`, `presentation_format`, `proposal_review`, `presentation_model`, `presentation_bank`, `presentation_bryke`, `builder_polish`, `presentation_workbook` (5,797), `presentation`, the `pipeline_tests` order classes; from the critic: `agency_logo`, `at_a_glance`, `big_deal_speed`, `client_document`, `client_outputs`, `compare_slots`, `composite_rates`, `export_guard`, `intent_outputs`, `plan_counts`, `print_page`, `table_note`, `multiline`, `current_plans`, `grid_sizes`, `value_review`, `template_import`, `claude_lock`.

**2Vantage, read for fit**

| File (lines) | What it is / what it taught |
|---|---|
| `CLAUDE.md` (43) [A] | The chain, rules 1–9 |
| `plan.md` §3.3, §5.4–5.5, §6.6–6.10, §7.7, §7.9, §8.11–8.17, §9.4–9.7, §12–16, App. C [A][F] | M6 built, M7/M8 planned; §15 ruled out previews, slot swaps, merges and proposal templates; §5.4 bars recommending a current plan (Daniel, 2026-11-10) |
| `proposals/models.py`, `selection.py`, `services.py`, `selectors.py`, `preview.py`, `formatting.py`, `views.py`, `urls.py`, `golden.py`, `tests/test_proposal.py` [A] | ProposalConfig; the carrier-grouped order; a GET creates a row; lines gated by `requested_lines` [F] |
| `quotes/models.py`, `marks.py`, `selectors.py`, `packages.py` [A] | `option_label` unique per deal; `recommended` refused on a current plan; `sold` any number; `lines_summary` queries per line [F] |
| `quotes/math.py` (176), `values.py` (91), `template.py` (290), `fields.py` (205) [F] | `round_money` at 15 digits; no `base_ids` for a current plan; no proxy; rates in cents; openpyxl-only formula guard; `client` flags; `plan_notes` |
| `deals/models.py`, `activity.py`, `values.py`, `stages.py`, `lines.py`, `downloads.py` [A] | Activity merges 10 minutes per key; `locked()`; `safe_filename` |
| `documents/kinds.py`, `documents/models.py`, `backend/meta.py`, `requirements.txt` [A] | Kind `proposal`; no reportlab, pptx, pypdf or XlsxWriter yet |
| `frontend/src/api/proposals.js`, `deal/proposal/*.jsx`, `lib/download.js`, `styles/tokens.css` [A] | Simplified M6 UI |

## J.2 Old data model, in brief

- **`BenefitsCase.proposal_config`** is one JSON blob, cleaned by `clean_proposal_config` and merged one top-level key at a time. It holds:
  - the words: `title`, `intro`, `recommendation`;
  - the picks: `recommended_plan_ids`, `recommended_by_current`, `recommendation_by_line`;
  - `next_steps`, `experience`, `team`, `tier_counts` (no screen), `tier_counts_by_line`;
  - `composition`: `exec_summary`, line `order`, `markets_checked`, and per line `parts`, `rows`, `plan_ids` (vestigial), `card_stats`, `plan_order`, `market_notes`/`market_hidden`, `table_note`, `merged`;
  - `output`: style, orientation, density, layout, cover, sections, pages, `link_period`, `compare_tabs`, `disclaimers`, `compare_slots`, pictures, `cover_image`;
  - `review`: the card marks.
- **Plan fields the proposal reads or writes:** `is_shortlisted` (★), `shortlist_reason`, `is_current` (several allowed), `sort_order`; `renewal_of`, `compares_to`, `concession_of`, `concession`; `option_number`, `client_name`, `enrollment {counts, on}`, `is_sold`, `read_state`.
- **Sharing:** ProposalShareLink (token, email, 7-day expiry, old single-pick fields); ProposalSelection (one pick per link and line).
- **Templates:** ProposalTemplate (seven kinds; four have UI).
- **Firm records:** AgencyProfile (facts, `producer_name`, `about_*`, `service_calendar`), AgencyCoverImage (≤24), AgencyTeamMember (≤40), ClientPlanYear (history and the renewal letter's four facts, D-039).
- **Built on every read by `proposal_payload`:** membership, order, rows, picks, executive summary, at a glance, packages, page plan, document facts (stamp, Draft, version, disclaimers). Option numbers are stamped during this read.

## J.3 Functionality inventory and verdicts

### J.3.1 Membership, order, slots and links (needs 7, 8, 9)

| # | Functionality (what the user sees -> how it worked) | Verdict | New implementation |
|---|---|---|---|
| J1 | ★ puts a plan on the proposal -> `star-plans/`, `check_room`; a current plan takes no star; a lost deal is refused | Keep | quotes star service (Advisor) with `room()`; replies with the changed plans |
| J2 | Membership: current plus starred plans, or every quote when none is starred; lines the intent leaves off are removed | Keep, fixed | quotes `presented()`; a line shows when it has presented plans unless intake's intent leaves it off; `requested_lines` no longer gates it (B31, ch9) |
| J3 | 16 columns per line; the PDF and deck refuse past it; the spreadsheet never refuses | Keep | quotes `room()`; one `oversize()` for every door; a folded pair counts once (B17) |
| J4 | One order: current plans in slot order; each one's group (renewal, then quotes as added, each priced version behind its original); unlinked plans last; hand order inside groups | Keep | quotes `order.layout` only; 2V `selection.ordered` retired (B28) |
| J5 | Arrows: ‹ › on page columns, ◀ ▶ on grid headers; each refusal has a sentence | Keep | quotes move service |
| J6 | "Back to the default order" | Keep | quotes move `reset` |
| J7 | Stop-loss refuses arrows and slot picks (add only) | Simplify | one order rule for every line (Q5) |
| J8 | Picker list: "On the proposal" (CURRENT k, RENEWAL of k, ★, priced, page p.N), then "Other scanned quotes"; rows that cannot go there are greyed with the reason | Keep | `pages/PlanPicker.jsx` over the pages payload's light `others` list; the server words each greyed reason (ch23; ends B6's browser copy) |
| J9 | Picker search by name; ↑↓, Enter, Esc | Keep | `src/lib/findText.js` |
| J10 | Pick into a spot: the picked plan takes the spot's place, star and links; a plan off the proposal replaces one on it; the star count never changes; the recommendation lapses; a warning before a renewal page comes down | Keep | quotes slot service: one transaction, Deal lock, Activity before/after; clears `recommended` on the plan that leaves |
| J11 | ＋ Add a plan beside a current plan; landing note ("Page 1 is full…") | Keep | quotes slot `{beside}`; the note comes from the refreshed pages payload |
| J12 | "Replacing:" on lines with 2+ current plans; links clear when the target stops being current | Simplify | quotes links on 2V `replaces`; several allowed (a consolidation) |
| J13 | ✕ takes a plan off; on an unstarred line it stars every other quote; it confirms when the plan is the recommendation | Keep, fixed | past room it refuses with a sentence that names the fix (B5) |
| J14 | ⋯ More → "Name on client documents" | Simplify | `Plan.client_name` in quotes, on the PATCH whitelist, carried by copies (ch8: quotes' package captions read it, and an id map in config goes stale) |
| J15 | One column with… / Split (two plan numbers printed as one column) | Keep (was Defer; ch5) | a pure fold over `lines[line].merged` (≤8 pairs), for client files only, run before `pages.py` counts columns; its total is quotes' `package()` of the pair; the `split_plan` check and CSS stay; slice P6; Q12. Why changed: the 2026-11-05 call asked for it, and the Advisor keeps both plans, so it does not wait for Advisor pairs |
| J16 | Key rows / All rows (display only, localStorage) | Keep, fixed | key rows come from `/api/meta/` and never include a client-hidden field (B3) |

### J.3.2 Builder shell and toolbar (Advisor ▸ Proposal builder)

| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| J17 | The builder is the Advisor view "Proposal builder" | Keep | `deal/proposal/builder/`, handed to the Advisor's view switch by the route |
| J18 | Cards collapse; a completed mark per card; "n of N completed"; Expand/Collapse all | Keep (was Simplify; ch19) | marks stored in `config.marks`. Why changed: computing fingerprints on read would cost a full build per deal in lists |
| J19 | An edit clears its card's mark (`clearMarkAfterEdit` in the browser) | Simplify | `set_config` clears the card that owns each changed path in the same write; quotes' on-commit `plans_changed` clears the line's Plans card after star, slot, order and Claude writes (ch19) |
| J20 | Save queue, `savedBranch`, `settleSaves`, "Go ahead anyway?" | Simplify | PATCH one path at a time, merged on the server; downloads wait on `useIsMutating()` |
| J21 | Edit lock: "<name> has this proposal open", Take over | Drop | edit sessions are dropped (Wave 1) |
| J22 | RENEWAL chip | Keep (was Defer; ch28) | shown when the client already bought from us (an earlier sold deal), the deal type Agenda also uses. Why changed: it needs no renewal workflow |
| J23 | "n to check": the Before-you-export list (Stops / Check / Note) with Fix ▸ | Keep | pure `checks.py`, 17 checks (`demo_firm_pages` dropped) |
| J24 | Client PDF, PowerPoint and Client spreadsheet buttons, with a busy state | Keep | draft GETs |
| J25 | Orientation chip | Defer | Classic only (Q1) |
| J26 | Share with client | Defer | see J156 |
| J27 | Open proposal ▸ | Simplify | opens the Export viewer |
| J28 | `ready_message` banner | Keep | `ready.py` |
| J29 | "Nothing to build yet" panel | Keep | the builder payload has no lines |
| J30 | Off-the-proposal notice: Open the intent card, Put it on, "— they have it today", "— as new coverage" | Keep | intake's coverage-intent service |
| J31 | Line tabs: Off / guaranteed / new chips, ✓ when done, ◀ ▶ line order | Keep | `config.order`; the chips come from intake |

### J.3.3 Builder deal cards

| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| J32 | Cover tiles: pages of a server PDF drawn by pdf.js (7 designs, then uploads) | Keep, fixed | firm-level `proposal/covers/` built from stored thumbnails (≤600 px), with an ETag (ch24); `src/viewer/pdfjs.js`; a Retry per tile (B19) |
| J33 | Upload or delete a cover picture | Keep | `CoverImage` through documents' images helper (ch25) |
| J34 | Cover page on/off; Title; Introduction | Keep | `output.cover.on`, `title`, `intro` |
| J35 | Pictures per place (cover, agenda, sections, thank-you): stock, upload or none | Keep | pre-cropped stock files; catalogue in meta |
| J36 | Format: Presentation / Classic | Defer | Q1 |
| J37 | Classic orientation and density | Defer | Q1 |
| J38 | Layout: by carrier / side by side / best only (best only waits for every pick) | Keep | `output.layout`; `pages.py` |
| J39 | Package summary on/off | Keep | `output.package_summary` |
| J40 | Share-link period | Defer | share link |
| J41 | Spreadsheet: Compare tabs, Disclaimers tab, Compare columns 5/10/16 | Keep | `output` |
| J42 | Page switches plus ledger (prints, or why not, with Fix ▸) | Keep | `story/ledger.py` inside the builder payload; a firm Fix ▸ opens the Firm pages drawer |
| J43 | Team picks (null = firm default) | Keep | `config.team` |
| J44 | Past plan years; "Add a past year" | Defer | earlier years' history waits for renewals (Q10) |
| J45 | Plan experience: summary plus ≤6 periods | Keep | `config.experience` |
| J46 | Coverage & marketing intent card | Keep | intake's component; its mark lives in proposals |

### J.3.4 Builder line cards

| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| J47 | Plans on the proposal card; kept lines show the incumbent card instead | Keep | builder payload per line |
| J48 | EnrollmentStrip: expected enrollment, source label, Edit / Clear | Simplify | writes quotes `LineEnrollment` (tiers, volume or lives); sources typed → census → proxy ("Borrowed from medical") → none; a later census import wins (need 6; ch10; Q13) |
| J49 | Page tables: "Page n of N · caption", "x of 6 columns · full" | Keep | `GET proposal/pages/?line=` |
| J50 | Column head: place, CURRENT k / RENEWAL / PRICED, ‹ ›, ✕, Today / Option n, name button, Replacing:, ⋯ | Keep | `pages/PageColumn.jsx` |
| J51 | Rows: Monthly premium; Change vs current ($/mo · %); key or all rows | Keep, fixed | the server formats every cell (B17) |
| J52 | "Our recommendation" row: Recommend / Keep this plan | Simplify | 2V `recommended` flags; "Keep this plan" recommends the current plan's renewal and prints the old words; kept lines need no pick (B36; ch3 modified; Q4) |
| J53 | Unstarred line with more than 2 pages: two pages plus "Show every page" | Keep | local state |
| J54 | Toast when a write adds a page | Keep | page counts before and after |
| J55 | Recommendation status; "Recommend the renewal for every plan" | Keep | quotes `recommendation()`; batch recommend |
| J56 | "Why this, in your words" (per line, saved on blur) | Keep | `reasons[line]` |
| J57 | The deal-wide recommendation words | Keep, fixed (was Simplify; ch2) | one pure `why_for(line)` for all files: the line's words, else the deal-wide words only when no line has its own; the deal-wide words stay in the glance notes; the spreadsheet cover lists each line's reasons when the deal-wide words are blank (B7). Why changed: the PDF and deck already printed them, and printing them on every line would put medical words under dental |
| J58 | See the slides ▸ | Keep | Export viewer `?file=powerpoint&line=` |
| J59 | Part switches; client-facing stop-loss row preset | Keep | `lines[line].parts`; preset in the catalogue |
| J60 | Note under the table (≤4 lines, 600 characters) | Keep | `lines[line].table_note`; also a Claude tool |
| J61 | "On the plan cards" stats (≤6; reorder, remove, back to standard) | Keep | `lines[line].card_stats`; they also feed the recommendation panel |
| J62 | Row picker by group (all / none) | Keep | `lines[line].rows` (null = every row with a value) |
| J63 | Markets checked: Show it / Back to automatic; "no RFP sent" hint; unmatched names; per carrier: Quoted, On this proposal, note, show/hide | Keep | `rfp.markets()` imported directly (ch27) plus `config.markets` |

### J.3.5 Executive summary, next steps, templates

| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| J64 | Summary: Show it; 13 line and 8 deal blocks; standard (8) and new-business (5) sets; all / clear; ▲ ▼; pin a block to a line; live preview with the reason a block is unavailable | Keep | `summary_blocks/` (pure); catalogue in meta |
| J65 | Renewal blocks (`renewal_offer`, `renewal_vs_recommended`) | Keep (was Defer; ch28) | they read the renewal letter's four facts, asked of intake's CurrentCoverage; any deal that has them, new business included. Why changed: the incumbent's letter is asked for on every deal |
| J66 | Medicare-eligible (65+) block, medical only | Keep | census ages rollup; no birth date leaves the server |
| J67 | Next steps: ≤8 rows of date and text | Keep | `config.next_steps` |
| J68 | TemplateBar (layout, rows, summary): Built in / Mine / Shared; Save as, Update, Delete; dialog with Name, Purpose, Offer it on, Share | Simplify | `ProposalTemplate` with 3 kinds; the built-in default lives in code (Q6) |
| J69 | Template kinds `cost_summary`, `recommendation`, `proposal` | Drop | no UI |

### J.3.6 Proposal tab (plan comparison grid)

The tab is the Advisor's board component in a "presented plans" mode that keeps this tab's toolbar, chips and legend, plus the packet card. The route composes the two, so neither folder imports the other (ch31: the old grids drifted, `AdvisorTab.jsx:339`).

| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| J70 | "Plan comparison" title, refresh chip, load panel with Retry | Keep | `tab/ProposalTab.jsx` |
| J71 | Legend (Verified / Review / Approved / Ignored / Needs checking / Missing); cells coloured by mark | Keep | the shared board; documents' review rules |
| J72 | Claude lock switch | Keep | ai `DealAi.lock` |
| J73 | ✎ Edit / Done; double-clicking a locked cell offers Edit | Simplify | a local mode only; no session, no version |
| J74 | ↶ Undo, Ctrl+Z | Keep (was Simplify; ch1) | the grid's per-cell undo stack (50, this ✎ Edit session); Undo writes the earlier value through the values write with `expect`, refused if the cell changed since; Activity's "Revert this change" stays in the log. Why changed: Activity merges 10 minutes of edits, so reverting it undid a whole burst |
| J75 | Excel-like resizing, ↺ Reset sizes, sizes kept per user | Keep | `src/grid/` |
| J76 | ★ Shortlist (n) / Show all N plans | Keep | local filter over the presented ids |
| J77 | Import plan template | Keep | quotes template (built) |
| J78 | ＋ Add plan (carrier, name, Enter) | Keep | quotes create |
| J79 | ＋ Add quotes / ＋ Add SBCs | Keep | opens the Work with Claude drawer |
| J80 | ⟲ Re-read quotes (apply job; a toast per staged reason) | Simplify | ai job; `useAiState` is the only poller |
| J81 | 🧭 Advisor; line tabs with counts | Keep | counts from quotes `deal_state()` (B32, ch22) |
| J82 | Stop-loss "Show me how ▸" | Drop | a walkthrough |
| J83 | Enrollment-source notes (none / typed / medical proxy / per-plan counts) | Keep | the source from `enrollment_for`, which gains `proxy` (B35, ch10) |
| J84 | Bulk review bar (approve, ignore, needs checking, re-check) | Keep | `src/valuereview/`; quotes marks |
| J85 | Frozen panes, column windowing, Excel keys, "＋ Add" in a missing cell | Keep | `src/grid/` |
| J86 | Provenance tooltip, "View in document →" | Keep | sources plus the documents deep link |
| J87 | Chips: CURRENT k, RENEWAL, SOLD ✓, ★ FIT (shows the reason), priced, SBC ✓, compliance | Keep | payload flags; `star_reason` (internal only) |
| J88 | ◀ ▶ on headers | Keep | quotes move |
| J89 | ⋯ Mark as sold ✓ → stage, client, booking, BookingSummaryModal | Keep, fixed | quotes `set_sold` (several per line, Q9); commission's `sold_changed`; a booking failure is shown, not swallowed (B24) |
| J90 | ⋯ Remove as current / Add renewal / Set as current / Add as another current | Keep | quotes role and renewal |
| J91 | ⋯ Attach SBC… | Keep | ai SBC read |
| J92 | ⋯ Move to line… | Keep | quotes `move_line` |
| J93 | ⋯ Remove column (sold plans refused) | Keep | quotes soft delete |
| J94 | Cost rows: group monthly premium; % to claims funding; laser liability, maximum annual liability (MAL) and MAL vs current; employee cost per tier; tier counts in the header | Keep | quotes math |
| J95 | "Client selected" banner, Confirm & mark sold | Defer | share link |

### J.3.7 Packet, downloads and issue

| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| J96 | Packet zip of ticked files; ready gate; any failure refuses the whole zip | Simplify | the zip holds an issue's stored files |
| J97 | Single downloads | Keep | draft GETs; they write nothing |
| J98 | Internal spreadsheet (never in the zip) | Simplify (ch15) | the button downloads quotes' built plan-template export (every plan and field; round-trips through import), logged as a download because it prints `sl_lasers`; no `internal.py` |
| J99 | Benefit guide (once sold) | Defer | after the sale |
| J100 | Checks list on the card | Keep | `checks.py` |
| J101 | Every door waits for the grid's writes | Simplify | `useIsMutating()` |
| J102 | "Version n" stamp | Simplify | the issue's version; drafts wear Draft in page headers and footers, never in the cover tab's B3 (ch6; Q3) |
| J103 | Issue to client (v N), Issued list, stored bytes | New | `ProposalIssue` built by an `issue` Job (ch20); an issue also offers its Letter PDF, made from the stored PDF bytes (ch6) |
| J104 | File names `<Client> - <year> Benefits Proposal[-DRAFT]` | Keep | `safe_filename` |

### J.3.8 Export viewer (need 11)

| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| J105 | Chips Excel / PowerPoint / Paper / PDF; `?file=`; last pick remembered | Keep | `export/FileChips.jsx` |
| J106 | "Web form" chip | Drop | a placeholder |
| J107 | Builds only while shown; rebuilds 900 ms after the stamp moves; marks ignored; aborts superseded builds; keeps the last copy; refusals in the downloads' words | Simplify | React Query keyed on file, tab and the debounced files and firm stamps; staleTime Infinity, retry off, no refetch on focus or mount, previous data kept, short gcTime; enabled only while shown and nothing is saving; a refusal and a failure are shown apart (ch21) |
| J108 | Keeps the selected slide (by title and position) | Keep | viewer state |
| J109 | Deck viewer: opens on the first Medical table; ←→, PgUp/PgDn, Home/End; rail thumbnails; Jump chips with fit dots | Keep | `export/DeckViewer.jsx` |
| J110 | Fit report per table | Keep | the recorder's fit log |
| J111 | Speaker notes | Keep | page log |
| J112 | Draft badge, status line, Refresh, "Not printing" chips | Keep | preview payload |
| J113 | Classic notice on PowerPoint | Defer | Q1 |
| J114 | Paper frame plus "9 pt prints at 6.8 pt" | Keep | `paint/paper.placement` |
| J115 | Download PowerPoint / PDF / Letter PDF; Print… (window opened on the click; downloads if pop-ups are blocked) | Keep | `export/printPdf.js` |
| J116 | Workbook screen: frozen panes, zoom, run-on text, ####, read-only drop-downs, rows windowed past 160, cell select | Keep | `src/viewer/` sheet grid fed by the sheet model, one tab a request; `workbook/text.py` shows values as Excel does (ch11) |
| J117 | Printed pages: Letter, scale, repeated titles, page chips, footer number, near-edge notes | Keep | `viewer/workbook_pages.py` over the print plan |
| J118 | Checks per tab (error, ####, cut, tight) that jump to the cell; tab dots; Ctrl+PgUp/PgDn; capped tabs | Keep | `viewer/workbook_checks.py` |
| J119 | Every formula evaluated in memory (MiniBook) | Drop | the sheet model holds each formula with its stored result from quotes' math; an evaluator only in tests |
| J120 | Claude is told the file, slide, tab and fits | Simplify | the browser sends the viewer state; no rebuild per turn |
| J121 | Usage keys | Drop | analytics are out of scope |

### J.3.9 Client PDF and PowerPoint (need 12, Presentation format)

| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| J122 | One layout pass, so the PDF pages are the slides (16:9, 960×540 pt) | Simplify | keep reportlab's platypus flow through its public API (`wrap`, `split`, `drawOn`) with our own flowables that hold their text runs and cells; a recorder logs each placed frame; the PDF draws, the PowerPoint replays the frames (ch16; ends B14) |
| J123 | Cover: dark ground, client name as hero, logo, title, effective date, prepared by, picture, Draft; a Classic design prints on white | Keep | `story/opening.py`; "Prepared by" is the deal owner, else the firm (ch26) |
| J124 | Agenda and dividers, printed only together, only when switched on with ≥3 sections | Keep | `story/sequence.py` |
| J125 | About (text, ≤6 tiles); Team (≤8 cards a page) | Keep | `FirmPages`, `TeamMember` |
| J126 | Overview tiles, coverage table, kept lines, total | Keep | `story/coverage.py` |
| J127 | "What we negotiated" plus bars chart | Keep | `negotiated.py` |
| J128 | Premium chart (2+ rows); summary dashboard | Keep | `story/answer.py` |
| J129 | Renewal history page and chart | Defer | earlier years' history (Q10) |
| J130 | Plan experience (loss ratio derived); Markets checked page | Keep | `story/answer.py` |
| J131 | Renewal-set pages: ≤3 pairs a slide, never split, totals last; first-offer pages first | Keep | `pages.pair_slides` |
| J132 | "Your options" page when there are several pages | Keep | `story/answer.py` |
| J133 | Exhibit: header (Option n · carrier, RECOMMENDED), design rows (medical in/out-of-network map), Rates as "count × rate", See SBC, cost rows, notes | Keep | `rows.py` house maps |
| J134 | Cost-only line when the comparison part is off | Keep | `story/answer.py` |
| J135 | "What employees pay" pages (only when a non-current plan has an employee cost) | Keep | `story/answer.py` |
| J136 | Recommendation pages: WE RECOMMEND panel for one pick; one table for several current plans; the reasons | Keep | grouped by current plan |
| J137 | Incumbent pages; "nothing to compare" sentence | Keep | `story/coverage.py` |
| J138 | Next steps, meeting calendar, Thank-you (never hidden), bios, Important information | Keep | `story/closing.py` |
| J139 | Chrome: title 26→16 pt, rule, footer stamp, rates note, firm, page number, Draft | Keep | `layout/tokens.py` |
| J140 | Fitting: table type 12→8 pt, rows ≤2 lines, fits / notes follow / runs on, "(continued)", long values move to notes | Keep | `layout/fit.py` |
| J141 | PowerPoint: master, 4 layouts, title placeholders, native charts, notes, slide numbers | Keep | `paint/pptx/` |
| J142 | Type: Helvetica in the PDF, Arial in the PowerPoint | Keep | tokens; same metrics, so PowerPoint wraps where the layout did |
| J143 | Classic PDF and Classic PowerPoint | Defer | Q1 |
| J144 | Unleashed copy hooks; pie and line charts | Defer | Unleashed is deferred |
| J165 | Several recommended plans for one current plan | New (ch4) | J136's table with 2–3 rows under that current plan; the panel only when one plan answers each current plan; a golden case. Why: 2V allows several picks and the panel shows one |

### J.3.10 Client spreadsheet (need 12)

| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| J145 | Cover tab: banner, logo, title, intro, prepared by, summary snapshot, the recommendation words, "Figures as of this download" | Keep | `workbook/tabs/cover.py`; prepared by the deal owner |
| J146 | Markets Checked tab | Keep | `workbook/tabs/markets.py` |
| J147 | Rates tab per tier line (≤16 plans; title band; SOLD/RECOMMENDED markers; design rows; counts and rates; live totals; changes and packages with one current plan; credit and net; freeze B7; a break before each carrier) | Keep | the old formula templates ported verbatim: per-tier guards, the stated-premium fallback, text read as missing, counts through SUM; no SUMPRODUCT (B33, ch7); results stored |
| J148 | Dynamic Compare (5/10/16 drop-down slots; base-plan box; status words with fills; INDEX/MATCH; % vs current and renewal; contribution modes; 9 pt; zoom 110; the file opens here) | Keep | `workbook/tabs/compare.py`; results from quotes' contribution, credit and package math (ch13) |
| J149 | The quote list (prefixes, carrier headers, status words, a 2,000-plan cap note, prefill current → recommended → starred, the table note on top, SBC column) | Keep | `workbook/tabs/bank.py`; SBC links written one by one (ch12) |
| J150 | Composite Rates cards; All Plans (AutoFilter; unread, hidden-carrier and unrated plans left out) | Keep | `workbook/tabs/` |
| J151 | Generic, in-force and Disclaimers tabs | Keep | `workbook/tabs/` |
| J152 | File settings: agency as author, recalculation on open, zoom 130/110 | Keep | `workbook/write.py` |
| J153 | Formula-injection guard | Keep | documents' XlsxWriter helper: string-to-formula, URL and number conversion off; text only through `write_string` (B34, ch12) |
| J154 | A hidden carrier also leaves Compare and All Plans | Keep, labelled | a note on the Markets card (Q11) |

### J.3.11 Firm pages, share link, other files, machinery

| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| J155 | Agency facts, brand colour, logo (≤5 MB, re-encoded), About and figures, meeting calendar, team with photos | Simplify | logo, colour and contact stay in Django admin (`AgencySettings`, 2V rule 6); About, figures, calendar and team go to a proposals `FirmPages` singleton and `TeamMember`, edited in an in-app Firm pages drawer ported from `FirmPagesPanel.jsx`, open to every user as before (ch26 modified; Q7) |
| J156 | Mint a share link; the /p/ page; one pick per line | Defer | Q2; later in `review` on its `ClientLink`, over proposals' client Facts |
| J157 | Print page `/proposal-print` with its own editor | Drop | a second path to the same printout; its editor bypasses per-plan picks |
| J158 | GET builds stamp option numbers | Drop | Issue stamps (a POST download if Q3 is "no", ch6); previews predict with the same function |
| J159 | Option numbers: reading order, never reused, none for current plans or priced versions, renumbered on a line move | Keep | `quotes/labels.py`; reading order = first appearance in `pages.py`'s pages for the chosen layout (B4, ch18) |
| J160 | Claude tools `set_table_note`, `set_rows`; Proposal page context | Keep | ai registry |
| J161 | Claude tool `pair_plans` | Keep (was Defer; ch5) | calls `set_config` on `lines[line].merged`; slice P6. Why changed: the fold is kept (J15) |
| J162 | Management commands `seed_plan_links`, `seed_renewal_story`, `prune_orphan_media` | Drop | a one-off data fix, demo data, and a sweep made unneeded by on-commit deletes |
| J163 | Walkthrough anchors, test-only switches, dead code (B15), source-reading tests | Drop | machinery |
| J164 | Facts for Agenda and Overview | New | `summary.facts(deal_ids)`: the latest issue (version, date, by); Agenda reads issues, never marks (ch19) |
| J166 | Stop-loss analysis workbook (five tabs, live formulas; the stop-loss client document) | Keep (ch14) | owner: the Advisor section (Stop-loss view); math in quotes; written with documents' XlsxWriter helper (Q14) |
| J167 | Advisor board export (`advisor-export/`) | Simplify (ch14) | owner: the Advisor section; quotes' template export given the board's line, plans and columns |
| J168 | Contribution model (after the sale) | Defer (ch14) | after the sale; Implementation is out of scope |
| J169 | RFP packet card "Client proposal" (off on purpose: shows carriers the others' pricing) | Simplify (ch27) | owner: RFP; attaches the latest issued proposal Document, so rfp never imports proposals |
| J170 | post_delete file cleanup; smoke checks | Simplify | delete services remove files on commit; smoke checks become golden-deal tests (split from J162) |

## J.4 Data flow (in and out, by model, field or function)

**In:**
- **quotes:**
  - plan identity, client-only `values`, `client_name`;
  - `presented()`, `room()`, `order.layout()`;
  - one `deal_state(deal)` with per-plan results: enrollment used and its source, monthly and annual premium, change, `part_of`, employee cost, tier rate change, contribution, credit and net;
  - `package()`, `recommendation()`; `option_number` and `labels.numbers()`;
  - priced-version links and sentences; `star_reason`, `sold`, `read`; `LineEnrollment`; `facts.incumbent()`.
- **census:** only through quotes' `enrollment_for` (by plan name, by line, proxy), plus the 65+ count.
- **intake:** intent per line (shopped / new / kept / off); rate-guarantee date; CurrentCoverage for the incumbent pages and the renewal letter's four facts.
- **rfp** (left of proposals after ch27): `markets(deal)`: carriers asked per line, send dates.
- **deals:** client name, effective date, owner ("Prepared by"), AgencySettings (logo, colour, contact), Activity, `clock`.
- **documents:** storage, the images and XlsxWriter helpers, the viewers.
- **ai:** the viewer state the browser sends with a turn.

**Out:**
- **Own rows:** ProposalConfig; ProposalIssue with its Documents (kind `proposal`); ProposalTemplate; FirmPages; TeamMember; CoverImage.
- **Writes elsewhere:** `Plan.option_number` through quotes' stamp service at Issue; the stage moves to `proposal` (`deals.advance`); Activity rows (area `proposal`) with before/after.
- **Read by others:** `proposal/pages/` (the Advisor's Pages layout and picker); `summary.facts()` (Agenda, Overview); ai registry entries; rfp reads issued proposal Documents through documents.
- **Commission:** the tab's Mark as sold → quotes `set_sold` → commission's signal → BookingSummaryModal. The old report said proposals feed commissions nothing; booking starts here.
- **Never in a client file (ch29):** non-client fields, `sl_lasers`, commission figures, birth dates, status sentences, `star_reason` (Claude writes it from client guidance), intake's `client_guidance`, internal `Plan.notes`, sources, source and document names, review marks.

## J.5 Bugs and pain points found (with file evidence)

- **B1 GET requests write data.** `serializers/pipeline.py:1049`, `views/pipeline.py:1393` and `2163` call `proposal_payload(stamp=True)`; `option_numbers.ensure` uses Max() plus bulk_update with no lock and no Activity, so builds race.
- **B2 `proposal_config` is last-writer-wins.** `views/cases.py:441-456` reads without a lock and `merge_config` replaces `composition` whole; `write_plan_order` is unlocked (`views/pipeline.py:963`); the builder sends a stale composition (`ProposalBuilder.jsx:334-388`), so arrows, picks and Claude's `set_table_note` are lost.
- **B3 A hidden row shows on "What the client will see":** `keyRows.js:22` lists `sl_lasers` (`ProposalPages.jsx:160-166`).
- **B4 Predicted option numbers differ from stamped ones** on renewal-set lines: `ProposalPages.optionNumbers` uses deck order, `ensure` payload order. Fix: both follow `pages.py`'s reading order (ch18).
- **B5 ✕ fails on large unstarred lines:** it refuses past room (`ProposalPlansCard.jsx:166-185`, `stars.py:53`).
- **B6 Rules written twice:** `exec_summary.proposal_plan_ids` vs `plan_math.proposal_plans`; `chunk` vs `print_plan`; `designText`, `documentStyle`, `COVERS` vs server twins; `STAR_CAP`, `MAX_PLANS_PER_LINE` vs `MAX_SHORTLIST`; the JS money format; `pricedKinds.js`, `lines.js`, `KEY_ROWS_BY_SET`; the picker's greyed reasons (`PlanPicker.jsx:106`) vs `plan_slots`.
- **B7 Four renderers disagree.** The print page and /p/ lack the Presentation pages and `table_note`; `ProposalPrint.jsx:109-134` edits the old deal-wide picks; the spreadsheet prints only the deal-wide words, so per-line reasons never reach it (`presentation_workbook.py` has no `recommendation_by_line`).
- **B8 Heavy builds repeat:** the packet builds the payload once per member plus the gate and the bank; each preview also calls `presentation-pages/`; the workbook preview takes about 7 s on a 236-plan deal.
- **B9 "Version N" has no source in 2V** (`versions.live_number` is dropped).
- **B10 The client's per-line picks never reach the producer:** `client_selection_payload` (`serializers/pipeline.py:621`) reads only `selected_plan`, and the banner hides once anything is sold.
- **B11 Share links cannot be managed:** no list, revoke, extend or log; 7 days hard-coded; mint and select write no Activity; the public payload is a denylist pinned by a 299-path file; the public GET does not recheck the cap or a lost deal.
- **B12 The look depends on local files:** `branding.stored_path` uses `FieldFile.path`, so logo, covers and photos vanish on Cloud Storage; stock crops sit in the temp directory; 21 MB of originals ship in the image; the cover tiles embed up to 24 full-size uploads, rebuilt every time (`views/pipeline.py:2040-2075`).
- **B13 Production code imports demo code and other modules:** `proposal_checks` imports `seed_renewal_story`; `markets` imports `implementation.carrier_change`; the furniture uses the guide painters' private `_DRAW`; the painters import `docscan.export_guard`.
- **B14 Private reportlab internals:** `proposal_deck.py:58` imports `_processed_frags`; the deck and preview read `_cellvalues` and `blPara`.
- **B15 Dead code:** `queuedStars`, `namingPlan`; three template kinds with no UI; `composition.lines.plan_ids`; deal-wide `tier_counts`; the Web form chip; test-only switches (`FIT_HEIGHT`, `PER_CARRIER_BREAKS`, `TIER_TAB_LINES`, `BANK_TABS`, `DISCLAIMER_TAB`); docstrings say six covers, there are seven.
- **B16 Three typed-enrollment stores:** deal `tier_counts`, `tier_counts_by_line`, `Plan.enrollment`.
- **B17 Format and count drift:** `ProposalPages.cellText` prints `$797.5`; `oversize_line_message` counts a merged pair as two.
- **B18 /p/ renders live,** and nothing records what the client saw.
- **B19 A failed CoverPicker tile needs a page reload.**
- **B20 Need 9 exists only in the old working tree.** HEAD is `60688a5`; `plan_slots.py`, `plan_slot_tests.py`, `PlanPicker.jsx`, `ProposalPages.jsx`, `keyRows.js` are untracked; `QuoteFinder.jsx` is deleted; ten files are modified (`plan_merge.py` among them). Port from the working tree.
- **B21 Work with Claude rebuilds the whole preview every turn** (`page_context._export_viewer`).
- **B22 The PowerPoint view shows the deck-shaped PDF pages, not the .pptx.** Text wraps alike (Arial has Helvetica's metrics), but native charts differ and Classic deals get no PowerPoint view. Fix: label chart slides; test each pptx text box against its recorded frame (ch16).
- **B23 Hiding a carrier on the Markets card silently drops** its quotes from Compare and All Plans (`presentation_bank._hidden_carriers`).
- **B24 A booking failure after a sale is swallowed:** `sale.mark_plan_sold` only logs `book_case` errors.
- **B25 Files far over 300 lines:** ProposalBuilder 2,131; presentation_workbook 2,166; proposal_presentation 2,005; proposal_pdf 1,703; ComparisonGrid 1,365. Unleashed hooks run through the painters.
- **B26 Eight source-reading test classes,** and no JS test runner.
- **B27 (2V) A GET creates a row:** `proposals/selectors.payload` calls `ProposalConfig.for_deal` (`get_or_create`).
- **B28 (2V) A second order and a second membership list:** `selection.ordered` sorts alternates by carrier (against D-220); `ProposalConfig.lines` is a membership list beside the stars.
- **B29 (2V) The labels do not match the old documents:** `option_label` (C/R/P, unique per deal) is not the per-line "Option n".
- **B30 (2V) The planned formats are not the built ones:** plan.md §9.4 (Summary sheet; six functions) and §9.6–9.7 (a new deck; a LibreOffice PDF).
- **B31 (2V) A quote-first deal gets an empty proposal:** `proposals/selectors.proposal_lines` keeps only lines in `deal.requested_lines`, which a quick-quote deal has not set (ch9).
- **B32 (2V) Queries grow with lines:** `quotes/selectors.lines_summary` (132-155) counts each role, star, recommendation and sale per line and calls `line_state` per line (ch22).
- **B33 (2V plan) §9.4's whole-cent SUMPRODUCT total counts a blank rate as 0,** so a client's what-if count on an unrated tier gives a silently low total; the old guarded formula falls back to the stated premium or blank (`presentation_workbook.py:855-905`) (ch7).
- **B34 (2V plan) XlsxWriter's defaults** turn text starting with "=" into a formula and every http text into a link (at most 65,530 a sheet); the 2V guard (quotePrefix in `quotes/template.py`) is openpyxl-only (ch12).
- **B35 (2V) No proxy enrollment:** `quotes/math.enrollment_for` has no `proxy`, so worksite tier-rated lines the old app priced from the medical tally read "no enrollment" (`benefits/lines.py:139-149`, `plan_math.py:61-97`) (ch10).
- **B36 (2V) A kept line blocks Issue [F].** `proposals/selectors.payload` blocks on every uncovered line. A line kept as is can never be covered: `quotes/marks.set_recommended` refuses a current plan (lines 28-30) and `quotes/math.base_ids` (73-82) gives a current plan none. The old rule: kept lines need no pick (`proposal_ready.py` docstring).

## J.6 New design

**J.6.1 App.** Keep the existing `proposals` app.
- **Chain (ch27; Q15):** move it after `rfp`: `… quotes → commission → rfp → proposals → review → overview`. Neither `commission` nor `rfp` is built, so the move costs nothing.
- **Imports:** `deals`, `documents`, `ai` (registry only), `intake`, `census`, `quotes`, `rfp` (`markets()`, directly; no provider). Never `commission`, `review` or `overview`.
- **rfp never imports proposals:** its off-by-default card attaches the latest issued proposal Document (J169).
- **The painters stay here** as subpackages. An "exports" app would need proposals' config and would create a cycle.
- **Screens:** the builder, the Export viewer and `pages/` are proposals' code; the route hands them to the Advisor's view switch. The Proposal tab is the Advisor board in presented mode plus the packet card (ch31). The later /p/ page lives in `review`, which may import proposals.

**J.6.2 Models and JSON shapes.**

**ProposalConfig** keeps one row per deal, created on the first write; a GET reads the defaults (B27). `notes` becomes `intro`, `lines` changes meaning, and marks are stored.

| Key | Shape and limits |
|---|---|
| `title`, `intro`, `recommendation` | text ≤300 / ≤4000 / ≤4000 |
| `reasons` | {line: text ≤4000} |
| `order` | [line] |
| `lines` | {line: {parts: {comparison, cost, recommendation}, rows: [key] or null, card_stats: [key] ≤6, table_note: ≤600 characters and ≤4 lines, merged: [[plan id, plan id]] ≤8}} |
| `summary` | {on, blocks: [{key, line?}] ≤24} |
| `markets` | {on: true, false or null, lines: {line: {notes: {carrier: text}, hidden: [carrier]}}} |
| `next_steps` | [{date, text ≤300}] ≤8 |
| `experience` | {summary, rows: [{period, premium, claims}] ≤6} |
| `team` | [member id] or null |
| `output` | {layout, package_summary, cover: {on, design, image}, pictures: {place: key, "upload:id" or null}, pages: {agenda, about, team, experience, calendar, bios}, compare_tabs, disclaimers, compare_slots} |
| `marks` | {card: {by, at}, lines: {line: {card: {by, at}}}} |

**Other models:**
- **ProposalIssue:** deal, version (unique per deal), state (`building`/`issued`/`failed`), `pdf`/`pptx`/`xlsx` (each FK Document, PROTECT, null), `issued_by`, `issued_at`.
- **ProposalTemplate:** name, description, kind (`layout`/`rows`/`summary`), line ('' = any line), config (cleaned by `config.clean`), shared, owner, sort_order.
- **FirmPages** (singleton): `about_text` ≤900, `about_stats` (≤6), `service_calendar` (≤8).
- **TeamMember** (≤40): name, title, group, phone, email, bio ≤1400, photo, `on_by_default`, sort_order.
- **CoverImage** (≤24): a JPEG with a long side ≤2400 px, a thumbnail ≤600 px, no metadata; label, width, height, `uploaded_by`.

**Asked of quotes:** `Plan.option_number` (positive, null, unique per deal and line; replaces `option_label`, B29); `Plan.client_name` ≤200 (ch8); `LineEnrollment` (tiers, volume, lives); pure `labels.numbers(plans_in_reading_order, stored)`; `stamp_option_numbers(deal, ordered_ids)`.

**J.6.3 Pure rules** (each file ≤300 lines; data modules marked).
- **Config and pages:**
  - `catalog.py` (data): cards, parts, row presets, key rows, card stats, summary blocks, 7 covers, picture places, layouts, limits.
  - `config.py`: `clean(path, value)`, `merge(stored, changes)`, `card_of(path)`. `marks.py`: `done`, `cleared_by(paths)`.
  - `pages.py`: one splitter `split(lead, titles, groups, per_page)`, the layouts (by carrier, side by side, best only, by current plan), `pair_slides`, `reading_order`. The deck passes 6 a slide; the workbook's print plan passes its width-based count and keeps its own breaks and scale (ch17).
  - `merge.py`: the pair fold (J15).
- **Facts and gates:** `facts/` builds one client-shaped Facts from `deal_state()` in a fixed number of queries; only client fields enter. `ready.py`: missing picks and the refusal sentence; kept lines never block (B36). `checks.py`: 17 checks, each `{code, level, line, text, fix}`.
- **Content:** `summary_blocks/`, `negotiated.py`, `markets.py`, `why.py` (`why_for`), `formatting.py` (with the old `value_format`), `rows.py` (data). Every figure comes from quotes' math or `package()`.
- **Story and layout:** `story/` holds pure functions from Facts to our flowables (`sequence`, `opening`, `answer`, `coverage`, `closing`, `ledger`). `layout/` holds `tokens.py` (data), `flowables.py` (text block, fit table, slide title, slide note, chart; reportlab's public API only), `fit.py` and `record.py` (the frame recorder and fit log).
- **Painters:** `paint/pdf.py`; `paint/pptx/` (master, layouts, tables, native charts, notes; replays the recorded frames); `paint/paper.py` (pypdf, 75%).
- **Workbook:**
  - `workbook/model.py`: a pure sheet model (values, formulas with stored results, formats, merges, widths, drop-downs, print setup, images);
  - `formulas.py` (old templates verbatim), `tabs/` (cover, markets, rates, compare, bank, composite, all plans, generic, in-force, disclaimers), `print_plan.py`, `text.py` (port of `workbook_text`), `write.py` (XlsxWriter through documents' helper), `styles.py` (data);
  - functions: the old closed list IF, OR, AND, SUM, ROUND, INDEX, MATCH, IFERROR, MIN, MAX, HYPERLINK.
- **Viewer and packet:** `viewer/deck.py` (page log plus the PDF as base64, one build); `viewer/workbook.py` (serializes the model, one tab a call); `viewer/workbook_pages.py`; `viewer/workbook_checks.py`; `packet.py`.

**J.6.4 Services** (each locks its row, writes Activity with before/after and never member values, registers a reverter, and returns only what changed).
- `set_config(user, deal, changes)`: creates the row if needed, then locks it; cleans each path and skips unchanged ones; clears the marks of the cards owning changed paths; one Activity row a call; returns `{changed, activity_id}` (B2).
- `set_mark(user, deal, card, line, done)`: writes Activity; the deal stamp does not move.
- `clear_marks(deal_id, line, cards)`: the receiver of quotes' `plans_changed`; one JSONB key removal; no Activity of its own, since the quotes write is recorded.
- `issue(user, deal, include)` (ch20; fixes B1, B8, B9):
  - transaction 1 under the Deal lock: readiness and the 16 cap; quotes stamps the numbers; create `ProposalIssue(vN, building)`; queue an `issue` Job holding the Facts;
  - the Job builds the files outside any lock;
  - transaction 2: store the Documents ("Proposal vN · PDF"; kind `proposal`, unscreened), attach them, mark `issued`, `advance(deal, 'proposal')`, Activity "Issued proposal vN". A failure marks vN `failed` with Retry.
- `templates.save/update/delete` (the owner or an admin); `covers.upload/delete`, `firm_pages.save`, `team.*` through documents' images helper (B12).

**J.6.5 Payloads.**
- **Builder:** `config`; per line `{line, label, intent, chips, presented_ids, enrollment {counts, source, words}, recommendation {covered, missing, groups}, stats, highlights, marks}`; `checks`, `ready {ok, missing, sentence}`, `marks {done, total}`, `ledger`, `summary_preview`, `deck_order`, `issues`, `stamps {files, firm}`. The files stamp moves only when something a client file prints changes; the firm stamp moves on logo, firm pages, team and covers.
- **Pages:** `{line, pages: [{n, caption, full, columns: [{plan_id, place, kind, option, predicted, carrier, name, replacing, recommended, chips}], rows: [{key, label, cells}]}], others: [{plan_id, carrier, name, group, why_not}]}`. Cells arrive as formatted strings.
- **Deck preview:** `{style, draft, stamp, slides: [{n, title, kind, line, continued, notes, fit}], ledger, paper, pdf}`.
- **Workbook preview:** `{opens_on, tabs: [{title, capped, checks}], tab: {look, rows, checks, pages}}`.

**J.6.6 Endpoints** (under `/api/`).

| Method | Path | Purpose |
|---|---|---|
| GET / PATCH | `deals/{id}/proposal/` | Builder payload / `{path: value}` changes |
| POST | `deals/{id}/proposal/marks/` | `{card, line?, done}` |
| GET | `deals/{id}/proposal/pages/?line=` | Page split, columns, formatted cells, `others` |
| GET | `deals/{id}/proposal/preview/?file=deck` or `?file=workbook&tab=` | Viewer payloads; no-store; writes nothing |
| GET | `deals/{id}/proposal/files/{pdf,pptx,xlsx,letter}/` | Draft files; write nothing (POST twins only if Q3 is "no") |
| POST | `deals/{id}/proposal/issue/` | 202 `{version, state}` / 409 `{blockers}` |
| GET | `deals/{id}/proposal/issues/`, `…/issues/{v}/{pdf,pptx,xlsx,letter}/`, `…/issues/{v}/packet/` | Issued list with states; stored bytes; Letter made from the stored PDF; zip |
| GET | `proposal/covers/?orientation&picture` | Firm-level cover tiles from thumbnails; ETag |
| GET, POST / DELETE | `proposal/cover-images/`, `…/{id}/` | Uploads |
| GET / PATCH | `proposal/firm-pages/` | About, figures, calendar |
| GET, POST / PATCH, DELETE | `proposal/team/`, `…/{id}/` | Team and photos |
| GET, POST / PATCH, DELETE | `proposal/templates/?kind=`, `…/{id}/` | Templates |
| GET | `meta/` → `proposal` | Catalogue, covers, pictures, key rows |

Plan writes (star, recommend, slot, links, move, enrollment, sold, role, renewal, move_line, delete, values with `expect`, marks) stay in quotes (Advisor section). The internal spreadsheet is quotes' template export.

**J.6.7 What other modules must provide.**
- **Foundation and deals:** Activity before/after with revert, and a write that leaves the stamp; owner names; `advance`; `safe_filename`; `clock`; the Job model and worker (`issue`); the stylesheet port; Vitest; the chain change (Q15).
- **quotes:**
  - J.6.2's fields and numbering; `presented`, `room`, `order` with `reset`, slot (with `others` reasons; clears `recommended` on a plan that leaves), links;
  - `enrollment_for` sources typed → census → proxy → none (ch10); one `deal_state(deal)` (B32);
  - math for contribution modes, net after credit, slot and package change and the cost summary, split into ≤300-line files (ch13); `change.monthly_delta`;
  - priced-version sentences (replace `pricedKinds.js`); `star_reason`; a values write with `expect` (ch1); an on-commit `plans_changed` signal;
  - recommend and the AI rank both respect `room()` (ch32); the stop-loss workbook's math (J166).
- **intake:** intent per line, rate-guarantee date, the "Put it on" service, CurrentCoverage with the renewal letter's four facts (ch28), `CoverageIntentPanel`.
- **census:** the 65+ count as one aggregate.
- **rfp:** `markets(deal)`.
- **documents:** kind `proposal` (protected from archiving, not screened); an images helper (re-encode, strip metadata, thumbnails, a bounded cache) (ch25); an XlsxWriter helper (conversions off, `write_string`, explicit links) (ch12); `src/viewer/` (pdfjs, sheet grid), `src/grid/` (with the per-cell undo stack), `src/valuereview/`, `src/lib/findText.js`.
- **ai:** tools `set_table_note`, `set_rows`, `pair_plans`, each calling `set_config`; `proposal_context(deal, page)` takes the viewer state from the browser (B21); curation reads `quotes.presented()`.
- **commission:** BookingSummaryModal and the sold signal.

**J.6.8 Frontend** (`frontend/src/deal/proposal/`, React Query only, no hand-written stores).
- **`tab/`:** `ProposalTab` (the route composes the Advisor board in presented mode with the packet card); `proposalMode.js` (this tab's toolbar items, chips and legend).
- **`packet/`:** `PacketCard`, `IssuedList` (states, Retry), `ChecksList`.
- **`builder/`:** `ProposalBuilder` (shell), `BuilderToolbar`, `BuilderCard`, `CompletedMark`, `CoverCard`, `PicturesCard`, `OutputCard`, `PagesCard`, `FirmPagesDrawer`, `LineTabs`, `OffNotice`, `PlansCard`, `EnrollmentStrip`, `RecommendationWords`, `RowsCard`, `CardStatsPicker`, `SummaryCard`, `NextStepsCard`, `MarketsCard`, `TemplateBar`.
- **`pages/`** (handed to the Advisor by the route): `ProposalPages`, `PageTable`, `PageColumn`, `PlanPicker`, `PlanLinkPicker`, `pageToast.js`.
- **`export/`:** `ExportViewer`, `FileChips`, `DeckViewer`, `SlideRail`, `FitReport`, `PaperFrame`, `WorkbookViewer`, `WorkbookPages`, `printPdf.js`.
- **Hooks in `src/api/proposals.js`:** `useProposal`, `useSetConfig`, `useSetMark`, `usePages`, `usePreview` (J107's settings; staleTime Infinity is safe because the key holds the stamps), `useIssue`, `useIssues`, `useTemplates`, `useCoverImages`, `useFirmPages`, `useTeam`.
- **Vitest:** `pageToast.js`, the `printPdf` fallback, the slide-keeping rule, the grid's undo stack.

**J.6.9 Stylesheets** (copied verbatim with their class names; split at rule boundaries into files ≤300 lines).

| New file | Copied from |
|---|---|
| `styles/bnf/proposal-grid.css` | `benefits.css` 270–290, 346–380, 565–658, 3897–3979 (one copy, shared with the Advisor board) |
| `grid.css`, `freeze.css`, `grid-sizes.css` | the three old grid files |
| `proposal-builder-a.css`, `-b.css`, `-c.css` | `benefits.css` 4026–4633, without the edit-lock rules (4445–4452); the merged-pair rules stay (J15) |
| `proposal-covers.css` | `benefits.css` 4949–4999 and 5568–5625 |
| `export-deck.css` / `export-sheet.css` | `benefits-export.css`, split |

- **Classes kept:** `bnf-build-*`, `bnf-pg-*`, `bnf-pk-*`, `bnf-pp-*`, `bnf-present-*`, `bnf-firm-*`, `bnf-output-*`, `bnf-cover-*`, `bnf-pic*`, `bnf-packet-*`, `bnf-markets*`, `bnf-linetab*`, `bnf-order*`, `bnf-tiersource*`, `bnf-plan-col*`, `bnf-benefit-*`, `bnf-computed*`, `bnf-group-*`, `bnf-win-*`, `bnf-tip-*`, `bnf-chip-*`, `bnf-override-*`, `bnf-refresh-*`, `bnf-xv-*`, `bnf-xw-*`, `xg-*`.
- **Not ported:** print and /p/ styles (830–1041, 3376–3896, `--bnf-doc-*`); `benefits-unleashed.css`.

**J.6.10 Tests** (behavioural only).
- **Config and marks:** two concurrent writes to different paths both survive; an unchanged write changes nothing; a write clears its card's mark; a star, slot or Claude note clears the line's Plans mark; marks never move the stamp; revert works.
- **Undo:** it writes the earlier value and is refused when the cell changed since.
- **Pages and numbers:** splitter table cases (6 a slide, current plans repeated, ≤3 pairs never split, by current plan, best only); the workbook print plan breaks by width and carrier as before; the deck's slide count equals the pages payload's; predicted numbers equal stamped ones on by-carrier and renewal-set lines; numbers are stable across stars, order and rate edits, never reused, none for current plans or priced versions, renumbered on a line move.
- **Gate and stories:** ready and checks as table cases; kept lines never block (B36); a quote-first deal shows its lines (B31); `why_for` never prints deal-wide words under a line when any line has its own; agenda and dividers only when framed; the cost-only line; the employee-pay rules; pages switched off do not print; firm pages print nothing until written; the panel for one pick, the table for several current plans or several picks.
- **Client safety:** none of J.4's "never" items in any xlsx cell, PDF text or pptx text.
- **Layout:** type floors, rows ≤2 lines, "(continued)", long values moved to notes, every slide titled, native charts only with 2+ rows; each pptx text box equals its recorded frame and fits by the same measure.
- **Workbook:**
  - the file read back equals the sheet model (values, results, formats, merges) on golden deals;
  - stored results equal the app's figures, a test-only evaluator agrees, and `-m recalc` passes;
  - a what-if count on an unrated tier falls back to the stated premium or blank;
  - Compare prefill, hidden carriers, the 2,000-plan note, author, opening tab;
  - text starting with "=", "+", "-" or "@", and http text, stay text.
- **Pair fold:** its total equals `package()` of the pair; it counts once against 16.
- **Previews:** write nothing (query capture), are no-store, refuse in the downloads' words; workbook checks find ####, cut and error.
- **Paper:** placement.
- **Issue:** refuses until covered; stamps under the lock and builds outside it; a failed build leaves vN failed with Retry; stores the files and moves the stage; v1's bytes are unchanged after v2; the Letter PDF comes from the stored bytes.
- **Performance:** the Facts build and `deal_state` take a fixed number of queries regardless of plan count.
- **Golden deals:** golden deal 1 in all three files; a new quote-first deal with typed counts only.

**J.6.11 plan.md changes and build order.**
- **Replace** §6.8, §7.9, §8.12, §9.4, §9.5 (the internal workbook is quotes' export), §9.6 and §9.7.
- **§3.3 and CLAUDE.md:** the chain change (Q15).
- **§5.4:** per-line `option_number`; `client_name`; the pair fold (Q12); the 2026-11-10 recommendation rule stands pending Q4.
- **Remove from §15:** "paper view, previews", "slot swaps", "merges" (the client-file fold only), and proposal templates if Q6 keeps them.
- **Answer from the old formats:** §16 Q6 (Compare prints 5 a page; Rates break by width and carrier) and Q14 (8 pt table floor).
- **Slices:** P1 rules, config service and builder; P2 spreadsheet and Excel view; P3 story, layout, PDF, Paper and deck view; P4 PowerPoint; P5 Proposal tab, packet and Issue; P6 templates, covers, pictures, firm pages and the pair fold.
- **Look check:** after each slice, render the golden deals in both apps and compare them by eye. An optional `-m look` job diffs page images of the golden decks against images a person approved.

**J.6.12 Challenge rulings.**
- **Accepted as written:** 1, 2, 4, 5, 7–15, 17–20, 22–25, 28–30, 32. Each changed row or bug cites it as chN.
- **Accepted, with a decision left to Daniel:** 6 (it becomes the "no" answer to Q3); 27 (the chain change, Q15).
- **Modified:**
  - 3: Daniel's 2026-11-10 rule (plan.md §5.4) stays the default, because it is an owner decision. The dead ends close because kept lines never block (B36) and "Keep this plan" recommends the renewal. The challenge's evidence was wrong: 2V gives a current plan no `base_ids`, so allowing it needs one more rule in `recommendation()`.
  - 16: the first option (keep platypus, with our own flowables). Image diffs run only in an optional job, because pixel tests are fragile across machines.
  - 21: the settings are accepted. The PDF stays base64 in one response: one build, one request.
  - 26: logo and colour stay in Django admin (2V rule 6); only the firm pages come back in-app.
  - 31: one board, with a mode that keeps this tab's toolbar, chips and legend so it looks the same.
- **Rejected:** none.

## J.7 Open questions for Daniel

1. **Classic format:** are the Classic Letter pages (orientation and density) and their older deck still used? The Presentation format's Paper view and "Letter PDF" are kept either way. Until you answer: deferred.
2. **Client share link** (/p/) with online plan selection: is it needed in the MVP? Until you answer: built after the review portal, on its `ClientLink`.
3. **Drafts:** should every file that has not been issued carry Draft, with numbers stamped only at Issue? The old way was different: numbers were stamped at the first client download, Draft showed only when picks were missing, and the spreadsheet had no mark. Which files should an issue store? Until you answer: Draft until issued, and all three are stored.
4. **Recommending a current plan:** your 2026-11-10 rule says no; "keep" means recommending the renewal. Kept lines will need no pick. But a shopped line whose renewal has not arrived can be covered only by an alternate or a typed renewal. Keep your rule, or allow the current plan as the old app did? Until you answer: your rule.
5. **Stop-loss ordering:** may stop-loss plans be reordered with the arrows and slot picks? Until you answer: yes.
6. **Proposal templates** (layout, row sets, summary): plan.md §15 lists them as a non-goal. Keep them? Until you answer: kept.
7. **Firm pages:** logo, brand colour and contact move to Django admin (your rule 6). About, figures, calendar and team stay in an in-app drawer that any user can edit. "Prepared by" becomes the deal owner. Acceptable? Until you answer: yes.
8. **Option numbering:** keep the old "Option n" per line (renewals numbered; current plans and priced versions not) in place of C/R/P labels? Until you answer: the old numbering.
9. **Sold plans:** confirm that several sold plans per line are allowed (2V), where the old app un-sold the other plan.
10. **Renewal history page and past plan years:** do they wait for the renewals decision? Until you answer: deferred. The renewal-letter blocks and the RENEWAL chip no longer wait.
11. **Hidden carriers:** should a carrier hidden on Markets checked also leave the spreadsheet's Compare and All Plans lists, with a label on screen? Until you answer: yes.
12. **Florida Blue 5182/5183:** should the two plans fold into one client column, as the 2026-11-05 call asked, instead of plan.md §5.4's two ways? On a folded pair, should the in-network single deductible print as "EE $2,500 / PP $5,000" or as "$2,500" alone? Until you answer: fold in a late slice, and print both.
13. **Typed medical counts on a quote-first deal:** should they also price the worksite tier-rated lines, and dental and vision, until their own counts or the census arrive? Until you answer: worksite lines borrow them (labelled); dental and vision do not.
14. **Stop-loss analysis workbook:** is it still the client document for self-funded deals in the MVP? Until you answer: kept (Advisor section).
15. **Chain order:** may `rfp` move before `proposals` (commission → rfp → proposals)? Do you ever send carriers the proposal (the RFP packet's off-by-default "Client proposal" card)? Until you answer: the order is moved, and the card attaches the latest issued proposal.
