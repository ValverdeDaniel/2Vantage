# Part E — Documents review station

[← Porting plan](README.md)

**What it is:** The Documents tab holds every file on a deal. It is also where people check what Claude read from a file: the file sits on one side (PDF, image or spreadsheet, with the value highlighted) and its values on the other (plan grid, intake form, census roster, or a list sorted worst first), where people approve, ignore, flag, search, undo, re-read and ask Claude to re-check. "Open in file" on every other tab lands here, and the review queues, the client portal, Commissions and the Export viewer reuse its viewers.

Roots. Old: `c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/`. Frontend paths sit under `frontend/src/`; `shared/` means `frontend/src/components/benefits/shared/`. New: `c:/Users/fooba/OneDrive/desktop/Vantage_all/2Vantage/`, marked "2V". "ch. N" cites the adversarial challenge that changed a row.

## E.1 Files read, in order (one line each)

**Specs and READMEs**

| File (lines) | What it is / what it taught |
|---|---|
| benefits/README.md (395) | Documents is no module: it is spread over shared/, docscan, ai and value_review |
| docscan/README.md (149) | The file chassis: kinds, serving, chunking, sheets, locator; it never applies values |
| benefits/ai/README.md (827) | Readers; D-119 re-check; D-122 locator; agent turns take files of 100 pages or fewer |
| benefits/market/README.md (462) | Marks, batches, revert; origin words |
| PlanningDocs/Benefits/document-review-station.md (189) | D-122 slices and Daniel's choice "pypdf only: no pypdfium2, no server OCR" (:22, :108); D-126, D-127, D-164 |
| document-window-and-hotkeys.md (126) | D-125 keys, undo, pop-out; D-201 Review-mode keys |
| flag-review-and-sources.md (113) | D-119 re-check; sheet viewer; the `.mjs` MIME fix (:52, :71) |
| bulk-value-review.md (88) | D-116 approve, ignore, check |
| decisions.md (5,528; D-116–127, D-164–167, D-201, D-209) | Why each rule exists; archive over delete (2026-10-19) |
| documents-find-any-file.md (171) | Viewer file split from grid file; snippet pin |
| sheet-viewer-formatting.md (74) | D-167 Excel look; lookups not scoped |
| grid-selection-review.md (110) | D-123 picking; potential-error filter |
| 2V CLAUDE.md, README.md, plan.md §3.2–3.9, 6.3, 7.4, 7.7, 7.11, 8.3, 8.13, 8.16–8.17, 10, 11, 12.3–12.6, 13, 15, 16 | New rules; per-owner sources endpoints (§8.13); `deals/{id}/review/` belongs to review (§7.11); Job in `ai` (§3.3, §10.2); Cloud Run and WhiteNoise (§11); non-goals |

**Models**

| File (lines) | What it is / what it taught |
|---|---|
| benefits/models/case.py (1,878; 95–145, 724–1115, 1497–1868) | Value mixins, CaseDocument (19 types, `form_5500` among them), ExtractionJob, versions, sessions, CaseDocumentEvent; grouped warning counts |
| models/market.py (706; 156–215, 640–707) | CensusCell; ValueReviewBatch |
| models/pipeline.py (621; 45–62, 110–282) | `shortlist_reason`; plan provenance, PlanValue, plan order |
| models/questionnaire.py (74–148) | QuestionnaireAnswer: confirmable, stamped, never located, no snippet |
| commissions/models.py (845–860) | Statements keep their own file and page count |
| 2V documents/models.py (46), kinds.py (44), migrations/0001 | Document v1; 11 kinds; 3 roles; `PHI_KINDS` census and claims only |
| 2V quotes/models.py (73), deals/models.py (94) | Plan values and sources as JSON, `starred` only; Activity with coalescing, no target |

**Rules and services**

| File (lines) | What it is / what it taught |
|---|---|
| docscan/kinds.py (195) | SHAPES, KINDS, `shape_of`, `accepts` |
| docscan/serving.py (75) | `file_response` (sandbox CSP inline); `unlink_file` and why it exists |
| docscan/chunking.py (461; 130–320) | `grids_from_bytes`; `visible_only` off by default |
| docscan/phi_screen.py (250) | pypdf page texts with filled form fields (D-209) |
| docscan/locate.py (579) | Pure locator; `printed` for derived figures; scanned pages "nocheck" |
| docscan/sheet_preview.py (288) | Windows, `find_cell`, `cell_match`, limits |
| docscan/sheet_format.py (353) | The Excel look: .xlsx and .xlsm, up to 5 MB |
| docscan/jobs.py (189) | Heartbeat and reaper |
| benefits/ai/source_check.py (374) | The only writer of `located_*`; `query_for`; `recheck`; bare threads |
| benefits/pipeline/normalize.py | `snippet_with`, `reader_line` |
| benefits/market/value_review.py (492) | Marks rule, scopes (questionnaire included), batches, revert, payload weight |
| benefits/market/value_origin.py (231) | Origin words; `write_hand_edit` |
| benefits/market/marketing_checklist.py | `PER_YEAR_DOC_TYPES`; `document_rows` filter |
| benefits/history.py (384) | Change-history groups; detail whitelist |
| benefits/signals.py (71) | Unlink at once on `post_delete` |
| benefits/review/uploads.py (109) | The only writer of `review_state` |
| benefits/pipeline/workbook_import.py (378) | Imported template stored as `other` |
| benefits/pipeline/claude_edits.py (684) | Flag-check approvals with no batch |
| benefits/pipeline/plan_math.py (525–550) | `proposal_order`, the order every old screen drew |
| benefits/pipeline/export_check.py (1–105) | D-143: counts open and "not in the file" values |
| benefits/pipeline/workbook_preview.py (1–30, 88–165) | Export viewer's Excel view draws with `sheet_format.look` |
| benefits/renewal.py (947) | Copies documents into next year's deal |
| 2V deals/values.py (47), activity.py (47), downloads.py (28), selectors.py (94) | `locked`, `source`, `apply`; coalescing; headers; "Last updated" from Activity |
| 2V documents/services.py (120) | Upload, update, delete, download log |
| 2V quotes/services.py (224), marks.py (162), values.py (91), selectors.py (155), template_views.py (48) | A typed change drops `doc`; `statuses()` reads `confirmed_by`; `ordered_plans`; template kind `other` |
| 2V start.sh (15), requirements.txt (23) | 2 workers × 4 threads, 60 s; no pypdf |

**Views and payloads**

| File (lines) | What it is / what it taught |
|---|---|
| serializers/primitives.py (360) | `document_payload` (year labels); `_source_payload` keeps the file on edits; `_loc_payload` |
| serializers/scan.py (269–562) | Staged payloads |
| serializers/pipeline.py (207–316, 505–594) | Cells with source and marks; `documents`; `order_into` |
| serializers/case.py (140–219), serializers/market.py (481) | `overview_payload`; census page size 100 |
| serializers/journey.py (90–115), review/items.py (1050–1136) | Multi-deal counts in one query; census queue paged in SQL |
| benefits/urls.py (362) | Routes |
| views/cases.py (123–300, 555–1116) | Creation with files; upload, PATCH, delete; picker types |
| views/versions.py (155–180, 433–552) | History; download; sheet; locate (60 pages sync) |
| views/shared.py (297) | `extensions_for_doc_type`, `_get_case`, `_confirm_value`, `_autostart_reader` |
| views/ai.py (1–340, 600–865) | Scan start; audit; flag check; apply, discard |
| views/review.py (628), views/pipeline.py (2,581), views/market.py (2,148), views/portal.py (2,609) | Upload decision; Add value; `confirm` keys; portal uploads auto-start reads |
| docscan/views.py, docscan/urls.py | Kinds endpoint (lessons only) |
| users/permissions.py (1–80), backend/settings.py, backend/urls.py (30–31) | Module gate only; no cap; media in DEBUG |
| commands locate_sources.py (72), prune_orphan_media.py (163), reader_trial.py (1,166) | Ops tools; the orphan backlog |
| 2V documents/views.py (79), urls.py, backend/meta.py (28), settings.py | v1 API; vocabularies; 50 MB cap; 5,000/hour throttle |

