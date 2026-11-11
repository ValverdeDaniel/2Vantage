# Part D — AI readers and Work with Claude

[← Porting plan](README.md)

**What it is:** Work with Claude is the drawer that works over the whole deal: a person drops carrier quotes, SBCs and client files, asks Claude to read them or to change the plan table, and checks what Claude did. The AI readers turn files into plan, intake, census and questionnaire values that keep their page or cell, and the Documents review station shows each value beside its file. In 2Vantage this becomes one `ai` app (a worker-run job queue, one reader per target registered by the app that owns the data, one change set per job, one landing rule, Undo for every landing) plus the station's screens.

## D.1 Files read, in order (one line each)

Old root `c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/`; **2V** rows are under `c:/Users/fooba/OneDrive/desktop/Vantage_all/2Vantage/`.

**Specs and READMEs**
| File (lines) | What it is / what it taught |
|---|---|
| `benefits/README.md` (394), `benefits/ai/README.md` (826) | Module map; reader history; the 16k output cap drove all windowing. |
| `docscan/README.md` (148), `docscan/CLAUDE.md` (103) | Chassis rules; the reaper race (line 70). |
| `PlanningDocs/Benefits/decisions.md` | D-149–D-152, D-195–D-201 and D-218–D-223 in full; other headings. |
| `docs/CyberSecurity_PHI/claude-and-the-anthropic-baa.md` | BAA of 2026-11-06: Messages API only, no beta features; tools, inline PDFs, effort and the 1-hour cache not yet confirmed in writing. |
| `lessons/README.md` (386), `assistant/README.md` | Lessons and saved readers; the help bubble is out of scope. |
| **2V** `CLAUDE.md` (42); `plan.md` §3.3–§3.8, §5.4, §5.5, §8.13, §10, §12–§16; Claude API reference (bundled skill, 2026-11-03) | Conventions, enrollment order, staged reader, non-goals; prices, Opus 5.5 rules, structured outputs, caching, refusals. |

**Models and settings**
| File (lines) | What it is / what it taught |
|---|---|
| `benefits/models/case.py` (1878), `models/pipeline.py` (621), `users/models.py` (229) | Jobs, messages, documents, value layers, plan bookkeeping; `claude_direct`. |
| `backend/settings.py` (220–405), `backend/checks.py` (98) | `BENEFITS_*` flags; check E004. |
| `lessons/models.py`, `services.py`, `governance.py`, `agents.py` (100), `access.py` (271) | Lessons, agents, `injection_for`. |
| **2V** `deals/models.py` (94), `activity.py` (47), `values.py` (47), `stages.py` (23), `services.py` (143); `documents/models.py` (46), `kinds.py` (44), `services.py` (120), `urls.py` | Activity merges writes by actor and key and has no before/after; `advance` trusts the object it is given; reader kinds missing; `record_download`. |
| **2V** `quotes/models.py` (73), `services.py` (224), `marks.py` (162), `selectors.py` (155), `values.py` (91), `fields.py`, `template.py`, `urls.py`; `proposals/models.py`, `selectors.py` (90), `selection.py` (44); `backend/settings.py`, `meta.py`, `urls.py` | All-or-nothing `clean_values`; one renewal per current plan; marks through `.update()`; typed enrollment wins; the Proposal shows requested lines only; stars pick default alternates. |

**Rules and services**
| File (lines) | What it is / what it taught |
|---|---|
| `benefits/ai/pages.py` (169), `page_labels.py` (198), `page_plan.py` (280), `doc_format.py` (191) | Tab kinds and targets; page map; text-layer planner (18 output tokens a number); layout hash (off). |
| `pipeline/plan_codes.py` (152), `plan_checks.py` (186), `quote_checks.py` (364), `spend.py` (110), `table_lock.py` (109) | Codes, findings, insurance checks (off); spend, `show_costs`, Opus gate; the lock. |
| `quote_reconcile.py` (1083), `extraction.py` (846), `pipeline/claude_writes.py` (222), `claude_edits.py` (684) | Matcher and unseen rule; dispatcher and rank after read; the agent's writers. |
| `pipeline/advisor.py` (715), `advisor_filters.py` (351), `composition.py` (843), `plan_remove.py` (193), `plan_merge.py` (434), `normalize.py` (276), `workbook_import.py` (378), `enrollment.py`, `exec_summary.py` (1170–1180) | Rank, `curated_reason`, `set_board`; row lists, order, pairs; house formats; line counts; carrier counts never reconciled with ours. |
| `market/value_review.py` (492), `census_pivot.py` (629), `census_upsert.py` (271), `census_request.py` (844) | Review marks; census layouts, upsert, asks. |
| `key_builder.py`, `answer_keys.py`, `key_adjudication.py`, `synthetic_docs.py`, `target_keys.py`; commands `reader_trial` (1166), `reader_corpus`, `make_mock_quotes`, `target_fixture`, `target_trial`, `answer_key`, `seed_agents`, `locate_sources`; shims `benefits/{claude_readers,extraction,scan_chat,census_reader,advisor}.py` | Trial tooling, backfills, re-exports. |

**AI**
| File (lines) | What it is / what it taught |
|---|---|
| `docscan/client.py` (320), `pricing.py` (83), `jobs.py` (189) | Forced tool, thinking off, 16k; mispriced cache reads; reaper and a 30-second keepalive thread. |
| `docscan/phi_screen.py` (250), `chunking.py` (461), `kinds.py` (195), `urls.py` (7), `views.py` (28), `locate.py` (579) | Member-page rules, text-less pages unscreened; windows; kinds; the locator's five states. |
| `docscan/export_guard.py` (114), `serving.py` (75), `sheet_preview.py` (288), `sheet_format.py` (353) | Formula guard; no-store serving; sheet drawing. |
| `benefits/ai/claude_readers.py` (4127), `scan_chat.py` (2342), `page_context.py` (667) | Prompts (enrollment pages ignored, 108–112), merge; chat, seven tools, routing; tab context. |
| `agent_turn.py` (1423), `table_agent.py` (922), `staged_turn.py` (262), `table_agent_bulk.py` (168), `table_agent_lessons.py` (80) | 3 files of 100 pages, Haiku for edits only; renewal, SBC and pair rules (prompt 111–165); replay; child jobs. |
| `read_correction.py` (508), `flag_check.py` (304), `scan_audit.py` (399), `source_check.py` (374), `intake_agent.py` (371), `census_agent.py` (605), `questionnaire_agent.py` (612), `unleashed_agent.py` (1029) | Four re-check paths; the other targets; the export sandbox. |

