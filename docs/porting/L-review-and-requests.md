# Part L — Review & requests, client portal

[← Porting plan](README.md)

**What it is:** Review & requests is the deal's outreach loop with the employer. It works out what is missing, collects asks in one tray per deal, and sends them on secure links: one request, with one link per person. The public client portal is where the employer answers, uploads and signs; the team then approves, sends back or discusses what came back, in keyboard queues and on a request page. Review stores requests, links, notes and last looks; the client's answers wait as pending entries on the owners' rows, and every state is worked out on read.

## L.1 Files read, in order (one line each)

Old repo: `c:/Users/fooba/OneDrive/desktop/Vantage_all/Vantage` (old paths are relative to it). New repo: `c:/Users/fooba/OneDrive/desktop/Vantage_all/2Vantage`. No client files, meeting folders or real data were opened.

**Specs and READMEs**

| File (lines) | What it is / what it taught |
|---|---|
| benefits/review/README.md (259) | Module map and the D-208 "change together" table. Traps: rolled-back previews, notes keyed on row index, clock skew, the nameless-PIN refusal, per-cell strips |
| reviewrequest/README.md (96), reviewrequest/CLAUDE.md (77), linkguard/CLAUDE.md (27) | The kit is words and config, and its UI takes props. The gate answers 428, never 401 |
| benefits/README.md (394), benefits/market/README.md (461) | Review, portal and link entries (grep) |
| PlanningDocs/Benefits/review-hub.md §2–4, review-requests-roadmap.md (157) | Daniel's calls 1–8; the team's gap list N1–N6 |
| PlanningDocs/Benefits/review-request-page.md (338), review-requests-v2.md (244), -one-way.md (431), -section-views.md (77), -link-settings.md (104), -builder.md (107), -ask-card.md (122), -scope-notices-nudge.md (91), review-and-request-multi-person.md (85), client-responses-dashboard.md (125), census-client-request.md (439) | Request page, builder, Ask card, settings card, nudges, fan-out, dashboard column, census asks |
| PlanningDocs/Platform/client-link-security.md (70), client-link-verification.md (283) | Daniel's 2026-08 ask to verify every recipient. R1–R8; R4, R7 and R8 are open. Opens record only the time, on purpose |
| 2V CLAUDE.md (42); plan.md §1.4, §3.3, §3.6–3.9, §5.2, §5.8–5.9, §6.2–6.10, §7.11–7.12, §8.1, §8.7, §8.15, §11, §12.3, §13, §15, §16 | The chain and the write rules; ClientValue; the blank template; the second factor (▲13); `deals.Contact`; 14-day links; an expired page with the agency's contact; logs exclude `/api/portal/` |

**Models**

| File (lines) | What it is / what it taught |
|---|---|
| benefits/models/review.py (159) | ReviewNote: `census_row` is SET_NULL, and there is no draft constraint. ReviewSeen |
| benefits/models/market.py (706) | ClientAskItem, CensusCell layers, BenefitsClientRequest, BenefitsClientLink (about 30 columns), CensusFieldRequirement, ValueReviewBatch |
| benefits/models/case.py (1,878), questionnaire.py (148) | Value-layer mixins, CaseField, `CaseDocument.review_state`; the questionnaire's client layer and signatures |
| linkguard/models.py (70), registry.py (24), guard.py (72), codes.py (172), views.py (82), urls.py (10); benefits/linkguard_adapter.py (20) | Challenges, PINs and sessions: 10-minute codes, 5 tries, a 60 s resend wait, and a 1 h session under an 8 h ceiling |
| reviewrequest/models.py (61), vocab.py (86), shapes.py (59), registry.py (300), access.py (371), views.py, urls.py; benefits/ask_surfaces.py (63) | SurfaceSetting. Every form defaults to a private link. Modes and levels; 7 days with a 30-day ceiling; the P&C forms |

**Rules and services**

| File (lines) | What it is / what it taught |
|---|---|
| benefits/market/client_request.py (1,617) | mint, build_ask, floors, extend, take off, revoke, restore, expiry, address, PIN, nudge and close; `NAMELESS_NEEDS_PERSON` |
| benefits/market/portal_base.py (55), value_origin.py (231), value_review.py (492) | Optional HMAC bases; origin words; batches of marks |
| benefits/market/field_request.py (913), census_request.py (844), census_upsert.py (271), intake_review.py (227), intake.py (`contacts_ok`, `portal_locked`, `we_read`) | The census board, scopes, the rebuild guard and SSN masks. The intake board and its lock. A client answer counts as filled |
| benefits/review/notes.py (2,552), items.py (1,544), board.py (724), request_page.py (1,569), new_link.py (371), link_form.py (461), preview.py (344), uploads.py (109) | The note writer, derived counts, lanes, Next, badge sums, the request page, builder, Ask card, previews and file decisions |
| benefits/pipeline/export_check.py (449), pipeline/workbooks.py | `deal_problems`, the questionnaire lines and the `?ack=` digest; the census template |
| benefits/tasks/deal_tasks.py, tasks/check.py (149), tasks/steps.py, radar/reminders.py (1,640), renewal.py, history.py (384) | The nudge task; Agenda's `_ask_steps`, with its own wait; the renewal refresh; link labels |

**Views and payloads**

| File (lines) | What it is / what it taught |
|---|---|
| benefits/views/review.py (628), requests.py (508), intake_review.py (62), market.py, cases.py (1,256), shared.py (297), ai.py (1,316) | Staff endpoints, Revert, `_autostart_reader`, and `CensusRowDeleteView`, which has no guard |
| benefits/views/portal.py (2,609) | The public API: the open stamp, which `?refresh` or `?preview` skips; staff detected by a DRF token; save, attest, add people; specs repeated on every cell; the form stamp; file names from the whole deal; the lines write; the scan poll |
| benefits/serializers/overview.py (1,703), market.py (980), journey.py (557), primitives.py (360) | Outreach, activity and carry payloads |
| benefits/urls.py, backend/urls.py, backend/settings.py, backend/checks.py (98), benefits/admin.py (151), users/permissions.py | Routes; throttles (anonymous 200/h, portal_stamp 300/h); deploy check E005; the link admin |

**AI**

| File (lines) | What it is / what it taught |
|---|---|
| benefits/ai/census_agent.py (605), ai/page_context.py (667) | The census turn keeps open asks. Claimant answers are reported only as "answered" |

**Frontend**

| File (lines) | What it is / what it taught |
|---|---|
| services/api/benefitsReview.js (217), benefitsMarket.js, benefitsShared.js (423), linkguard.js (15), reviewrequest.js (14), core.js, usage.js (40) | Endpoints. The verification token is kept in sessionStorage, one per link |
| components/reviewrequest/ (29 files: ReviewQueue 474, RequestRail 804, FollowUpCart 855, ReviewRequestSettings 359, NoteThread 240, RequestCard 237, CommentMargin 181, ReviewSectionBar 179, RecipientPicker and others); components/linkguard/LinkCodeGate.jsx (95) | The kit. Contacts with no email are shown disabled |
| components/benefits/shared/: DealReviewTab (671), RequestPage (1,749), LinkSettingsCard (950), RequestCards (455), RequestForm (449), useLinkBuilder (1,485), useRequestEntry (326), useRequestActions (200), useReviewTray (156), usePollStamp (120), 20 smaller hooks and helpers; CaseWorkspace.jsx; PdfViewer (586); DocumentViewer (91); ChangeHistoryCard (347); useExportCheck (151) | The request-page group and its hosts. `addPerson` saves every new contact as an HR admin |
| components/benefits/shared/overview/: RenewalCarryBanner (97), GetToMarketCard (832), ActivityFeed (204), WaitingBanner (52) | Tray writers outside the tab; the revalidation door |
| components/benefits/market/: BenefitsClientPortal (3,648), usePortalStamp (129), portalKeys, IntakeField (109), QuestionnaireForm (285), questionnaireCascade (228), QuestionnaireReview (831), CensusRequestPanel (435), MarketingChecklist (577), useMarketingChecklist (82), IntakeTab (1,638), CensusTab (948), QuestionnaireTab (1,140); censusreview/ (10 files); intakereview/ (IntakeQueue 665, IntakeReviewView 458) | The portal (company card, line chips, the help mailto) and the section hosts |
| contexts/EditSessionContext.jsx (205); utils/chromeless.js (13), usage.js (212), pageView.js (40), download.js (88); App.jsx; guides/ (8 review guides, about 2,000 lines) | Edit sessions, the chromeless /b/ route, usage tracking, routes, tours |