**AI**

| File (lines) | What it is / what it taught |
|---|---|
| ai/extraction.py (428–452, 540–660) | `_check_sources` skips `work`; audit chain for quote, census, intake |
| ai/plan_checks.py (1–130), ai/staged_turn.py (180–260) | Locates during agent turns; staged agent payload has no `loc` |
| ai/flag_check.py (304), ai/scan_audit.py (399), ai/quote_checks.py (364) | Re-check; machine-confirm with `confirmed_by` null; double-check |
| ai/pages.py (169), ai/doc_format.py (191) | Page gate, `target_for_doc_type`; the quote reader reads stop-loss quotes and TPA proposals |
| ai/claude_readers.py (4,127; 700–725), ai/scan_chat.py (2,342), ai/agent_turn.py (1,423) | `quote_read_lines`; snippet scrub; agent route ≤100 pages, queues |

**Frontend**

| File (lines) | What it is / what it taught |
|---|---|
| components/benefits/README.md (60–283) | Notes D-119 to D-166 |
| services/api/benefitsShared.js (424), benefitsMarket.js (455), benefitsClose.js (422), benefitsReview.js | Every call; token header for pdf.js |
| shared/DocumentsTab.jsx (3,073) | The station |
| shared/PdfViewer.jsx (586), pdfText.js (474), pdfOcr.js (83) | Legacy build, `disableRange`; matcher; OCR from jsDelivr |
| shared/ImageViewer.jsx (181), SheetViewer.jsx (336), DocumentViewer.jsx (91) | Image and sheet viewers; viewer by shape |
| shared/DocumentWindow.jsx (277), docWindowLink.js (232) | Pop-out; presence on deal and client pages |
| shared/FileReviewList.jsx (324), ReviewBulkBar.jsx (106), GridReviewToolbar.jsx (171) | List (sorted in the browser); strip; pick bar |
| shared/useReviewHotkeys.js (73), useGridSelection.js (496) | A/I/C/U/F; picking |
| shared/ScanFindBar.jsx (132), findText.js (49) | Find; word rule |
| shared/sourceTarget.js (49), valueReview.js (160) | Where a value opens; client marks rule |
| shared/ChangeHistoryCard.jsx (347), VersionRail.jsx (260), VersionDiff.jsx (140) | History; versions |
| shared/StagedScanReview.jsx (583), ProposedChangesCard.jsx (450), ScanChat.jsx (590–700, 1389), claudePages.js (112) | Staged review; re-check card; Daniel's six "File as" |
| shared/CaseWorkspace.jsx (195–235, 495–531, 975–998, 1244–1252) | `openSource`, `recheckFlags`, `rereadFiles` |
| shared/ReviewFilePane.jsx (85), RequestCards.jsx (455), RequestForm.jsx (449), PdfPagesPreview.jsx | Queues reuse the viewer; a request door; export previews |
| shared/useWindowedPlans.js (224), useWriteQueue.js (60), useDealJobStore.js (239), useGridKeys.js (435), useFreezePanes.js (40), useGridSizes.js | Grid machinery; `WINDOW_COLS_OVER` 40; Ctrl+Z as a new edit |
| close/useComparisonStore.js (101), sourceDocs.js (16), planFinder.js (25), PlanPicker.jsx (298), CloseoutTab.jsx (397), ExportViewer.jsx (25–35) | Shared comparison copy; plan finder; close-out door; legacy pdf.js on purpose |
| market/CoverageIntentPanel.jsx (300–360), useMarketingChecklist.js (82), CensusGrid.jsx, CensusTab.jsx, IntakeTab.jsx | Line-scoped doors; tabs that open values here |
| market/QuestionnaireReview.jsx (831), censusreview/CensusAiReview.jsx (495), intakereview/IntakeQueue.jsx (665), BenefitsClientPortal.jsx (3,648) | Viewer reusers; questionnaire marks; portal blob URL |
| commissions/StatementDocumentsTab.jsx (803; 640–680), implementation/useImplementationChecklist.js (86), radar/ClientWorkspace.jsx | `PdfViewer` with snippet and value; an upload door; presence |
| components/benefits/docTypes.js (36), App.jsx, utils/chromeless.js | Picker types and locks; window route |
| contexts/EditSessionContext.jsx (205), GuideContext.jsx (338), reviewrequest/FromClientToggle.jsx (28) | Sessions; walkthroughs; "from the client" toggle |
| utils/fileDrag.js (55), download.js (88), columnHeaders.js (83), usage.js (212), frontend/nginx.conf (59) | Drop, download, widths, analytics; no proxy cap |
| 2V frontend deal/documents/DocumentsTab.jsx (147), DocumentDialogs.jsx (156), api/documents.js (49), App.jsx, DealPage.jsx, ActivityDrawer.jsx | v1 table, dialogs, routes, Activity drawer |
| 2V frontend api/deals.js, api/queryClient.js, package.json, deal/advisor/ValueCell.jsx | `invalidateDeal` refetches everything; focus refetch on; no test runner; amber `to_check` |

**Styles**

| File (lines) | What it is / what it taught |
|---|---|
| styles/benefits.css (6,275; 477, 532–651, 722–727, 774–785, 1043, 1187–1376, 2408–2851, 3781–3966, 5632–6042, 6265–6273) | Compare table, plan heads and chips, `bnf-docs`, `bnf-doc`, `bnf-scan`, `bnf-frl`, `bnf-staged`, `bnf-sheet`, `bnf-review`, `bnf-file-bar`, `dw-*` |
| App.css (2441–2453, 2750–2954) | `bb-badge*`; `bb-pdf-*`, `bb-doc-tab(s)`, `bb-cell-provenance/noprov/active` |
| styles/benefits-grid.css (200), benefits-freeze.css (104), benefits-grid-sizes.css (92) | `gs-*`, `sf-*`, `bnf-freeze`, `bnf-sized` |
| styles/benefits-history.css (151), benefits-census-review.css (924–926) | `hst-*`; `bnf-rv-file-viewer` |

**Tests:**
- Old: doc_review_tests.py (1,070), source_check_tests.py (489), flag_check_tests.py (398), value_review_tests.py (442), review_revert_tests.py (207), history_tests.py, docscan/tests.py (2,098).
- Old classes: ai_tests (DocumentTypePatch, QuoteUploadFormat, StagedScan, ScopedScan, ScanAudit, AutoAuditChain, DocumentCarrierHint); case_tests (DocumentReassign, CloseoutDocType, ValueConfirmation); versions_tests.DocumentDownloadTests; work_with_claude_tests.DocumentUploadTypeTests; market_tests (LineDocument, CensusProvenance); prompt_pack_tests.ProvenanceScrubTests; wwc_accuracy_tests (LateWriteLocated, PageLabel); quote_checks_tests.ApprovedDocumentsTests; review_request_page_tests.RPUploadReviewTests; portal_tests.PortalCensusUploadSafetyTests; upload_drop_tests.DropAcceptParityTests; agency_logo_tests.MediaInventoryTests; pipeline_tests.ComparisonQueryCountTests.
- 2V: documents/tests/test_documents.py (55).

