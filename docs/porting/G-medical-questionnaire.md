# Part G — Medical questionnaire

[← Porting plan](README.md)

**What it is:** The carrier forms a large-group deal needs before it goes to market: Florida Blue's 51+ underwriting questionnaire (the default at 51+ enrolled), Warner Pacific's large-group coverage form (a producer pick) and the SIIA stop-loss disclosure (a producer opt-in). Staff fill and sign a form in the app, or the client does it on their link. Each form downloads as the carrier's own PDF for the RFP, and a paper copy is filed and read by Claude on the staff side. None of the owner's twelve Advisor and Proposal needs is built here. This module reads (6) to set the size band and (7) to fill its plan rows.

## G.1 Files read, in order (one line each)

**Specs, READMEs and assets**
| File (lines) | What it is / what it taught |
|---|---|
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/benefits/questionnaires/README.md (235) | Module contract: the spec is code; export modes; provenance, carry and portal rules; portal reads ran in parallel on purpose |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/benefits/README.md (394) | Module map: questionnaires sit beside market and are read by ai |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/PlanningDocs/Benefits/decisions.md (5,528) | D-007, D-022 #2, D-043, D-141, D-145, D-153 #3 and #7, D-161 #5, D-179, D-187, D-203 to D-206 |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/PlanningDocs/Benefits/GetToMarketRoadmap.md (166) | Open gates: the live underwriting test, which Florida Blue copy to send, and e-signature ("typed names won't fly") |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/benefits/questionnaires/sources/ (7 files, listed only) | FL Blue flat blank, XFA original and template XML; SIIA and Warner AcroForms; Arimo font and licence |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/assistant/platform_notes.py (809; 426–440) | In-app help text for the tab |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/2Vantage/CLAUDE.md (43) | App chain, write rules, 300-line limit, behavioural tests |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/2Vantage/plan.md (3,432) | §1.4 and §15 still exclude in-app questionnaires. Also read: §3.3 chain; §3.7 sources; §3.8 PHI; §3.9 data modules; §5.3.6 rollup; §5.7 band and group facts; §5.8, §6.10, §7.11–§7.12 (links, client values, second factor); §10.1–§10.2 (staged reads, one-job worker); §12.4 (no parity tests); §13; §16 #9 and #13 |

**Models**
| File (lines) | What it is / what it taught |
|---|---|
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/benefits/models/questionnaire.py (148) | Response plus EAV answers in three layers; effective value; derived status |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/benefits/models/case.py (1,878) | Mark and stamp mixins (724–903); doc types (1003–1005); job kind `qform` (1517–1520); per-form history (1654–1820) |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/benefits/models/market.py (706) | Attestation `form_key` (15–75); link forms and picks (399–408); `hide_on_file` (512–518); ReviewBatch (665–690) |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/2Vantage/deals/models.py (94) | Deal, Activity with coalescing, AgencySettings |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/2Vantage/documents/models.py (46); c:/Users/fooba/OneDrive/desktop/Vantage_all/2Vantage/documents/kinds.py (44) | Document source and review state; no link id; no questionnaire kinds; PHI kinds are census and claims |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/2Vantage/quotes/models.py (73); c:/Users/fooba/OneDrive/desktop/Vantage_all/2Vantage/quotes/selectors.py (155); c:/Users/fooba/OneDrive/desktop/Vantage_all/2Vantage/quotes/math.py (176) | Plan roles, typed `enrollment` with `enrollment_on`, tier rates `rate_ee`…`rate_fam`; `ordered_plans`; `enrollment_for`, `monthly_premium` |

**Rules and services**
| File (lines) | What it is / what it taught |
|---|---|
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/benefits/questionnaires/__init__.py (163) | Form registry, sensitive slots, asset paths (flat blank vs XFA original) |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/benefits/questionnaires/base.py (443) | Pure cascade, narrowing, spec payload; FL Blue names inside |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/benefits/questionnaires/fl_blue_51.py (390) | Sections I–V, plans block (max 12) and conditions block (max 60), aliases, legal text |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/benefits/questionnaires/fl_blue_51_data.py (2,012) | Generated categories, legend, effects, conditions, details, SIC pairs |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/benefits/questionnaires/fl_blue_51_layout.py (215) | Hand-derived stamp geometry |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/benefits/questionnaires/wp_lg.py (388) | Warner spec, Yes/No pairs, rate grids, `rfp_carriers` |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/benefits/questionnaires/stop_loss_siia.py (201) | SIIA spec, `no_risks` gate, 10 risk rows, field map |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/benefits/questionnaires/xfa_extract.py (424); c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/benefits/management/commands/extract_questionnaire_spec.py (76) | XFA compiler, its two traps, and the command that prints its output |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/benefits/questionnaires/service.py (701) | Seeding, prefill, rows, carry, layers, write whitelist, signing |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/benefits/questionnaires/check.py (176) | Claimant names, clipping, scan findings |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/benefits/questionnaires/export.py (42) | PDF dispatch and filenames |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/benefits/questionnaires/questionnaire_pdf.py (495) | Unreachable replica plus shared attachment helpers |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/benefits/questionnaires/questionnaire_stamp.py (680) | FL Blue stamping and attachment pages |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/benefits/questionnaires/questionnaire_acroform.py (412) | AcroForm fill and signature overlay |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/benefits/questionnaires/xfa_fill.py (479) | Carrier XFA fill |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/benefits/ — questionnaire_pdf.py, questionnaire_stamp.py, marketing_checklist.py (5 each) | Re-export shims |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/benefits/market/marketing_checklist.py (615) | Tiers, form defaults, `_resolve_form` (`none`), headcount, the "done" rule |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/benefits/market/client_request.py (1,617) | Link forms and narrowing (155–272, 946–1018); `is_historical` (72–91) |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/benefits/market/intake.py (1,055) | Approving client answers (1029–1055) |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/benefits/market/value_review.py (492); c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/benefits/market/value_origin.py (231) | Review marks and origin |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/benefits/review/items.py (1,544) | Queue lists; the rule for an open AI read |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/benefits/review/notes.py (2,552) | Send-back, asks, row re-keying, portal threads |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/benefits/review/board.py (724) | Board entries per form, Next |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/benefits/review/request_page.py (1,569) | Request-page pane, ask validity, counts |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/benefits/review/ — link_form.py (461), new_link.py (371), preview.py (344) | Forms on links; staff preview of the portal |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/benefits/renewal.py (947) | Carry from the prior year (570–632) |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/benefits/market/rfp.py (608); c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/benefits/market/rfp_carriers.py (357) | `questionnaire_takes`, `stop_loss_quoted` (funding gate), `stop_loss_takes` |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/benefits/market/census_lens.py (437) | Resolving form keys re-validates the roster (96–98) |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/benefits/pipeline/rfp_bundle.py (243); c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/benefits/pipeline/rfp_email.py (426) | Packet; per-carrier attachments; `sent_with` |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/benefits/pipeline/export_check.py (449) | `questionnaire_problems`; nothing blocks a download |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/benefits/pipeline/workbooks.py (2,056) | Stop-loss Binding Notes (1078–1111) |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/benefits/radar/reminders.py (1,640); c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/benefits/tasks/steps.py (677) | Renewal reminder; task wording |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/benefits/ask_surfaces.py (63); c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/reviewrequest/registry.py (300) | Request surface and its link-security setting |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/backend/settings.py (489) | Throttles, model settings, verification flag |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/benefits/versions.py (2,589); c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/benefits/views/versions.py (552); c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/benefits/history.py (384) | Per-form history |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/usage/features.py (136) | Usage events |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/formbuilder/definition.py (735); c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/benibridge/forms_service.py (1,343) | Copies of the engine in other products |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/benefits/management/commands/ — seed_gtm.py (318), seed_benefits.py (1,134), target_trial.py (214) | Demo seeds and trials that write forms |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/2Vantage/deals/values.py (47); c:/Users/fooba/OneDrive/desktop/Vantage_all/2Vantage/deals/activity.py (47) | Clearing removes value and source; Activity coalescing merges a burst |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/2Vantage/quotes/values.py (91); c:/Users/fooba/OneDrive/desktop/Vantage_all/2Vantage/quotes/marks.py (162); c:/Users/fooba/OneDrive/desktop/Vantage_all/2Vantage/quotes/services.py (224) | Cleaning, locked writes, Activity pattern |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/2Vantage/backend/meta.py (28); c:/Users/fooba/OneDrive/desktop/Vantage_all/2Vantage/requirements.txt (23) | Meta endpoint; no PDF libraries yet |