**Views and payloads**
| File (lines) | What it is / what it taught |
|---|---|
| `benefits/views/ai.py` (1316), `views/portal.py` (2609), `views/shared.py` (297) | AI endpoints, unlocked cancel (1287–1289); portal reads. |
| `views/versions.py` (552), `views/review.py` (628), `review/items.py` (1544), `views/cases.py` (1256), `views/pipeline.py` (2581) | Sheet and locate views; review queues; upload gate, value review, stars, imports. |
| `serializers/scan.py` (562), `serializers/primitives.py`, `benefits/urls.py` (362), `lessons/urls.py` (26), `lessons/views_agents.py` (404) | Payloads; routes. |

**Frontend** (`frontend/src/`)
| File (lines) | What it is / what it taught |
|---|---|
| `services/api/benefitsShared.js` (423), `benefitsClose.js`, `lessons.js`, `agents.js` | Every AI call. |
| `components/benefits/shared/ScanChat.jsx` (2068), `ScanDrawer.jsx` (45), `chatControls.jsx` (249), `ClaudeLockSwitch.jsx` (44), `claudePages.js` (112), `StagedScanReview.jsx` (583), `ProposedChangesCard.jsx` (450) | Drawer, ChatBar, pickers, lock; review cards (pins unwired, line 576). |
| `CaseWorkspace.jsx` (1346), `useDealJobStore.js` (239), `flashPlans.js` (35), `NewCase.jsx` (346) | ✦ button, strip, job watcher, flashes, quotes-first deal. |
| `DocumentsTab.jsx` (3073), `FileReviewList.jsx` (324), `ReviewBulkBar.jsx` (106), `valueReview.js` (160), `useReviewHotkeys.js` (73), `ScanFindBar.jsx` (132), `GridReviewToolbar.jsx` (171), `ReviewFilePane.jsx` (85), `PdfPagesPreview.jsx` (125), `findText.js` (49), `SectionReviewBar.jsx` (180), `overview/DataConfidence.jsx` (402) | The review station: List, Grid, keys, Review mode, bulk bar (asks over 25), find, pop-out, potential errors (`LOOK_AGAIN`); double-check. |
| `close/WorkWithClaude.jsx` (262), `AddQuotes.jsx` (137), `ComparisonGrid.jsx` (1365), `AdvisorTab.jsx` (3924), `PlanTemplateImport.jsx` (89), `UnleashedDrawer.jsx` (633) | Guidance, a dead page, grid, SBC button, template hand-off, sandbox. |
| `market/CensusTab.jsx` (948), `IntakeTab.jsx` (1638), `BenefitsClientPortal.jsx` (3648) | Census and Intake doors; portal poll. |
| `voice/localSpeech.js` (226), `MicButton.jsx` (249); `lessons/AgentPicker.jsx` (106), `TeachLessonButton.jsx` (141), `ReadByStamp.jsx` (84); `utils/fileDrag.js` (55), `usage.js` (212), `benefits/docTypes.js` (36), `contexts/UserContext.jsx` (114), `App.jsx`, `guides/library.js` (313) | Dictation; readers and lesson flags; drops, usage, types, user flags, routes. |
| **2V** `pages/DealPage/DealPage.jsx` (99), `ui/Drawer.jsx` (49), `api/documents.js` (49), `package.json` | Mount point; the kit drawer is a modal. |

**Styles**
| File (lines) | What it is / what it taught |
|---|---|
| `styles/benefits.css` (6275) | `bnf-chatbar` 384–467; `bnf-wwc-*`, `bnf-claude-lock` 403–528; messages 468–530; `bnf-scanchat-*` 394–3940; `bnf-scan-drawer` 1378–1471; `bnf-staged-*` 1322–5998; `bnf-pchg-*` 5691–5821; `bnf-claude-strip` 5729–5795; `bnf-src-pin` 5990–5997; station `bnf-frl-*`, `bnf-rv-file*`, `bnf-review-bar*`, `gs-*`, `sf-*`. |
| `styles/assistant.css` (444), `styles/lessons.css` | `hlp-mic*` 398–444; `agt-*`, `lsn-*`. |

**Tests (by name):** `benefits/tests_pkg/`: ai_tests (3493), reread_tests (4297), work_with_claude_tests (988), wwc_accuracy_tests (1928), wwc_targets_tests (1299), wwc_keys_tests, claude_lock_tests (380), sbc_read_tests (409), partial_read_tests (484), read_speed_tests (572), prompt_pack_tests (404), scan_control_tests, claude_edits_tests, read_correction_tests, flag_check_tests, source_check_tests, staged_review_tests, dense_read_tests, plan_type_tests, portal_tests, questionnaire_tests, board_filters_tests (354), table_note_tests (174), workbook_preview_tests (411), normalize_tests (231), upload_drop_tests (165), quote_checks_tests (326), mock_quote_tests (271), reader_trial_tests (633), case_tests; `docscan/tests.py` (2098); `lessons/tests.py` (2440); `assistant/tests_pkg/frontend_guard_tests.py`.

## D.2 Old data model, in brief

- **ExtractionJob**, one table for all background work: `case`, `kind` (quote, census, intake, rank, qform, audit, correct, work), `document`, `status`, `pct`, `log`, `mode` (apply or staged), `resolution`, `error`, `started_by` (null = portal), `heartbeat_at`. `params` is a sparse bag (inputs, models, chat, permissions, saved reader, telemetry, cancel flag); `result` holds a staged read, report, turn result, proposal or rank change. An SBC read is `kind='quote'` with `params.design_only`; a routed read is `kind='work'`.
- **AdvisorMessage**: `role`, `thread` (advisor, scan, unleashed), `content`, `user`, `job`, `context` (chat number, open file and page, scan-context text, model, usage). Chat 0 is "Earlier chat".
- **BenefitsCase**: `client_guidance` (4,000 characters), `claude_table_lock`, `ai_budget_usd` (no screen), `proposal_config` (notes, pairs, row lists, plan order, `tier_counts_by_line`).
- **CaseDocument**: `doc_type` (19), `carrier`, `lines`, `page_count`, `page_labels` (also caches screen counts).
- **Plan**: `read_key`, `read_state`, `plan_codes`, `carrier_from_document`, `source_document`, `renewal_of`, `sort_order`, `is_shortlisted`, `shortlist_reason`. **PlanValue** (EAV): `extracted_value`, `low_confidence`, `edited_value`, document, page, snippet, confirmation, review mark, `located_*`.
- **UserProfile**: `claude_direct`, `agents_access`, `is_developer`. **lessons**: Lesson, LessonSignal, Agent with versions, shares and runs.
- **Derived on read**: effective value `edited ?? extracted`; a confirmation, mark or location counts only while its value is still effective; deal spend summed over every job and reply; the screen's state from the running job after reaping, the newest staged job and the newest proposal.