## E.2 Old data model, in brief

- **CaseDocument:** `case`; `file` (one flat `benefits/` folder); `original_name`; `page_count` (PDFs only); `doc_type` (19 choices, default `unknown`); `label` (blank = worked out on read); `carrier`; `lines` (empty = every line); `carried_forward`; `page_labels`; `uploaded_at/by`; `client_link`; `review_state/at/by`. Ordered by upload time.
- **CaseDocumentEvent** (edited or removed) keeps whitelisted detail, never label text. **ValueReviewBatch** keeps marks as they were, keyed by value id: people, times and states, never values.
- **Per-value mixins:**
  - `ConfirmableValue` on CaseField, PlanValue, CensusCell and QuestionnaireAnswer. A machine confirmation has `confirmed_by` null and is told apart from a person's.
  - `LocatedValue` (`located`, `located_value`, `located_doc` as a plain integer, `located_where`) on the first three only.
  - `LayerStamps` on CaseField, CensusCell and QuestionnaireAnswer.
  - Provenance: `source_document` (SET_NULL), `source_page`, `source_snippet` (≤300 characters), the reader's doubt (`low_confidence` or `confidence='low'`).
- **Plan provenance:** `source_document`, `carrier_from_document`, `read_key`, `read_state`, `plan_codes`; `is_shortlisted` with `shortlist_reason`.
- **ExtractionJob:** kinds quote, census, intake, rank, qform, audit, correct, work; mode apply or staged; statuses include `queued`; `document`, `started_by`, `params`, `result`, `log`, `pct`, `error`, `heartbeat_at`.
- **DataVersion and EditSession** were dropped in wave 1.
- **Worked out on read:** confirmations, marks and locations hold only while the value (and, for locations, the file) is unchanged; `open_warning` = marked check, or low and neither confirmed nor ignored (with a SQL twin); `shows_confirmation` = low, or located absent or weak; year labels; on the client, the bucket rule (`bucketWith`, `BUCKET_OF`), `potentialError` and the quality headline.

**Corrected facts** (proved by the critics):
- `WINDOW_COLS_OVER` is 40.
- QuestionnaireAnswer carries LayerStamps and takes marks through the shared review endpoint (`value_review.SCOPES`).
- Every door (close-out, implementation, coverage, checklist, RequestForm) sends a `doc_type`; only a file sent without one stays `unknown`.
- `_confirm_value` is also reached through the `confirm` key on three PATCH routes.
- The auto-audit runs after quote, census and intake reads, never after `work` reads.
- An unchanged PATCH answers 400; a refused type also throws away the rename.
- The agent route needs every file at 100 pages or fewer and queues behind a running job.
- A file may be re-typed away from wrap or POP, not into them.
- The missing object-level check is app-wide.
- `download_url` and `raw_url` are pinned by a test but unread by the tab.
- D-122: the server matches with pypdf only and never OCRs; the browser highlights and OCRs, using the locator's `printed` for derived figures.
- A hand-edited value kept its file (`edited: true`).
- Year labels apply on every deal (renewal, claims, invoice, wrap, POP), not on renewals only.
- `form_5500` ("Prior 5500") already exists; the quote reader also reads stop-loss quotes and TPA proposals.
- Commission statements are their own model and use `PdfViewer` with snippet and value. The Export viewer's Excel view draws with `sheet_format.look`.

## E.3 Functionality inventory and verdicts

### Files: list, upload, manage

| # | Functionality (what the user sees -> how it worked) | Verdict | New implementation |
|---|---|---|---|
| E1 | File tabs in upload order: label, bucket tag (PROPOSAL / CENSUS / INTAKE / QUESTIONNAIRE), full name on hover, in-scope tint -> `bucketWith` (kind, or any file a plan cites) | Keep | `FileTabs.jsx`, oldest first. **Changed (ch. 10):** bucket from the kind alone (/api/meta/), so no plan lookup and no late-picked scope. A renewal read only for Intake links to its answers. Classes `bb-doc-tabs`, `bb-doc-tab`, `bnf-doc-bucket`, `bnf-doc-inscope` |
| E2 | Picking a tab moves grid and viewer, closes All proposals and Re-read -> `selectDoc` | Keep | `?doc=` in `useStationState.js` |
| E3 | "All proposals (N)" with 2+ proposal files; grid, counts, strips and List cover all | Keep | `?doc=proposals` |
| E4 | Files dropped anywhere go to the Work with Claude "File as" list; no upload button | Keep | `useFileDrop`, `is-dropping`; the drawer is the WWC section's |
| E5 | "File as" offers 6 types, the File panel 11; `other` is "Other" in one, "Intake" in the other | Simplify | One kind constant. **Changed (ch. 18):** a `file_as` flag keeps Daniel's six (2026-10-15); the File panel offers every kind; "Other" everywhere |
| E6 | Untyped uploads refused; extensions per type (`extensions_for_doc_type`) | Keep | `accept` per kind; kind required on upload and re-type; a blank kind is a 400 (2V turns it into `other`) |
| E7 | No size cap; extension checks only; one flat folder; a batch saves earlier files then answers 400 | Simplify | `deals/<id>/<uuid>-name`; one file per request; magic-byte check; page count at upload (pypdf). **Changed (ch. 39, 15):** 30 MB cap, since Cloud Run refuses bodies over 32 MiB; bytes removed when the upload's own transaction fails |
| E8 | Other doors: coverage chips (lines), checklist, RequestForm, portal, Attach SBC, deal creation, template import | Keep | All call `documents.services.upload` with a kind; imports get `plan_template` |
| E9 | Close-out (wrap and POP replace the old file) and implementation doors; UI-only type lock | Defer | Those modules are outside this plan |
| E10 | File panel: rename (Enter saves, Esc cancels, blur does not save, blank ignored), carrier (blank clears), toasts | Keep | `FilePanel.jsx`, `PATCH documents/{id}/` |
| E11 | Re-type: a refused type keeps the panel open, saves nothing; then "Reassigned — re-read this file… Map census → / Re-scan quotes →" | Keep | Same PATCH, all-or-nothing |
| E12 | Line scope (empty = every line), set only from the coverage card | Keep | Lines picker in `FilePanel.jsx` |
| E13 | Role: current plans, renewal or alternates | Keep | Existing 2V field. **Changed (ch. 19):** also asked for stop-loss quotes and TPA proposals, which become plans |
| E14 | An unchanged PATCH answers 400 | Simplify | 200, nothing written, no Activity row |
| E15 | Remove: confirm, log, hard delete, unlink; values lose their file | Simplify | Archive (`archived_at/by`); values keep `doc`. **Added (ch. 14):** the default manager hides archived rows, so checklist, packet, chips and portal slots drop them without a filter of their own; `all_objects` for value links and opening files; issued proposals cannot be archived |
| E16 | "Show removed files (N)" and Restore | New | `FileTabs.jsx` (archive-never-delete) |
| E17 | Download as attachment; the viewer fetches inline under a sandbox CSP | Keep | 2V `DownloadView` plus the CSP. **Changed (ch. 40):** v1's "View in a new tab" opens the file in the station, because Chrome's own viewer may refuse a sandboxed PDF |
| E18 | Deep links `?doc=`, `?claude=1`, `back=` ("‹ Back to review"); other tabs open a value's file and page; a missing file toasts, never swapped | Keep | `/deals/:id/documents?doc=&ref=&page=&back=` |
| E19 | `?history=` opens the version rail | Drop | Versions dropped (wave 1) |
| E20 | Line picker for scans when 2+ lines are requested; default "All lines (label each plan)" | Keep | Page context for the drawer. **Ch. 11, modified:** the old rule stays; with no requested lines the default already reads every line |