**Views and payloads**
| File (lines) | What it is / what it taught |
|---|---|
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/benefits/serializers/market.py (980) | Form seams, options, progress, payload; the spec is about 68 KB (898) |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/benefits/serializers/case.py (261) | Overview keys |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/benefits/serializers/pipeline.py (1,958) | RFP cards, default ticks, deliberate-off reasons, paper copies |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/benefits/serializers/overview.py (1,703) | Re-sign tracking, link asks, activity labels |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/benefits/serializers/client_overview.py (540) | Per-year chips paying census reads per year (220–234) |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/benefits/views/market.py (2,148) | Six questionnaire views, producer edits on the edited layer, form pick, blank, stale ack |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/benefits/views/portal.py (2,609) | Portal payload, writes, uploads, scans, signature holds (1744–1766) |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/benefits/views/review.py (628) | "Enter it" and clear |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/benefits/views/cases.py (1,256) | Carry flag, "File as", review marks and revert |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/benefits/views/ai.py (1,316); c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/benefits/views/pipeline.py (2,581) | Job poll; stop-loss workbook |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/benefits/urls.py (362); c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/docscan/kinds.py (195) | Routes; the questionnaire kind accepts scans only |

**AI**
| File (lines) | What it is / what it taught |
|---|---|
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/benefits/ai/claude_readers.py (4,127) | Questionnaire reader (3745–4127); it writes the base layer, over unconfirmed prefill |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/benefits/ai/questionnaire_agent.py (612) | Work with Claude turn and its seven tools |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/benefits/ai/scan_chat.py (2,342) | Armed forms; starting a read |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/benefits/ai/ — pages.py (169), page_context.py (667), extraction.py (846), agent_turn.py (1,423) | Page map, chat context, job dispatch, target registration |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/benefits/ai/ — synthetic_docs.py (355), target_keys.py (160) | Reader evaluation tooling |

**Frontend**
| File (lines) | What it is / what it taught |
|---|---|
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/frontend/src/components/benefits/market/QuestionnaireTab.jsx (1,140) | Tab, views, download menu, signatures |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/frontend/src/components/benefits/market/QuestionnaireForm.jsx (285) | Paper form shared by staff and portal |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/frontend/src/components/benefits/market/QuestionnaireReview.jsx (831) | Queue, FormCheck, form pane |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/frontend/src/components/benefits/market/ — questionnaireCascade.js (228), questionnaireFlow.js (80) | Browser copy of the engine; slot order; `withoutSaved` |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/frontend/src/components/benefits/market/ — IntakeField.jsx (109), CarryNotice.jsx (43) | Typed inputs; renewal notice |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/frontend/src/components/benefits/market/ — IntakeTab.jsx (1,638), useMarketingChecklist.js (82), MarketingChecklist.jsx (577), CoverageIntentPanel.jsx (1,112) | "＋ Ask all"; two pickers; short labels in a narrow column (645–697) |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/frontend/src/components/benefits/shared/overview/GetToMarketCard.jsx (832) | Overview picker and counts |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/frontend/src/components/benefits/market/CarriersTab.jsx (1,366) | RFP questionnaire section |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/frontend/src/components/benefits/market/BenefitsClientPortal.jsx (3,648) | Portal cards, upload, signature holds, to-do list |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/frontend/src/components/benefits/market/ — portalKeys.js (151), censusreview/CensusRequestsView.jsx (602) | Client Tab/Enter; links in the waiting lane |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/frontend/src/components/benefits/shared/CaseWorkspace.jsx (1,346) | Chip union kept on purpose (550–569), tab mount, sidebar ↩ |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/frontend/src/components/benefits/shared/ — useRestingFormKeys.js (34), useWriteQueue.js (60) | Keyboard flow; write queue |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/frontend/src/components/benefits/shared/ — DealReviewTab.jsx (671), RequestPage.jsx (1,749), RequestForm.jsx (449), RequestCards.jsx (455), useLinkBuilder.js (1,485) | Board (owns `bnf-q-chip`, `bnf-q-mark`), Request page, link builder |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/frontend/src/components/benefits/shared/ — SectionReviewBar.jsx (180), SectionViews.jsx (70), reviewScope.js (98), trayRefs.js (36), useReviewTray.js (156), useItemDecisions.js (125), useReviewHotkeys.js (73), ReviewBulkBar.jsx (106), ReviewFilePane.jsx (85), portalPreview.js (62), requestFilters.js (81), requestEntryFlow.js (99), useExportCheck.jsx (151) | Review plumbing scoped to the questionnaire; export-check modal |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/frontend/src/components/benefits/shared/ — ScanChat.jsx (2,068), claudePages.js (112), useDealJobStore.js (239); c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/frontend/src/components/benefits/close/WorkWithClaude.jsx (262) | Drawer form picker; job polling |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/frontend/src/components/benefits/shared/ — DocumentsTab.jsx (3,073), NewCase.jsx (346), overview/RenewalCarryBanner.jsx (97) | "File as"; renewal carry choices |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/frontend/src/components/benefits/radar/ — ClientWorkspace.jsx (493), client/ArtifactChips.jsx (90) | Client-page chips |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/frontend/src/components/reviewrequest/ — ReviewQueue.jsx (474), ReviewFormContext.jsx (102), NoteThread.jsx (240) | Queue, context pane, threads |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/frontend/src/services/api/ — benefitsMarket.js (455), benefitsReview.js (217), benefitsShared.js (423) | API calls, including form-keyed history |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/frontend/src/guides/ — clientQuestionnaire.js (176), reviewQuestionnaire.js (206), stopLossDisclosure.js (270) | "Show me how ▸" tours |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/2Vantage/frontend/package.json; c:/Users/fooba/OneDrive/desktop/Vantage_all/2Vantage/frontend/src/ | React Query 5; no questionnaire folder yet |

**Styles**
| File (lines) | What it is / what it taught |
|---|---|
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/frontend/src/styles/benefits-questionnaire.css (404) | Every `bnf-q-*` class for the tab and the portal |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/frontend/src/styles/benefits.css (6,275) | Review and check classes (2248, 6143–6162); the board's `bnf-q-chip`/`bnf-q-mark` (6226–6248) |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/frontend/src/styles/reviewrequest.css (1,667) | Portal question cards and marks |
| c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/frontend/src/App.css (4,357) | Tokens; every token used here is defined |

**Tests:** c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/benefits/tests_pkg/ — questionnaire_tests.py (4,717; 30 classes), questionnaire_review_tests.py (714), and the questionnaire parts of ai_tests, wwc_targets_tests, case_tests, versions_tests, portal_tests, pipeline_tests, market_tests and the review_*_tests files. Also c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage/devtools/checks/benefits_checks.py (763).

## G.2 Old data model, in brief

- **QuestionnaireResponse.** One row per (case, form_key). `form_version` (never checked again), typed officer and agent names with their times, `esign_provider` and `esign_envelope_id` (unused), `submitted_at` (never written). `signed` and `locked` both mean the officer has signed.
- **QuestionnaireAnswer (EAV).** One row per slot: (response, block, row_index, field_key); a scalar has block `''` and row 0.
  - Three layers: `value` (prefill, carry or AI read), `client_value`, `edited_value` (a producer edit or an approval). Effective value: edited, else client, else value. A client answer takes effect at once, and a changed one takes an approval off.
  - Each row also holds the source file, page and doubt; confirmation and review-mark columns; layer stamps (origin, link, editor, kind `hand`, `approve` or `relay`).
  - Status is derived: missing, client, scan, prefill or high.
- **MarketingAttestation.form_key**, one row per checklist item: `''` is the band default, a key is that form, `none` is "upload only" on medical but resolves to "not needed" on stop-loss. Also `requirement`, `checked`, `note`.
- **BenefitsClientLink**: `requested_questionnaires` (ordered list) and `questionnaire_picks` (narrowing).
- **Elsewhere:** CaseDocument doc types `questionnaire` and `stop_loss` (with their link); ExtractionJob kind `qform`; ReviewNotes keyed by form, block, row and field; Version and EditSession keyed by form.
- **Spec.** One Python dict per form with form, section, block and field keys. On the wire a slot is one flat key of block, row and field.

## G.3 Functionality inventory and verdicts