## D.3 Functionality inventory and verdicts

Owner needs covered: (1) D14, D16, D17, D39, D43, D46, D49–D51; (2) D15, D38, D47, D54, D57–D59, D116, D117; (3) D28, D66, D123, D133; (4) and (5) D80; (6) D67, D88; (7) D96, D97, D117; (8) D28, D115; (12) D114. Need (9), the slot picker, is the Advisor's; D62 only keeps reads from moving plans. "After review" marks a verdict or reason changed by the adversarial review.

### Doors, drawer and composer
| # | Functionality (what the user sees -> how it worked) | Verdict | New implementation |
|---|---|---|---|
| D1 | ✦ Work with Claude pill, navy, bottom-right on Intake, Census, Questionnaire, Advisor, Proposal, Documents; hidden while open -> `openClaude(PAGE_DEFAULT_KIND[tab])` | Keep | `deal/claude/ClaudeButton.jsx`, once in DealPage, same classes. |
| D2 | Gold "Claude Unleashed" pill | Defer | With D101. |
| D3 | URL doors `?claude=1`, `?scan=<kind>`; a button-opened drawer stays open across tabs | Simplify | Keep `?claude=1` and stay-open; `?scan=` served guides only. |
| D4 | Right panel, no scrim, min(560px, 94vw), 880px while a review shows; Escape stops the mic, then closes | Keep | `ClaudeDrawer.jsx`, not the modal `ui/Drawer`: the table stays usable. |
| D5 | "Reading" picker for people without direct mode; lock switch | Simplify | Same look; the picker stamps the kind on new files, for everyone. |
| D6 | Client guidance box; ⚖ Rank plans or "Rank filtered (N)" | Keep | `GuidanceBox.jsx`; guidance on `DealAi`; the rank is a job. |
| D7 | Chats ▾ (title · tab · date, "last used by"), ＋ New chat (draft until sent), ✎ Rename | Keep | `Chat` gains `tab`, `last_used_by`; numbers under the `DealAi` lock. |
| D8 | "This chat $x" (admins), "Deal $y of $25", "Last read"; loops over every job | Simplify | Message costs for admins, deal line and run summaries for everyone; one SUM of `Job.cost_usd`. |
| D9 | Model pickers by permission; Haiku 5.5 "edits only"; "Long files" | Simplify | One picker; Opus 5.5 for admins and direct people; Haiku only for chat and edits, a send with files uses the default (B10). |
| D10 | "Read with" saved-reader picker | Defer | With D103. |
| D11 | Earlier years' chats, read-only | Defer | Renewal-only; renewals are open. |
| D12 | "Earlier chat" (chat 0, retired thread) | Drop | Legacy data; 2V starts empty. |
| D13 | File chips: name, "scanned"; type and page facts for direct people | Keep | For everyone, plus a role select; facts from `Document.screen`. |
| D14 | File room: File as, Upload N files ▸, ticks, 👁, type, "📥 Read N files into the table" / "🔍 Scan N selected"; untyped refused | Simplify | `FileRoom.jsx`, one "Read N files"; landing per D71. |
| D15 | "Read N SBCs (into the table)" | Simplify | One button; SBC reads always wait. |
| D16 | 📎, drop on panel or Documents zone, "Drop to attach…" overlay, toasts; drops refused while a job runs | Keep | `useAttach.js`, types from meta; a drop is never refused, the send queues. |
| D17 | Attaching is the request; a mixed set runs census → questionnaire → intake → proposal | Keep | For everyone; one job per send, same order. |
| D18 | AddQuotes page | Drop | Dead: no door reaches it. |
| D19 | Enter sends, Shift+Enter new line; Send off mid-turn; locked placeholder | Keep | `Composer.jsx`. |
| D20 | Mic: Chrome on-device speech, 60 MB setup card, progress, help card, banners | Simplify | After review (was Keep): from the Ask Claude assistant, not on the owner's list. Shown where Chrome offers it; first click installs the pack; no cards. |
| D21 | Thinking seconds; "a big request can take a minute" after 30 s | Keep | From `Job.started_at`. |
| D22 | Running card: %, "$x so far", Stop, last 8 steps, model, queue place | Keep | `RunningCard.jsx`; Stop for every kind (B20). |
| D23 | ↶ Undo this run, ↻ Try again with <next model>, ✓ Check again; Haiku → Sonnet → Opus | Keep | D73–D76. |
| D24 | Over-budget card: Run anyway (admins, direct) or Dismiss | Keep | Re-sends with `budget_override`. |
| D25 | Hint after 30 messages; Retry when a chat fails to load | Keep | — |
| D26 | No key: "Scan a document" panel; demo stubs invent plans | Drop | Demo code; without a key every door hides. |
| D27 | "Claude finished one part — the next is under way" | Simplify | One job whose steps name each part. |

### Reviews, strip and results
| # | Functionality (what the user sees -> how it worked) | Verdict | New implementation |
|---|---|---|---|
| D28 | Staged review: Review this scan, Discard, Use this scan ▸; ReadByStamp; banners; field-group diff with chips (NEW, No match, Fills, Sold), % move, "not in the file" | Keep | Generic `ReviewCard.jsx`, quote renderers in `deal/advisor/claude/`; printed row order; renews/replaces selects (need 8); pick-current rows; live pins (B9). |
| D29 | Census and intake diffs in the drawer; Documents shows the waiting review in Scanned data | Simplify | After review (reason rewritten): census → `CensusImport` on Census, intake → Intake's review, the drawer links; Documents shows a waiting change set in the same card. |
| D30 | "🔒 Rule saved… suggested fix" line | Defer | With lessons. |
| D31 | Proposed changes: old → new, % move, page, evidence; stale and unsure unticked; Apply N selected ▸; Undo; Discard; "Left alone" | Keep | `ChangeList.jsx` over the same change set. |
| D32 | Flag re-check variant | Keep | Check mode (D93). |
| D33 | Teach the reader; 🚩 Teach a lesson | Defer | With lessons. |
| D34 | ClaudeStrip: progress with Stop, "✓ N values changed", news (Review ▸, ★ rank, failed, "✦ Re-check N flags") | Keep | `ClaudeStrip.jsx` over `useAiState`. |
| D35 | Changed columns flash after a landing | Keep | Plan ids ride the finished job, so automatic landings flash too. |
| D36 | Documents' polled rank toast | Simplify | The strip's rank news. |