### Viewers

| # | Functionality (what the user sees -> how it worked) | Verdict | New implementation |
|---|---|---|---|
| E21 | Viewer by shape (pdf, image, sheet, none) | Keep | `src/viewer/DocumentViewer.jsx`; `shape` in the payload |
| E22 | PDF canvas; Prev / page box / Next; zoom 0.4–4×; Fit; refit on resize; "Loading document · x of y MB…"; 20 s stall; 401 "sign in again"; last 6 files in memory | Keep | `PdfViewer.jsx`, `usePdfDocument.js`, `pdfjs.js` (legacy build, bundled worker; ch. 37); session cookie; cache by id. **Ch. 38:** whole-file download stays |
| E23 | Highlight: box on the value, fainter box on its line, flash; row by geometry, column by plan hint, short values only inside the snippet -> `pdfText.js` | Simplify | **Changed (ch. 1):** stays in the browser as D-122 decided, and Commissions statements need it. `pdfFind.js` and `pdfGeometry.js` port `pdfText.js` trimmed to drawing: open `loc.page`, draw `loc.printed`. Found or absent is decided only in Python |
| E24 | Pages ±1, ±2 tried; "Found on p. N (recorded as p. M)"; "Couldn't locate the exact text on this page" | Keep | Same texts; the sweep runs only without `loc.page` |
| E25 | Scanned pages OCR'd in the browser by tesseract.js from jsDelivr ("Locating on the scanned image…"); images once | Simplify | **Changed (ch. 1, 27):** browser OCR stays, served from our `/static`. OCR only draws; the locator keeps scanned pages "check by eye", never "not in the file" |
| E26 | Image viewer: zoom 0.05–6×, Fit, status line | Keep | `ImageViewer.jsx` |
| E27 | Sheet tabs (hidden tagged, dashed); 200-row windows; "Rows a–b of n"; hidden rows and columns hatched | Keep | `SheetViewer.jsx`, `SheetTable.jsx` |
| E28 | "Found in 'Sheet' B7" with a ring; a located cell opens without searching; search in GET query strings | Simplify | `POST documents/{id}/sheet/find/`; values never in URLs |
| E29 | "As in Excel" or Plain (remembered); limits 150 columns, 20,000 rows, 200 characters, 15 MB | Keep | `documents/sheets.py`, `sheet_look.py`. **Changed (ch. 29, 34):** no per-process cache; one parse per request; streaming for Plain; full load only for "As in Excel" ≤5 MB. `look()` is pure over a workbook, so the Export viewer's Excel view reuses it |
| E30 | Other formats: "can't be previewed here — download the file" | Keep | `bnf-nopreview` |
| E31 | File bar: name · bucket · page N of M; "Opened to show <row · plan>…", "← Back to <file>" | Keep | `FileBar.jsx`; viewer file and grid file are separate params |
| E32 | Expand, Collapse, Esc; "Hide", "Scanned data" | Keep | `bnf-docs-expanded`, `bnf-docs-hidden` |
| E33 | e2e data hooks | Drop | Old e2e only; click-throughs use roles and labels |

### The Scanned data panel

| # | Functionality (what the user sees -> how it worked) | Verdict | New implementation |
|---|---|---|---|
| E34 | "Scanned data · bucket · all N files"; quality headline (90% clean, 70%, needs review) with high / review / missing chips | Keep | **Changed (ch. 9):** counts from the owner's sources endpoint, which alone knows required blanks; thresholds in `review_rules.quality_headline` |
| E35 | List / Grid (remembered), Reset sizes, History, Hide, Review, Edit last | Keep | `ScannedData.jsx` |
| E36 | Proposal grid columns: plans read from the scope files | Keep | **Changed (ch. 22):** the Advisor's cached comparison per line, filtered in the browser, so arriving from the Advisor is instant; detail from `plans/sources/` |
| E37 | Order: current first, then `sort_order`, unlike the Proposal | Simplify | **Changed (ch. 21):** the Advisor section's one order function (current in slot order, then quotes under the current plan they compare to, renewal first, hand order inside), not `ordered_plans` |
| E38 | Rows: fields of the deal's lines in group order, with bands | Keep | `quotes/fields.py`. **Changed (ch. 11):** plan lines joined with requested lines, so an early quote has rows |
| E39 | Fixed layout, frozen panes, per-user sizes, 3-line cut (full on hover), columns windowed above 40 plans | Keep | `src/grid/`, the one grid base for Advisor, Proposal, Documents and Census (ch. 23) |
| E40 | Plan heads: CURRENT, SOLD ✓, ★ FIT (reason on hover), ⚠ count | Keep | From `role`, `sold`, `starred`, counts; RENEWAL chip (`bnf-chip-renewal`). **Ch. 17:** the hover needs `star_reason` and who starred (Advisor section) |
| E41 | Cell look: check, approved, ignored, low colours; underline when from this file, greyer from another, none when typed; ring on the open value; snippet on hover | Keep | State per key from the server. **Ch. 4:** a hand-corrected value keeps its file and stays here |
| E42 | "As in the file": the file's plan columns and printed rows | New | **Changed (ch. 6):** reads `quotes.QuoteLayout`, written at apply by the quote reader (Advisor and AI sections; need 3) |
| E43 | Census grid; only the first 100 employees load | Simplify | The Census tab's grid for this file's people, paged on the server. **Ch. 23, partly rejected:** the roster stays the default, since the file beside it shows the same people (Q3) |
| E44 | Intake view (D-209): bands, muted rows, "Other file" badge, status badges, "N of M questions read…", read-only Contacts and Current coverage | Keep | `IntakeFileView.jsx` |
| E45 | Questionnaire files: a pointer to the Questionnaire tab | Keep | A link |
| E46 | UNKNOWN bucket | Drop | Every file has a kind (Daniel, 2026-10-15) |
| E47 | Empty and loading texts | Keep | Same texts |

### Reviewing values