### A. Which forms a deal uses
| # | Functionality (what the user sees -> how it worked) | Verdict | New implementation |
|---|---|---|---|
| G1 | Three forms, one engine: FL Blue 51+ the medical band default, Warner a medical pick, SIIA a stop-loss opt-in -> `FORMS` registry | Keep | `forms/` registry of specs. The catalogue (keys, kinds, long and short labels, band defaults) is a constant in intake, served by `/api/meta/`; a start-up check keeps the two in step (challenge 18c) |
| G2 | The medical picker on the checklist row, the coverage panel's medical line and the Overview card -> PATCH `marketing-checklist`, which kind-checks and seeds | Simplify | One `FormPicker` (intake's frontend folder) in all three places. It writes `PATCH …/questionnaires/choice/`, which checks the signature, then calls intake's `set_form_choice`. Nothing is seeded |
| G3 | Options "Auto by group size — <label>", each medical form, "No fillable form — upload only"; stop-loss "Not needed for this group" / "Needed — SIIA". Wording differs by place | Simplify | One option list per kind from `/api/meta/`, each with a long label (checklist, Overview) and a short one for the coverage panel's narrow column ("Auto by group size", "No fillable form", "Not needed", "Upload only"), so every place looks as before (challenge 22) |
| G4 | The coverage panel's stop-loss "Upload only" saves `none`, which reads as "not needed" (N12) | Simplify | Fix: explicit stored values. Medical: `auto`, a form key or `upload`. Stop-loss: `''` (not needed), a form key or `upload` (needed, upload only; arms a required upload ask) (challenge 22) |
| G5 | Size band. Headcount: intake enrolled, then census employees (waivers counted), then eligible or total. Tiers ≤10 / 11–50 / 51–99 / 100+; FL Blue at 51+, smaller bands upload only | Keep | Fix: one `enrolled_headcount(deal) -> {count, source}` in `quotes/facts.py`: the census medical rollup (EE+ES+EC+FAM) when it has employees, else typed tier counts summed over current medical plans with `enrollment_on` (never alternates, D-179), else intake `enrolled_count`. One provider feeds intake; rfp imports it. Behaviour change: census first, waivers out, no eligible/total fallback (challenge 7) |
| G6 | The medical item applies when medical is requested or no lines are set; a waiver drops it, even from links already sent | Keep | Pure `choice.forms_for()`: waiver, then choice, then band |
| G7 | The tab shows when a form resolves. Chips are the union of resolved forms and every form held, so a signed form keeps a way in; forms seeded by a GET leave orphan chips | Keep | Chips = armed forms plus started ones (a stored answer or a signature). Opening never starts a form, so no orphans (Changed from Simplify: challenge 1, armed-only chips would strand a signed form) |
| G8 | The medical form and the disclosure on one deal, each with its own review, signatures, reads and exports | Keep | One `Questionnaire` row per (deal, form) |
| G9 | "Signed — the form can no longer be swapped", enforced in the UI only; the band could still swap it | Keep | Fix: the choice endpoint refuses (409) a swap away from a signed form; G133 closes the band path |
| G10 | Checklist wording by band; "Chosen by you"; "Open questionnaire ▸" / "Open disclosure ▸"; "On file"; attach; "＋ Ask" | Keep | Intake and Overview UIs; links carry `?form=`; a band-frozen choice reads "Chosen by group size" |
| G11 | Done with a document of its type, an attestation or the officer's signature; any filed copy counts (N6) | Keep | This app's one provider to intake returns `{form, source, armed, started, progress, signed, done}`. Fix: a client upload counts once accepted; a "wrong" file, or a copy this app filed before a reopen, never counts |
| G133 | Nothing stopped a group-size change from disarming a started or signed form (N11) | New | The first write freezes the band's form into the checklist choice (source `band`). A later band change shows "Group size now says ≤50 — Keep Florida Blue 51+ · Switch" on the checklist row and the tab. It never swaps silently (challenge 1) |

