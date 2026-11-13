# Part M — Overview

[← Porting plan](README.md)

**What it is:** The Overview is the deal's home tab. It shows who the client is, whose move it is, what is still needed to go to market, how quoting is going, recent activity and notes, expected revenue, and how far scanned values can be trusted. It holds Mark lost and Archive. It stores and writes nothing itself: every block reads other apps, and every control calls another app's service.

## M.1 Files read, in order (one line each)

Paths start at `c:/Users/fooba/OneDrive/desktop/Vantage_all/`. `Old` = `Vantage/`, `2V` = `2Vantage/`, `FE` = `Old/frontend/src/components/benefits/`. (F) = opened by the finaliser to settle a challenge.

**Specs and READMEs**

| File (lines) | What it is / what it taught |
|---|---|
| Old/benefits/README.md (394) | Module map; `ov`, `jr` and `co` coordinate modules; archive rules. |
| Old/PlanningDocs/Benefits/decisions.md (5,528) | D-097; D-110 archive (.3 sold refusal, .5 money and lineage reads never filter); D-116 #5; D-119 re-check (agreements pre-ticked, a person applies); D-131 speed; D-037 lost portal. |
| Old/PlanningDocs/Benefits/experience-review/experience-review.md (5,142) | X-10, 13, 14, 25, 31, 33, 35, 40, 53, 54, 60, 64, 79, 84 (Waiting banner below the fold, 1884–1898), 85. |
| FE/README.md (421) | Component contract; `--ink-soft`, `--accent` undefined. |
| Old/PlanningDocs/WorkSummaries/workCheckpointMidAugust.md (140) (F) | Calls the status report "fit for the client's leadership"; its PDF says Internal. |
| 2V/CLAUDE.md (42) | App chain, write rules, 300-line rule. |
| 2V/plan.md (3,432): §3.6–3.8, §4.6, §5.1, §5.2, §5.7, §5.9, §5.10, §6.2, §7.3, §7.13, §8.4, §8.5, §9.7, §12.6, §13 R4.1, §15, §16 | A GET never changes a deal; `downloaded` rows; contact roles, funding vocabulary; `contacts_ok`; first-access `get_or_create` (1657–1659); PDF by deck conversion; status reports do-not-build; Q13 second factor; Q15 starts empty. |
| 2V/requirements.txt (23) (F) | No ReportLab. |

**Models**

| File (lines) | What it is / what it taught |
|---|---|
| Old/benefits/models/case.py (1,878) | BenefitsCase, CaseContact, CaseNote, ExtractionJob; AgencyProfile `producer_name`, `producer_npn` (1309–1315); `CoverageLine.notes` Char(300). |
| Old/benefits/registry.py (632), demo_data.py (1,895) | 8 legacy account CaseFields on every deal. |
| Old/benefits/stages.py (118) | Ladder includes enrollment and complete. |
| 2V/deals/models.py (94), stages.py (23), clock.py (25), activity.py (47), values.py (47) | No archive fields, `deal_size`, Note or Contact; Activity has no subject, actor kind or changes; `clock.today()` in the agency zone. |
| 2V/quotes/marks.py (162) (F) | Selling flips `Client.relationship` to existing (52–54). |

**Rules and services**

| File (lines) | What it is / what it taught |
|---|---|
| Old/benefits/archive.py (188) | Only archive writer; sold refusal checks `is_sold` only. |
| Old/benefits/pipeline/sale.py (162) | Lost deletes ClientPlanYear rows; reopen not atomic. |
| Old/benefits/pipeline/plan_math.py (1,440) | `tier_counts_with_source`, the revenue enrollment basis. |
| Old/commissions/services.py (1,694) | `_book_case` freezes float figures. |
| Old/benefits/market/intake.py (1,055) | `current_carrier`, `funding_type` are retired legacy fields. |
| Old/benefits/market/marketing_checklist.py (615), value_origin.py (231), value_review.py (492) | Checklist keys; `origin_of`; the review-values writer. |
| Old/benefits/market/client_request.py (1,617), census_request.py (844), ask_surfaces.py (63), Old/reviewrequest/vocab.py (86) | `is_historical`, `asking_refusal` (72–91): one refusal for lost or past deals; outreach inputs. |
| Old/benefits/market/rfp.py (608), Old/benefits/questionnaires/service.py (701), Old/benefits/pipeline/workbooks.py (2,056, parts) (F) | Carrier forms print `agent_name or producer_name or AgencyProfile.producer_name` (rfp 495–496; service 94, 134–135; workbooks 670); NPN (workbooks 810). |
| Old/benefits/pipeline/exec_summary.py (1,448, parts), presentation_content.py (173) (F) | `renewal_offer_for` also feeds the proposal's renewal blocks (1137–1150, 1338–1369; 168–171). |
| Old/benefits/radar/lineage.py (182), radar/reminders.py (1,640), renewal.py (947), implementation/checklist.py (447) | `case_type_as_of` (63–84); reminders; renewal helpers; card 3. |
| 2V/deals/services.py (143), selectors.py (94) | `mark_lost` requires a reason and re-stamps a lost deal; `delete_client` hard-deletes; one deal per client. |

**Views and payloads**

| File (lines) | What it is / what it taught |
|---|---|
| Old/benefits/serializers/overview.py (1,703) | Every builder: deal type (74–99), renewal offer (102–137), waiting `view` (1007–1011), timeline details (1095–1180), confidence walked in Python (1230–1273). |
| Old/benefits/serializers/journey.py (557) | `next_action_for`; "skipped" (485–490); current dot computed apart (492–509). |
| Old/benefits/serializers/status_report.py (420) | "A principal on a phone"; 7 sections, windows, caps. |
| Old/benefits/serializers/client_overview.py (540), case.py (261) | `is_past_deal` (lost, complete, or 365 days past renewal); `overview_payload`. |
| Old/benefits/serializers/market.py (980), radar.py (814), scan.py (562), primitives.py (360) | Contact and coverage shapes; `_case_type` (524–543); `_prior_cases`. |
| Old/benefits/pipeline/status_report_pdf.py (728), status_report_text.py (223) | ReportLab, importing benefit-guide helpers (39); 60-column text. |
| Old/benefits/views/cases.py (300–1117), pipeline.py (1625–2019), market.py (728–800, 1245–1400), radar.py (236–546), shared.py (297), ai.py (276–306, 1135–1245) | Every endpoint; notes unchecked by author; confirm row by row; audit start race. |
| Old/backend/settings.py (489), Old/docscan/kinds.py | `TIME_ZONE='UTC'`, `BENEFITS_AUTO_AUDIT`; questionnaire kind takes PDFs and images only. |
| 2V/deals/views.py (151), urls.py (15), backend/meta.py (28), documents/kinds.py (44) | Endpoints built; no per-kind accept list. |

**AI**

| File (lines) | What it is / what it taught |
|---|---|
| Old/benefits/ai/scan_audit.py (399) | Claims census cells; stores `value`, `found_value`. |
| Old/benefits/ai/extraction.py (846), flag_check.py (304), page_context.py (667) | Automatic audit chain; flag check reuses `audit_claims`; differences fed to Claude. |

**Frontend**