| # | Functionality (what the user sees -> how it worked) | Verdict | New implementation |
|---|---|---|---|
| E48 | File strip: "N AI values to review · M need checking"; Approve, Ignore, Needs checking on open warnings; disabled when all marked; "No AI warnings to review on X" | Keep | `src/valuereview/ReviewBulkBar.jsx` plus inline Undo |
| E49 | "Show me how" walkthrough | Drop | Walkthroughs dropped |
| E50 | Filter: All plans / Potential errors / Only rows with potential errors | Keep | `potential_error` per key from the server |
| E51 | Picking: click, drag, Shift, Ctrl, head picks a column, label a row, arrows, Ctrl+A, Esc, edge scroll | Keep | `useGridSelection.js`; range math in `selectionRange.js` |
| E52 | Pick bar: "N selected · M potential errors"; A, I, C, F, "Only potential errors"; legend; confirm above 25 values | Keep | `GridToolbar.jsx`, `HotkeyLegend.jsx` |
| E53 | Marks patched in place; above 2,000 the page reloads; badges refresh after 1.5 s | Simplify | Returned marks written into both caches; narrow invalidation above the cap; no timers (ch. 30) |
| E54 | Undo after a pick or key ("Undone — N back; M changed since…") | Keep | `ReviewDone.jsx` reverts the Activity id the request returned; review rows never coalesce (ch. 12) |
| E55 | A/I/C/U/F, off while typing, with a modifier, on repeat, in Edit, in a staged review | Keep | `useReviewHotkeys.js` |
| E56 | List: 8 buckets worst first, finished rows sink, chips with help, details (never a name), 200 then "Show more", ↑/↓/J/K, Enter, F, double-click, side by side at 1,100 px | Keep | `ReviewList.jsx`, `ReviewListRow.jsx`. **Changed (ch. 24):** the owner buckets, orders, counts and pages on the server, so a census never ships 45,000 rows |
| E57 | Chips count values already dealt with; approving a clean found value shows no mark | Simplify | Open counts plus "N done"; the per-file payload carries every confirmation |
| E58 | List strip acts by ids, no undo, wrong toast; three Approve buttons work three ways | Simplify | One marks endpoint per owner; buttons name their target; all undoable |
| E59 | Check this file: synchronous up to 60 pages, else 202 "reopen in a minute" | Simplify | **Changed (ch. 26):** always a `locate` job with progress; it never waits behind a read |

### Find

| # | Functionality (what the user sees -> how it worked) | Verdict | New implementation |
|---|---|---|---|
| E60 | Ctrl+F (again = browser find), 120 ms settle, sticky, amber matches, current ringed | Keep | `FindBar.jsx`, `sf-*` |
| E61 | Word rule: every word, case and punctuation ignored, most specific hit, blanks never match | Keep | One `src/lib/findText.js`, shared with the Advisor |
| E62 | Plan heads match carrier and name only | Simplify | Advisor finder fields: name, plan number, carrier, network, plan type |
| E63 | "N of M"; Enter / Shift+Enter; Only matches; Esc keeps the match for the keys; census, intake, List | Keep | Same; the List matches loaded rows |
| E64 | Carrier aliases ("UHC") | New | One alias table with the Advisor finder (Q8) |

### Review mode and Edit

| # | Functionality (what the user sees -> how it worked) | Verdict | New implementation |
|---|---|---|---|
| E65 | Review mode: a click finds the value, arrows after 200 ms; E or double-click edits; List values open on the Grid | Keep | `useStationState.js` |
| E66 | Edit as a session: session bar, "Done" files a version, write queue | Simplify | Each cell saves through its owner's PATCH. **Changed (ch. 4):** a typed change keeps `doc`, `page`, `cell`, `line` and drops `low`, `loc`, `mark`, `confirmed` |
| E67 | Excel keys, "＋ Add", blue border; Ctrl+Z writes the old value as a new edit | Keep | Shared keys. **Changed (ch. 4):** Ctrl+Z restores value and source entry through the owner's restore, only while unchanged |
| E68 | "These came from the client" toggle | Simplify | `origin: client`, `by` = the user, no link |

### The pop-out window

| # | Functionality (what the user sees -> how it worked) | Verdict | New implementation |
|---|---|---|---|
| E69 | New window (980×1100); toast when blocked; "Show the window / Bring it back here" | Keep | `src/viewer/docWindowLink.js` |
| E70 | Window: client header, file buttons, status pill, keys relayed (never E); loads the whole case | Keep | `/deals/:id/documents/window?link=`; files list only |
| E71 | Presence: 2 s beat, 6.5 s silence, "You're no longer working on…" | Simplify | One hook in the deal layout and the client page (ch. 41) |

### History

| # | Functionality (what the user sees -> how it worked) | Verdict | New implementation |
|---|---|---|---|
| E72 | Version rail, diff, restore, "Save a version", drift and lock notes, "Editing now" | Drop | Dropped in wave 1 |
| E73 | Change history: paged, Refresh, grouped by actor in 30-minute spans, uploads, edits from → to, removals, batches with Revert | Simplify | Same `hst-*` card over Activity rows; Revert per row |
| E74 | CaseDocumentEvent and ValueReviewBatch | Simplify | Activity before/after of kind, role, carrier, lines, archive and marks; never values or labels |

### Work with Claude hand-offs (jobs and cards belong to the WWC and AI sections)

| # | Functionality (what the user sees -> how it worked) | Verdict | New implementation |
|---|---|---|---|
| E75 | Re-read panel: tick files, "Re-read N files", staged job | Keep | `RereadPanel.jsx` → `deals/{id}/ai/reads/` |
| E76 | Re-read for quote files only | Simplify | Every proposal-bucket kind |
| E77 | Ask Claude to re-check; results on the approve-first card | Keep | `deals/{id}/ai/recheck/`. **Ch. 3:** applied approvals carry the person who pressed Apply (`via: recheck`) and can be undone |
| E78 | Staged review: banner, Current vs New, "Use this scan" or Discard, census 409 and force, rank toast | Keep | AI section's component; apply locked; pin wired |
| E79 | Staged agent reads never located | Simplify | The read job locates before staging |
| E80 | "Re-check N flags" above 20; drawer hand-offs | Keep | WWC section; invalidation by key |

### Backend rules and machinery

| # | Functionality (what the user sees -> how it worked) | Verdict | New implementation |
|---|---|---|---|
| E81 | Locator: folding; figures as numbers; nearest page; snippet pin; common figures need an anchor; derived figures; codes; 4 date forms; words weak, never absent; >1,500 pages too large; text-layer guard | Keep | Pure `documents/locate/`, table tests; owner hooks through the `ai` registry (ch. 2, 42); `loc.v` (ch. 28) |
| E82 | Locator reads hidden cells | Simplify | Visible cells only |
| E83 | Four `located_*` columns | Simplify | `loc` in the source entry |
| E84 | Triggers: bare threads, after apply, agent checks, `locate_sources [--recheck]` | Simplify | Read job; Check this file; `check_sources [--recheck]` |
| E85 | Marks: approve, ignore, check, clear; blanks unmarked; lapse on change | Simplify | Pure `review_rules.apply_mark`; lapsing is free |
| E86 | Targets: ids (empty 400), plan ids, one file, scope; warnings only without ids | Keep | Each owner's `mark_values` (ch. 2) |
| E87 | Bulk writes in batches of 500 | Simplify | `select_for_update` ordered by id (ch. 32); one Activity row |
| E88 | Revert only what is still as left, once | Keep | Activity revert, locked |
| E89 | Side writers: `_confirm_value`, scan_audit, Overview confirm-all, flag-check `mark_values` | Simplify | One marks service per owner. **Changed (ch. 3):** machine approval is `via: audit`; whether it may approve is Q2 |
| E90 | `confirm` key on three PATCH routes | Drop | No UI caller |
| E91 | `open_warning_q` SQL twin and parity tests | Drop | One Python rule. **Ch. 8:** no 2V multi-deal list counts warnings; if one comes, owners store `review_counts` in the same write |
| E92 | `shows_confirmation` | Keep | `review_rules.shows_approval` |
| E93 | Member-data snippet scrub | Keep | Reader apply; census and questionnaire values never store `line` |
| E94 | Printed page labels (D-149) | Keep | `Document.page_labels` |
| E95 | Year labels ("2027 Renewal / Rates") | Keep | **Changed from Defer (ch. 16):** Rebecca's naming ask, on every deal: blank labels on renewal, invoice and claims files read effective-date year plus kind |
| E96 | Unlink on `post_delete` at once | Simplify | **Changed (ch. 15):** every row deletion (purge, deal or client cascade) removes bytes on commit |
| E97 | `/api/docscan/kinds/`, `bucket` PATCH, URL fields, DEBUG `/media/` | Drop | Dead or no caller |
| E98 | `prune_orphan_media`, dry run by default | Keep | **Changed from Defer (ch. 15):** rollbacks can leave PHI bytes; `sweep_orphan_files` |
| E99 | Log views of PHI files | New | **Changed (ch. 12, 13):** `viewed`/`downloaded` rows carry the document id, never the name; views coalesce per file; not "Last updated"; PHI kinds census, claims, questionnaire, stop_loss, stop_loss_quote |
| E100 | Walkthroughs, `usageTrack`, e2e seed, source-reading tests | Drop | Non-goals |
| E101 | Locating questionnaire answers | Defer | Not on the owner's list |
| E102 | Carried-forward files (split from E95) | Defer | Renewals are an open question |
| E103 | Questionnaire answers take approve, ignore, check and undo | Keep | **New row (ch. 5):** `questionnaire/marks/` from day one; no `line`; never located |
| E104 | Antivirus (split from E98) | Defer | Waits for the PHI gate |