### Doors on other tabs
| # | Functionality (what the user sees -> how it worked) | Verdict | New implementation |
|---|---|---|---|
| D37 | ＋ Add quotes, ＋ Add SBCs | Keep | Open the drawer on that kind. |
| D38 | Attach SBC… in a plan column menu; toast "review it before it changes the plan" | Keep | `POST plans/{id}/sbc/`; always reviewed, so the toast is true (B12). |
| D39 | ⟲ Re-read quotes (grid); Documents ↻ Re-read… | Simplify | One `POST deals/{id}/ai/reads/`. |
| D40 | ✦ Ask Claude to re-check; Overview "double-check" with its own poller | Simplify | `POST deals/{id}/ai/checks/`; results on the strip. |
| D41 | Census opens the drawer on an empty roster; "Scan the census with Claude ▸" | Defer | After review (was Keep): before the PHI gate the drawer cannot read a roster, so it offers nothing. |
| D42 | "Not our template? Read it with Claude ▸" | Keep | Same hand-off. |
| D43 | "I already have carrier quotes": deal made on first attach; lands on Proposal | Simplify | Deal created first, then the Advisor with `?claude=1`, deliberately: 2V reviews plans there. Fixes B21, B22. |
| D44 | Portal Save and Submit start readers, labelled "Client portal" | Simplify | `ai.services.start` with no actor, work lane, after the PHI gate (B6). |
| D45 | Portal polls its scan status | Keep | Read-only; never reaps. |
| D134 | Intake's ✦ button | Keep | `openClaude('intake')`. |

### The reader
| # | Functionality (what the user sees -> how it worked) | Verdict | New implementation |
|---|---|---|---|
| D46 | 13 routing decisions over four paths | Simplify | Registry target → Job → reader → change set → landing. |
| D47 | SBC: design only; beats a quote, flagged; typed beats both; never adds a plan | Keep | `quotes/read_rules.py`, always reviewed; an unmatched SBC becomes an unticked design-only plan (the old agent did this on request). |
| D48 | Tab gates, type checks, document pick, `GET kinds/` | Simplify | Kinds per target in `ai/registry.py`, served by meta (B8). |
| D49 | Units: images, 8+6-row sheet windows, `page_plan`, 28-page windows | Simplify | `ai/ranges.py`: text-layer planner drops member and header-only pages, sizes page ranges by estimated output (≈18 tokens a number) under a quarter of `max_tokens`, 600 pages, 24 MB; sheets as A1 grids. |
| D50 | Overflow ladders and retries | Simplify | Halve on `max_tokens`; a page still over is a failed part. |
| D51 | Eight parallel windows; usage saved every 5 s | Simplify | Four ranges at once; usage saved per call. |
| D52 | Member-data screen; chips name left-out pages | Keep | `documents/screening.py` at upload; rows of people always left out (age-band tables kept); image pages sent only after the PHI gate, marked unscreened; no "read anyway". |
| D53 | Estimate, $2 limit, read anyway, deal budget, overrun stop | Simplify | `ai/budget.py` estimates from pages and numbers, no API call; run cap and budget on real usage; past the cap keep and wait. |
| D54 | Prompt rules: printed only, money pairs, coinsurance, no member data, codes, totals never rates, networks | Keep | One cached prompt per target; rates copied exactly as printed (0.185 stays 0.185). |
| D55 | Per-call note with guidance, carrier hint and lessons | Simplify | Carrier notes (D119) replace lessons; outside the cache. |
| D56 | Lines: named, else most; an empty deal → medical and dental | Simplify | Every printed line; unrequested lines become `add_lines`, ticked when the deal has none, through Intake's intent service. |
| D57 | Merge key, code joins, newer file wins across files | Keep | `quotes/read_merge.py`. |
| D58 | House formats (`normalize.py`) | Keep | `quotes/values.clean` per cell; a bad cell is a finding, never a failed landing. |
| D59 | Six match tiers; reader-made plans only; sold frozen | Simplify | `read_match.py` by role; hand-made plans by number, codes, then unique name; "A / B" matches either half; never a duplicate current plan. |
| D60 | Equal values write nothing; unseen plans flagged | Simplify | "Not in the latest read" scoped by carrier, line and role. |
| D61 | Who wins: `edited ?? extracted` | Simplify | Fills blanks, replaces unconfirmed AI values; typed, imported, client and confirmed values "Left alone", unticked. |
| D62 | New plans Max+1 or count+1 | Simplify | `next_sort_order()`; reads never move plans; new plans append in printed order. |
| D63 | Stale copies, priced versions | Drop | Not rebuilt (§15). |
| D64 | Report sentence; `preview_quotes` | Simplify | The change set is the preview. |
| D65 | Scoped and partial reads | Keep | `params.pages`, `failed_parts`. |
| D66 | Printed rows and order (need 3) | New | Row-major schema; `quotes.PrintedLayout` per file and line keeps order, labels and printed-only cells, never in `Plan.values`; "As printed" beside the file and in the Advisor for one file's plans (Q4, Q5). |
| D67 | Printed tier counts | New | Never a plan's enrollment; with no census and no typed counts, proposed unticked as the line's summary counts, ranked below a census (Q7). |
| D68 | Printed-page map | Drop | PDF pages; the locator corrects. |
| D69 | `quote_checks`, `doc_format` | Drop | Flagged off. |
| D70 | Comparison workbook staged as "template" | Drop | The template import previews. |
| D115 | Which plan a quote replaces | New | From the file's side-by-side columns, unticked when unsure. |
| D116 | One plan under two numbers (05182 / 05183) | New | "A / B" plans take both halves; fresh halves get an unticked "Combine as one plan" (`quotes/split.py`; Q9). |
| D117 | Renewal packets (current and renewal columns) | Keep | The current side creates current plans only on an empty line, else fills blanks or asks to pick; extra incumbent options become alternates. |
| D118 | Stop-loss lasers read as initials | Defer | PHI (§3.8): left out, page named, typed by a person. |

### Landing, undo and retry
| # | Functionality (what the user sees -> how it worked) | Verdict | New implementation |
|---|---|---|---|
| D71 | Direct turns write; others stage; lock, SBC, partial stage | Simplify | `ai/land.py`: automatic only for quotes, admins and direct people, unless locked, lost, partial or the target's `must_review`. |
| D72 | Use this scan: refusals, apply, version, note, chains | Simplify | `quotes/read_apply.py`: one transaction locking the deal and the line's plans; one Activity row with before/after. |
| D73 | ↶ Undo this run; "undo anyway" | Simplify | Checked against the stored "after"; created plans kept if starred, recommended, sold, packaged, linked or typed; census undo by `CensusImport`. |
| D74 | Discard empties `result` | Keep | Census, intake and questionnaire results emptied after apply (B13). |
| D75 | After-effects: stage, census chain, rank, audit | Simplify | `advance` on the locked deal, census chain, rank (D96). |
| D76 | Try again, Check again, step-up to Opus | Simplify | `retry_of`; the step-up runs before landing. |