### B. Rules engine
| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| G12 | Dependent pickers: category -> condition -> detail. Three aliases repair the carrier's form. An empty option list hides the field | Keep | `engine/options.py`. Aliases are declared on the field (P1). Payloads carry an option-list key per row into the cached spec tables, and a save returns them for touched rows only (challenge 20b) |
| G13 | Effects: a category sets surgery, transplant or cancer-count flags; a condition re-decides only the overridden flags; a fresh row shows the counts | Keep | `engine/options.py: effects()`; the block names its driver fields (P1) |
| G14 | `visible_if` with nonempty/eq/ne/gt/gte (`ne` true when blank): Q12 "Other", Q14's %/% or $/$, details after a count above 0 | Keep | `engine/conditions.py: condition_met()` |
| G15 | Block gates: Q13 ≠ No shows plans; Q16 = Yes shows conditions; SIIA's grid while "no risks" ≠ Yes | Keep | `engine/conditions.py: block_visible()` |
| G16 | SIC code and description set or clear each other; a duplicate description resolves to the first row; a batch setting both is kept | Keep | `engine/options.py: paired()` |
| G17 | The SIC select has 1,013 options rebuilt on every render, no search, six carrier "Test Industry" rows | Keep | Fix: the native select stays, keeping its type-ahead and D-205's keys. Options are built once, and test rows are filtered when the tables load. The fix changed because of challenge 5: a type-to-filter box would change the keys |
| G18 | Write whitelist: unknown, auto, non-number and not-offered values dropped; a row past max a 400; a locked form a 400; plain fields before dependent ones; US dates to ISO | Keep | Pure `cleaning.clean_batch()`; dropped values are always returned |
| G19 | Hidden answers kept, never exported (`visible_values`) | Keep | `engine/walk.py` |
| G20 | Progress and the blank list from one walk; the browser had its own copy | Simplify | `engine/walk.py: progress()` on the server only. Every read and save returns filled/total/pct and the ordered blanks; "N% complete" moves when a save returns |
| G21 | `after_blocks` puts FL Blue's comments under the grid | Keep | Same flag |
| G22 | Narrowed form (D-187): picked questions plus their dependencies; no signature, upload or carrier PDF; done when answered | Keep | Pure `engine/narrow.py: narrow(spec, picks)` |
| G23 | Sensitive slots = `ANNUAL_SLOTS` plus `deidentified` fields | Simplify | `sensitive: True` in the spec; one `sensitive_slots()` |
| G24 | Gate questions flagged on the Request page | Keep | `gate_slots()`, with no FL Blue names |
| G25 | Browser copy of the engine and slot order | Drop | A duplicate path (rule 6). Instead the spec marks every field another rule hangs on as a driver. Enter or Tab on a driver flushes its save and waits for the reply, as Intake does (D-161 #5), so a revealed question is next (challenge 5) |
| G136 | One answer per slot on every surface -> edited, else client, else value | Keep | Pure `values.effective()`. Order: a staff-typed or relayed answer; then the client's waiting answer (violet "From the client"); then the stored value (approved, read or frozen prefill); then live prefill, unless the slot is cleared. Display, progress, checks, the PDF and the portal to-do all read it (challenge 2) |

### C. Prefill
| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| G26 | `ensure_questionnaire` seeds lazily from about ten callers, including GETs and PDF builds | Drop | Nothing is seeded. GETs never write deal data; a download writes only its `downloaded` Activity row (challenge 21) |
| G27 | Prefill frozen at the first seed (B4) | Simplify | Live prefill for every slot nobody wrote. It is frozen (origin `prefill`) when someone confirms it or the officer signs. A reopen drops unconfirmed frozen prefill so it goes live again (challenge 6) |
| G28 | `prefill_map`: legal name, split address, state (falls back to `'FL'`), FEIN, ATNE, eligible count, carrier and "replacing = Yes", anniversary, SIC on an exact match, officer, agent, agency | Keep | Pure `prefill(spec, facts)` over `quotes/facts.group_facts(deal)`, the fact set rfp also uses (challenge 8). Fixes: no `'FL'` (B7); carrier from the medical current plans, else the medical coverage row (N1); officer = primary contact, else HR admin, else first; one address parser, intake's `split_address` |
| G29 | Q16, contributions and medical answers never prefilled | Keep | Same |
| G30 | Plans row 1: the first current medical plan's name and the medical effective date | Keep | Extended by G134 |
| G31 | Warner's waiting period, years in business and agent of record stay blank although intake knows them | New | From intake `waiting_period`, `years_in_business` and the BOR on file |
| G32 | "Filled in from the deal" | Keep | Status `prefill` |
| G33 | Clearing a box stores `''` on the top layer, hiding later client answers and reads (N2) | Simplify | Fix: emptying a prefilled box adds the slot to `cleared`, which hides only the live prefill. A client answer still shows, and a read may still fill it. Other slots clear as `deals/values.apply` does (challenge 6) |
| G134 | Only row 1 is prefilled; Warner's rate grids stay blank; SIC needs an exact match | New | One plans row per current medical plan, in `ordered_plans` order. Warner's current and renewal rate grids are copied as-is from the current plans' and renewals' `rate_ee`…`rate_fam`, up to the form's options. SIC matches a leading four-digit code, never a NAICS code. A prefilled row remembers its plan, and its unwritten slots follow that plan (challenge 9) |

### D. Producer tab
| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| G34 | Pills Form · Board · Request · Review, with lane addresses `view=review&lane=&chip=&item=` | Keep | Board, Request and Review are the review app's views, scoped to the questionnaire |
| G35 | Form chips; a switch first lets pending saves land; `?form=` deep link | Keep | Mutations with one serial `scope` per form settle before a switch |
| G36 | Paper layout: navy bands, 3-column grid by width, red stars, italic hints, legend, row cards with a navy "Plan 2" chip and Remove | Keep | Same markup and classes |
| G37 | Table layout: Section / Question / Answer, Remove, "＋ Add …"; a signed form shows "— not answered" | Keep | Same |
| G38 | "Form view" / "Table view" toggle | Keep | Same |
| G39 | Inputs: text, date, number, money, percent, select, yes/no | Keep | One `QuestionInput` |
| G40 | Autosave: 700 ms debounce and a hand-built write queue | Simplify | Text debounced 700 ms; pickers save at once; one serial mutation scope. A returned save clears only the draft keys it carried that still match (`withoutSaved`, D-204 #5), so typing during a save survives (challenge 5) |
| G41 | Enter: next question; Tab: next blank required one. Both wrap; Shift goes back; a filled answer is selected; never a button; off when locked | Keep | `useFormKeys` over the server's slot order and blanks, with G25's driver wait |
| G42 | Header: title, subtitle, "N% complete" (amber, then green), "Saving…" | Keep | Percentage from the server |
| G43 | Rows added and removed with min/max, dense renumbering, notes moved | Simplify | Stable row ids, each with its origin, so a removal moves nothing. Fix: an unknown or negative row is a 404 (B6) |
| G44 | "Signed by X — the form is now read-only." | Keep | Same |
| G45 | Section review bar with counts and "Approve N ready ✓" | Keep | A review app component |
| G46 | Work with Claude pill and strip; a finished read reloads the form | Keep | Registered with Work with Claude; a finished read opens its staged result in the review lane |
| G47 | Violet ↩ in the sidebar while client answers or questions wait | Keep | From the review counts |
| G48 | Past-year mode hides asks but still allows editing and signing | Keep | A computed deal flag from deals (`historical`: complete, lost, or a year past the effective date) hides "＋ Ask" and the tray; review refuses asks with 409 (Changed from Defer: challenge 15, it covers complete and lost deals, not only renewals) |

### E. Signatures
| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| G49 | Card with the officer ("Plan sponsor — authorized company officer" on SIIA) and the "Licensed agent", one typed-name input | Keep | Same |
| G50 | "Sign as agent" warns while answers wait for review; offered after the lock | Keep | Same; an agent signature after the officer's files a fresh copy (G135) |
| G51 | "Sign for the company officer": authorization tick and confirm; blanks give 409 with "Sign anyway"; a lost deal 409 | Keep | Signing freezes what the signer saw: on the tab, the staff form; on the link, the client's own answers. The confirm names client answers still waiting (challenge 2) |
| G52 | The officer's signature locks the form and completes the item | Keep | `locked` computed from `officer_signed_at` |
| G53 | Who signed survives only in a version label; stamped and AcroForm copies have no caption (B9) | Keep | Fix: store signer, authorization and link; Activity names them; PDFs print "Electronically signed (typed name) · date" |
| G54 | A mistaken officer signature is permanent (B8) | New | "Reopen the form" with a reason, kept on the row; Activity records it; the filed signed copy stays in Documents (G135) |
| G55 | A portal signature keeps only name and time (N7) | Keep | Fix: also the link id |
| G135 | What the officer attested lived only in versions | New | The officer's signature files the filled PDF as an immutable Document (kind `questionnaire` or `stop_loss`). Signed downloads, the RFP and "changed since" use that file, so a reopen never loses what was attested (challenge 11) |

### F. Downloads and checks
| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| G56 | The "⬇" menu: "Download PDF", "Carrier PDF (Acrobat)", "Blank carrier PDF", each with a detail line | Keep | Same menu. The Acrobat item is absent until G58 is built, as it already is for forms without that file |
| G57 | FL Blue stamped copy: CMYK repaint, Arimo 9.5 pt shrinking to 6 pt, state's full name, shared Q12 box, inline boxes, cancer-area repaint, "See attachment" with real row numbers, DRAFT | Keep | Pure placement plus drawing. Fix: the first filled row prints when row 1 is blank (B1); the officer box falls back to the signed name (B3) |
| G58 | Carrier XFA variant: datasets rebuilt, Yes/No pairs, two injected scripts, `/Perms` dropped | Defer | Off by default in the packet ("the same questionnaire as the flat copy, for Acrobat only"), and which copy Florida Blue accepts is Q4. Build it, with DRAFT in its filename (B9) and a template check, when Florida Blue asks for its original (Changed from Keep: challenge 12) |
| G59 | SIIA and Warner AcroForm fill: Warner's No box, typed name at `/Sig`, dates, a loud error on missing names, Warner's detail page | Keep | `pdf/acroform.py` |
| G60 | Reportlab replica | Drop | Unreachable for all three forms (P2). Its helpers become `pdf/attachment.py` |
| G61 | Blank download on the tab and in the portal | Keep | Same |
| G62 | Filenames `<slug>-<export_slug>.pdf`; the tab renames the blank | Keep | Fix: the browser keeps the server's filename |
| G63 | Filled PDFs carry medical history but downloads are not logged | New | A `downloaded` Activity row; `questionnaire` and `stop_loss` become PHI kinds |
| G64 | Check codes: empty, incomplete, unsigned, claimant_name, clipped, on_attachment, rows_on_attachment, not_printed, scan findings, AI open, client waiting, client in progress | Keep | Pure `checks.problems()`. Fix: hidden rows computed live (B2); findings from the latest read of each document (N3) |
| G65 | "Before you download: …" with Fix links, "Not now", "Download anyway ⬇"; nothing blocks | Keep | The shared export-check modal |
| G66 | A download with a stale `ack` gets 409 and the fresh report | Keep | The ack is a hash of the problem list |
| G67 | "Check the form ▸" shows the PDF beside the problems | Keep | The shared PDF pane (the Documents viewer, also used by the Proposal's export viewer) |

### G. Review & requests
| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| G68 | Review lane with chips "From the client" / "Read by AI" | Keep | Review app; this app supplies `review_items()` |
| G69 | A client item: ours struck -> theirs, a change chip, link and date, why it is ready (submitted, or idle N days with Nudge) | Keep | Client entries carry their link and time |
| G70 | Approve (A), Send back (X), Correct (E), Keep ours (U), Note (N) | Keep | `approve`, `send_back`, `set_answers`, `reject`. Correct and Keep ours keep the client's entry as `rejected`, with who and when, as the old layer did (challenge 2) |
| G71 | An AI item: "Read as V · p.N", unsure first; Approve, Ignore (I), Needs checking (C), Correct, "＋ Ask", Open in Documents (F) | Keep | Items from the staged read (G99) and from applied, unconfirmed reads; `confirm` and `set_mark` |
| G72 | Client questions: Resolve, Reply, "Copy notice" | Keep | Review notes |
| G73 | "Approve N client answers ✓" with the idle tick; bulk approve, ignore or flag of AI reads | Keep | The same services over many slots |
| G74 | Context panes: the form section old -> new; their copy at the page with the value highlighted | Keep | Review components |
| G75 | Keys R, J/K, arrows and ? | Keep | Review hotkeys |
| G76 | Missing lane: four blank names, "+N more", "＋ Ask them to fill it out online", "✓ In tray", "Asked · name · date", "Open the form ▸" | Keep | Blanks from `progress()` |
| G77 | Waiting lane: links asking for the form, "Not submitted yet", "Going back", the tray, "＋ New link ▸" | Keep | Review app |
| G78 | Request page: each armed, unsigned form by section; "＋ Ask" per question; gates flagged; "Approve N ready" | Keep | Review app over this app's selectors |
| G79 | "Enter it" ("From the client — entered by us") and clear | Keep | Origin `relay`; clear removes only that entry |
| G80 | Link builder: each form online, as a signed copy, or off; narrowing | Keep | Link asks `questionnaires: [{form, mode, picks}]` |
| G81 | A changed client answer takes our approval off | Keep | The new answer waits and shows (G136); the approved value stays stored underneath until reviewed (Changed from Simplify: challenge 2, this keeps the old behaviour) |
| G82 | Review-mark batch revert; notes re-keyed to `REMOVED_ROW` | Drop | Replaced by Activity revert and stable row ids |

### H. Client portal
| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| G83 | One card per requested form, in order; waived forms dropped; an intro line | Keep | Same |
| G84 | "View the official carrier form ▸", "⬇ Download blank PDF", `?blank=1` | Keep | Same |
| G85 | Per-question ask, "This is right" and conversation marks | Keep | Same classes |
| G86 | FL Blue's signature section hidden, including the required officer print-name (B3); SIIA and Warner broker fields editable (B12) | Keep | Fix: a spec flag `broker: True` shows the field as text and refuses client writes; officer fields are shown |
| G87 | Rows can be added but never removed (P8) | Simplify | Fix: the client removes rows its link added that hold no approved answer. A client row keeps the browser's key, so autosave never remounts it (D-206 #7, challenge 16) |
| G88 | Debounced save; only non-number refusals named | Keep | Saves into client entries; a newer answer from any link replaces the waiting one (plan §5.8). Fix: every refusal is named |
| G89 | "This is right" | Keep | A confirm entry that holds the value it confirms (challenge 6) |
| G90 | "Already filled this out on paper? Attach completed form": filed as the form's kind, then a read per form, in parallel | Simplify | The upload only files a document: the form's kind, `link_id`, PDF or image. Staff read it (G101) (Changed from Keep: challenge 3, see G91) |
| G91 | The read polled every second with a progress bar; the refreshed form folded in, the draft kept | Defer | No read on the link. AI never writes to a deal directly (plan §10.1), the one-job worker cannot promise the client a quick read, and real reads wait for the BAA. Q9 asks Daniel (Changed from Keep: challenge 3) |
| G92 | Upload states: "attached — save to send ×", "Received — <name>" with Replace, reading, done, failed, "Lost connection…" | Keep | The first two states, with Replace. Fix: only this link's files, never a "wrong" one (B11). The reading states wait with G91 |
| G93 | Officer signature: typed name and attestation; held while their copy is read; held by blanks, with "Sign anyway" | Keep | Saved with the request, never held in the browser; held only by blanks (challenge 3) |
| G94 | Thank-you card; the form disabled after Submit unless a follow-up is open | Keep | Same |
| G95 | To-do item per form with filled/total; the browser marks unsigned forms done (B5) | Keep | Fix: computed on the server from G136; done only when signed (or a narrowed form is answered) |
| G96 | Medical rows reach any link that carries the form; only sensitive conversations need a verified link | New | A second factor for a link asking for a whole form, a paper copy or any sensitive slot. A narrowed ask of other questions opens without one, as intake-only links do (plan §7.12). Narrowed because of challenge 4 |
| G97 | Staff preview writes nothing; a lost deal returns 410; a `form_stamp` poll reloads the page | Keep | Review app portal |
| G98 | The client's Tab/Enter flow | Keep | The shared `useFormKeys` in portal mode |

### I. AI reader and Work with Claude
| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| G99 | `qform` reader: one forced tool call per chunk; schema from the spec; merge; apply with the gate forced and rows grown, page and doubt kept; fails when nothing is saved; refuses a signed form | Keep | Reader kind `questionnaire`, registered with ai. Its staged result lists each slot old → new with page and doubt, plus new rows. Nothing is written until a person acts in the review lane: Approve applies and confirms; "Apply N to blank questions" applies the rest as "Read by AI · p.N". A read may fill live prefill and unconfirmed reads; anything else is a listed conflict. Refuses a signed form; a read finding nothing fails (challenge 3) |
| G100 | A re-read leaves stale rows and mixes into client rows (B13) | Keep | Fix: it stages updates only to untouched rows from earlier reads of the same document |
| G101 | A read starts from a portal upload, the scan chat or Documents "File as" | Simplify | Two doors: Documents and the drawer. A client's paper copy offers "Read it ▸" in the review lane (Changed from Keep: challenge 3) |
| G102 | The drawer's "Reading [form]" picker when two forms are armed | Keep | Work with Claude drawer |
| G103 | `QuestionnaireTurn` (behind `claude_direct`): get, read, write, add or remove rows, verify | Defer | Not on the owner's list ((1) and (2) are quotes and SBCs). It cannot touch medical or claimant answers, its `read_form` only runs the reader, and prefill fills the company facts. Revisit with the Advisor's agent (Changed from Keep: challenge 14) |
| G104 | `read_form` records a failed read as done (B10) | Defer | With G103; the fix (record the real outcome) carries over |
| G105 | `remember_rule`: lessons scoped to one form | Defer | Follows the Work with Claude decision on lessons |
| G106 | Page context hides medical answers using `ANNUAL_SLOTS` | Keep | Fix: uses `sensitive_slots()` (answered or blank only) |
| G107 | Progress lines: "Pages a–b…", "✓ N answers found so far", "Filled N answers — ready for review" | Keep | The job log |
| G108 | Documents shows a filled form with "open the History rail" | Simplify | "Open on the Questionnaire tab ▸" |
| G109 | A synthetic filled FL Blue form and scoring, for reader trials | Simplify | A dev command outside the suite |

### J. RFP packet and emails
| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| G110 | Cards: the in-app PDF, the XFA copy (off), stop-loss (by funding), paper copies. The DRAFT and a paper copy can both go out (N5) | Simplify | The ticks stay. Each form's default tick comes from `copy_to_send`: the signed copy, else an accepted paper copy, else the DRAFT with a warning. Two ticked copies of one form warn; "wrong" files never go (challenge 10) |
| G111 | "Carrier questionnaires & disclosures": bulk tick, rows per carrier, "Not set up" with "Open Overview ▸", reasons | Keep | RFP UI fed by `rfp_files()` |
| G112 | Emails send each form by `questionnaire_takes`; the disclosure goes only to medical carriers, and only on level-funded, ASO or stop-loss requests | Keep | Pure `takes(spec, carrier)` and `disclosure_needed(lines, funding)` (challenge 10) |
| G113 | `sent_with` version numbers and "changed since" | Simplify | At send, store the signed copy's id, else a hash of the printed values; "changed since" compares them (challenge 6) |

### K. Downstream readers
| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| G114 | Overview card: "Not started", "N/M answered", "Upload only", "Not needed" | Keep | `summary(deal)` |
| G115 | "— signed in portal" and "signed by the client officer" even when staff signed | Keep | Fix: both name who signed and where |
| G116 | Client-page chips "Questionnaire ✓" / "Stop-loss ✓" | Keep | `summaries(deals)`, one batched read per client (challenge 20d) |
| G117 | Stop-loss workbook Binding Notes | Keep | A `summary()` key, if that workbook is rebuilt |
| G118 | Task wording for links with forms; intake's "＋ Ask all" adds form asks | Keep | Agenda and review read the link's asks |
| G119 | The `renewal_refresh` reminder names the forms | Defer | Renewals are open |

### L. Renewal carry
| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| G120 | `carry_answers`: last year's values into empty slots; this year's prefill wins; owned rows skipped; signatures never carry | Defer | Renewals are open. If they come into scope, the rule is already decided: D-022 #2, narrowed by D-141 (no SIIA claimants, no Warner medical answers) (challenge 24) |
| G121 | Renewal checkbox, carry notice, "Send it for confirmation →", re-sign tracking | Defer | Same reason |

### M. Machinery and dead code
| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| G122 | EAV rows, three layers, mark and stamp columns | Drop | Flat JSON `answers`, `sources`, `client`, `cleared` and `rows` |
| G123 | Per-form snapshots, restore, edit sessions, agent undo | Drop | Activity before/after, for non-sensitive slots only. A coalesced row keeps the first before and the last after. Revert skips keys changed since, restores live prefill as "not written", and is never offered on a signed form (challenge 23) |
| G124 | `xfa_extract` generates a 2,012-line module, guarded by drift tests | Keep | Keep the generated data module: it is reviewable and exempt from the 300-line limit. The generator becomes a dev command, tested on a small synthetic template with both traps. No parity test (plan §12.4) (Changed from Simplify: challenge 13, parsing the form's scripts at start-up is slower and hides carrier data from review) |
| G125 | Hand-made stamp geometry labelled "GENERATED" | Keep | A data module with a corrected docstring. A start-up check compares the bundled blank's SHA-256 with the layout's, so a reissued form fails loudly |
| G126 | `POST questionnaire/` (only devtools calls it) | Drop | No caller |
| G127 | Shims; `submitted_at`, `esign_envelope_id`, `esign_provider`; `downloading`; unused imports | Drop | Dead. `form_version` is kept and checked on read |
| G128 | Guides, `data-guide` anchors, usage events, help text | Drop | Walkthrough and analytics machinery |
| G129 | Seed and trial commands; devtools checks; engine copies in formbuilder and benibridge | Drop | Demo code and other products. Golden deals build forms through services |
| G130 | Per-surface link security and `LINK_VERIFICATION_ENABLED` | Simplify | One rule (G96) |
| G131 | Tests that read JSX source | Drop | Not allowed |
| G132 | DocuSign seam | Defer | The vendor is undecided (Q3) |

## G.4 Data flow (in and out, by model, field or function)

**In (built once per request by `selectors/facts.py`):**
- `quotes/facts.group_facts(deal)`: legal name, address parts, situs state, FEIN, SIC, total employees, ATNE, eligible, years in business, waiting period, current carrier (medical current plans, else the medical `CurrentCoverage` row), medical renewal and effective dates, officer contact (`Contact`: primary, else HR admin, else first), agent (`Deal.owner`), agency (`AgencySettings`), BOR on file.
- `quotes/facts.enrolled_headcount(deal)`: `{count, source}`. The census part is one aggregate, never a validation run (challenge 20c).
- **quotes:** current medical plans in `ordered_plans` order (name, `rate_ee`…`rate_fam`) and their renewals.
- **intake:** form choices with their source, waivers, `requested_lines`; the catalogue constant.
- **deals:** `Deal.stage` (lost), `historical`, `effective_date`.
- **documents:** `kind`, `source`, `review_state`, `link_id`.
- **ai:** staged read results.
- **review:** calls this app's services with the link id and whether the second factor passed.

**Out:**
- **This app's rows:** `Questionnaire.answers`, `sources`, `rows`, `client`, `cleared`, the signature columns and `signed_document`.
- **Intake:** one provider, per item `{form, source, armed, started, progress, signed, done}`.
- **review:** `review_items()`, `portal_form()`, `spec_payload()`, `sensitive_slots()`, `gate_slots()`; services `approve`, `reject`, `send_back`, `confirm`, `set_mark`, `set_answers(origin='relay')`, `clear_entry`, `save_from_link`, `sign_from_link`, `apply_read`.
- **rfp:** `rfp_files()`, `copy_to_send()`, `takes()`, `disclosure_needed()`, `pdf.build()` and the printed-values hash.
- **overview, Agenda, client page:** `summary(deal)`, `summaries(deals)`.
- **documents:** the signed copies this app files.
- **Activity (area `questionnaire`):** coalesced "Edited N answers on <form>", rows, signatures (signer and place), reopen, approvals, applied reads, downloads. Summaries never carry values; before/after only for non-sensitive slots.
- **ai and Work with Claude:** reader registration and page context.

## G.5 Bugs and pain points found (with file evidence)

File names refer to the absolute paths in G.1.

- **B1** The stamp drops a filled row when row 1 is blank: `_overlay` prints row 1 as it is, while `_rows_with_data` drives the attachment and the check (questionnaire_stamp.py 268–271, 430–436). Fixed in G57.
- **B2** False "hidden rows": the seeded row number counts as data (questionnaire_agent.py 488–497, 594–602; service.py 208–209; check.py 111–131). Fixed in G64; row numbers are not stored.
- **B3** The required officer print-name is hidden on the portal (BenefitsClientPortal.jsx 3017; fl_blue_51.py 264). It is blank when no contact existed at the first seed, and the stamp has no fallback to the signed name (xfa_fill.py 243 has one). Fixed in G86 and G57.
- **B4** Prefill is frozen at the first seed (service.py 181–198), and early touches, GETs and PDF builds seed (views/market.py 591, 1308). Fixed in G27.
- **B5** The portal to-do marks a full but unsigned form done (BenefitsClientPortal.jsx 313; views/portal.py 397–399). Fixed in G95.
- **B6** In row removal, a negative index gives a 500 and an index past the end "succeeds" doing nothing (views/market.py 1481; service.py 240–285). Fixed in G43.
- **B7** State falls back to `'FL'` (service.py 78). Fixed in G28.
- **B8** No way to reopen a signed form. Fixed in G54 and G135.
- **B9** Weak signature evidence: the caption exists only in the replica (questionnaire_pdf.py 356–361); who signed survives only in a version label (views/market.py 1626–1631); the XFA copy has no DRAFT mark. Fixed in G53; the XFA part with G58.
- **B10** A failed agent read is recorded as done (questionnaire_agent.py 401–405). Fixed when G103/G104 are built.
- **B11** The portal shows other people's reads and files, including files marked wrong (views/portal.py 545, 551, 2429). Fixed in G92; reads leave the portal (G91).
- **B12** The client can overwrite broker fields on SIIA and Warner. Fixed in G86.
- **B13** A re-read leaves stale rows and mixes into client rows (claude_readers.py 3992–4019). Fixed in G100.
- **N1** Carrier and dates come from any coverage line when no medical line exists (service.py 66–69, 88–89, 102). Fixed in G28.
- **N2** A producer's blank outranks later client answers and reads (service.py 510–512; models/questionnaire.py 126–131). Fixed in G33.
- **N3** Old scan findings never clear (check.py 108–137). Fixed in G64.
- **N4** Portal polls, saves and blanks shared the anonymous 200/hour limit, and a 429 killed the poll (settings.py 153–160; BenefitsClientPortal.jsx 1524–1559). Gone with the portal read (G91).
- **N5** Carriers can receive two versions of the form, and "wrong" files ride along (serializers/pipeline.py 1465–1489, 1520–1533). Fixed in G110.
- **N6** Any filed copy, even an unreviewed or wrong client upload, turns the item green (marketing_checklist.py 496, 504). Fixed in G11.
- **N7** A portal signature keeps no link (service.py 686–701). Fixed in G55.
- **N8** A checklist item forced to "required" can never read done, even after signing (marketing_checklist.py 507–508). For the intake section.
- **N9** One headcount had two rules: the checklist counts intake enrolled first (marketing_checklist.py 228–252), plan.md §5.7 the census first. Resolved in G5.
- **N10** A GET wrote: `ensure_questionnaire` seeded answers from GETs and PDF builds, and a test pinned the export as "writing". Fixed in G26. A download's own Activity row is required (plan §3.8). Reworded because of challenge 21.
- **N11** (new) A group-size change silently disarms a started or signed form. The item reads only the resolved form's response (marketing_checklist.py 343–350), and only the chip union keeps a way in (CaseWorkspace.jsx 550–569). Fixed in G133, G7 and G9.
- **N12** (new) The coverage panel's stop-loss "Upload only" stores `none`, which resolves to "not needed" (CoverageIntentPanel.jsx 689–693; marketing_checklist.py 164–172). Fixed in G4.
- **P1** FL Blue names hard-coded in the generic engine and renderers (base.py 150, 181–182, 305; questionnaireCascade.js 58, 85–86; QuestionnaireForm.jsx 191).
- **P2** The replica is unreachable (export.py 31–35).
- **P3** Dead fields and code (G127).
- **P4** Stale docs: fl_blue_51.py 19–23; the layout labelled "GENERATED"; the command says the carrier PDF is gitignored; the RFP card calls the download a "replica" (serializers/pipeline.py 1617); wp_lg.py 100–101; page_context.py 404–406.
- **P5** Six carrier test rows in the SIC list.
- **P6** Slow reads: prefill on every seed, answers read three or more times per payload, `_placement` three times per build.
- **P7** No row locks: `bulk_update` writes stale instances (service.py 664).
- **P8** The portal cannot remove rows.
- **P9** Orphan chips; the server allows a swap away from a signed form (views/market.py 1286–1308).
- **P10** Coupling to versions, edit sessions, undo and `sent_with`.
- **P11** File sizes: 1,140, 831 and 3,648 lines.
- **P12** `bnf-q-*` means two things (benefits.css 6226–6248).
- **P13** The stamp geometry has no generator.
- **P14** Open go-live gates: typed names only, and the live underwriting test.
- **P15** (new) Resolving the form keys re-validates the whole roster (census_lens.py 96–98), and the client page pays census and attestation reads per year (client_overview.py 220–234). Fixed in G.4 (facts once, one aggregate) and G116.

## G.6 New design

**App.** A new Django app `questionnaire`, placed `… census → quotes → questionnaire → commission → proposals → rfp → review → overview`. Agenda must sit to its right.
- It owns a model, a tab, two exporters (stamp and AcroForm) and a reader.
- It reads intake, quotes, deals and documents (census through `quotes/facts.py`). rfp, review and overview read it.
- Intake gets one provider from this app (item state). The catalogue is intake's constant. The headcount and the group facts live in `quotes/facts.py`, shared with rfp.

**Model `Questionnaire`**, one row per (deal, form), never deleted.

| Field | Type / notes |
|---|---|
| `deal`, `form`, `form_version` | FK; Char(40); Char(20) set at creation; a mismatch shows a warning |
| `answers` | JSON `{slot: value}`, flat |
| `sources` | JSON `{slot: {origin, by, at, doc, page, link, low, mark, confirmed}}`; origins `typed`, `relay`, `client`, `ai`, `prefill` |
| `rows` | JSON `{block: [{id, origin, by, link, doc, plan, key}]}`. List order is the row number; `plan` ties a prefilled row to its Advisor plan; `key` is the portal's browser key |
| `client` | JSON `{slot: {value or confirm, link, at, status, by, reviewed_at}}`; status `pending`, `approved` or `rejected` |
| `cleared` | JSON list of slots a person emptied on purpose; hides live prefill only |
| `last_row_id` | PositiveInt; row ids are never reused |
| `officer_name`, `officer_signed_at`, `officer_signed_by`, `officer_link`, `officer_authorized` | `officer_link` is a plain integer, because review sits to the right (challenge 18a) |
| `agent_name`, `agent_signed_at`, `agent_signed_by` | Agent signature |
| `signed_document` | FK Document, null: the copy filed at the officer's signature (G135) |
| `signed_copies`, `reopens` | JSON lists: every copy this app filed; `{at, by, reason}` per reopen |
| `created_at`, `updated_at` | Unique (deal, form) |

- A slot is `field` or `block.<row id>.field`. Row numbers are never stored (challenge 16). So `answers` and `sources` reuse `deals/values.apply`.
- Status per slot is computed: missing, blank, prefill, client, to_check or ok.
- Example: `{"answers": {"txtCoName": "Example Co", "plans.1.txtCurrPlanName": "PPO 1500"}, "sources": {"plans.1.txtCurrPlanName": {"origin": "ai", "doc": 41, "page": 2, "low": true}}, "rows": {"plans": [{"id": 1, "origin": "prefill", "plan": 12}]}, "client": {"txtCoName": {"confirm": true, "value": "Example Co", "link": 7, "at": "2026-11-21T09:00:00Z", "status": "pending"}}, "cleared": ["txtPhone"]}`.

**Pure modules (no database).**
- `forms/`: the registry plus data modules `fl_blue_51.py`, `fl_blue_51_data.py` (generated), `fl_blue_51_layout.py`, `wp_lg.py`, `stop_loss_siia.py`. Start-up checks: aliases and categories resolve; the catalogue and registry agree; the bundled blank's SHA-256 matches the layout's.
- `engine/`: `conditions.py`, `options.py`, `walk.py` (slot order, drivers, `visible_values`, progress, blanks), `narrow.py` (`narrow`, `sensitive_slots`, `gate_slots`).
- `values.py` (`effective`, statuses), `cleaning.py`, `prefill.py`, `choice.py` (`forms_for`), `checks.py`, `rfp_rules.py` (`takes`, `disclosure_needed`, `copy_to_send`).
- `pdf/`: `stamp_place.py` (pure), `stamp_draw.py`, `acroform.py`, `attachment.py`, `build.py`. pypdf and reportlab join the requirements in slice Q3.
- `management/commands/extract_questionnaire_spec.py`: dev only.

**`services/` (a package; `services/__init__.py` exports it, so the `<app>.services` rule holds; challenge 19).** Each write runs in a transaction, gets or creates the row (Django's `get_or_create` re-reads after a unique-key conflict), locks it with `select_for_update`, records Activity and returns only what changed (challenge 17).
- `answers.py`: `set_answers` (typed or relay), `clear_entry`, `confirm`, `set_mark`, `revert`.
- `rows.py`: `add_row`, `remove_row`.
- `signing.py`: `sign`, `sign_from_link`, `reopen`, filing the signed copy.
- `client.py`: `save_from_link`, `approve`, `reject`, `send_back`.
- `reads.py`: `apply_read`.
- `picks.py`: `choose_form`, and freezing the band's choice on the first write.
- Rules:
  - the first write creates the row with its starting rows: minimum rows and one per current medical plan, with ids 1..n in the order the payload showed them;
  - clients never write `broker` fields;
  - applying a read never overwrites a typed, relayed, approved-client or confirmed value, or a slot with a waiting client answer;
  - confirming live prefill stores it;
  - signing freezes what the signer saw and files the copy; a lost deal cannot be signed;
  - a reopen needs a reason, clears the signature and `signed_document`, and drops unconfirmed `prefill` values;
  - a swap away from a signed form is refused.

**Selectors.** `selectors/` (`facts.py`, `payload.py`, `portal.py`, `review.py`, `rfp.py`) and `summary.py` (`summary`, `summaries`). Each file stays under 300 lines.

**AI.** `reader.py` registers job kind `questionnaire`: a schema from the spec, one forced tool call per chunk, merge, and staging against `effective()`. Reads are deduped per (deal, form, document) and queue like any job. Real documents are read only after the BAA.

**Endpoints**

| Method | Path | Does |
|---|---|---|
| GET | `meta/questionnaires/{form}/` | The spec: sections, flags, drivers, tables, legend, legal text. Cached per version |
| GET | `deals/{id}/questionnaires/` | The deal's forms: armed, started, choice source, band notice, progress, signed |
| PATCH | `deals/{id}/questionnaires/choice/` | `{item, choice}` -> the item's state. 409 for a swap away from a signed form |
| GET | `…/{form}/` | Effective values, statuses, rows, option keys, progress, blanks, signatures. Never writes |
| PATCH | `…/{form}/answers/` | `{answers, relay?}` -> changed, dropped, touched rows' visibility and option keys, progress, blanks. 409 when locked |
| POST / DELETE | `…/{form}/rows/{block}/`, `…/rows/{block}/{row_id}/` | Add or remove a row. 404 for an unknown row; 400 past min or max |
| POST | `…/{form}/sign/` | `{who, name, authorized, sign_anyway}`. 400 without authorization; 409 for blanks, a lost deal or already signed |
| POST | `…/{form}/reopen/` | `{reason}` |
| GET | `…/{form}/check/` | `{problems, ack}` |
| GET | `…/{form}/pdf/?ack=` | The filled PDF, or the filed copy once signed. 409 for a stale ack. Logs the download |
| GET | `…/{form}/blank/` | The bundled blank |

- Review actions go through review's endpoints, which call these services.
- The portal (review app) adds `questionnaires` to `GET portal/{token}/` (values and state, no spec) and `GET portal/{token}/questionnaires/{form}/spec/?v=` (the narrowed spec, cacheable per version; challenge 20a).
- It also adds `questionnaires: {form: {answers, rows, sign}}` to `POST …/save/`, `kind` and `form` to `POST …/upload/`, and `GET …/questionnaires/{form}/blank/`. There is no read poll.

**Changes in other apps (built by their owners):**
- **documents:** kinds `questionnaire` and `stop_loss`, as PHI kinds accepting PDFs and images only; a plain-integer `link_id` on Document (plan §7.11 already lists uploads with their link; challenge 18b).
- **ai:** Job kind `questionnaire`, staged results, and apply through this app.
- **intake:** the catalogue constant; `set_form_choice(deal, item, choice, source)`; one provider slot; `split_address()`.
- **quotes:** `facts.py` with `group_facts()` and `enrolled_headcount()`, plus one provider into intake.
- **review:** link asks `questionnaires`; the second-factor rule (G96); client entries addressed by (form, slot); the `bnf-q-chip` and `bnf-q-mark` styles (challenge 18d).
- **deals:** Activity area `questionnaire`; before/after merged on coalescing; `historical`.
- **rfp:** default ticks from `copy_to_send`, the two-copy warning, `disclosure_needed`, and the sent hash or document id.
- **assets:** the source files under `assets/questionnaires/`. The XFA original stays for the generator and G58.

**Frontend.**
- `frontend/src/deal/questionnaire/`:
  - screens: `QuestionnaireTab.jsx`, `FormChips.jsx`, `BandNotice.jsx`, `Toolbar.jsx`, `DownloadMenu.jsx`;
  - the form, shared with the portal: `PaperForm.jsx`, `RowBlock.jsx`, `Legend.jsx`, `QuestionInput.jsx`, `SicSelect.jsx`;
  - `TableLayout.jsx`, `SignatureCard.jsx`, `ReopenDialog.jsx`, `FormCheck.jsx`;
  - hooks: `useQuestionnaire.js` (keys `['deal', id, 'questionnaire', form]`, `staleTime 0`, one mutation `scope` per form, `withoutSaved`) and `useFormKeys.js` (driver wait).
- `frontend/src/deal/intake/FormPicker.jsx`, with long and short labels.
- Portal: `frontend/src/pages/PortalPage/questionnaire/` with `QuestionnaireCard.jsx`, `PaperCopy.jsx`, `OfficerSign.jsx`.
- API: `frontend/src/api/questionnaire.js`.
- Board, Request and Review are review components with `scope="questionnaire"`.
- The browser holds no cascade, progress or option logic. Every file stays under 300 lines.

**Stylesheets to copy verbatim.**
- All of `benefits-questionnaire.css`. Once ported, delete classes no component uses (the scan states wait for G91):
  - layout and form: `bnf-q-paper(-plain)`, `-section`, `-secthead`, `-grid`, `-w1/-w2/-w3`, `-field`, `-label`, `-req`, `-hint`, `-intro`, `-legend`, `-block`, `-row`, `-rowhead`, `-rowchip`, `-remove`, `-empty`, `-none`;
  - table: `-table`, `-tsection`, `-tanswer`, `-tblank`, `-tremove`, `-taddrow`;
  - toolbar and menus: `-toolbar`, `-title`, `-subtitle`, `-actions`, `-saving`, `-dlmenu(-list/-item)`, `-formpick`, `-formselect`;
  - signatures: `-locked`, `-sign`, `-signrow`, `-signval`, `-signform`, `-signhold`, `-signanyway`, `-attestation`, `-note`;
  - lanes and upload: `-missing(-text/-count/-actions)`, `-asked`, `-askmode`, `-blank`, `-blankbar`, `-upload(-title)`, `-scan(-done/-failed)`, `-staged-note`;
  - shared: `bb-checkbox-label`.
- From benefits.css 2248 and 6143–6162: `bnf-qb-star`, `bnf-q-review(-actions)`, `bnf-qcheck(-head/-body/-pdf/-list/-ok)`, `bnf-q-signauth`, `bnf-q-origin`.
- From reviewrequest.css: `bnf-qcard(-h/-title/-new/-newtag/-why/-ask/-confirm/-confirmed/-actions/-below)`, `bnf-qmark(-new/-open/-added)`, `bnf-qfoot`.
- The coverage panel's `bnf-cvg-forms` and `bnf-cvg-formpick` go with intake.
- Foundation classes used here: `bb-acord-picker`, `bb-acord-chip`, `bb-acord-viewtoggle`, `bb-badge bb-green bb-amber`, `card`, `btn btn-primary btn-secondary btn-sm`, `bnf-intake-input`, `bnf-override-link`, `bnf-review-note`.

**Tests to write.** All behavioural, with synthetic data and no pinned counts.
- **Engine:** every operator, including `ne` on a blank; aliases; a transplant flag survives naming a transplant; a condition overrides its category's surgery flag; block gates; SIC fill, clear and duplicates; progress counts only visible required slots, and the blanks match; `narrow` keeps dependencies and strips signatures; drivers are marked.
- **Values:** each step of G136; `cleared` hides only prefill; a second link's answer replaces the first.
- **Cleaning:** each drop is reported; a same-batch dependent validates; US dates become ISO; an unchanged value changes nothing (value, source, Activity).
- **Prefill:**
  - each fact, and no `'FL'`;
  - an unparseable address leaves blanks;
  - a dental-only deal gets no carrier;
  - NAICS leaves SIC blank, while "3441 — …" fills it;
  - one row per current plan, and Warner's rates are copied;
  - facts entered later appear;
  - confirming stores, and signing freezes;
  - a reopen drops unconfirmed prefill.
- **Choice:** band, choice, waiver and `upload`; typed counts give a band; a later census never swaps a started form and shows the notice; a swap away from a signed form is refused.
- **Services:**
  - two concurrent writes to different slots both survive;
  - two first writes at once make one row;
  - writes to a locked form are refused;
  - rows keep stable ids and enforce min and max;
  - each side's signature freezes what that side saw;
  - the signed copy is filed and survives a reopen.
- **Portal:**
  - answers become client entries, and "This is right" works;
  - broker fields are refused, and the officer name can be written;
  - a client removes only its own rows;
  - a paper copy is filed with its link, and only this link's files show;
  - waived forms are ignored;
  - the second-factor rule works both ways;
  - the payload holds only allowlisted keys.
- **Review:** approve writes origin `client`; Keep ours keeps a `rejected` entry; a changed answer waits and shows; marks drop when the value changes.
- **Reader (mocked):** the schema comes from the spec; it stages only; conflicts are listed; apply never overwrites protected slots; the gate is forced; a re-read touches only its untouched rows; a signed form is refused; a failure is recorded as failed. The generator is tested on a synthetic template with a stale `<variables>` block and dirty labels.
- **PDFs:**
  - values land inside the blank's boxes;
  - row 2 prints when row 1 is blank;
  - overflow goes to the attachment with real row numbers;
  - hidden values never print;
  - DRAFT until signed, then the caption;
  - AcroForm values read back with pypdf, and a blank missing a field raises;
  - Warner's "No" ticks its box;
  - a changed blank fails the start-up check;
  - downloads are logged.
- **Checks, RFP, Summary:** every problem code; a stale ack gives 409; `takes` per form; the disclosure funding gate; default ticks and the two-copy warning; "changed since"; every summary key is present, and the client page reads in one batch.

**Build slices (challenge 25).**
- **Q1 Rules,** after intake R3.1 and `quotes/facts.py`: forms, data modules, engine, values, cleaning, prefill, choice.
- **Q2 Staff tab:** model, services (answers, rows, signing, picks), payload, Form and Table, keys, signatures, chips, band notice, `FormPicker`, the intake provider.
- **Q3 PDFs, checks and RFP files,** with R3.8: stamp, AcroForm, attachment, the check modal, blank, the filed signed copy, download logging, the rfp rules.
- **Q4 Review lanes,** after R4.3 and R4.5.
- **Q5 Portal,** after R4.4 and the second factor.
- **Q6 Reader,** after R2.2 and the BAA.
- Deferred: G58, G91, G103–G105, G119–G121, G132.

## G.7 Open questions for Daniel

1. plan.md §1.4 and §15 still exclude in-app carrier questionnaires, but this rebuild includes the medical questionnaire. Confirm, so plan.md can be updated. Are all three forms in the first build? Default: yes.
2. Second factor (mechanism: plan §16 #13). Is the narrowed rule right? It is required for a link asking for a whole form, a paper copy or any medical or claimant question; a narrowed ask of other questions opens without one. Until then, staff fill the form or send the blank.
3. Will carriers accept typed names, including staff signing for the officer with written authorization? The roadmap records "typed names won't fly" and paper or Adobe signing in practice. Default: typed names plus the paper-copy route.
4. Which Florida Blue copy does underwriting accept: the stamped flat copy (built) or the Acrobat-only original (G58, deferred)? Default: stamped.
5. Size band: census first, then typed tier counts on current medical plans, then intake enrolled. The old app put intake first and counted waived employees. Confirm. The near-50 rule (§16 #9) stays with Stephanie; the form choice is the override.
6. Who may reopen a signed form? Default: any user, with a reason.
7. Should Florida Blue's Q15 current and renewal premiums prefill from the Advisor, through quotes/math, as monthly or annual figures? Is Warner's "Double" the Advisor's EE+Spouse rate?
8. Should the SIIA disclosure stay opt-in, or default on for level-funded and self-funded groups?
9. A paper copy the client attaches was read at once and shown back to them before signing. The new default only files it for staff to read. Keep the new default, or bring back the read on the link, with read values labelled and confirmed by the client?