**Owner's needs served here.**
- (1) E4, E5, E20, E75, E78, E80.
- (2) E21–E29, E48–E59, E76, E77, E79, E81–E89.
- (3) E42 over `QuoteLayout`, with E37, E22, E29.
- (4) E60–E64.
- (7) and (9) are shown only: E40 chips, E37 order.
- (11) E29's `look()` drives the Export viewer's Excel view; `pdfjs.js` drives its PDF view.

## E.4 Data flow (in and out, by model, field or function)

**In**
- `Document` rows only through `documents.services.upload`:
  - the drop and "File as"; coverage chips (`lines`); the checklist and RequestForm;
  - the portal (`source` client, link). Portal census and intake uploads also start reads, staged when a roster exists (Review and AI sections);
  - Attach SBC; deal creation; template import (`plan_template`).
  - Deferred: close-out, implementation, renewal carry.
- `archived_at/by` from archive and restore; `review_state` from the review app.
- `Document.page_labels` and `quotes.QuoteLayout` from the quote reader's apply.
- Source entries (`Plan.sources`, `Intake.sources`, `Member.sources`, questionnaire answers):
  - readers write `origin ai`, `doc`, `page`, `cell`, `line`, `low`;
  - typed changes keep `doc`, `page`, `cell`, `line`;
  - client answers write `origin client` and `link`.
- `loc` from the read job before staging and from `locate` jobs, through each owner's `save_locations`.
- `mark` and `confirmed` only through each owner's `mark_values` and Activity revert.

**Out**
- Readers: bytes, `kind`, `role`, `carrier`, `lines`, `page_count` (agent route ≤100 pages).
- Intake checklist, coverage chips, RFP packet, portal slots: active files by kind and lines; archived ones never count.
- Overview, journey, next action: `review_rules.open_warning` over owner rows. "Not in the file" stays out of those counts (D-122).
- Export check (D-143, RFP section): open and "not in the file" counts, same rules.
- Advisor and Proposal: `QuoteLayout`, the grid base, "open in file" via `?doc=&ref=`.
- Proposals' Export viewer: `sheet_look.look()` and `src/viewer/pdfjs.js`.
- Commissions statements: `src/viewer/PdfViewer` with snippet and value.
- Review queues: `src/viewer/`, `src/valuereview/`. Portal payloads are allowlists, never `sources`.
- Activity feed: document, review and file-access rows, with Revert.

## E.5 Bugs and pain points found (with file evidence)

**Old app**
1. Staged "open in file" pin is dead: `StagedScanReview.jsx` takes the handler (:493), never passes it (:576); neither does `ScanChat.jsx:1389`; the test matches a string (`doc_review_tests.py:305`). Fixed in E78.
2. Only 100 census employees load (`DocumentsTab.jsx:355-358`, `serializers/market.py:481`). Fixed in E43.
3. Plan order ignores `proposal_order` (`serializers/pipeline.py:578-594`). Fixed in E37.
4. An unchanged PATCH answers 400 (`cases.py:767-773`). Fixed in E14.
5. Batch uploads are not atomic; wrap and POP files go before the new row exists (`cases.py:604-639`). Fixed in E7.
6. Files unlinked before commit (`signals.py:27-29`). Fixed in E96.
7. Hard delete loses provenance (`cases.py:815-825`). Fixed in E15.
8. Values in GET query strings can put census names in access logs (`SheetViewer.jsx:110-113`). Fixed in E28.
9. Viewing a PHI file is never logged (`views/versions.py:451`). Fixed in E99.
10. Several mark writers: `_confirm_value` (`views/shared.py:269`, from `views/pipeline.py:1137`, `views/market.py:366`, `views/cases.py:852`) and batchless flag-check approvals (`claude_edits.py:546`), absent from history and not undoable. Fixed in E77, E89.
11. Staged agent reads never located (`extraction.py:436`, `staged_turn.py:223-227`). Fixed in E79.
12. Agent reads never audited (`extraction.py:631`). AI readers section.
13. Checks on bare threads; the 202 has no job (`source_check.py:287-302`, `DocumentsTab.jsx:1838`). Fixed in E59.
14. No lock on staged apply (`views/ai.py:675-757`) or revert (`value_review.py:350-353`); stale `params` saved (`extraction.py:449-451`). Fixed in E78, E88.
15. The List shows no progress (`FileReviewList.jsx:103-107`); a clean approval shows no mark (`value_review.py:382-389`). Fixed in E57.
16. Approve means three things: the List strip sends no `on_document`, has no undo (`DocumentsTab.jsx:1501-1520` against `1643-1655`), and its toast is wrong (:1514). Fixed in E58.
17. Re-read for quote files only (`DocumentsTab.jsx:1855, 2467`). Fixed in E76.
18. `other` is "Intake" in `docTypes.js:7`, "Other" in `claudePages.js:106`. Fixed in E5.
19. Every sheet window parses twice, uncached (`views/versions.py:500-512`, `sheet_format.py:254`). Fixed in E29.
20. The locator reads hidden cells (`chunking.py`). Fixed in E82.
21. PDF viewer sends a localStorage token (`benefitsShared.js:366-376`), loads OCR from a CDN (`pdfOcr.js:13`), has benibridge twins: fixed in E22–E25. Whole-file download (`PdfViewer.jsx:199-203`) stays.
22. `ORIGIN` lacks `duplicate`, `remove` (`VersionRail.jsx:32-48`); `REVIEW_SCOPE_LABELS` lacks questionnaire (`history.py:249-251`); `--accent` undefined (`benefits.css:3790`). Fixed in E73 and the CSS port.
23. `DocumentsTab.jsx` is 3,073 lines; `scopeDocId` is picked before plans load and sticks (:240-255). Fixed in E1.
24. Dead code: `bucket` PATCH, URL fields, `.bnf-doc-adder-file`, `.bb-pdf-link`, `.bb-doc-pages`, 13 guide references. E97, E100.
25. The window loads the whole case (`DocumentWindow.jsx`). Fixed in E70.
26. No proxy upload cap (`frontend/nginx.conf`). Fixed in E7.