| File (lines) | What it is / what it taught |
|---|---|
| FE/shared/CaseOverviewTab.jsx (333), JourneyStepper.jsx (61), CaseWorkspace.jsx (1,346, parts) | Block order (150–320): lost and archive banners already above the facts; steps are clickable divs; no lost marker off the Overview. |
| FE/shared/overview/ClientHeader.jsx (238), OverviewRow.jsx (58), WaitingBanner.jsx (52), RenewalCarryBanner.jsx (97) | Fact rows (27–33); primary contact (39); Agent and Producer (184–197). |
| FE/shared/overview/PhaseCards.jsx (131), GetToMarketCard.jsx (832) | Cards 1–3; "Secure link the client opens" (75); Open questionnaire / disclosure (502–508, 605–613). |
| FE/market/MarketingChecklist.jsx (577), IntakeTab.jsx (1245–1304), useMarketingChecklist.js (82) | A second UI over the checklist. |
| FE/shared/overview/ActivityFeed.jsx (204), CaseNotes.jsx (242), CoverageNotesCard.jsx (64), CommissionSummaryCard.jsx (81), CommissionPanel.jsx (173), SplitsPanel.jsx (552) | Feed, notes, side cards; last two unmounted. |
| FE/shared/overview/DataConfidence.jsx (402), ExportReportModal.jsx (333), FE/shared/PdfPagesPreview.jsx (125) | Three POSTs per action (41–56); legend (175–176); re-read; report preview. |
| FE/shared/ArchivedPage.jsx (169), archiveCopy.js (25), trayRefs.js (36), useReviewTray.js (156), valueReview.js (160) | Archived page, tooltips, "In tray", toasts. |
| FE/radar/client/ClientOverviewTab.jsx (471), ClientHeaderCard.jsx (242), ClientNotesTab.jsx (90), ArtifactChips.jsx (90), ClientCommissionSnapshot.jsx (76), clientMath.js (135); FE/radar/ClientWorkspace.jsx (200–290) | The client page. |
| Old/frontend/src/components/commissions/BookTab.jsx (300), Old/frontend/src/components/reviewrequest/LinkStatus.jsx (67) | `SplitChips`; link-state vocabulary. |
| Old/frontend/src/services/api/benefitsShared.js (423), benefitsMarket.js (455), benefitsRadar.js (88), benefitsReview.js (217), usage.js (40) | API calls. |
| Old/frontend/src/utils/format.js (198), download.js (88), usage.js (212); Old/frontend/src/contexts/GuideContext.jsx (338) | `timeAgo` "0h ago"; usage; guides. |
| 2V/frontend/src/api/deals.js (220), pages/DealPage/DealPage.jsx (99), lib/format.js (100) | `invalidateDeal` refetches every deal key but the header (21–28); paged activity (118–122). |
| 2V/frontend/src/pages/DealPage/DealHeader.jsx (122), ActivityDrawer.jsx (71) (F) | Lost banner and Mark lost on every tab today; drawer pages with Show more. |

**Styles**

| File (lines) | What it is / what it taught |
|---|---|
| Old/frontend/src/styles/benefits-overview.css (1,020) | `bnf-ov-*`, `bnf-rep-*`; dead rules; `var(--muted)` undefined (1005). |
| Old/frontend/src/styles/benefits-journey.css (318) | `bnf-journey-*`, `bnf-phase-*`, `bnf-req-*`, `bnf-seg-*`. |
| Old/frontend/src/styles/benefits.css (6,275, parts), App.css (4,357, `bb-*`) | Next, lost, archive, carry banners; snapshot grid; the `.btn-primary` width rule. |
| Old/frontend/src/styles/benefits-radar.css (744), commissions.css (975) | `bnf-cat-*`, `bnf-cal-*`, `bnf-com-*`. |

**Tests**

| File (lines) | What it is / what it taught |
|---|---|
| Old/benefits/tests_pkg/: case_tests, pipeline_tests, archive_tests, radar_tests, big_deal_speed_tests, ai_tests, existing_client_tests, versions_tests, market_tests, tasks_tests (959), portal_tests (3,576), review_hub_tests (592) | NextAction, Journey, OverviewCrmPayload, ConfidenceOrigin, CaseNote, Commission, ValueConfirmation, StatusReport*, MarkCaseLost, Archive*, ClientOverviewApi, OverviewSpeed, ScanAudit, AutoAuditChain, ActivityTimeline, LostPortal, AskStates, StepParity, PrimaryContact, PlanYearRenewalFacts, PageContextPrivacy. |
| 2V/deals/tests/test_deals.py (99), test_platform.py (51) | What 2V covers. |

## M.2 Old data model, in brief

- **Stored and edited by the Overview:**
  - BenefitsCase: `agent_name`, `producer_name`, `deal_size`, `renewal_date`; JSON `commission_rates`, `requested_lines`, `carried`, `client_fold`; stamps `lost_*`, `archived_at/by`, `marketed_at`, `bor_*`.
  - CaseNote: body cut at 8,000 characters; kinds note, call, email, meeting, internal; `pinned`; author SET_NULL; hard delete.
  - CaseContact: eight roles; one `is_primary`, enforced only over HTTP; email unvalidated.
  - Client: owner, service owner, main contact, line-of-business flags, `notes`, archive stamps.
  - Account facts as layered CaseField rows (edited ?? client ?? value); `current_carrier`, `funding_type` legacy.
  - Confirmation and review-mark columns on every CaseField, PlanValue and CensusCell; undo in ValueReviewBatch.
  - `ExtractionJob(kind=audit).result`: per-value differences, values included.
- **Read only:** client links and requests, proposal share links, plans, hub submissions, ask items, attestations, questionnaire responses, DataVersion, CaseDocument, the implementation checklist, commission records and splits, ClientPlanYear (with renewal-letter facts), reminders, client events, CensusImport, AgencyProfile.
- **Derived on read, all inside `GET cases/<id>/`:** deal type, earlier deals, `historical`, renewal offer, reminders, carry and ask states, outreach, `waiting_on`, timeline, confidence, commission rows, `next_action`, journey, the archived block.

## M.3 Functionality inventory and verdicts

"Changed (Cn)" marks a row that review challenge n changed, with the reason.

### Page shell and deal actions