**Styles**

| File (lines) | What it is / what it taught |
|---|---|
| styles/reviewrequest.css (1,667; 539 rr- classes), linkguard.css (36), benefits-census-review.css (928), benefits-questionnaire.css (404); the portal, board and badge parts of benefits.css; App.css (4,357: bb-portal-*, .btn-violet); token uses in benefits-overview.css, commissions.css, formbuilder.css | The classes to copy. `--accent` is never defined. `--red`, `--line` and `--border-strong` fall back to different values in different files |

**Tests and tools (names only)**

| File (lines) | What it is / what it taught |
|---|---|
| benefits/tests_pkg: portal_tests (210), review_request_page_tests (316), review_link_form_tests (126), review_board_tests (76), review_connection_tests (56), review_notes_tests (49), review_new_link_tests (45), questionnaire_review_tests (43), review_hub_tests (38), review_loop_tests (27), review_intake_tests (15), market_tests, questionnaire_tests, existing_client_tests, case_tests, ai_tests, wwc_targets_tests, value_review_tests, review_revert_tests, radar_tests, tasks_tests, pipeline_tests; reviewrequest/tests.py (61); linkguard/tests.py (31) | The invariants carried into L.6 |
| devtools/checks/benefits_checks.py (763), devtools/e2e/review_request.mjs (209), suites.py (806), walkthroughs.py (1,137), cleanup.py (181); usage/features.py (136); assistant/platform_notes.py (809) | Live checks, the browser sweep, tours, usage keys, assistant notes |
| 2V: deals/models.py, activity.py, clock.py, values.py, services.py; documents/models.py, services.py, kinds.py; backend/settings.py, meta.py; frontend/src/api/client.js, App.jsx, styles/tokens.css | Activity merges only into the deal's latest row (same actor and key). Also there: `clock`, `values.apply`, the upload door, `PHI_KINDS`. Missing: `Contact`, `Document.slot` and its link, `set_review_state`. `/api/meta/` needs sign-in. Global anonymous throttle 200/h; `portal` 1000/h |

## L.2 Old data model, in brief

- **Values (EAV).** CensusCell, CaseField and QuestionnaireAnswer each hold:
  - a base value;
  - a client layer (`client_value`, `client_link`, `client_at`);
  - an edited layer (`edited_kind` hand, approve or relay);
  - an origin stamp;
  - a confirmation and a review mark, each with the value it was set on;
  - location fields.

  The value used is the edited one, else the client's, else the base. So a pending client answer counted in every rollup at once. Approving copied it into the edited layer.
- **BenefitsClientRequest:** the deal, a message (up to 1,000 characters), `census_keys`, when it was created, and when and why it closed (answered_elsewhere, superseded or cancelled). Its state comes from its links.
- **BenefitsClientLink:** one per person.
  - The ask is copied onto every sibling: about 15 columns plus `requested_cells`.
  - A policy snapshot: surfaces, security, life, slides.
  - Tracking: sent, opened, last opened, open count, expires, submitted (overwritten on every submit), revoked, `hide_on_file`.
  - Employee links add `recipient_kind` and `census_row`.
- **ReviewNote:** surface, `field_key`, `census_row`, request, link, parent, audience, text, author, time, `sent_at` (null while in the tray), resolved. The kind is note, sendback, ask, question or reply.
- **ReviewSeen:** one stamp per viewer per deal, which only moves forward.
- **Elsewhere:**
  - ClientAskItem (`fulfilled_by`);
  - CaseDocument (`client_link`, `review_state`);
  - `DealTask.nudge_link`;
  - CensusFieldRequirement (`client_note`, `assigned_contact`);
  - `MarketingAttestation.client_note`;
  - SurfaceSetting;
  - the linkguard rows.
- **Derived on read:**
  - pending answers and differs-open;
  - the phase: going_back, to_review or in_progress;
  - the change: changed, differs, added, filled, cleared or same;
  - AI buckets and missing values;
  - `ready_why` and `idle_days`;
  - the request-page status: in_cart, question, asked, answered, on_file or missing;
  - filters and badges;
  - the staff, portal and form stamps.

## L.3 Functionality inventory and verdicts

- B and P numbers refer to L.5.
- "Ch. N" marks a change made because of challenge N.

### Board, badges and section bars

| # | Functionality (what the user sees -> how it worked) | Verdict | New implementation |
|---|---|---|---|
| L1 | View row: Board, Request ("N to send") and Review (count) pills. Review is greyed at 0. Set by `?view=` | Keep | `deal/review/ReviewTab.jsx`; counts from `badges/` |
| L2 | Readiness strip: the intake readiness chip and % | Keep | Read from the badges payload |
| L3 | Next banner: one entry, with Go and Skip (Skip lasts this visit) | Keep | Skip is held in component state |
| L4 | Next ranking: (1) a link expiring within 2 days, unopened since the newest ask; (2) a question older than 24 h; (3) blocks a carrier, or required to market; (4) other expiring links; (5) newer questions; (6) the oldest answer, then client files. Up to 8, one per form | Keep | Pure `rules/next.py rank()`. Fixes B19: once quotes exist, intake-required items drop below answers. Ch. 8: rank 3 adds "quotes in, enrollment typed, no census". Agenda imports these predicates, so there is one rule |
| L5 | "N questions from the client": the oldest 6, each with section, where, who, a 140-character excerpt and Answer; "+N more" | Keep | Board selector |
| L6 | Missing lane (rose): census required blanks by column; intake required to market; checklist documents not on file; each armed form's required blanks; "No census on file yet". Each card has "(N with a question open)", Open and "＋ Ask all" | Keep | Counts from the owners' selectors. Ch. 2: one rule for every owner: a slot is missing when its stored value is blank and no pending client entry exists. Asked items still count, as before. "＋ Ask all" adds only unasked items and hides when none remain |
| L7 | Waiting lane (amber): requests that run out soonest, then the newest; "X is still answering" | Keep | `selectors/requests.py`, moved from serializers/overview |
| L8 | Request card: state, ask chips, message, progress. Per person: status, "N values came back", Copy link (marks sent), Copy message, Mark sent / Not sent after all, Nudge, Copy notice, Extend, View as client. Open the request; Close… with a reason. Chips: questions open, follow-ups, replies not seen, "Runs out in N" | Keep | One `RequestCard` on every Waiting lane. Message texts come from the server, fetched on click (Ch. 14f) |
| L9 | To review lane (violet): census client, intake, each form, client files; Review ▸ and Here ▸ | Keep | The owners' pending entries and documents' files to review. Ch. 4: adds staged client reads (L135) |
| L10 | To review cards for census and intake AI reads | Simplify | Shows the owner's AI count and opens the Documents review station. No second AI queue |
| L11 | Queue view (`?view=queue&section=`) with section chips and counts | Keep | `QueueView` |
| L12 | Section scope: the board cut to one section, with "All links ▸" | Keep | `board/?scope=` (L45) |
| L13 | Nav badges: three tones plus "?", and a violet ↩ on Intake, Census and Questionnaire. Fetched 400 ms after paint and on every refresh | Simplify | One `badges/` GET with a fixed number of queries and no export run. Invalidated by review writes and the stamp (P2). Ch. 5: the old sums stay: rose includes missing checklist documents, violet includes AI reads. They come from census `summary()` and intake's missing-documents selector |
| L14 | Section bar on Intake, Census and each form: a lazy Next; to-review, waiting, missing and in-tray counts; "all sections ▸"; the return line ("answered 3 · 2 ready · 1 still typing · 1 question"); the idle tick; "Approve N ready ✓" | Keep | `section/SectionBar.jsx`. Next is the first entry of the scoped board |
| L135 | A To review row per staged read of a client upload: "Their census file was read · Review and apply ▸" | New | Ch. 4: without it, a client's census sits read but unapplied while the Advisor keeps the typed counts (need 6). Rows come from ai's staged jobs that have no actor |