**2V code already built**
27. `documents/services.py:97-104` saves and logs unchanged edits. Fixed in E14.
28. `documents/models.py:43-46` unlinks at once. Fixed in E96.
29. `documents/tests/test_documents.py:28-29` asserts hard delete. Changes with E15.
30. `deals/downloads.py:20-28` has no sandbox CSP. Fixed in E17.
31. `page_count` never set; no pypdf (`documents/services.py:58-75`). Fixed in E7.
32. `quotes/template_views.py:46` stores imports as `other`. Fixed in E8.
33. `quotes/selectors.py:50-62` marks every unconfirmed AI value `to_check` by `confirmed_by`; the Advisor paints it amber (`advisor/ValueCell.jsx:87`). Fixed by one `open_warning` (E.6).
34. `deals/values.py:42-46` with `quotes/services.py:104-109, 144-149`: a typed change drops `doc`. Fixed in E66.
35. `documents/kinds.py:28`: `PHI_KINDS` misses questionnaire and stop-loss kinds. Fixed in E99.
36. `documents/services.py:118-120`: the download row omits which file (§3.8) and moves "Last updated" (`deals/selectors.py:33-45`). Fixed in E99.
37. `documents/services.py:21`: blank kind becomes `other`. Fixed in E6.
38. `backend/settings.py:105`: 50 MB exceeds Cloud Run's 32 MiB. Fixed in E7.
39. `documents/services.py:70-71`: bytes stored before commit. Fixed in E7, E98.
40. `frontend/src/api/deals.js:21-28`: every write refetches every deal query; focus refetch on. Fixed in E53.
41. `quotes/selectors.py:82`: every Advisor cell ships its whole source entry. Fixed in E.6.
42. `quotes/selectors.py:13-15`: role then `sort_order`, not the old order. Fixed in E37.

## E.6 New design

**Placement: no new Django app.**
- The station is `documents` plus `frontend/src/deal/documents/`. Shared code: `src/viewer/`, `src/valuereview/`, `src/grid/`.
- `documents` has no registry (ch. 2). Each owner serves its own sources and marks endpoints (§8.13).
- Owners register locate hooks with the `ai` registry. The `locate` job is an `ai` Job kind; Job stays in `ai` (§3.3, §10.2).

**Models (documents)**
- `Document` (exists). Add `archived_at`, `archived_by`, `page_labels` JSON (`{"3": "2"}`); fill `page_count` at upload.
- Managers: `objects` hides archived rows; `all_objects` serves value links, opening files and "Show removed files".
- Kinds (`kinds.py`, /api/meta/), one entry per kind with `label`, `bucket`, `accept`, `file_as`, `asks_role`, `phi`:
  - add `form_5500`, `questionnaire`, `stop_loss`, `stop_loss_quote`, `tpa_proposal`, `plan_template`;
  - buckets: proposal (quote, renewal, sbc, stop_loss_quote, tpa_proposal, plan_template), census, questionnaire (questionnaire, stop_loss), none (issued `proposal`), intake (the rest);
  - `file_as`: census, sbc, questionnaire, stop_loss, quote, other;
  - `asks_role`: quote, renewal, sbc, stop_loss_quote, tpa_proposal;
  - `phi`: census, claims, questionnaire, stop_loss, stop_loss_quote.
- No `DocumentText` and no `layout` field (ch. 1, 25, 6). The locator re-extracts text with pypdf inside its job.

**Model (quotes, with the Advisor and AI sections): `QuoteLayout`**
- `document` FK, `line`, `where` (`{"page": 3}` or `{"sheet": "Medical"}`).
- `columns`: `[{"plan": 41, "head": "Gold PPO 1500"}]`.
- `rows`: `[{"label": "Deductible (Ind/Fam)", "keys": ["deductible_single", "deductible_family"]}, {"label": "Chiro visits", "keys": [], "printed": ["20/yr", "30/yr"]}]`.
- One row per table. Written at apply from the plans applied. `printed` is never kept for PHI kinds.

**Source entry additions** (agree with the foundation):
- `line`: reader's line, ≤300 characters; never on census or questionnaire values.
- `loc`: `{state, page or sheet+cell, hits, via, why, printed, v, at}`; state found, derived, weak, absent or nocheck.
- `mark`: `{state: ignored or check, by, at}`.
- `confirmed`: `{by, at}`; a machine adds `via: "audit"` with `by` null; a person applying a re-check adds `via: "recheck"`.
- A typed change keeps `doc`, `page`, `cell`, `line`; drops `low`, `loc`, `mark`, `confirmed`.