| # | Functionality (what the user sees -> how it worked) | Verdict | New implementation |
|---|---|---|---|
| M1 | Title "Overview", subtitle; Mark as lost…, Archive… (ⓘ), Export status report | Keep | `TitleActions.jsx`. The 2V header's Mark lost and lost banner move here: one way to do it. Export waits for M95 (C14). |
| M2 | Inline lost row "Why did we lose it? (optional)"; Enter or Confirm lost; Cancel | Keep | `POST deals/{id}/lost/` (built). Reason optional, ≤300 (Q3). Server's sentence shown. |
| M3 | Lost rule: refuses lost, sold, complete; stamps from-stage, time, reason; deletes ClientPlanYear rows | Simplify | `deals.services.mark_lost` (built, locks the row). Sold or already lost → 409 (B33). Deletes nothing. |
| M4 | Banner "✕ Lost <date> — <reason \| no reason recorded>" + Reopen deal | Keep | `deals.services.reopen` (built); `bnf-lost-banner`. |
| M5 | Archive… disabled on a sold deal, with the sold tooltip | Drop | Changed (C15), was Keep: v1 archives the client, which D-110.3 already allowed for a sold deal ("archive its client instead"). The refusal only pointed there. |
| M6 | Inline confirm "Archive this deal?" + tip | Keep | `bnf-archive-confirm`. Names the client, since the client and its one deal leave the lists together. |
| M7 | Banner "🗄 Archived <date> by <name> — off every list. Nothing was deleted." + Restore | Keep | Reads `Client.archived_at/by`; Restore posts `{archived: false}`. |
| M8 | Banner "Hidden with its client…" + Open client to restore | Drop | Changed (C15), was Simplify: in v1 a deal is only hidden with its client, so M7 is that banner. |
| M9 | Archive rules: stamps only; a client archive hides its deals | Simplify | Changed (C15): `archive_client`/`restore_client` lock the client row and write Activity. No `Deal.archived_at` until a client can have two deals. No default manager: only list selectors filter; Overview, commission and lineage never do (D-110.5). Portal writes answer 410 via `client_asks_open`. |
| M10 | Each write re-fetched the whole payload; "Updated" or a generic failure | Simplify | Mutations invalidate only their keys (M.6); error toasts show the server's message. |
| M11 | Usage events | Drop | Usage analytics (plan §15). |
| M12 | "Show me how ▸", `data-guide` anchors | Drop | Walkthroughs. |

### Header

| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| M13 | Initials avatar, account name, legal name when it differs | Keep | `OverviewHeader.jsx`; intake `legal_name`. Blank shows the client name, not stored or counted (C9). |
| M14 | Renewal / New business chip; same-name fallback | Simplify | Changed (C1): `deals.rules.deal_type(deal)` over `Deal.opened_as`, copied from the client's type at creation, following edits until the deal sells, then frozen. One rule for this chip, dashboard, work queue, proposal label and commission; Agenda drops its own. The dashboard's New/Existing stays a client fact (B35). |
| M15 | Stage pill | Keep | `bb-stage-pill`, plus a `proposal` class. |
| M16 | "Open N days" | Keep | `created_at` against `clock.today()`. |
| M17 | "Renews <date>", read-only | Keep | `Deal.effective_date`. |
| M18 | "Owner: producer, else agent, else client owner" | Simplify | `Deal.owner`, else `Client.owner`. |
| M19 | P&C client badge | Defer | Another product; its flag lives on the deferred client page. |
| M20 | Renewal offer chip "$X/yr (+Y%)" | Defer | Reason changed (C17): one rule feeds this chip and the proposal's renewal blocks; both return if the Proposal ports them (Q8). |
| M21 | Client box "<client> ↗" | Simplify | Opens the client dialog. |
| M22 | "N earlier deals", reminder badges | Defer | Renewals and reminders. |
| M23 | "Not on the client book yet", Link to client | Drop | Every 2V deal has a client. |
| M24 | Click-to-edit row: click, Enter or blur commits; Escape cancels; unchanged never sent; hint; read-only rows | Keep | `ui/FactRow.jsx`, shared with the commission drawer, plus a select variant for vocabularies (C2). Errors under the row. |
| M25 | Legal name, FEIN, SIC code, Situs state, Eligible employees | Simplify | Intake answers via `PATCH deals/{id}/intake/` with intake's messages; no lock protocol. |
| M26 | Funding, Current carrier (legacy CaseFields) | Simplify | Changed (C2): `quotes.facts.incumbent(deal, 'medical')`: current plan first, then medical `CurrentCoverage`, as RFP, questionnaire and commission read it. Editable (writes `CurrentCoverage` via intake) only when it comes from there or is empty; else read-only, "from the current plan ↗". Funding is a select (§4.6); carrier through the shared alias list. |
| M27 | Agent and Producer free-text rows | Simplify | Changed (C4), was Drop: carrier forms print `agent_name or producer_name or AgencyProfile.producer_name`, and an outside agent may have no login. One "Agent of record" row on `Deal.agent_of_record`; blank shows the default in grey. `deals.rules.agent_name` (row → owner → `AgencySettings.producer_name`) is what RFP and questionnaire print. Producer was only a fallback, so it goes. |
| M28 | In-force commission per line, read-only | Keep | `CurrentCoverage` comp via `deals.comp.comp_label`. |
| M29 | Potential deal size ($ and commas stripped; blank clears) | Keep | `Deal.deal_size` (Decimal) via `PATCH deals/{id}/`. |
| M30 | Primary contact's name, email, phone; first edit creates an hr_admin | Keep | Rule fixed (C3, B32): `deals.contacts.primary`: `is_primary` on a client-side role → hr_admin or benefit_admin → first client-side role; never `prior_broker`. First edit creates an hr_admin when no client-side contact exists. RFP and questionnaire use it. Email validated. |

### Banners and tiles

| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| M31 | Carry banner: texts, revalidation, re-signature, settled look, carried events | Defer | Renewals. |
| M32 | "What's unconfirmed" (does nothing) | Defer | With M31; will open Data confidence filtered to unconfirmed. |
| M33 | Waiting banner: With us / With them or Status; label, detail, "Next step — …", Go ▸, tone | Keep | Changed (C6, C18, C19): reads Agenda's light read; sits directly under the title, above the facts (X-84, Q9); Go ▸ passes `next_step.params` (view, focus, documents). `bnf-ov-waiting*`, `bnf-next-*`. |
| M34 | Hidden on a lost deal | Keep | Agenda returns a lost state. |
| M35 | Intake complete % | Keep | Intake answered over needed. |
| M36 | Plans quoted | Keep | Renewal and alternate plans not removed. |
| M37 | Last contact (newest link or share, `timeAgo`) | Simplify | `overview.rules.last_contact`: newest link sent, proposal issued, call/email/meeting note or logged follow-up; "just now", not "0h ago". |
| M38 | Expected revenue (green) | Keep | `commission.summary(...)['expected_total']`: Decimal, half up, whole dollars. |

### Journey and phase cards

| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| M39 | Stepper on every tab: dots (✓, current, todo, –), tooltips, click to the step's tab, "✓ Complete", compact | Keep | `pages/DealPage/JourneyStepper.jsx` on Agenda's light read; replaces `StageStepper`. Changed (C5, B31): the current dot is the step owning `next_step.key`, so dot and banner agree. Steps are buttons. |
| M40 | Module 1 "skipped" when quotes come first, even on lost deals | Simplify | No "skipped" state; steps stay todo. |
| M41 | Module 3 and Card 3 | Defer | Implementation is out of scope. |
| M42 | Card 1 badge (Blocked, Ready to market, Sent to market), "N of M requirements met · <tier>" | Keep | Intake facts; `bnf-ready-badge`, `bnf-req-rollup`. Tier from `quotes.facts.enrolled_headcount`, the one headcount rule, so Card 1, questionnaire and RFP agree on typed-count deals (C21). |
| M43 | "Started from carrier quotes — intake was skipped" | Simplify | "Quotes came in first — intake, census and the RFP still apply". |
| M44 | Groups open until met, then the user's toggle wins | Keep | `gtm/ReqGroup.jsx`; heads are buttons. |
| M45 | Coverage intent, read-only: Shopping / Not shopped, new line, on the proposal, guaranteed to; Open, Changed, ✓ Confirmed by | Keep | Intake intent rows; "Changed" compares decisions, no hash. |
| M46 | Intake group: missing quote-blocking items, HR admin contact, BOR, client answers with Review ▸, "Intake complete · N lines", Open intake ▸ | Keep | Intake facts plus review's pending counts. |
| M47 | "BOR on file from <year>" | Defer | Renewal-only. |
| M48 | Census group: roster counts, x/y required cells, errors, client values with Review ▸, Open census ▸ | Keep | Census facts plus review's pending counts. |
| M49 | Census ask: "＋ Ask ▸" or "＋ Ask for their census file", then "✓ In tray"; hidden on historical deals | Keep | Review's tray (`censusfile`). Hidden when `deals.rules.client_asks_open` refuses: one rule replacing `historical` (C16). |
| M50 | Questionnaire row: glyph, where signed, form, chooser, "x/y answered · signed", "Client sees" | Keep | Intake checklist row plus the questionnaire provider. |
| M51 | Fillable form select; disabled once signed | Keep | `intake.services.set_form_choice`; control shared with Intake. |
| M52 | ⬆ Attach | Keep | Documents upload; accept list from the kind (B23). |
| M53 | On file checkbox | Keep | Intake checklist attestation. |
| M54 | "＋ Ask" (`qform:` or `doc:`) | Keep | Review tray; gated as M49 and M111 (C16). |
| M55 | Not needed / Still needed ▸ (note ≤300) / Undo | Keep | Intake checklist override. |
| M56 | Stop-loss disclosure: Optional until "Needed — <SIIA form>" | Keep | Intake checklist plus `questionnaire.disclosure_needed`. |
| M57 | Documents carriers need (renewal, invoice, claims): Attach, On file, Ask, override | Keep | Intake checklist rows per line. |
| M58 | Custom asks: Done, Remove | Keep | Intake ask items; Remove archives. |
| M59 | "＋ Add request" (label ≤120, note ≤300, Enter) | Keep | Adds the item only; the client is reached through "＋ Ask" and the tray (X-79, Q6). |
| M60 | Confirmations (COBRA, salary/occupation) | Keep | Intake attestation and override. |
| M61 | Footer: Send to market ▸, Open intake ▸, Open census ▸ | Keep | Send to market opens Intake at `?focus=marketed`. |
| M62 | Card 2: Quotes in ("N plans · X to review · Y missing" or "Waiting on carrier responses"), Shortlist, Proposal shared, Sold | Keep | States from the journey read; details from quotes counts and the latest issue. Copy (C22): "Secure link the client opens" becomes "Proposal issued <date>". |
| M63 | "Client selected" step and event | Defer | Needs share links with a client pick (plan §15). |
| M64 | Hand-off row | Defer | With M41. |
| M65 | Open comparison ▸ | Keep | Opens the Advisor. |
| M66 | Open hub ▸ | Drop | Data Hub stub. |
| M67 | Enrollment check: one warning naming intake, census and Advisor counts | New | `quotes.facts.enrollment_check`, shared with the RFP; one line in the Census group. |
| M108 | "Open questionnaire ▸" once a form is chosen | Keep | Added (C22; GetToMarketCard.jsx 502–508). |
| M109 | "Open disclosure ▸" on the stop-loss row | Keep | Added (C22; 605–613); opens the SIIA form. |
| M110 | Census group on a typed-count deal: "The Advisor is priced from typed counts — add the census when it arrives" | New | Added (C21, need 6): shown when the headcount comes from typed counts and the census is empty. |
| M111 | Asks for a census or documents disabled, with the reason, until the portal's second factor exists | New | Added (C16): plan §3.8 and §16 Q13. Review supplies the flag. |

### Activity and outreach

| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| M68 | Outreach strip: Last contact, Last response, Open asks | Keep | Review facts plus M37. |
| M69 | "Who we've asked": counts; per link person and role, asks, shared chip, LinkStatus, days left, "N from them"; 4 rows, Show all; cap 50; "Never asked: …" | Keep | `review.selectors.outreach(deal)`; `LinkStatus` from `deal/review/`. |
| M70 | Timeline: newest first, 8 shown, Show all N / Show less; tone dot, icon, label, detail, actor | Simplify | Changed (C10): `deals.selectors.feed(deal)`, Activity minus `downloaded` rows, one predicate for rows and count; Show all pages with Show more (25). Pure `activityLook(area, action, byClient)` keeps the violet client tone. |
| M71 | Events: opened; document received, read, staged, failed; link sent, opened, returned; request closed; asked; checklist confirmed; BOR and questionnaire signed; sent to market; proposal shared; sold; note logged; edit batches | Simplify | Each service writes its row; new rows for lost, reopened, archived, restored, contacts, facts, note edits and deletes, link revoke and extend. Changed (C10): stored summaries name no people; the detail line (file name, recipient and role, signer, the note's first line) is resolved at read time from the row's subject, batched per page; a deleted subject shows none. |
| M72 | "Output generated — <hub>" | Drop | Data Hub. |

### Notes and side cards

| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| M73 | Composer: textarea, kind chips Note/Call/Email/Meeting/Internal, Add note | Keep | `deals.Note`, `POST deals/{id}/notes/`; five kinds. |
| M74 | List: pinned first in amber, kind badges, date, author; actions on hover | Keep | Actions also on focus (X-14). |
| M75 | Pin / Unpin | Keep | `PATCH notes/{id}/`. |
| M76 | Edit: blur saves, Escape cancels | Keep | Author or admin. |
| M77 | Delete: permanent, no confirmation | Simplify | `deleted_at` plus an Undo toast; author or admin. |
| M78 | Notes from earlier deals | Defer | Renewals. |
| M79 | "N unlinked deals share this name…" | Drop | No unlinked deals. |
| M80 | Coverage notes card, Edit on Intake ▸; hidden when empty | Keep | `CurrentCoverage.notes`. |
| M81 | Commission card: expected, received, months short, booked with holes and house share, who gets what, no-producer nudge, Open Commission tab | Keep | `commission.summary(deal, viewer, states)`, ledger figures by tier; card from `deal/commission/`. "Works it" partners show in who gets what; no Overview contacts card (C20). |
| M82 | CommissionPanel and SplitsPanel in `overview/` | Drop | Not on the Overview; moved to commission. |

### Data confidence and the AI re-check

| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| M83 | Cells: Scanned (N corrected by hand), Typed, From the client (N awaiting approval) | Simplify | Changed (C8, C11): `review.selectors.confidence(deal)` over each owner's `source_counts`, SQL aggregates over `jsonb_each(sources)`, bucketed by `documents.review_rules.origin_bucket`. "Corrected" = a typed value keeping its `doc`. |
| M84 | "N carried from last year" | Defer | Renewals. |
| M85 | "N demo data · N on file from before…" | Drop | Demo code. |
| M86 | Confirmed bar and legend ("by a person", "by the re-read") | Keep | `bnf-ov-conf-*`, `bnf-ov-key-*`. "By the re-read" counts approvals a person applied from a re-check (C13). |
| M87 | Per document: quality chip (Clean ≥90%, Mostly ≥70%, Needs review, Not scanned yet), "N values · M confirmed" | Keep | `review_rules.quality_headline`. |
| M88 | Confirm all for one document, census included; no question, no undo | Keep | Changed home (C11): `POST deals/{id}/review/marks/` approve, the endpoint the Documents station also uses. Asks "Confirm N values from this file?"; Undo reverts its one Activity row. |
| M89 | Ignore N warnings, ⚑ Needs checking (three POSTs each) | Simplify | Same endpoint; one transaction across owners. |
| M90 | Ignored list: where, label, value (never census), by, date, file; Undo; Undo all; cap 50 + "and N more" | Keep | Owners' marked rows. Changed (C12): value null for census, questionnaire and `sl_lasers`. |
| M91 | Needs checking list: ✓ Approve, Undo | Keep | Same. |
| M92 | Double-check with AI: disabled while running, with no key or nothing scanned; result line; first 6 differences; Open the documents ▸ | Keep | Changed (C13): starts `ai`'s `recheck` reader on the deal's scanned values, low confidence first, in the work lane; disabled while any read runs; "Review ▸" opens its staged change set. `useAiState`. |
| M93 | Audit job: low confidence first, 60 per document, page windows, forced tool, merged verdicts; a confident agreement confirms | Simplify | Changed (C13): one `recheck` reader, shared with the per-flag re-check (D-119). Agreements arrive pre-ticked, differences as fixes, not-found listed; nothing clears until a person presses Apply. No `audit` kind; never claims census, questionnaire or `sl_lasers`. |
| M94 | Automatic audit after every read | Drop | Changed (C13), was Defer: a paid read started on its own contradicts D-119.3 and duplicates M92. |

### Status report

Changed (C14), all were Keep or Simplify: plan.md §15 lists status reports as do-not-build; they are not on the owner's list; the old PDF needs ReportLab, which §9.7 rules out, and benefit-guide helpers that are not ported (Q1).

| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| M95 | Modal: Text or PDF; 30/90/365/Everything; Phone or Letter; rail; live preview, page count | Defer | If built: text first (window, preview, Copy text). |
| M96 | Copy text, Copy PDF (stitched PNG), Download PDF, Close | Defer | Copy text first; PDFs after the Proposal's PDF engine. |
| M97 | Payload: 7 sections; only activity and notes windowed; pinned notes survive; caps 24 and 8 with counts | Defer | If built: `overview/report/build.py` over the same facts; revenue by tier; agency dates. |
| M98 | "Everything" adds prior-year notes | Defer | Renewals. |
| M99 | PDF: brand band, callout, stat cards, timeline, journey bars, money table, facts, top 3 contacts, "Internal · page N" | Defer | Through the proposal PDF route (deck conversion), never ReportLab. |
| M100 | Text: 60 columns, CAPS headings, aligned pairs | Defer | `report/text.py`, first if built. |

### Client page, archive and shell

| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| M101 | Client page overview | Defer | Renewals; one deal per client. |
| M102 | Deal Overview inside the client page, past-year band | Defer | Same. |
| M103 | Archive client… with confirm and banner | Simplify | Changed (C15): it is M6–M7, one button; `POST clients/{id}/archive/`. Dashboard row buttons (D-110.6) belong to the dashboard. |
| M104 | `DELETE clients/{id}` → 405 "Clients are archived, never deleted." | Keep | Replaces 2V's hard delete (B36, Q7). |
| M105 | Archived page: clients with deal counts, deals hidden by their client, Restore, Try again | Simplify | Changed (C15), was Keep: archived clients with their deal's stage; Restore; Try again. `GET archived/`; `pages/ArchivedPage/`. |
| M106 | Work with Claude on the Overview, with deal context | Keep | Context from the browser, as Agenda does; the drawer sits beside the page (X-53/54). |
| M107 | Review tray dock | Keep | The page leaves room for it (X-84). |
| M112 | "Lost" stage pill in the deal header on every tab | New | Added (C22): Mark lost and its banner live on the Overview only; the header shows the stage. |

## M.4 Data flow (in and out, by model, field or function)

| Block | Reads | Writes (service) |
|---|---|---|
| Identity and chips | `Deal` (`created_at`, `stage`, `effective_date`, `owner`); `deals.rules.deal_type`; `Client` (`name`, `owner`); intake `legal_name` | — |
| Fact rows | Intake `fein`, `sic_code`, `situs_state`, `employee_count`; `quotes.facts.incumbent`; `CurrentCoverage` comp; `Deal.deal_size`, `agent_of_record`; `rules.agent_name`; `contacts.primary` | `intake.services.set_answers`, `set_coverage`; `deals.services.update_deal`, `create_contact`, `update_contact` |
| Lost and archive | `Deal.lost_*`; `Client.archived_*` | `mark_lost`, `reopen`, `archive_client`, `restore_client` |
| Waiting, next step, journey | Agenda's light read | — |
| Tiles | Intake answered/needed; quotes plan counts; `rules.last_contact`; `commission.summary` | — |
| Card 1 | Intake ready, `marketed_at`, checklist and intent rows (headcount from `quotes.facts.enrolled_headcount`); questionnaire provider; census facts; review pending, tray state, second-factor flag; `client_asks_open`; `enrollment_check` | Intake attest, override, form choice, ask items; `documents.services.upload`; review tray ask |
| Card 2 | Journey module 2 states; quotes counts; proposals latest issue | — |
| Outreach and timeline | `review.selectors.outreach`; `deals.selectors.feed` | Every service writes its own row |
| Notes and side cards | `Note`; `CurrentCoverage.notes`; `commission.summary(deal, viewer, states)` | Note add, update, delete; Activity revert |
| Data confidence | `review.selectors.confidence` (owners' `source_counts`, marked rows, last `recheck` job) | `review.services.mark_document`; `ai.services.start('recheck')` |

**Old builders and their new homes:**

| Old builder | New home |
|---|---|
| `commission_payload` | `commission.summary` |
| `deal_client_type`, `_case_type` | `deals.rules.deal_type` |
| `is_past_deal`, `asking_refusal` | `deals.rules.client_asks_open` |
| Agent fallback in rfp, questionnaires, workbooks | `deals.rules.agent_name` |
| `ask_states`, `outreach_payload`, `census_ask_sent` | review |
| `confidence_payload`, value-review writer | `review.selectors.confidence`, `review.services.mark_document` |
| `waiting_on`, `next_action_for`, `journey_payload` | agenda |
| `renewal_offer_for` | With the Proposal's renewal blocks (Q8) |
| `_prior_cases`, client-overview helpers, status report builders | Deferred |

## M.5 Bugs and pain points found (with file evidence)

| # | Bug, with evidence | Fix |
|---|---|---|
| B1 | **PHI in the AI re-read.** Census cells claimed (scan_audit.py 162–170), sent (183–193), stored (357–369), shipped (`ov` 1475), rendered (DataConfidence.jsx 315–329), fed to Claude (page_context.py 646–653); file names logged (271). | No census, questionnaire or `sl_lasers` claims; no PHI in job results or logs. |
| B2 | **Ledger figures shown to everyone** (`ov` 1626–1635); the client page gates them (ClientOverviewTab.jsx 229–236); the report does not. | `commission.summary(viewer)`. |
| B3 | **Float money, half-to-even** (`ov` 1547–1561); booking freezes floats (commissions/services.py 870, 896). | Decimal, half up. |
| B4 | **PEPM uses medical enrollment on every line**; the basis note ignores typed counts (`ov` 1538, 1545, 1560). | Per-line enrollment in commission. |
| B5 | **One premium plan per line**: sold → starred → current → first (`ov` 1484–1498). | Commission's basis rule. |
| B6 | **Carrier and funding diverge** from intake and current plans (ClientHeader.jsx 27–33; `sr` 405–407; intake.py 353–368). | `quotes.facts.incumbent` (M26). |
| B7 | **"What's unconfirmed" does nothing** (RenewalCarryBanner.jsx 83–89). | Deferred with M31. |
| B8 | **Carry shows "approved" after any submitted link** (`ov` 243–244). | Deferred with M31. |
| B9 | **No lost branch in `waiting_on`** (`ov` 892–1004); the report can headline "At market" on a lost deal. | Agenda's lost state. |
| B10 | **Timeline.** Missing job labels ("work read", "Plan ranking read"); a discarded read logged as read (1019–1022, 1105–1108); deleting a document or note erases its event (decisions.md 2573); lost, archive, contact, fact, rate, note-edit and revoke events missing; Show all ignores the total; "employer" copy (X-60). | Service-written rows; M70–M71. |
| B11 | **Dates in UTC** (settings 134; `ov` 39–46; `sr` 68–70, 158; X-40). | `clock.today()`, `clock.local()`. |
| B12 | **Anyone edits or deletes any note**, permanently (views/cases.py 895–932; CaseNotes.jsx 97–104; X-25). | Author or admin; soft delete, Undo. |
| B13 | **Contact email unvalidated** (X-33); every error becomes "Could not save that value" (CaseOverviewTab.jsx 91–94). | Validate; show the server's message. |
| B14 | **Lost deletes plan-year facts** (sale.py 68); reopen re-snapshots in a swallowed try, not atomic (74–93). | Lost deletes nothing. |
| B15 | **Archive** checks `is_sold` only and locks nothing (archive.py 70–75); links stay writable. | Lock the row; portal writes 410 via `client_asks_open`. |
| B16 | **Audit start** loads every value to test emptiness, then races (views/ai.py 292–305); a running automatic audit is invisible; button state lost on navigation; filtering lives in DataConfidence 302–345. | One running job per deal and lane (database constraint); `useAiState`. |
| B17 | **Text.** "1 days", printed only when non-zero (status_report_text.py 71–72; `ov` 969, 991, 1000); raw line keys (`sr` 410); the employer wait routes to Intake, and `since`/`days` disagree (`ov` 969–970). | Agenda routes waits to Review; report fixes when built. |
| B18 | **Last contact ignores logged calls and emails** (`ov` 712). | M37. |
| B19 | **Quote-first deals read "skipped"** (`jr` 485–490), so do never-marketed lost deals; next action stalls at "Import the census" despite typed tiers (`jr` 292–302); a read flips the stage (extraction.py 741); X-10. | Agenda's quote-first rules; M39, M110. |
| B20 | **The automatic audit holds the job slot** (scan_chat.py 1353). | Dropped (M94). |
| B21 | **Confirm all** asks nothing, has no undo, saves row by row with no lock or log (shared.py 269–295; X-85). | M88. |
| B22 | **"＋ Add request" skips the tray** (X-79). | M59. |
| B23 | **Attach offers spreadsheets** the questionnaire and stop-loss kinds refuse (docscan/kinds.py) → 400. | M52. |
| B24 | **Speed.** The header payload computes everything (D-131: 3.0 s, 11 s); confidence walks every filled value in Python (`ov` 1230–1273); every write computes twice (CaseOverviewTab.jsx 85–95; views/cases.py 552; DataConfidence.jsx 26–37); the client page prefetches every plan value (shared.py 209); notes queried twice (`ov` 1678–1680); PATCH skips `updated_at` (views/cases.py 551). | Separate queries, SQL aggregates, fixed query count. |
| B25 | **Ledger errors swallowed** by a bare `except` (`ov` 1636–1637). | No try. |
| B26 | **Dead code.** Keys `people_waiting`, `last_proposal_sent`, `census_row_id`, `recipient_kind` (`days_since_*` is read, `sr` 139, 149); dead CSS (`.bnf-ov-docsplit`, `-docline`, `-dash`, `.bnf-ov-comm-line`, `-meta`); the letter two-column branch never fires (status_report_pdf.py 489). | Not ported. |
| B27 | **Style debts.** `--muted` undefined (benefits-overview.css 1005); rules undo `.btn-primary` width (137–144, 346; benefits.css 162, 4641); look spread over seven sheets. | Fix token and global rule; split CSS by component. |
| B28 | **Accessibility.** Clickable divs, stepper included (X-13); the modal ignores Esc and shadows `window` (ExportReportModal.jsx 171); failures in the success toast (X-35). | Buttons; error toasts. |
| B29 | **Name-match renewal** (`ov` 74–99) can print "Renewal" on the client proposal. | M14. |
| B30 | **Two UIs over one checklist** (MarketingChecklist.jsx; GetToMarketCard.jsx; IntakeTab.jsx 1252–1262). | One set of controls, two frames. |
| B31 | **Current dot computed apart from next action** (journey.py 492–509): on quote-first deals it sits on Shortlist while the banner asks for the census. | M39. |
| B32 | **Primary contact can be the prior broker** and ignores benefit_admin (ClientHeader.jsx 39). | M30. |
| B33 | **2V `mark_lost` re-stamps a lost deal** with a new reason, time and Activity row (2V/deals/services.py). | 409, as the old rule did. |
| B34 | **2V plan: first access creates rows** (Intake, Commission, ProposalConfig, RfpConfig) and stamps a typed `legal_name` (plan.md 1657–1659), so a GET would write and inflate Intake complete %, against §3.6. | Missing rows read as empty (M13). |
| B35 | **Three deal-type rules across 2V plans**: `opened_as`, Agenda's "earlier sold deal", and `Client.relationship`, which flips on sale (quotes/marks.py 52–54). | M14. |
| B36 | **2V `delete_client` hard-deletes** deals, documents and files (2V/deals/services.py). | M104. |

## M.6 New design

**App.** `overview`, last in the chain; nothing imports it. No models, no services: it reads and assembles. Files under 300 lines:

| File | What it holds |
|---|---|
| `payload.py` | `overview(deal, viewer, today)`: gathers each app's facts once, then applies the rules |
| `rules.py` | Pure: `last_contact`, `tiles`, `gtm_groups`, `quote_to_close` |
| `views.py`, `urls.py` | One endpoint |
| `report/` | Only if Q1 says build: `build.py`, `text.py` first |

**Endpoints the Overview calls:**

| Method | Path | Owner | Answer |
|---|---|---|---|
| GET | `deals/{id}/overview/` | overview | The payload below |
| GET | `deals/{id}/journey/` | agenda | `{journey, waiting, next_step: {key, label, tab, params}}`, from counts and EXISTS checks only |
| GET | `deals/{id}/confidence/` | review | Cells, confirmed bar, documents, ignored and check rows (50 each plus `more`), the last re-check |
| POST | `deals/{id}/review/marks/` | review | `{document_id, action: approve\|ignore\|check\|clear}` → `{changed: {owner: n}, activity_id}`; another deal's document → 404 |
| POST | `activity/{id}/revert/` | deals | Undo for marks, note deletes, fact edits |
| POST | `clients/{id}/archive/` | deals | `{archived}` → the archive block |
| GET | `archived/` | deals | Archived clients with their deal |

Notes, contacts, lost, reopen, intake writes, upload, tray asks and `ai` starts use their owners' endpoints. `mark_document` runs in one transaction: it locks the Deal row first, then the owners' rows in a fixed order (intake, census, quotes, questionnaire), and writes one Activity row whose `changes` hold before and after marks by owner, never values.

**Payload shape:**

```json
{"identity": {"type": "new", "legal_name": "", "legal_name_default": "…", "open_days": 12, "owner": {"id": 3, "name": "…"}},
 "facts": {"fein": "", "sic_code": "", "situs_state": "", "employee_count": "",
           "carrier": {"value": "…", "from": "plan", "plan_id": 88},
           "funding": {"value": "level_funded", "from": "coverage", "plan_id": null},
           "agent_of_record": {"value": "", "default": "…"},
           "deal_size": "250000.00", "in_force": [{"line": "medical", "label": "Medical 4%"}],
           "contact": {"id": 7, "name": "", "email": "", "phone": ""}},
 "archived": null, "asks": {"refusal": null, "file_asks_ready": false},
 "tiles": {"intake_pct": 80, "plans_quoted": 6, "last_contact_at": "…", "expected_revenue": 12450},
 "get_to_market": {"badge": "ready", "quotes_first": true, "met": 7, "required": 9, "tier": "small",
                   "headcount": {"value": 42, "from": "typed"},
                   "groups": [{"key": "census", "met": false, "rows": ["intake checklist rows"]}]},
 "quote_to_close": [{"key": "quotes", "detail": "6 plans · 2 to review · 1 missing"}],
 "enrollment_check": {"intake": 42, "census": null, "advisor": 45},
 "outreach": {"last_sent_at": "…", "last_response_at": "…", "open": 2, "oldest_days": 9, "links": [], "never_asked": []},
 "commission": {}, "coverage_notes": [{"line": "medical", "carrier": "…", "body": "…"}]}
```

Census, questionnaire and `sl_lasers` entries in the confidence lists carry their label and `value: null`; none names a person. GETs create no rows.

**Query keys** (`staleTime 0`):
- `['deal', id, 'overview']`
- `['deal', id, 'journey']`: every tab; light, because `invalidateDeal` refetches it after every write.
- `['deal', id, 'confidence']`: a sibling, so a pin or fact edit never refetches it. No in-view gating (C7).
- `['deal', id, 'notes']`
- `['deal', id, 'activity', 'feed']`: under the drawer's prefix.

Mutations invalidate narrowly: notes → notes, activity; facts → overview, journey, activity, confidence; checklist → overview, journey, activity; marks → confidence, activity; archive → overview, header, clients.

**What other apps must provide:**

| App | Must provide |
|---|---|
| deals | Note (five kinds, 1–8,000 characters, `deleted_at`, author-or-admin); Contact email check, `contacts.primary`; `Deal.deal_size`, `opened_as`, `agent_of_record`; `Client.archived_at/by`; no default managers; `AgencySettings.producer_name`, `producer_npn`; `rules.deal_type`, `agent_name`, `client_asks_open`; `mark_lost` 409 on lost; archive services; `DELETE clients/{id}` → 405; Activity `subject`, `actor_kind`, `changes`, `selectors.feed`, revert; actions archived, restored, opened, returned, signed, read, staged, failed, logged, marketed |
| documents | `review_rules.origin_bucket`, `quality_headline`; per-kind accept list in `/api/meta/` |
| ai | `recheck` reader with scopes, work lane, staged result; no PHI claimed or stored; `useAiState`; drawer beside the page |
| intake | Facts that never create rows; answered/needed, missing labels, `contacts_ok`, BOR, `marketed_at`; checklist rows with group and control flags, taking the headcount; intent rows with `changed`; `CurrentCoverage` notes and comp; shared controls in `deal/intake/checklist/` (`bnf-override-link`, `bnf-attest-toggle`, `bnf-q-formselect`, `bnf-in-tray`, `bnf-client-note`, `bnf-ask-form`); `?focus=marketed` |
| census | Counts, required cells, errors, pending client values from its derived row |
| quotes | `facts.incumbent`, `enrolled_headcount`, `enrollment_check`; plan counts (quoted, to review, missing, starred, sold); `source_counts` and marked rows as SQL aggregates |
| questionnaire | Provider (form, chooser, signed, answered, `disclosure_needed`); counts and marked rows with `value: null` |
| commission | `summary(deal, viewer, states)`; the card and `SplitChips` |
| proposals | Latest issue; the renewal-offer rule if Q8 says yes |
| review | `outreach`, pending counts, tray state, `LinkStatus`, census lane, second-factor flag; `selectors.confidence`, `services.mark_document`; a dock that leaves room |
| agenda | The light journey read; step-for-next-step map; `params`; lost state; no "skipped"; no own deal-type rule; logged follow-up times |

**Frontend** (`deal/overview/`, each file under 300 lines):

| Area | Files |
|---|---|
| Shell and header | `OverviewTab.jsx`, `TitleActions.jsx`, `Banners.jsx`, `OverviewHeader.jsx`, `HeaderFacts.jsx`, `WaitingBanner.jsx`, `MetricTiles.jsx` |
| Card 1 | `gtm/GetToMarketCard.jsx`, `gtm/ReqGroup.jsx`, `gtm/IntentGroup.jsx`, `gtm/IntakeGroup.jsx`, `gtm/CensusGroup.jsx`, `gtm/FormGroup.jsx`, `gtm/DocumentsGroup.jsx`, `gtm/ConfirmGroup.jsx` |
| Card 2 | `QuoteToCloseCard.jsx` |
| Feed | `feed/OutreachStrip.jsx`, `feed/AskedList.jsx`, `feed/Timeline.jsx`, `feed/activityLook.js` |
| Notes and side cards | `notes/NotesCard.jsx`, `notes/NoteItem.jsx`, `CoverageNotesCard.jsx` |
| Data confidence | `confidence/ConfidenceCard.jsx`, `confidence/DocumentRows.jsx`, `confidence/MarkedList.jsx`, `confidence/RecheckPanel.jsx` |
| API | `api/overview.js` |
| Shared elsewhere | `ui/FactRow.jsx` (text and select), `pages/DealPage/JourneyStepper.jsx`, `pages/ArchivedPage/` |
| Deferred | `report/StatusReportModal.jsx` |

**Styles to copy verbatim**, split into files of at most 300 lines under `styles/overview/` and `styles/journey/`:
- benefits-overview.css: header and layout `bnf-ov-titlerow`, `-titlebtns`, `-exportbtn`, `-header`, `-identity`, `-avatar`, `-name`, `-legal`, `-chips`, `-stage`, `-clientbox`, `-clientlink`, `-clientmeta`, `-clientnext`, `-facts`, `-row`, `-row-hint`, `-readonly`, `-cols`; waiting `-waiting*`, `-side*`; feed `-outreach*`, `-links*`, `-link-*`, `-timeline`, `-event*`, `-dot-*`, `-actor`, `-showall`, `-activity`; notes `-notes`, `-note*`, `-notelist`, `-kindchips`, `-kind-*`, `-history`, `-prior*`; side cards and confidence `-cvgnote*`, `-commission`, `-confidence`, `-conf-*`, `-key*`, `-marked*`, `-audit*`; `bnf-rep-*` only if the report is built.
- benefits-journey.css: `bnf-journey-*`, `bnf-seg*`, `bnf-phase-*`, `bnf-req-*`, `bnf-ready-badge`.
- benefits.css: `bnf-next-*`, `bnf-lost-banner`, `bnf-lost-confirm`, `bnf-archive-*`, `bnf-snapshot-grid`, `bnf-progress-*`, `bnf-quality-label`, `bnf-review-btn-check`, `bnf-viewtab*`, `bnf-chip*`; `bnf-carry-*` with the carry banner.
- benefits-radar.css: `bnf-cat-chip`, `-static`, `-renewal`, `-custom`, `bnf-cal-*`. ArchivedPage: `bnf-archived-*`. The `bb-*` base belongs to the foundation.
- Dead rules are not copied; `--muted` is defined; the width-undo rules go once the global `.btn-primary` rule is fixed.

**Tests to write** (behavioural only):
- **Payload:** an empty deal returns every block; overview, journey and dashboard GETs create no rows and no Activity; a quote-first deal with typed counts shows plans, Card 2, the enrollment line, M110 and its tier, nothing "skipped", and the current dot on the step that owns the next step; a lost deal has a lost waiting state.
- **Deal type:** a won prospect stays New business while its client becomes a New client (plan.md §5.1, §13.11; OQ2); a status edit before the sale changes the type, after the sale it does not.
- **Facts:** facts land in intake; a bad FEIN returns intake's message; a current plan's carrier is read-only with its source; with no plan a typed carrier lands in `CurrentCoverage`; unknown funding answers 400; the agent falls back to owner, then agency producer.
- **Contacts:** a prior broker is never primary; a benefit_admin can be; the first edit creates an hr_admin; a bad email answers 400.
- **Archive:** archive and restore write Activity; the client leaves the dashboard and work queue, its Overview opens with the banner, the commission book keeps its sold deal; portal writes answer 410; `DELETE clients/{id}` answers 405.
- **Asks:** `client_asks_open` refuses lost, archived and stale deals with their sentences; census and document asks are refused until the second factor exists.
- **Last contact:** a call note counts; a draft link does not.
- **Commission card:** the producer's own tier sees no ledger figures; $502.50 shows as $503.
- **Confidence and marks:** each origin lands in one cell; no census, questionnaire or `sl_lasers` value appears; one Activity row per mark action and one revert restores every owner; another deal's document answers 404; two concurrent marks on one plan both survive.
- **Timeline:** `downloaded` rows are neither listed nor counted; a deleted note's event shows no detail; portal rows return as client rows; Show more pages.
- **Notes:** author or admin; soft delete and restore; pinned first; 8,000 characters.
- **Re-check:** census, questionnaire and `sl_lasers` never claimed; nothing approved before Apply; a start while a read runs is refused.
- **Speed:** with 600 plans, 2,000 members, 200 links, 200 notes, 100 documents and 5,000 Activity rows, the overview, journey and confidence reads run a fixed number of queries, one aggregate per owner.
- **Vitest:** `activityLook`, `FactRow` (text and select) commit rules, `formatAgo`.

**plan.md updates:**
- Rewrite §5.9 (point to Agenda), §5.10, §7.13 and §8.5 to match this section.
- §6.2: Note (five kinds, 8,000 characters, `deleted_at`), the contact rule, `Client.archived_at/by`, `Deal.deal_size`, `opened_as`, `agent_of_record`, `AgencySettings.producer_name/npn`, Activity `subject`, `actor_kind`, `changes`; one-to-one rows are created on first write, never on a read.
- §7.3: `DELETE clients/{id}` answers 405; archive endpoints.
- §15: the status-report row stands unless Q1 says build; the checklist attestation and override row changes, as the intake section keeps them.

**Slices:**

| Slice | Build | Depends on | Done when |
|---|---|---|---|
| O1 | deals additions, Archived page | — | Archive, restore and the 405 work; notes undo; the contact rule holds. |
| O2 | Shell, header, banners, tiles, stepper | Agenda's light read; intake and quotes facts; commission summary | Block order and class names match a screenshot of an equivalent synthetic deal in the old app (2V starts empty, §16 Q15). |
| O3 | Card 1, Card 2 | Intake's shared controls; questionnaire provider; review tray and second-factor flag | Every control writes through its owner. |
| O4 | Feed, notes, side cards | Review outreach; Activity subject and actor kind | Each logged event appears with its detail. |
| O5 | Data confidence, re-check | Review confidence and marks; the Documents station; `ai` recheck | Confirm, ignore and Undo work per document. |
| O6 | Status report text, only if Q1 says build | — | Sections, windows and caps match the old digest. |

**Rulings on the challenges.** C1 modified: one `deal_type`, but over `opened_as` frozen at sale; the relationship flip stays a client fact, because a won prospect is an existing client whose first deal was new business (D-102). C2–C6 accepted. C7 modified: sibling key kept; in-view loading dropped, since SQL aggregates make the read cheap. C8–C10 accepted. C11 accepted and extended: the confidence read moves to review too. C12 accepted and extended to `sl_lasers` (PHI, §3.8). C13 accepted; the old Q2 is answered by D-119. C14–C16 accepted. C17 accepted: the chip follows the Proposal's decision. C18 accepted in part: only the Waiting banner moves; lost and archive banners already sit above the facts. C19–C23 accepted.

## M.7 Open questions for Daniel

1. **Status report.** plan.md §15 lists it as do-not-build, and it is not on your list of needs. Build it? If yes, who reads it: only the team, or the client's leadership too? If the client may see it, revenue and internal notes never print. Default: defer; if wanted, text first.
2. **Renewal parts.** The carry banner, earlier deals, reminders, prior-year notes, a BOR from an earlier year and the client page wait for the renewals decision. Agree? Default: yes.
3. **Lost reason.** Optional, as on the old screen, or required, as plan.md §5.1 says? Default: optional.
4. **Agent of record.** Does anyone act as agent of record without a login? Default: one "Agent of record" row that falls back to the deal owner, then the agency's producer name set in admin.
5. **Archive.** In version 1 each client has one deal, so Archive hides the client and its deal together, even a sold one. Archived clients' links stay readable but refuse writes, as on lost deals. Agree? Default: yes.
6. **"＋ Add request".** Should a new custom ask wait in the request tray instead of reaching the client portal at once? Default: the tray.
7. **Client deletion.** Never (the old 405), or admin-only when the client has no sale and no ledger rows? Default: never; archive instead.
8. **Renewal letter figures.** Should the carrier's renewal offer ($/yr, % change) show, both on the Overview chip and in the proposal's "The carrier's renewal" and "Ours vs the renewal" blocks? Default: decided with the Proposal section; deferred if those blocks are not ported.
9. **Layout.** The experience review measured the "Waiting on" banner below the fold (X-84). Move it directly under the title, above the facts? Default: move it; everything else keeps the old order.

---