### Keyboard review queues

| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| L15 | Keys: A approve, X send back, R later, N note, E correct, J/K and arrows move, ? lists the keys. Moves on after each decision. Chips: All, the host's filters, Later. "N of M reviewed" | Keep | Shared `src/valuereview/ReviewQueue.jsx` and `keys.js`. The Documents station adds I, C, U and F |
| L16 | Census client queue: grouped by column and change; "Approve all N ✓" (up to 5,000 ids, idle answers included); phases To review, Not submitted yet and Going back; ours → theirs; a numeric hint (warns at 50% or more); origin chip; via link; ready-why; thread; "blocks Aetna" columns first | Keep | `queue/?surface=census`. The hint and the change are pure functions. Carrier columns come from rfp |
| L17 | Queue writes: approve, correct, Keep ours, send back, note, reply | Simplify | The owner's `approve_client` / `reject_client`. "Keep ours" is a reject, so there is one writer. Correct is the owner's typed write. Ch. 13d: that write marks the entry `replaced`, so the portal never says "rejected" |
| L18 | The roster beside the census queue; a click focuses the item and loads its page | Keep | Read-only mode of `src/grid` |
| L19 | Census AI queue: buckets, "How their columns were read", the viewer at the page, undoable marks, X asks the client | Simplify | Lives only in the Documents station (it was a duplicate path). The station's X drafts a tray ask through `TrayContext` |
| L20 | Intake queue: by section and change, with the form section beside it; required to market first | Keep | Its AI file pane moves to the station |
| L21 | Questionnaire queue: client answers, unsure reads first, questions. X is greyed with the reason. One form at a time | Keep | `questionnaire.selectors.review_items()` |
| L22 | Thread on each item: To client or 🔒 Team only. A reply closes the question. Resolve; new-since dots; Copy notice | Keep | `thread/NoteThread.jsx` |
| L23 | Split layout: context on the left, queue on the right; breakpoints at 1200, 1100 and 900 px | Keep | `rr-*` classes copied |

### Request page

| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| L24 | Header: RFP due date, effective date, "N need you", key legend | Keep | — |
| L25 | Next banner: Extend or Nudge an expiring link, Log a call, Skip | Keep | Log a call posts to Agenda's task endpoint from the browser. Review never imports agenda |
| L26 | Who bar: All people (the default with two or more); person chips (opened N×, days left, ?, Copy link, View ▸); request groups; "A new link…"; "People & links (N) ▸" | Keep | — |
| L27 | Show chips: All, Client questions, To review, Notes, Resolved, counted per tab and per link | Keep | One server rule |
| L28 | Tabs: Intake, Census, Questionnaire, Documents (`?pane=`) | Keep | Ch. 14a: each pane is its own GET. The census pane is paged. Counts come from badges |
| L29 | Ask rail: required items lifted; status chips; "＋ Add all N"; ticks; census bands by column; over 500, it offers their census file; whole form; census file; locks; fold and widen | Keep | Status is one pure function over asks, drafts, entries and notes |
| L30 | Middle: their form (the embedded portal, with "New · not sent" and ×), or our rows (`?as=staff`, Upload it, a compact census table) | Simplify | Built by the portal's own pure payload builder, fed a draft ask. Nothing is written then rolled back (P5) |
| L31 | Comment-margin cards: question (quick replies, Enter it, Reply), answer, upload (Accept, Wrong file, Read with Claude), notes. A live line; an editable draft note; cards sit inline below 1180 px | Keep | The old AI card links to the station |
| L32 | Page keys: A, X, R, N (pick mode; Esc stops), E, J/K, ?. They work across tabs | Keep | L15's key module |
| L33 | "N new since your last look · Show ▸"; "Already answered (N)"; "<pane> has N ▸" | Keep | `Seen` |
| L34 | Double-clicking a row offers Edit mode | Keep | — |
| L35 | Edit mode, for answers read over the phone. Enter goes to the next box, Tab to the next required blank, and Esc undoes the box. The From-client toggle marks a save as relayed or typed. Saves run in turn, then one re-read. Census blanks are listed per person (up to 500). Clearing a box reverts our typed value | Keep | `POST review/enter/` calls the owner's typed write, with `origin: client, via: relay`, or as typed |
| L36 | Update links (All people) | Simplify | One `POST review/links/update/`, with a result per change (B8). Ch. 18: asks live on the request, so ask changes commit per request. Blank, expiry and nudge commit per link |
| L37 | Going out and "In the cart (N)": a card per destination, a "Goes on" picker, every why, the count-only message, the result | Keep | — |
| L38 | People & links: every link ever made, with Edit | Keep | — |
| L39 | Link settings card. Who can open it, filled or blank, expiry, "Remind me to nudge" and the message go with Update link. These act at once: on/off, New PIN (shown once), Extend, Correct the address (only if never opened), Give someone else access, Copy link | Keep | — |
| L40 | Link builder. Who: contacts, typed emails, "＋ Add a person to the deal", or nobody. Then security, blank, date and ticks. Ask all missing, only required, or the whole form. Live numbers after 350 ms; a preview. Create link shows each link and PIN once; a LinkReady card | Keep | A reducer plus small parts. The numbers and preview are pure functions. The write is `POST review/requests/` |
| L41 | Builder doors: `?preset=required`, `census-missing`, `form:<key>`. Landing writes nothing | Keep | — |
| L42 | Ask card on an open link. Ticks are drafts. Removals, part switches, whole forms, blocks, narrowing, the level and per-person settings wait for "Update link", one locked write. The order is removals, level, adds, then settings. It never raises the level by itself (409 `needs_level`) | Keep | `POST review/requests/{id}/form/[?dry_run=1]`. Plans come from the pure `rules/form_plan.py` (Ch. 17). It locks the request |
| L43 | Approve N ready, with the idle tick | Keep | `POST review/approve/ {surface, form?, ready_only, include_idle}` |
| L44 | Staff polling: at once, then every 30 s backing off to 2 min, paused while hidden. A moved stamp re-reads the page. `seen` is posted on leaving after 5 s visible | Keep | React Query on `['deal', id, 'review', 'stamp']`. Ch. 14c–d: refetched on the deal page's one poll tick (the AI section's `useAiState`). The stamp reads link, request and note columns, plus the newest Activity id in the value areas. It never scans JSON. Portal saves never touch `Deal` |
| L45 | Each section's own Board, Request and Review, with its notices; a section's Undo takes back only its own edits | Simplify | One component set with a `scope` prop, wrapped by `SectionHost` |
| L46 | Census request panel: By person or By field; missing or the whole census; "Only cells I pick"; "＋ Ask N"; the census-file ask above the limit | Keep | The census-scope Missing lane plus the grid's select mode |
| L47 | Census board per column: counts, origin mix, requiredness picker, assignee picker, format lens | Simplify | Counts and asks stay. Requiredness overrides go (plan §15). The assignee picker goes with partition (L67). The lens moves to rfp |
| L48 | Intake board's Missing panel and per-deal requirements | Simplify | The panel stays. Per-deal overrides go (plan §15) |

### The tray

| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| L49 | Tray bar: "Request tray · N · → Dana's link (expires Oct 30)"; hidden on the request page | Keep | `tray/TrayBar.jsx`. Ch. 14e: the count and destination come from badges, and the tray loads only when opened |
| L50 | Tray snippet: items by section, ×, "Open the request ▸", `?tray=open` | Keep | — |
| L51 | Asking: one draft per item (a bulk ask keeps a draft's own note). Census asks over 500 are refused whole. Remove one or many | Keep | Fixes B7: a partial unique constraint, and every scope skips items already asked on a live link |
| L52 | Each draft's target and why (needs a link, needs a PIN, signed, gone); options; link cards with "expires if sent"; "needs a new request" | Keep | Pure `rules/tray.py`. "Verified only" becomes "needs a PIN" (B18) |
| L53 | Send plan: one part at a time, keeping what went | Simplify | One `POST review/tray/send/`, with a transaction and a result per destination |
| L54 | "＋ Ask" and "✓ In tray" outside the tab: intake, checklist and carrier-form rows; the census-file ask; picked census cells; the Overview's Get to Market card | Keep | `TrayContext`, in a neutral module, provided by review |

### Requests and links

| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| L55 | One request to several people: a link each, one shared form, answers in one place, "N colleagues asked too". States: draft, partly_sent, waiting, answered, expired, closed | Simplify | The ask is stored once, in `ClientRequest.asks`. Links hold the person, access and tracking. `request_state` is pure |
| L56 | Create a request. Refused on lost and past-year deals. 1–20 recipients, de-duplicated. A contact with no email is refused by name. The level is the strictest form's or the person's pick. A PIN per link, shown once | Keep | Archived deals are refused too (B10). Ch. 7: a name is enough while Copy link is the send; the email is optional (Q8) |
| L57 | A private link to nobody named | Keep | Ch. 1: it may carry a PIN that staff hold, so it can ask anything. `NAMELESS_NEEDS_PERSON` goes |
| L58 | Extend: a send-back or ask joins the open request. A lapsed link comes back if within its ceiling. A stricter form needs a new request. A link is never loosened | Keep | `services/form.join()`; locks the request |
| L59 | Take off, shrink or widen what a link asks, never what the client said. Refused by name for part of a whole form, intake or "whatever is missing" | Keep | Pure plan plus one write; bumps `form_version` |
| L60 | Revoke, and Restore (the same URL, its own life, at most 30 days) | Keep | `PATCH links/{id}/`. Restore bumps `pin_version` |
| L61 | Set expiry: 23:59:59 on the picked day, capped at the ceiling. It stops the save sliding it | Keep | Agency time zone via `deals/clock` (B6). `slides` is its own field (B15) |
| L62 | Slide on save: 7 days, never past 30 days from creation. Submit does not slide it | Keep | At most once a day, in one UPDATE (P2) |
| L63 | Correct the address, only before the link is first opened | Keep | — |
| L64 | Security: private link or PIN. Never below the floor; never lowered while a sensitive ask is open. New PIN unlocks the link and ends sessions | Keep | One floor table in `review/policy.py`. Ch. 1: the floor follows what the page shows. A PIN is needed when it shows census people (any cell scope) or questionnaire answers (online), and for medical or claimant send-backs. Upload-only asks (census file, documents, a form in upload mode) and intake need only a private link, the old default (Q1) |
| L65 | Emailed code ("verified recipient"), its flag and deploy check E005 | Defer | Needs outbound mail. Plan §7.12 says a code sent to the same inbox is not a second factor (Q1, Q8) |
| L66 | Blank link: it shows only the person's own answers and sent-backs. Submit attests only what was shown | Keep | `ClientLink.blank` |
| L67 | Partition mode, column assignment, the assignee breakdown, "Never asked", `census-links/batch/` | Drop | Off unless an admin switched it on (Q9) |
| L68 | Per-employee census links | Drop | Behind a flag that is off. The census is asked of the employer |
| L69 | Nudge reminder a day before expiry, one per link; it lapses when the link ends or the deal is lost | Simplify | `ClientLink.nudge_on` and `nudge_done_at`, with pure `nudge_open`. Agenda lists it. No DealTask |
| L70 | Close with a reason; every live sibling then answers 410 | Keep | — |
| L71 | Mark sent (copying is the send) and its undo, which is refused once the link was opened or submitted | Keep | — |
| L72 | Give someone else access | Keep | `POST review/requests/{id}/people/` |
| L73 | "＋ Add a person to the deal" creates an HR-admin contact | Keep | Through the `deals.Contact` service. Ch. 7: the form asks for the role, with nothing pre-picked. So a CFO added only to receive a link never passes intake's contacts gate (B21) |
| L74 | Settings page: per-form on/off, ways of asking, security, days, slides, locked facts, "N already out" | Simplify | Constants in `review/policy.py`, served by `/api/meta/`. Floors and their reasons show in the builder and the settings card. The P&C rows, `FormSwitchLine` and the modes go (Q6) |
| L75 | The frozen flat mint; endpoints with no UI caller (`security/`, `on-file/`, notes `?ref=`, `POST client-requests/`); `mint(nobody=True)` | Drop | No callers once the tours and rolled-back previews go |

### The client portal

| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| L76 | A page with no navbar and no Ask Claude bubble | Keep | `/portal/:token` outside `AppLayout` |
| L77 | Gate: unknown 404; expired, revoked or closed 410; PIN 428 with a six-digit box; locked after 5 wrong tries | Keep | `review/portal/guard.py`. A signed token in `X-Link-Verification`, kept in sessionStorage per link |
| L78 | Staff with a token skip the gate; a signed-in staff note | Simplify | View as client opens `/preview/links/:id`, signed in. Ch. 10: portal views have no DRF authentication, so the guard reads Django's session user. A staff session on `/portal/` sees the note and records no open. Its writes answer 403 "use Edit mode" |
| L79 | Opens counted on the client's GET only | Keep | Verdict changed from Simplify (Ch. 11a): a browser beacon can be skipped. So the payload GET records the open in one conditional UPDATE, as plan §7.12 says. Re-reads within 30 minutes add nothing. Staff never count. No `?refresh` or `?preview` flag decides (B20). No other GET writes (P1) |
| L80 | Top bar "Secure link · expires in N days"; the preview banner | Keep | — |
| L81 | To-do rail: a row per form, intake, employee details, census file, each document, and Follow-ups. New replies are counted. A blank with an open question counts as done for now | Keep | The server sends each item's "done while blank" flag, and the browser only counts (N1) |
| L82 | Shared request card: "N colleagues asked too", "a colleague submitted on …" | Keep | Colleagues are a count, never names |
| L83 | Intake section: typed fields, live show/hide, locked fields, the "we read" marker, the broker's note, "Where do I find this?" | Keep | Pure `editable(source, reopened)` in review |
| L84 | Company details card ("About your company · Group information") | Simplify | Ch. 21: the card and its look stay, as a group over intake keys. Only the storage merges |
| L85 | Intake blocks: contacts, coverage in force, lines to quote (with a stale check), compliance PDFs | Keep | Same look. Contacts and coverage become pending entries that a person approves (P8, N3a; Q3). Ch. 6: the line chips become one pending "please shop" entry. Approving it goes through intake's intent service, which adds Shop with origin client and lapses the confirmation. Unticking never removes a Shop or Keep decision; staff see it on the entry |
| L86 | Broker of Record typed-name e-sign, or "on file from" | Keep | `intake.services.sign_bor` adds the link, IP and user agent |
| L87 | "Upload a document to prefill" | Simplify | The file is read as a staged job; values appear once staff apply them. Ch. 24: renamed "Upload a document and we'll fill this in" |
| L88 | Employee details: grouped people, typed cells. A prefill means "confirm, don't retype". Submit attests untouched prefills | Keep | Ch. 24: Submit stores one attestation on the link (`attested_form_version` and the time), not an entry per cell |
| L89 | SSN on the portal: masked to the last four; a mask is never accepted | Simplify | Never asked, shown masked (plan §3.8; Q2) |
| L90 | "＋ Add an employee / a dependent" (names required, up to 50 per request) | Keep | Ch. 12: added people stay pending. Census's default manager hides them from every read until a person approves or rejects them whole in the census queue |
| L91 | Questionnaires: the cascade, added rows, the blank carrier PDF, uploading a filled copy, the officer signature (held while answers are blank, with "Sign anyway"). A narrowed form takes no file or signature | Keep | The questionnaire app provides `portal_form`, `save_from_link` and `sign_from_link`. It plugs in after V2 (Ch. 16) |
| L92 | Auto-scan of an uploaded filled copy, polled every second | Simplify | Filed for staff to read, as the questionnaire section decided. This removes B2's cause |
| L93 | Document slots per kind and line, several files each, "Received", and slots for free-text asks | Keep | `documents.services.upload(source=client, link_id, slot)`, with the size cap and content screening (B12). Ch. 19: the portal names only files uploaded through that request (B22) |
| L94 | Census file upload and template download | Keep | The template is always blank (B3). Ch. 4: an upload starts a staged import, shown by L135 |
| L95 | Autosave: 1.5 s debounce, one save in flight, backoff up to 60 s, 429 retried, refusals in a card, never wipes, "Saved automatically" | Keep | `useAutosave`. Ch. 14g: bodies carry only changed slots |
| L96 | Compare-and-set: a base per field; conflicts; "keep theirs" or "use mine" | Keep | The base is required on every write. It is a version stamp, not an HMAC (B13) |
| L97 | Files and the BOR go only on Save or Submit | Keep | — |
| L98 | "Submit to Vantage ▸": warns what is missing, then thanks, or shows follow-ups | Keep | `first_submitted_at` is kept (B6) |
| L99 | A receipt after Submit | New | What went, by section, with the time (N1). Built last (Ch. 16) |
| L100 | Follow-up mode ("Submit for review ▸") | Keep | — |
| L101 | Threads: the 💬 mark, margin cards from 1200 px, "Ask a question", and why a sensitive item takes no question | Keep | One door: `POST portal/{t}/questions/` |
| L102 | "This is right": up to 100 per save; needs an open ask; never on a masked number | Keep | A `confirm: true` entry |
| L103 | Portal polling: first at 4 s, then 30 s backing off to 2 min. A changed form re-reads and keeps typing. `seen` after 5 s | Keep | Ch. 15: the form stamp covers `form_version`, blank, submitted, security and closed |
| L104 | Keys: Tab and Enter go to the next field, Shift goes back, a chip group is one stop, and Enter reaches Save, never Submit | Keep | `portalKeys.js` |
| L105 | "Nothing is needed from you right now". A lost deal stays readable, and its writes answer 410 | Keep | Archived deals answer 410 too |
| L106 | Footer "Stuck? Get help ▸", "Welcome back — N items left", "Updated by someone else on your team", "Link unavailable · Try again", post-submit notices | Keep | Help address from AgencySettings (P10) |
| L107 | Expired page | Keep | Ch. 11c: the 410 answer carries the agency's name, phone and email (plan §8.15). "Ask for a new link" mails the agency, never an owner |
| L108 | Commission and coverage intent are never shown to or written by the client | Keep | An allowlist test guards it. Ch. 6: the only intent-side write is L85's pending "please shop" entry. Never Keep, Leave off, `on_proposal` or commission |
| L109 | Anonymous scan-status messages | Drop | The client sees no reads (L87, L92) |
| L110 | Portal security: `no-store`, `no-referrer` and `noindex`; per-token throttles | New | Fixes B11 and B2. Ch. 11b, 14h, 15: explicit per-token rates; the global anonymous rate never applies. Logs drop `/api/portal/`. The questionnaire spec is the one cacheable response |
| L136 | Old `/b/<token>` links after cutover | New | Ch. 24: a "This link has moved" page with the agency's phone and email (Q12) |

### Background work and links to other modules

| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| L111 | Client uploads start readers automatically (the census mapping, staged; the intake reader), one per kind | Simplify | `ai.services.start(actor=None)`, after the PHI gate (B16; Q7). Ch. 4: needs a queued state from ai, which fixes B17 |
| L112 | Roster rebuild guard: 409, or force and re-point asks and notes by identity | Simplify | Ch. 12: census soft-removes members (`removed_at`) and restores them by identity. Notes keep their member, and a removed person's asks read "removed". No 409, no re-pointing, no hook |
| L113 | Deleting a census row by hand | Keep | Ch. 12: removal is soft, so nothing needs refusing (B9) |
| L114 | Removing a questionnaire row shifts the notes on later rows | Drop | Row ids are stable |
| L115 | Client versions and edit sessions on each portal save | Drop | Wave 1 |
| L116 | Activity feed derived from link stamps | Simplify | Rows are written as events happen. Ch. 13a–b: client saves coalesce per link (`review:save:<link>`). Submit and the first open get their own rows |
| L117 | Message drafts: request, follow-up, nudge, reply notice (counts only) | Simplify | Built on the server from AgencySettings, on click |
| L118 | Client responses column on the dashboard | Keep | `review.summary.facts`. Ch. 14b: pending counts per link come from census `summary()`; "ready" comes from link stamps |
| L119 | Agenda steps from review data (approve, review answers, follow up, answer questions, checklist asks) | Keep | The same facts, plus `rules/next.py` (Ch. 8) |
| L120 | The export check (D-143) reads client counts and open questions | Keep | Verdict changed from Simplify (Ch. 3). rfp gets a check-provider registry. Review registers its lines there: not reviewed, still typing, going back (tray drafts included), and questions open per form. The report and its `?ack=` digest stay whole on the server. New wording: "not in the file until approved" |
| L121 | Free-text asks: "＋ Add request" (label ≤120, note ≤300), edit, mark handled, remove. Each has its own upload slot. Implementation asks never ride a link | Keep | Intake's checklist, with stable ids, asked as `doc:custom:<id>`. Remove is soft |
| L122 | "Client sees: …" notes on checklist rows and census columns | Simplify | A client-audience note, shown as "From your broker:", on questionnaires too (N1) |
| L123 | Waiving a form drops it from links already sent; the BOR ask drops once a BOR is on file | Keep | Derived on read |
| L124 | File decisions: Accept, Wrong file (drafts a send-back), clear | Keep | `documents.services.set_review_state`. The slot is stored at upload, so clear and accept re-link the ask (B1). Ch. 4: on a client census file, Accept reads "Review and apply ▸". Applying the import marks the file accepted |
| L125 | "Read with Claude" on a client file | Simplify | Opens Work with Claude on the file. A renewal or quote goes to the quote reader |
| L126 | Work with Claude page context: counts only; claimant answers reported as "answered" | Keep | A provider registered with ai |
| L127 | The census agent keeps open asks | Defer | Census-turn writes are deferred (AI section) |
| L128 | Renewal revalidation: the banner, `preset=revalidate:<year>`, the filled scope, the prefilled template, re-signing, the Agenda step, `renewal_refresh`, and never carrying medical answers | Defer | Renewals are an open question (Q4) |
| L129 | Past-year read-only mode: tray, badges, ask controls and queue keys off | Keep | `deal.historical`, from deals |
| L130 | Roadmap item N2 (request owner, due date, nudge stamps); R7 (a log of every token access); R8 (alerts on failed tokens); R4 (SSN and date-of-birth encryption) | Defer | Not on the owner's list. R4 belongs to census and the platform. Ch. 11a: R7 is answered at the PHI gate (Q10). Until then, link stamps are the record |
| L131 | Usage tracking (about 30 calls, 55 keys) | Drop | plan §15 |
| L132 | Walkthrough guides, `data-guide` anchors, the seeded tray draft, live checks, the browser sweep | Drop | Tours and devtools |
| L133 | Words twinned in Python and JS, with parity and source-reading tests | Drop | Words come from `/api/meta/` and the portal payload (Ch. 9) |
| L134 | Django admin for links | Simplify | A read-only list |

## L.4 Data flow (in and out, by model, field or function)

**Reads in**
- **deals:** `Deal` (stage, `archived_at`, `historical`, effective date, owner); `Contact` (with roles); `AgencySettings` (name, phone, email, logo, colour); `clock`.
- **documents:**
  - `Document` (kind, lines, source, `link_id`, `slot`, `review_state`);
  - `kinds` (label, PHI, accept);
  - `upload` and `set_review_state`.
- **ai:** `start`; a queued state; staged jobs per deal; the page-context registry.
- **intake:**
  - `answers`, `sources` and `client`; `form.py`;
  - readiness;
  - checklist rows, missing documents and free-text asks;
  - `bor_on_file`;
  - `CurrentCoverage`, without commission or intent;
  - the intent service.
- **census:**
  - `Member.data`, `sources` and `client`, through the default manager;
  - column specs; `summary(deal_ids)`; `client_entries`;
  - the blank template and the staged import.
- **quotes:** whether quote plans exist, and whether enrollment is typed.
- **questionnaire:**
  - `answers`, `client` and `rows`;
  - `spec_payload`, `sensitive_slots`, `gate_slots`, `progress`, `takes`, `review_items`, `portal_form`.
- **rfp:** the chosen carriers' required census columns; the check-provider registry.

**Writes out**
- **Its own rows:** `ClientRequest`, `ClientLink`, `ReviewNote`, `Seen`.
- **Owners, only through their services:**
  - pending entries in `Intake.client`, `Member.client` and `Questionnaire.client`;
  - pending added people;
  - signatures and the BOR;
  - approvals into `answers` and `data`, with the source `{origin: client, link}`;
  - "please shop" approvals, through the intent service.
- **documents:** client uploads and their review state.
- **ai:** jobs with no actor.
- **deals:** contacts, and Activity rows (area `review`).

**Read by others**
- `review.summary.facts(deal_ids)`: Agenda (steps, work queue, client responses) and Overview (outreach rows).
- `review.rules.next`: Agenda's review steps.
- `badges/`: the nav.
- `overlay/`: asked chips, the 🔒 marker and ↩ on the section screens.
- `TrayContext`: the section screens and the Overview card.
- rfp's export check and ai's page context, through providers that review registers.

## L.5 Bugs and pain points found (with file evidence)

**Bugs**
- **B1. "Wrong file" on a free-text ask strands its send-back.** It empties `fulfilled_by`. A later clear or accept falls to `doc:other`, so the send-back stays and the ask is never re-linked. Evidence: `review/uploads.py` (`decide`, `ref_of`, `_take_back`).
- **B2. Autosave and the 1 s questionnaire scan poll share the 200/h anonymous budget.** A 429 kills the watch. Evidence: `backend/settings.py`; `BenefitsClientPortal.jsx` `startQScanPoll`.
- **B3. The portal's census template hands over the prefilled roster.** It ignores blank links and narrowing. Evidence: `views/portal.py` `ClientCensusTemplateView`.
- **B4. Raw query ids give 500s.** Evidence: `views/requests.py` `ClientReturnsView`; `notes._take_off_targets`.
- **B5. Undefined CSS tokens.** `--accent` has no fallback. `--red`, `--line` and `--border-strong` are undefined. Evidence: `styles/reviewrequest.css` lines 113, 210, 376, 543, 1593, 1608.
- **B6. Times are off.**
  - Submit overwrites `submitted_at`.
  - Expiry uses server time.
  - `earliest_today` treats the US as UTC−12.
  - Evidence: `market/client_request.py`.
- **B7. One draft per item is not enforced.** There is no constraint, and `_queue` reads then writes. Census "missing" and "all" asks re-ask items already out. Evidence: `review/notes.py`, `models/review.py`.
- **B8. Partial writes.**
  - `apply_client_payload` can answer 400 after writes have landed.
  - `ReviewEnterView` runs two writes with no transaction.
  - `extend_ask`'s full `save()` can undo Blank.
  - `updateLinks` fires take-offs in parallel.
  - Evidence: `views/portal.py`, `views/review.py`, `client_request.py`, `RequestPage.jsx`.
- **B9. Deleting a census row by hand has no guard.** Its asks drop and its notes read "gone". Evidence: `views/market.py` `CensusRowDeleteView`.
- **B10. Archived deals keep live links.** Evidence: `client_request.asking_refusal`; `views/portal.py`.
- **B11. Portal data responses can be cached.** Only the stamp sets `no-store`. Evidence: `views/portal.py`.
- **B12. Uploads are checked only by extension and the 25 MB limit.** Evidence: `views/portal.py` `MAX_UPLOAD_MB`.
- **B13. Compare-and-set is optional, and its bases hang on `SECRET_KEY`.** Evidence: `market/portal_base.py`.
- **B14. Almost no link or note write locks a row.** Evidence: `client_request.py`, `notes.send_tray`.
- **B15. `set_expiry` changes the policy snapshot's `policy_slides`.** Evidence: `client_request.py`.
- **B16. A client's census PDF on a deal with no roster is applied unreviewed.** Evidence: `views/portal._start_client_reads`.
- **B17. An upload that arrives while a read of its kind runs is never read.** Evidence: `views/shared._autostart_reader`.
- **B18. By default, medical and claimant send-backs are refused everywhere.** Verification is off. Evidence: review README, `VERIFIED_ONLY`.
- **B19. No quote-first awareness.** After quotes arrive, intake items required to market still rank as "blocks a carrier", and "No census on file" ranks low. Evidence: `review/board.py`.
- **B20. Any link holder can view without an open being recorded.** Adding `?preview=1` or `?refresh=1` skips it. Evidence: `views/portal.py` `_is_preview`, `_is_refresh`, `ClientViewView.get`.
- **B21. "＋ Add a person" saves every contact as an HR admin.** That can pass intake's contacts gate. Evidence: `useLinkBuilder.js` `addPerson`; `market/intake.py` `contacts_ok`.
- **B22. The portal shows the newest file name of each kind on the whole deal, staff uploads included.** Evidence: `views/portal.py` `latest_name`.

**Pain points**
- **P1. GETs that write:** `ClientViewView` (`ensure_*`, job reaping), the scan poll, `intake_board`.
- **P2. Heavy hot paths.**
  - `board_facts` runs on every deal page and again per section bar.
  - The request page is rebuilt on every stamp move, with a strip per carried cell.
  - `_questionnaire_question` is N+1.
  - Each autosave slides the expiry, re-posts every contact and versions three surfaces.
- **P3. Layering inversions.**
  - Services import views.
  - Intake, census and questionnaire call review.
  - The export check imports review.
  - The Waiting lane comes from `serializers/overview.py`.
- **P4. Size.**
  - `notes.py` is 2,552 lines.
  - The portal is one component of about 2,370 lines, with about 60 `useState`s.
  - `RequestPage` is 1,749 lines and `useLinkBuilder` 1,485.
  - `views/portal.py` has about 30 unused imports.
- **P5. Previews mint real links and roll them back.** Anything outside the database leaks, and sequence ids are spent. Evidence: `preview.py`, `new_link.py`, `link_form.py`.
- **P6. Twinned rules.**
  - Words exist in Python and JS, pinned by tests that read source.
  - The AI buckets exist twice.
  - D-208's six rules are drawn in three to five places each.
  - Agenda's follow-up wait and the board's Next disagree. Evidence: `tasks/steps.py` `_ask_steps`.
- **P7. Fragile note keys.** Notes key on a questionnaire row's index, and census cell ids die on every rebuild.
- **P8. Weak trust.**
  - Nothing is mailed, so `sent_at` is only a claim.
  - The BOR is a typed name.
  - The client writes contacts, coverage, lines and the BOR straight onto live rows (N3a).
  - Add people creates roster rows directly.
- **P9. Staff detection assumes a DRF token in localStorage.** Evidence: `_staff_may_open`, `_is_staff_preview`.
- **P10. Hard-coded brand and help address.**
- **P11. Any user can act on any link id.** This is acceptable in 2V, where every user sees every client.
- **P12. The old container clock stepped backward under load.** Evidence: README trap. This is a hosting quirk. 2V keeps `deals/clock` and orders our own stamps by time, then id (Ch. 22).
- **P13. Roadmap items still open:** N1, N2, R4, R7 and R8.

## L.6 New design: Django app, models, services, selectors, endpoints, frontend, styles, tests

**Django app.** `review` sits after rfp: … quotes → questionnaire → commission → proposals → rfp → review → agenda → overview.
- **What it imports:** accounts, deals, documents, ai, intake, census, quotes, questionnaire and rfp.
- **The public side:** `review/portal/`. It writes only through the owners.
- **Nothing to the left imports review:**
  - member and questionnaire row ids are stable, so notes never move;
  - intake's portal lock is computed here, from intake's sources and review's reopened asks;
  - rfp's export check and ai's page context call providers that review registers at `apps.ready()`;
  - owner screens get marks from `overlay/` through a React context;
  - nudges live on the link.

**Models (`review/models.py`)**
- **`ClientRequest`:**
  - fields: deal, asks, message (≤1,000), `created_by`/`at`, `closed_at`/`by`, `close_reason`;
  - `form_version`: every change to the asks bumps it;
  - asks shape: `{"intake": {"scope": "selected|missing|required|all", "keys": [], "blocks": ["contacts","coverage","lines","bor","files"]}, "census": {"scope": "none|selected|blank|missing|all", "columns": [], "cells": [[member_id, "column"]], "file": false}, "questionnaires": [{"form": "<key>", "mode": "online|upload", "picks": {"fields": [], "blocks": []}}], "documents": {"slots": ["invoice@medical", "claims", "custom:7"], "missing": false}}`.
- **`ClientLink`:**
  - request; `token` (unique, `token_urlsafe(32)`); contact (`deals.Contact`, SET_NULL; Ch. 20); name and optional email snapshots;
  - `security` (link or pin), `pin_hash`, `pin_tries`, `pin_version`; `blank`; `slides`;
  - `expires_at`; `ceiling_at` (created plus 30 days); `nudge_on`, `nudge_done_at`;
  - `sent_at`, `opened_at`, `last_opened_at`, `open_count`, `first_submitted_at`, `submitted_at`, `attested_form_version`, `last_saved_at`;
  - `revoked_at`/`by`, `created_by`/`at`.
- **`ReviewNote`:**
  - deal; surface;
  - key: an intake key, a census column, `<form>:<slot>`, a form key, a document slot, or `census_file`;
  - member (`census.Member`, PROTECT; members are only soft-removed; Ch. 12);
  - request and link (SET_NULL); parent;
  - audience; kind; text (≤1,000); author (null for the client); time; `sent_at`; `resolved_at`/`by`;
  - a partial unique constraint: one open ask or send-back draft per (deal, surface, key, member), with nulls not distinct.
- **`Seen`:** deal, user or link (a check constraint), `seen_at`, two partial unique constraints. It only moves forward.
- **Gone:** SurfaceSetting, the linkguard tables, nudge DealTasks and the policy snapshot.

**The owner contract (intake, census, questionnaire).** One shape, so review has one code path.
- **The entry.** A `client` JSON on the owner's row, keyed by slot: `{"value": "", "confirm": false, "link": 41, "at": "", "status": "pending|approved|rejected|replaced", "by": 3, "decided_at": ""}`.
  - Census and questionnaire entries add `prior`, because their values never go into Activity.
  - Intake reverts an approval through the foundation's Activity before/after (Ch. 13c).
- **`save_client(deal, link_id, entries, bases)`:**
  - cleans values by the owner's rules and ignores unchanged ones;
  - checks every base;
  - refuses all or nothing;
  - never touches `answers` or `data`.
- **Decisions:** `approve_client`, `reject_client` and `revert_approval`. A typed write closes the pending entry as `replaced` (Ch. 13d).
- **`client_entries(deal)`:** one query.
- **One rule (Ch. 2).** Rollups, readiness, gates, exports and printed PDFs read stored values only. This holds for every owner, the questionnaire's `effective()` included (Q11). A slot is missing when its stored value is blank and no pending entry exists.
- **Census also (Ch. 5, 9, 12, 14b):**
  - members are soft-removed (`removed_at`) and restored by identity;
  - a default manager hides removed and pending-added people;
  - added people are approved or rejected whole;
  - `summary(deal_ids)` runs in a fixed number of queries. It gives required blanks by column, errors, open AI warnings, pending entries by link and pending added people. Census may keep it as a per-deal row written with each census write, which Agenda also wants; a test rebuilds it from the members;
  - a spec for each asked column;
  - a staged import whose apply marks a client file accepted.
- **Intake also (Ch. 5, 6):**
  - pending contacts and coverage;
  - the line chips as one "please shop" entry, approved through the intent service;
  - `sign_bor`, which records the link, IP and user agent;
  - free-text asks with stable ids;
  - missing checklist documents in fixed queries.

**Pure rules (`review/rules/`, tested table by table)**
- `items.py`: `phase`, `change`, `state`, `differs`, and `ready_why` (submitted after the last save, or idle 24 h).
- `requests.py`: `request_state`, and `carries(asks, ref)`, the one "what a link asks" rule. The portal whitelist, rail, tray and board all read it.
- `policy.py`: `floor(asks)`, by what the page shows; `expiry(day)` in agency time; `slide`, at most once a day; `nudge_open`.
- `next.py`: `rank`, and the predicates Agenda imports.
- `form_plan.py`: the Ask card and Update link plans, and their dry runs.
- `tray.py`, `cas.py`, `portal/progress.py`.

**Services (`review/services/`).** Each locks the request row, then its links in id order.
- `requests.py`: `create_request`, `add_people`, `close`.
- `form.py`: `change_form`, `join`, `update_links`, one transaction per request.
- `link_actions.py`: a dispatch table for the PATCH actions, plus `record_open`.
- `notes.py`: add, reply, resolve, queue, remove drafts. `send_tray` uses one transaction per destination.
- `decisions.py`: approve, reject, enter and upload state, each one transaction through the owner.
- `seen.py`.
- `portal/save.py`: one transaction. It whitelists by `carries` and validates every owner first. It then writes intake, questionnaires by id, members by id, then link stamps, in the staff services' lock order.

**Selectors (fixed queries)**
- `badges`, which includes the tray's count and destination.
- `board`, `queue`, `overlay`, `tray`, `stamp`.
- `request/`, one per pane; the census pane is paged.
- `summary.facts(deal_ids)`. Per deal:
  - request states, `first_sent_at`, what each asks, and names;
  - pending and ready counts by surface;
  - open questions and the oldest;
  - the response state: waiting, answering or answered; when, how, and whose link;
  - nudges;
  - tray size.

**Endpoints.** Ids are parsed as integers, and a bad one answers 400 (fixes B4).

| Method | Path | Purpose |
|---|---|---|
| GET | `deals/{id}/review/badges/`, `board/?scope=` | Counts; lanes, Next, questions |
| GET | `…/review/queue/?surface=&form=&group=&phase=&link=&page=` | Client answers, 50 a page |
| GET | `…/review/request/?pane=&page=`, `census-blanks/`, `overlay/?surface=`, `messages/?link=&kind=` | The request page by pane; blanks for edit mode; section marks; a message draft |
| GET, POST | `…/review/stamp/`, `seen/`, `tray/`, `tray/remove/`, `tray/send/` | Polling, the last look, drafts, the send plan |
| POST, PATCH, DELETE | `…/review/notes/`, `notes/{nid}/` | Note, reply, resolve, delete a draft |
| POST | `…/review/approve/`, `reject/`, `enter/`, `uploads/{doc}/`, `preview/` | Decisions; their form for a draft ask (writes nothing) |
| POST | `…/review/requests/[?dry_run=1]`, `requests/{rid}/form/[?dry_run=1]`, `requests/{rid}/people/`, `requests/{rid}/close/`, `links/update/` | Builder, Ask card, access, close, Update links |
| PATCH, GET | `links/{lid}/` `{action}`, `links/{lid}/preview/` | mark_sent, unsend, extend, revoke, restore, expiry, address, new_pin, security, blank, nudge; View as client |
| GET, POST | `portal/{t}/` (records the open), `verify/`, `save/`, `files/`, `submit/`, `people/`, `questions/`, `sign/`, `stamp/?since=`, `seen/` | Public portal (AllowAny) |
| GET | `portal/{t}/census-template/`, `questionnaires/{form}/blank/`, `questionnaires/{form}/spec/`, `logo/` | Files; the cacheable spec |

**Portal security**
- **Throttles:** no authentication classes. A throttle keyed by token, with explicit scopes: `portal_read` 300/h, `portal_write` 3,600/h, `portal_poll` 600/h, and `portal_pin` 10/h on top of the 5-try lock. The global anonymous rate never applies (Ch. 14h).
- **Status codes:**
  - unknown 404;
  - expired, revoked or closed 410, carrying the agency's contact;
  - writes on a lost or archived deal also 410;
  - 428 until the PIN is given.
- **Verification:** a TimestampSigner token `{link, pin_version, first}`. It lasts 1 h idle under an 8 h ceiling and is re-issued with each response.
- **Staff:** the guard reads Django's session user. A staff session sees the note and records no open; its writes answer 403 (Ch. 10).
- **Headers:** `private, no-store`, `no-referrer`, `noindex`. Only the questionnaire spec is `private, max-age` (Ch. 15).
- **GETs write nothing** except the open stamp.
- **Payloads are allowlisted:** no team notes, commission, intent, document ids, owner names, other deals, or files from outside the request.
- **Logs:** request logs and error reports drop `/api/portal/` paths (plan §11; Ch. 11b).

**Activity (area `review`; never values, member names or file names)**
- Recorded:
  - request created; link copied; first open;
  - client saves, coalesced per link; submitted;
  - client uploaded a <kind>; client asked a question;
  - N follow-ups sent; closed with its reason;
  - revoked, restored, extended;
  - a client file accepted or marked wrong.
- The owners record approvals.
- Times come from `deals/clock`. Our own stamps that must be ordered sort by time, then id (Ch. 22).

**Frontend**
- **`deal/review/`:**
  - `ReviewTab`, `api.js` (query keys `['deal', id, 'review', area]`), `usePollStamp`;
  - `board/`, `queue/`, `thread/`;
  - `request/`, with panes, `edit/`, and `builder/` holding a reducer;
  - `tray/`: `TrayProvider`, `TrayBar`, `TraySnippet`;
  - `section/`: `SectionHost`, `SectionBar`.
- **`deal/shared/reviewContext.js`:** `TrayContext` and `ReviewOverlayContext`.
- **`valuereview/ReviewQueue.jsx` and `keys.js`:** shared with the Documents station.
- **`portal/`:**
  - `PortalPage`, `PortalGate`, `PortalShell`, `TodoRail`, `SharedCard`;
  - `IntakeSection` (with the company card), and `blocks/` (Contacts, Coverage, Lines, BorSign, Files);
  - `PeopleSection`, `CellInput`, `AddPeople`;
  - `QuestionnaireSection`, `DocumentSlots`, `CensusFile`;
  - `Threads`, `FollowUps`, `SubmitBar`, `Receipt`, `ConflictNote`, `Expired`, `Moved`;
  - `useAutosave`, `usePortalStamp`, `portalKeys`;
  - `portalApi`: its own axios instance, sending `X-Link-Verification`.
- **Routes:** `/portal/:token`, `/preview/links/:linkId` and `/b/:token` sit outside `AppLayout`.
- **One `CellInput` per census type,** taking a column spec as a prop. Staff screens pass specs from `/api/meta/`; the portal passes its payload's (Ch. 9). The grid, portal, edit mode and rail share it, which retires D-208's copies.
- **File size:** every file stays under 300 lines.

**Stylesheets** (copied verbatim, split into files of at most 300 lines, class names unchanged)
- `rr-*` (board, queue, request, rail, cart, cards, link, builder, settings card) go into `styles/review/*`.
- Portal: `bnf-portal-*`, `bnf-todo-*`, `bb-portal-*`, `lg-*`, `bnf-save-problem`.
- Board and nav: `bnf-board-*`, `bb-nav-badge-*`.
- Census review: `bnf-review-*`, `bnf-send-*`, `bnf-ireview-*`.
- Shared with the questionnaire: `bnf-q-chip`, `bnf-q-mark`. Also `.btn-violet`.
- **Undefined tokens (Ch. 23).** Each use is pinned to what the old screen rendered, so the foundation's token fix cannot restyle these screens:
  - `var(--accent)` with no fallback becomes the inherited colour (currentColor on borders);
  - `--red` becomes #c0392b;
  - `--line` becomes #d8dde6;
  - `--border-strong` becomes `var(--border)`.

**Tests to write**

Backend: behavioural pytest.
- **Rules:** each pure function, table-driven: quote-first ranking with the census item; agency time and the ceiling; the floor by what the page shows; form plans; `carries`.
- **Links:**
  - create refusals; a contact with no email is accepted;
  - a nameless link can hold a PIN; adding a person needs a role;
  - the PIN is shown once, hashed, and locked after five tries; New PIN ends tokens;
  - take-off refusals by name;
  - revoke survives extend and asks; restore stays within the ceiling;
  - close makes every sibling answer 410;
  - undoing Mark sent is refused once the link was opened;
  - the level is never below the floor, never raised by itself (409), and never lowered while a sensitive ask is open;
  - two concurrent asks leave one draft.
- **Portal:**
  - 404, 410 (with the agency's contact, no owner) and 428;
  - exactly the allowlisted keys;
  - SSN masked and never asked; the template blank;
  - a GET writes only the open, and a re-read within 30 minutes adds none;
  - `?preview` and `?refresh` change nothing;
  - a staff session records no open and gets 403 on writes;
  - saves are all or nothing, and unchanged slots write nothing;
  - stale bases conflict, while the same value twice does not;
  - "This is right" confirms;
  - questions need a real slot, and a PIN when sensitive;
  - line ticks never remove Shop or Keep;
  - `first_submitted_at` is kept; one attestation per Submit;
  - headers on every response, and only the spec is cacheable;
  - polling never throttles a save.
- **Review:**
  - readiness after submit, after 24 h idle, and after a resave;
  - Approve ready takes only submitted answers unless the idle tick is on;
  - a typed write marks the entry `replaced`, with no rejection shown;
  - pending entries feed no rollup, readiness, export or PDF;
  - Missing excludes pending slots, and Ask all skips asked items;
  - an ask on an ended link reads missing again;
  - Enter it as relay versus typed, where an unchanged value writes nothing;
  - B1's re-link;
  - a removed person keeps their notes, their asks read removed, and re-import restores them;
  - the export-check digest includes review's lines;
  - applying a client's census import marks the file accepted.
- **Facts and badges:** the same query count for one deal and for four.
- **Activity:** no values or names; saves coalesce per link; one row for the open.

Frontend: Vitest on tray grouping, filters, the autosave queue, portal counts and the key maps.

**Build order.** Review never waits for the questionnaire (Ch. 16).
1. V1: models, rules, link services, a minimal New link, the Waiting lane, `summary.facts`.
2. V2: the portal for intake, census and documents.
3. V3: queues, approvals, badges, section bars, the export-check provider.
4. V4: tray, notes, threads and the request page.
5. V5: the full builder, Ask card, settings card, People & links, edit mode and the comment margin.
6. V6: questionnaires, through `portal_form`, once that section ships.
7. V7: reads started by client uploads (after the PHI gate), then the receipt.

## L.7 Open questions for Daniel

1. **Second factor.** In August 2026 you asked that every send-to-client link verify the person. Plan §7.12 asks for a second factor on any census or documents link. The old app never switched one on.
   - The working default is a PIN you give by phone. It applies when the page shows census people or questionnaire answers, and to medical or claimant send-backs.
   - Upload-only asks (a census file, documents) and intake open with the link alone. So a quick census ask on a quote-first deal needs no PIN.
   - Is that enough, or should every link need a PIN?
2. **SSN.** 2V never asks for it and shows it masked. The old portal could ask for blank SSN cells. Keep "never asked"?
3. **Contacts, coverage and lines from the client.** Should they wait for staff approval (the working decision), or land directly as before?
4. **Renewals.** If they are in scope, L128 comes back: the revalidation loop, the prefilled template, re-signing, BOR on file from earlier years, and never carrying medical answers.
5. **Link life.** Keep 7 days that slide on save, under a 30-day ceiling (the old app), or use plan.md's 14 days?
6. **Admin switches.** Do admins need per-form on/off switches or raised floors, or are fixed rules enough?
7. **Client uploads.** Should the census mapping and the intake read start automatically after the BAA, or only when staff click?
8. **Sending.** Is copying the link still how it is sent? The answer decides emailed codes, nudges, reply notices, and whether recipients need an email.
9. **Partition mode and column assignment.** Confirm they can go.
10. **Access log (R7).** Before real PHI, must every open, save and submit be logged with IP and browser? Or are the link's time stamps enough?
11. **Unapproved answers in files.** The old app printed the client's unapproved answers on carrier census files and questionnaire PDFs, with a warning. 2V prints only approved values. Confirm.
12. **Cutover.** Should open requests in the old app be closed first, or should it stay read-only until they lapse? Old `/b/` links will show "This link has moved".