**Pure rules, `documents/review_rules.py`** (they read the locator's vocabulary, ch. 42):
- `apply_mark(entry, action, user_id, at)`; blanks take no mark.
- `is_approved`, `open_warning`, `potential_error`, `shows_approval`, `review_bucket` (8 buckets; "moved" when `loc.page` differs), `quality_headline`.
- `open_warning` is the one rule. Owners' `statuses()` call it, so the Advisor's amber agrees (ch. 3). Default: the old meaning, until Q2.

**Locator and sheets (documents)**, each module under 300 lines:
- `locate/fold.py`, `locate/pdf_text.py` (pypdf texts with form fields, guard), `locate/pdf_index.py`, `locate/sheet_index.py` (visible cells), `locate/query.py` (`Query`, `Located`, `VERSION`).
- `sheets.py`: windows, `find_cell`, `cell_match`; one parse per request; streaming for Plain.
- `sheet_look.py`: `look(workbook, sheet, start, rows, cols)`, pure; `proposals` reuses it.

**Services and selectors**
- `documents/services.py`:
  - `upload`: kind required, magic bytes, page count, bytes removed if its transaction fails;
  - `update`: writes nothing when nothing differs; a bad kind saves nothing;
  - `archive` (refuses issued proposals), `restore`, `purge` (admin);
  - `record_access`: PHI kinds; Activity row with the document id; views coalesce per file.
  - Every row deletion removes bytes on commit.
- Each owner's `mark_values(user, deal, action, target)`:
  - target: ids, plan ids, document ids or scope;
  - rows locked by id; one non-coalesced Activity row with marks before and after, never values;
  - returns changed marks and the Activity id; registers its revert.
- Each owner's `source_rows(deal, document_ids, bucket, page)`: rows, bucket counts, quality with required blanks; 200 per page.
- `ai/check.py`: the `locate` job calls owners' `locate_queries` and `save_locations`; it runs beside reads. `manage.py check_sources [--recheck] [--dry-run]`.
- Compact Advisor payload: per key only `origin`, `doc`, `page` or `cell`, status (ch. 7).

**Endpoints**

| Method and path | Purpose |
|---|---|
| GET/POST `deals/{id}/documents/` | List (`?archived=1`); upload (kind required) |
| PATCH `documents/{id}/` | Label, kind, role, carrier, lines |
| POST `documents/{id}/archive/`, `restore/` | Archive, restore; DELETE is the admin purge |
| GET `documents/{id}/download/[?inline=1]` | Bytes; sandbox CSP inline; PHI logged |
| GET `documents/{id}/sheet/?sheet=&start=&look=1` | Sheet window |
| POST `documents/{id}/sheet/find/` | `{value, line, hint}` → `{sheet, cell, state}` |
| GET `deals/{id}/plans/sources/?documents=&bucket=&page=` (also intake, census, questionnaire) | List rows, counts, quality |
| POST `deals/{id}/plans/marks/` (also intake, census, questionnaire) | `{action, ids or plan_ids or document_ids}` → changed marks, Activity id |
| POST `deals/{id}/ai/check/` | `{document_ids, recheck}` → `201 job` |
| POST `activity/{id}/revert/` (deals) | Undo and Revert |
| GET `deals/{id}/plans/?line=` (quotes) | Advisor comparison reused by the grid |

**Frontend**
- `deal/documents/`: `DocumentsTab`, `useStationState`, `FileTabs`, `FilePanel`, `RereadPanel`, `ViewerPane`, `ScannedData`, `ProposalGrid`, `PlanHead`, `ValueCell`, `GridToolbar`, `IntakeFileView`, `CensusFileView`, `FindBar`, `HistoryCard`, `DocumentWindowPage`.
- `src/viewer/`: `DocumentViewer`, `PdfViewer`, `usePdfDocument`, `pdfFind`, `pdfGeometry`, `pdfOcr`, `pdfjs`, `ImageViewer`, `SheetViewer`, `SheetTable`, `FileBar`, `docWindowLink`. Takes a URL or a blob.
- `src/valuereview/`: `ReviewBulkBar`, `ReviewList`, `ReviewListRow`, `HotkeyLegend`, `ReviewDone`, `useReviewHotkeys`, `useMarks`.
- `src/grid/`: `useGridSelection`, `selectionRange`, `useGridKeys`, `useGridSizes`, `useFreezePanes`, `useWindowedColumns`. `src/lib/findText.js`.
- Queries: the grid reads `['deal', id, 'plans', line]`; the station adds `['deal', id, 'sources', owner, ids, page]`. Marks write into both. No `invalidateDeal` from station writes; focus refetch off for heavy queries; BroadcastChannel tells the pop-out.
- localStorage keys for List/Grid, Review mode, sheet look and sizes are kept.

**Stylesheets to copy verbatim** (same class names):
- `benefits.css`: 477 (`bnf-chip-renewal`); 532–651 (`bnf-compare-table`, `bnf-benefit-col`, `bnf-plan-head`, `-carrier`, `-name`, `bnf-plan-chip`, `bnf-chip-current/-sold`, `bnf-group-row`, `bnf-cell`); 722–727 (`bnf-cell-error/-warn`); 774–785 (`bnf-nopreview`); 1043 (`bnf-chip-shortlist`); 2408–2851 (`bnf-docs-*`, `bnf-doc-*` except `bnf-doc-adder*`, `bnf-scan-*`, `bnf-quality*`, `bnf-rescan-*`, `bb-doc-tab`, `dw-*`); 3781–3966 (`bnf-scan-body/split`, `bnf-linklike` with `--accent` fixed, `bnf-locked`, `bnf-load-*`, `bnf-refresh-*`, `bnf-staged-banner`; not `bnf-ver-*`, `bnf-vdiff-*`, `bnf-edit-bar`); 5632–6042 (`bnf-file-bar`, `bnf-frl-*`, `bnf-review-*`, `bnf-sheet-*`, `bnf-image-doc`, `bnf-viewer-host`, `bnf-reread-*`, `bnf-src-pin`, `bnf-cell-elsewhere`, `bnf-has-src`, `bb-cell-approved/check/ignored`, `bb-swatch-*`, `dw-file*`, `dw-what`); 6265–6273 (`bnf-back-review`).
- `App.css`: 2441–2453 (`bb-badge*`); 2750–2954 (`bb-pdf-*` except `bb-pdf-link`, `bb-doc-tab(s)`, `bb-doc-open-link`, `bb-cell-provenance/noprov/active`).
- `benefits-grid.css`, `benefits-freeze.css`, `benefits-grid-sizes.css`, `benefits-history.css`.
- Ranges the Advisor also needs are copied once. The staged review (1187–1376), `bnf-pchg-*` and `bnf-claude-strip` belong to the AI and WWC sections.

**Tests (behavioural)**
- documents: accept lists; magic bytes; page count; blank kind 400; unchanged PATCH writes nothing; refused kind saves nothing; archive keeps `doc`; archived files leave checklist, packet and portal slots; issued proposals refuse archive; bytes go only after commit, also on cascade; failed uploads leave no bytes; inline CSP; PHI rows carry the id, no name, and leave "Last updated"; sheet paging, hidden rows, limits, look, .xls, .csv; `look()` on an in-memory workbook.
- Locator: a table for every state and `via`/`why`; guard; hidden cells; scanned pages "nocheck"; `--recheck`; no answer carries file text.
- `review_rules`: every action against every prior state; blanks; a changed value drops marks; a typed change keeps the file.
- Per owner: targets; other deals' ids refused; empty list 400; one non-coalesced Activity row with no values; revert skips changed values, runs once (409); concurrent reviews survive; review beside apply never deadlocks; quality counts blanks; paging; bounded query counts.
- ai: staged values carry `loc`; double apply refused; `locate` runs beside a read; re-check approvals carry the person.
- Vitest (new; pure modules only): `findText`, `selectionRange`, `pdfFind` on synthetic text items, List order.
- Click-through on a golden deal with synthetic files.

**Deployment**
- 30 MB upload cap (verify Cloud Run's limit).
- Release gate: WhiteNoise serves `.mjs` as JavaScript; a sandboxed PDF opens in the station on Chrome and Edge.
- tesseract.js assets under `/static`.
- Job polls get their own throttle scope (ch. 31).

**Build order**
1. Kinds, archive, 2V fixes.
2. Viewers and `look()` (before the Export viewer).
3. Rules, owner endpoints, List, Undo.
4. Proposal grid on the shared base.
5. Locator and `locate` job.
6. Intake and census views.
7. Re-read and re-check hand-offs.
8. Pop-out.
9. OCR.
10. "As in the file".

**Rulings on the challenges.**
- Accepted: 2–7, 9, 10, 12–22, 26–30, 32–38, 40, 41.
- Modified:
  - 1: the browser highlight is a trimmed port; repeated figures still need the row and column logic.
  - 8: no 2V multi-deal list counts warnings.
  - 11: the picker keeps its rule.
  - 23: roster default until Q3.
  - 24: server paging for every List.
  - 25: no stored page text.
  - 31: no per-arrow requests remain.
  - 39: direct uploads only if Q10.
  - 42: Job stays in `ai`.
- Rejected outright: none.

## E.7 Open questions for Daniel

1. **Remove.** Should Remove archive a file, keeping its values linked? Or delete it for good? Do you ever need a true purge, for example when a client asks for PHI to be deleted?
2. **What needs approval.** Every value Claude read (the 2V plan)? Or only values Claude doubted or the check could not find, as before (the default here)? May Claude's own double-check clear a doubt by itself, as before?
3. **Census files on Documents.** The full roster beside the file, as before? Or only the review list?
4. **Logs.** Should viewing a PHI file be logged, not only downloading? Are invoices PHI too (list bills name members)?
5. **Hidden rows.** Claude skips hidden rows and columns. Should the viewer still show them greyed?
6. **File types.** Wrap, POP and sold paperwork wait for close-out and implementation. Agreed?
7. **Scanned pages.** Is highlighting on scanned pages needed at launch?
8. **Carrier nicknames.** Should search treat "UHC" as UnitedHealthcare?
9. **Pop-out window.** Is it used enough to build before launch?
10. **File size.** Do you get files over 30 MB? If so, uploads go straight to storage.