### Chat and agent turns
| # | Functionality (what the user sees -> how it worked) | Verdict | New implementation |
|---|---|---|---|
| D77 | Agent turns for direct people; in-request chat for others | Simplify | One engine in the worker's chat lane: a question never waits behind a read. |
| D78 | Context blocks on the newest message | Simplify | Providers per app, never stored; census counts only. |
| D79 | History: last 30 messages | Keep | `ai/history.py`. |
| D80 | `set_board`: filters and picks, no data | Keep | Patch in the Advisor's words: name search, budget against the monthly total. |
| D81 | Six chat tools | Simplify | Strict tools: `read_documents` (inside the turn's job), `read_document`, `propose_changes`, `check_values`, `rank_plans`, `update_client_guidance`, `set_board`, `set_table_note`, `set_rows`; validated in code. |
| D82 | First message: 3 files of 100 pages, blocks | Simplify | Same without lessons; table capped at 120k characters. |
| D83 | Effort by shape, 25 or 8 rounds, 32k | Simplify | Up to 8 streamed rounds; files cached across rounds. |
| D84 | get_table, read_document, view_page, bulk_read, apply_read | Simplify | After review (was Drop): unattached files must stay reachable, so `read_document(document_id, pages)` stays; the rest go. |
| D85 | write_plans with page and snippet | Simplify | `propose_changes`; dictated values `origin: typed`; no snippets. |
| D86 | delete_plans | Simplify | Always reviewed; sold or recommended refused. |
| D87 | merge_plans, clear_plans, pair_plans | Drop | Merges not rebuilt (§15); pairing gives way to D116. |
| D88 | verify_table | Keep | `quotes/read_checks.py` with printed counts. |
| D89 | StagedTable replay | Drop | Change sets are reviewable. |
| D90 | Reply lines; "This run $x · Deal $y · model" | Keep | No "Remembered" line. |
| D91 | Opus for admins and direct; scanned PDFs on Opus | Keep | Reads never on Haiku; a refusal retries once on the other model; no server-side fallbacks (a beta). |

### Checks, rank, guidance, budget, lock, jobs
| # | Functionality (what the user sees -> how it worked) | Verdict | New implementation |
|---|---|---|---|
| D92 | edit_plans targets and operations | Simplify | Explicit values per plan, cleaned per cell. |
| D93 | correct_read, flag re-check, audit | Simplify | One check mode: agree, fix, not found (Q6). |
| D94 | Automatic audit chain | Drop | Dead in practice (B11). |
| D95 | Source check; `locate_sources` backfill | Simplify | `documents/locate.py` in every read; `sources.loc`; `low` only for unsure, absent or weak values. |
| D96 | Rank: 5–8 picks, 16 stars a line, uncurated lines after a read | Keep | `marks.rank()` with its own Activity row; no cap (2V stars any number); curated = stars, sales, recommendations, saved selection; needs guidance. |
| D97 | Clear stars | Keep | The Advisor's star service. |
| D98 | Client guidance, 4,000 characters | Keep | `DealAi.guidance`. |
| D99 | Deal $25, run $3, read $2, chat estimate $0.10 | Simplify | `ai/budget.py`, two settings. |
| D100 | AI budget per deal | New | Admins edit it in the drawer head (B16). |
| D101 | Claude Unleashed: sandbox of the exports | Defer | After review (reason rewritten): a second export engine before 2V has exports, and §15 bars sandboxes; Daniel approved it (D-195), so Q8 asks. Stand-in: D120. |
| D102 | Lessons | Defer | A governance subsystem, not on the owner's list; carrier notes cover per-carrier rules. |
| D103 | Saved readers | Defer | As D102. |
| D104 | Table lock | Simplify | `DealAi.locked_by/at`, checked at landing. |
| D105 | Daemon threads, keepalive, lazy reaper, a GET that starts jobs | Simplify | Worker, lanes, heartbeat on stream events, call timeouts, cancel aborts the stream; pure GETs. |
| D106 | Child jobs | Drop | One job reads its files. |
| D107 | `usageTrack` | Drop | Out of scope (§15). |
| D108 | Source tests, prompt freeze, shims, trial tooling | Drop | Forbidden or not product code. |
| D119 | Carrier notes | New | Admin `CarrierNote(carrier, text)` added to the per-call note. |
| D120 | `set_rows` tool | New | Registered by proposals over the builder's per-line row list, if that list is kept. |

### Census, intake and questionnaire readers
| # | Functionality (what the user sees -> how it worked) | Verdict | New implementation |
|---|---|---|---|
| D109 | Mapping assist (15 rows), classifier (25 rows) | Simplify | Headers and value shapes only. |
| D110 | Census PDF roster read | Keep | `CensusImport` with a `job` FK; after the PHI gate. |
| D111 | CensusTurn tools | Defer | Roster writes only through the Census review until the gate. |
| D112 | Intake prefill | Keep | Intake review, `origin: ai`. |
| D113 | Questionnaire read, never a signed response | Keep | Questionnaire app; after the gate. |
| D114 | Formula guard for AI text in XLSX and CSV | Keep | One helper (today `quotes/template.put`) moved left. |

### Documents review station (added after review)
| # | Functionality (what the user sees -> how it worked) | Verdict | New implementation |
|---|---|---|---|
| D121 | Scanned data beside the file; List or Grid per browser; collapse; back to the review queue | Keep | `deal/documents/station/` over each app's `sources?document=`. |
| D122 | List worst first: not in the file, cannot check, warnings, unchecked, found | Keep | Sorted and filtered on `loc` and `low`. |
| D123 | Grid with frozen panes; Excel-like picks; potential-errors filter | Keep | The Advisor's grid, plus "As printed" (D66). |
| D124 | Keys A, I, C, U, F always shown; never move the view; ↶ Undo | Keep | `useReviewKeys.js`; marks through each app's review service. |
| D125 | Review mode: a click or arrow finds the value in the file; E edits | Keep | Locator page and cell. |
| D126 | Bulk bar: approve, ignore (on the record), flag; a key over 25 values asks | Keep | Shared with Advisor, Intake, Census. |
| D127 | Find bar: marks, "3 of 20", Only matches | Keep | `findText.js`. |
| D128 | Pop-out file window with relayed keys | Keep | — |
| D129 | One file or 📚 All proposal files; F opens a value's own file | Keep | — |
| D130 | Intake and questionnaire answers; census people | Simplify | Census as counts per column only (§8.13). |
| D131 | ✎ Edit pass filed as one version | Simplify | Each fix is a typed write. |
| D132 | History rail; walkthrough button | Drop | Versions and walkthroughs; Activity covers it. |
| D133 | Viewer: PDF highlight, formatted sheets, images | Keep | 2V's Release 4 viewer; until then the PDF opens at the page. |

## D.4 Data flow (in and out, by model, field or function)

**In**
- `documents.Document`: bytes, `kind`, `role`, `carrier`, `lines`, `page_count`, `screen`.
- `deals.Deal`, locked at landing: `requested_lines`, `stage`, client name. `ai.DealAi`, `ai.CarrierNote`.
- `quotes.Plan`: line, role, carrier, name, `plan_number`, `renews`, `replaces`, `values`, `sources`, `read`, `sold`, `recommended`, `starred`, `sort_order`, packages; totals only from `quotes/math.py`.
- Census: tier counts and column states as counts; the line summary counts and their origin.
- Intake readiness and intent; questionnaire armed forms; proposals' saved selections, notes and row lists; `accounts.can_direct(user)`.

**Out** (only through the owning app's services)
- `quotes.read_apply`: plans created and updated (`origin: ai` with doc, page, cell, `loc`, `low`; dictated values `origin: typed`), `Plan.read`, links, `PrintedLayout`; one Activity row with before/after.
- `quotes.marks.rank` (`starred`, `star_note`); proposed summary counts; Intake's intent service for `add_lines`; `deals.advance(…, 'quoting')`.
- Intake prefill, `CensusImport` with its `job`, questionnaire answers, proposals' note and rows; `ai` Job, Chat, ChatMessage, DealAi.
- Never in Activity, `Job.error`, steps or a landed result: census values, `sl_lasers`, file names.

## D.5 Bugs and pain points found (with file evidence)

- **B1** Need (3) not built: reads map to registry keys (`claude_readers.build_quote_tool`); labels live only in snippets; `TABLE_AGENT_PROMPT` (76–84) calls the table fixed. → D66.
- **B2** `docscan/client.call_tool` forces the tool with thinking off, so `pricing.READ_MODELS` omits Sonnet 5.5 and Opus 5.5. → new client.
- **B3** No streaming; 16k–32k caps drive all windowing (`ai/README.md`). → D49, D50.
- **B4** `ScanChatView.post` fits 4 rounds into 40 s; a chat cannot see the read it starts. → D77, D81.
- **B5** Jobs on web daemon threads; `JobStatusView`, a GET, reaps and starts jobs. → D105.
- **B6** One job per deal fails: child jobs without keepalive (`table_agent_bulk.py` 80, `census_agent.py` 374, `questionnaire_agent.py` 389), parallel portal readers (`views/shared._autostart_reader`), rank and checks jump the queue. → D105, D106, D44.
- **B7** Two column-order rules (`quote_reconcile.py` 843, `claude_writes.py` 83) collide after a delete. → D62.
- **B8** `renewal` missing from `SCAN_KIND_DOC_TYPES['quote']` but in `TARGET_DOC_TYPES['proposal']`; `stop_loss_quote`, `tpa_proposal` pass one gate and fail `WorkTurn.gate_documents`. → D48.
- **B9** `StagedScanReview.jsx` 576 passes no `onOpenSource`. → D28.
- **B10** Routed reads drop the Reading pick (`scan_chat.py` 1340–1345); only `extraction._run_quote` (741) moves the stage; `apply_staged_work` skips rank, census chain and audit. → D9, D75.
- **B11** `_maybe_chain_audit` skips `work` jobs; `AUTO_AUDIT_MAX_PAGES` 60; applied staged reads never audited. → D94.
- **B12** `claude_writes.write_plans` writes direct SBC turns with no SBC rule while the toast says review. → D47, D38.
- **B13** People stay in `job.result` (`census_agent.py` 393; `claude_readers.py` 3477–3480); scan context stored per turn (`scan_chat.py` 2174–2179). → D74, D78.
- **B14** Unscreened census PDFs, quote sheets, images and scanned PDFs; the mapper sends 15 raw rows, `classify_shape` 25; Census context sends names and birth dates; `job.error` carries file names. → D52, D78, D109.
- **B15** The screen dropped rate pages (D-218), told only by a log line. → D52.
- **B16** `ai_budget_usd` has no screen, yet the refusal says to raise it. → D100.
- **B17** Sonnet 5.5 cache reads priced at $0.20 (`pricing.py` 29; list $0.10); Haiku's tier above 100k missing; `BENEFITS_ADVISOR_MODEL` never set; effort sent via `extra_body`. → `ai/pricing.py`.
- **B18** `spend.deal_spend` and `chat_state` loop over every job and message; `_screen_entry` runs pypdf on first sight. → D8, D52.
- **B19** Six pollers (ScanChat 900 ms, `useDealJobStore` 1.5 s, rank, grid, DataConfidence, DocumentsTab). → `useAiState`.
- **B20** No Stop for agent jobs (`CaseWorkspace.jsx` 1145; `STRIP_DOING` lacks "work"). → D22.
- **B21** An empty deal's agent sees medical and dental only (`table_agent._lines_in_play`). → D56.
- **B22** Deals stay at intake after agent reads; the no-key stub writes invented plans. → D75, D26.
- **B23** Census progress skips the heartbeat (`extraction.py` 768); `JobCancelView` (`views/ai.py` 1287–1289) and `_save_read_stats` save `params` unlocked; reaping filters by id only. → D105.
- **B24** Step-up, Undo and Try again restore `versions/<n-1>/`. → D73, D76.
- **B25** Source-reading tests: `WorkWithClaudeSourceTests`, `ScanDrawerSourceTests`, `VoiceSourceGuardTests`, `ClaudePagesParityTests`, `DropAcceptParityTests`, `FlagReviewSourceTests`, `ClaudeCorrectionsSourceTests`, `ClaudeSyncSourceTests`, `BoardFilterSourceTests`, `RuleFieldParityTests`, `DropZoneSourceTests`, `MoveToLineSourceTests`, `TargetMirrorTests`, `ReadUiSourceTests`, `PartialReadSourceTests`, `PromptFreezeTests`. → D108.
- **B26** Four quote-read paths, three proposal-card producers, about 40 stray imports in `views/ai.py`, AddQuotes still in `guides/library.js`. → D46, D18.
- **B27** Pages without a text layer go unscreened (`phi_screen.MIN_SCREENABLE_TEXT`; `page_plan.py` header, point 1). → D52.
- **B28** `docscan/jobs.keepalive` beats from a timer thread, so a hung API call is never reaped. → D105.

## D.6 New design

**App and registry.** `ai` sits after `documents` (plan.md §3.3, §10.2) and imports only accounts, deals and documents. It owns jobs, chats, the client, budgets, change sets and landing; it never touches plans, answers or people. File knowledge (screen, page text, sheet grid, locator) lives in `documents`, which the viewer shares. Apps register in `ai/registry.py` from `apps.ready()`: readers `{target, kinds, prompt, schema, build_changes, must_review, apply, undo}`, context providers and tools. `quotes`: `quotes`, `sbc`, rank, `set_board`, checks, table context. `intake`: prefill. `census`: mapping assist, roster proposal. `questionnaire` (right of census): its reader. `proposals`: `set_table_note`, `set_rows`, preview context. The review app (portal) and Attach SBC call `ai.services.start`.

**Models (`ai/models.py`).**
- `DealAi` (1:1; created on the first write; reads return defaults): `guidance`, `locked_by`, `locked_at`, `budget_usd`, `next_chat`.
- `Chat`: `deal`, `number`, `title`, `tab`, `created_by`, `created_at`, `last_used_at`, `last_used_by`.
- `ChatMessage`: `chat`, `role`, `text`, `author`, `job`; no context, no cost.
- `Job`: `deal`, `lane` (work, chat), `kind` (read, turn, check, rank), `target`, `documents`, `params`, `chat`, `status`, `progress`, `steps` (50 short lines, no file text or names), `result`, `land`, `wait_reason`, `resolution`, `activity`, `model`, `usage`, `cost_usd`, `error`, `cancel_requested_at`, `created_by` (null = portal), `actor_label`, times, `heartbeat_at`. Unique (deal, lane) while running.
- `CarrierNote`: `carrier`, `text`, `updated_by`, `updated_at`; Django admin.

**Needed from other sections.** Foundation: Activity before/after in a side table lists never load, with revert; `sources.loc`; `low` as reason text; reload and lock the Deal before `advance`. Documents: `Document.screen {version, left_out_pages, image_pages, lists_members}` at upload (the worker screens first if large uploads prove slow; downloads logged until screened); `screening.py`, `pages.py`, `sheets.py`, `locate.py`; kinds `questionnaire`, `stop_loss_disclosure`, `form_5500`. Quotes: `Plan.read {key, codes, doc, unseen}` (never copied by Copy as alternate), `Plan.star_note`, `PrintedLayout` (deal, document, line, `columns`, `rows [{key|null, label}]`, `cells`), `next_sort_order()`, `read_apply.py`, `split.py`, `marks.rank`. Advisor and Census: line summary counts with sources. Census: `CensusImport.job`. Intake: intent service with `origin: ai`.

**Change set** (`Job.result`), one shape for every target and both cards: `{v, target, documents, summary, items: [{id, op, plan|ref, line, role, renews, replaces, carrier, name, plan_number, values: [{key, new, old, page, cell, loc, low, why}], tick, stale}], layout, kept, left_alone, findings: [{text, hard}], failed_parts, left_out_pages, landed: {plan_ids, areas}}`. Ops: `create_plan`, `set_values`, `set_plan`, `pick_current`, `combine`, `summary_counts`, `add_lines`, `remove_plan`, `confirm`, `table_note`, `rows`. Census and intake jobs hold only a pointer.

**Pure modules.** `ai/budget.py`, `land.py`, `ranges.py`, `history.py`, `pricing.py` (Haiku 5.5 $0.10/$0.50 per million, $0.50/$2.50 above 100k; Sonnet 5.5 $2/$10, cache reads $0.10; Opus 5.5 $4/$20, cache reads $0.20; cache writes 1.25 × input; unlisted models at the top price); `documents/screening.py`, `locate.py`; `quotes/read_merge`, `read_match`, `read_rules`, `read_changes`, `read_checks`, `layout`, `split`, `rank_rules`.

**Services** (`ai/services/`, split under 300 lines): `jobs.py` (start, cancel, retry), `chats.py` (send_message, rename_chat), `landing.py` (apply, discard, undo), `deal_ai.py` (guidance, lock, budget for admins). Each locks its row, logs Activity without file names and returns only what changed.

**Client (`ai/client.py`)**, the only importer of `anthropic`. Messages API only: no beta features, no Files API, no token counting; files base64 per request.
- `extract()`: a streamed structured-output call (`output_config.format`, 128k `max_tokens`, `get_final_message`).
- `converse()`: one streamed round, strict tools, `tool_choice: auto`; inputs validated in code; eager input streaming off.
- Adaptive thinking; effort per kind from settings (chat low; reads and checks high until the trial).
- Prompt, schema and tools byte-identical across deals; a second cache breakpoint after the files only in turns; 5-minute TTL.
- Errors: `AccountError`, `OverLimit`, `Truncated`, `Refused` (one retry on the other of Sonnet 5.5 and Opus 5.5); cost from the model that answered.
- Settings: `ANTHROPIC_API_KEY`, `AI_MODEL`, `AI_READ_LIMIT_USD` (3), `AI_DEAL_BUDGET_USD` (25), `AI_EFFORT_*`.

**Reader (`ai/reading.py`)**, files in upload order, up to four ranges at once: screen → ranges → estimate, stop at the cap → content (PDF range minus left-out pages, with a page map; A1 grid; images) → `extract`, halving on `Truncated` → locate → merge → `build_changes` → `read_checks` → Opus step-up on a hard finding when allowed → `land.py`. Row-major schema: `lines: [{line, columns: [{col, carrier, plan_name, plan_number, codes, side, renews_col, replaces_text}], rows: [{label, key|null, cells: [{col, value, page, cell, unsure}]}], counts: [{col, tier, count}]}]`.

**Turn (`ai/turn.py`).** History, context, at most 3 attached files, the table capped at 120k characters, up to 8 streamed rounds; `read_documents` reads in the same job; one reply.

**Worker** (`manage.py run_worker`, own Compose service): claims the oldest queued job whose deal and lane are free (`select_for_update(skip_locked=True)` plus the constraint); beats on stream events and between calls, never on a timer; each call has a read timeout and a wall-clock cap; cancel aborts the stream and keeps finished ranges; after 10 silent minutes the reaper's UPDATE re-checks `heartbeat_at`. Tests run inline with a fake client (`ai/testing.py`).

**Endpoints** (`/api/`, payloads in `ai/selectors.py`)
| Method | Path | Purpose |
|---|---|---|
| GET, PATCH | `deals/{id}/ai/` | Light state (jobs, waiting change-set ids and counts, news, guidance, lock, spend, permissions), no side effects; PATCH `{guidance?, locked?, budget_usd?}`. |
| GET, PATCH | `deals/{id}/ai/chats/`, `ai/chats/{id}/`, `ai/chats/{id}/messages/?before=` | Chats, rename, messages. |
| POST | `deals/{id}/ai/messages/` | `{chat_id?, text, document_ids?, tab, viewer?, board?, model?, budget_override?}` → `201 {chat_id, message, job, queue_position}`. |
| POST | `deals/{id}/ai/reads/`, `checks/`, `rank/` | Button doors. |
| GET, POST | `ai/jobs/{id}/` (ETag); `cancel/`, `apply/ {select?}`, `discard/`, `undo/ {force?}`, `retry/ {model, mode}` | One job and its change set. |
| POST, GET | `plans/{id}/sbc/`; `deals/{id}/plans/layout/?document=`; `plans/sources/?document=`, `plans/review/` (and the same under `intake/`) | Attach SBC; printed layout; the station's values and marks (§8.13). |

`/api/meta/` gains `ai: {targets, models, ladder}` only when a key is set.

**Frontend.** `src/api/ai.js`: `useAiState`, the only poller (2 s rising to 10 s while queued or running; refetch on focus; on finish it invalidates `landed.areas` and flashes `landed.plan_ids`; change sets fetched once). `src/deal/claude/`: ClaudeButton, ClaudeDrawer, ChatBar, ModelPicker, MessageList, Message, Composer, FileChips, FileRoom, useAttach, RunningCard, OverBudget, ReviewCard, ClaudeStrip, GuidanceBox, LockSwitch, flashPlans, renderers. `src/deal/advisor/claude/`: PlanDiff, ChangeList. `src/deal/documents/station/`: ScannedData, ReviewList, ReviewGrid, useReviewKeys, ReviewBulkBar, FindBar, findText, FileWindow. `src/voice/`: localSpeech, MicButton. All under 300 lines.

**Stylesheets** (the foundation's verbatim port, one home per rule). `claude.css`: `bnf-wwc-*`, `bnf-claude-lock*`, `bnf-chatbar*`, the message rules, `bnf-work-*`, `bnf-overbudget*`, `bnf-lastrun`, `bb-extract-*`, `bnf-scan-stop`, `bnf-scanchat*`, `bnf-scan-drawer*` (with the `:has(.bnf-staged-review)` widening), `bnf-staged-*`, `bnf-pchg-*`, `bnf-claude-strip*`, `bnf-claude-section`, `bnf-thinking-note`, `bnf-src-pin`, `bnf-reread-*`, `hlp-mic*`. `review.css`: `bnf-frl-*`, `bnf-rv-file*`, `bnf-review-bar*`, `bnf-review-btn`, `gs-*`, `sf-*`, `bnf-file-bar`, `bnf-docs-expand`, `bnf-scan-grid`, `bnf-scan-field`. `bnf-compare-table` stays in the shared sheet. Leave out `agt-*`, `lsn-*`, `bnf-ver-*` and `data-guide`; remove the doubled `.btn.bnf-wwc-fab` after the `.btn-primary` fix.

**Tests** (behavioural, fake client, synthetic files): no key, no network; a renewal packet on an empty deal makes current plans and linked renewals in printed order, unmapped rows outside `Plan.values`; the same over hand-typed current plans makes no duplicate, asks to pick, turns extra options into alternates; an unchanged re-read writes nothing; a re-read after a reorder keeps it; typed and confirmed values left alone; "$512.34*" becomes a finding; SBC rules and the unmatched SBC; "5182 / 5183" halves; printed counts never touch `Plan.enrollment`; a quote on a deal with no lines gives a non-empty Proposal; landing by person, lock and lost deal (lost mid-read stays lost); census and intake always reviewed; Undo and its refusals; lanes and the claim race; reaper race, silent-call timeout, cancel keeps ranges; cap and Run anyway; a pure, flat-query state GET; shapes-only mapper, counts-only census, no file names or lasers in logs; age-band table kept, per-employee page left out; locator states, scanned pages never amber; the rank skips curated lines and needs guidance; history and chat numbers; `set_board` writes nothing; mixed-send order; string tool inputs parsed; automatic landings report plan ids.

**Build order.** 0: Activity before/after, `loc` and `low`, document kinds, `Document.screen`, page text, sheet grid, locator; pins open the PDF at the page until the Release 4 viewer. 1: `ai` core (Job, lanes, worker, client, state, strip). 2: quote reader, change set, ReviewCard, `read_apply`, Undo, `PrintedLayout`. 3: drawer, chats, turns. 4: SBC, checks, rank, `set_board`, carrier notes, the station. 5: after the PHI gate, the intake, questionnaire and census readers, the Census door, image pages; the mic last.

## D.7 Open questions for Daniel

1. plan.md §10.1 and §15 say AI only stages and rule out chat, agents and lessons. This plan keeps the chat and lets quote reads by admins and direct people land at once, with Undo. Agree?
2. The Foobalabs BAA (2026-11-06) covers the Messages API but no beta features; tools, inline PDFs and images, effort and caching await Anthropic's written confirmation. Will 2V use only that org's key, with the confirmation before real files are read? Should image pages, unscreenable without OCR, be sent then, or should we add OCR?
3. Should the golden-deal trial set the default model, read effort and caps? Should Opus 5.5 stay limited to admins and direct people?
4. Rows printed on a quote that match no field: Advisor and Documents only, or also the client spreadsheet, PowerPoint and PDF?
5. "Recreate the scanned quote in the viewer": beside the file on Documents, in the Advisor for one file's plans, or both?
6. When Claude's check agrees with a value, may it confirm the value, or only a person?
7. With no census, should Claude propose a quote's printed tier counts as the line's summary counts, unticked?
8. You approved Claude Unleashed (D-195, D-197–D-200). This plan defers it because it is a second export engine and §15 rules out sandboxes. Is a Proposal row list that Claude can set enough for the MVP?
9. One plan under two numbers: you chose "Let Claude pair them too" (D-219); 2V §5.4 offers one plan "5182 / 5183" or two plans bought together. Which should a read produce?
10. Defer lessons and saved readers, with admin carrier notes as the stand-in?
11. Should earlier-year chats wait for the renewals decision?
12. Should SBC reads wait for review even for direct people? Should only admins change a deal's AI budget?
