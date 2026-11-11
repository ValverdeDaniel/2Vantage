# Part A — Platform foundation

[← Porting plan](README.md)

**What it is:** everything every module stands on:
- sign-in and roles;
- the dashboard (home);
- creating a deal;
- the deal workspace shell (sidebar, journey, Claude strip, drawers);
- stages, archive, next action and journey;
- how values are stored and marked;
- version history and edit sessions;
- background jobs;
- notes, agency settings;
- the look (tokens and stylesheets).

## A.1 Files read, in order (one line each)

**Rules and READMEs**

| File (lines) | What it is / what it taught |
|---|---|
| `CLAUDE.md` (114) | House rules: layered values, version and edit-session rules, token links, import directions. |
| `benefits/README.md` (394) | Module map, cross-module seams, frozen import paths, performance rules. It says 91 routes; the real count is 257. |
| `benefits/CLAUDE.md` (120) | Data contracts, the version write protocol, stage and lost rules, mock seams. |
| `users/CLAUDE.md` (80) | Roles, access flags, known sign-in defects. |
| `frontend/CLAUDE.md` (99) | API barrel, CSS traps, route and anchor contracts, store rules. |
| `docscan/CLAUDE.md` (103) | Job heartbeat and reaper rules, file serving. |

**Models**

| File (lines) | What it is / what it taught |
|---|---|
| `benefits/models/__init__.py` (79) | Re-exports all 51 benefits models. |
| `benefits/models/case.py` (1,878, read in full) | Field registry model, `BenefitsCase` and its metric methods, the three value-layer mixins, `CaseField`, documents, contacts, coverage, agency, chat, notes, jobs, `DataVersion`, `EditSession`, `CaseDocumentEvent`. |
| `models/market.py` (706) | Census and request models (outline; CensusRow and CensusCell in full). |
| `models/pipeline.py` (621) | `Plan` and `PlanValue` in full; the rest from docstrings. |
| `models/questionnaire.py` (148) | `QuestionnaireResponse`, `QuestionnaireAnswer`. |
| `models/radar.py` (406) | Client through ReminderResolution. |
| `models/review.py`, `models/tasks.py`, `models/unleashed.py`, `models/guide.py` (159/110/84/89) | Outlines. |

**Rules and services**

| File (lines) | What it is / what it taught |
|---|---|
| `benefits/registry.py` (632) | The frozen seed lists. |
| `benefits/migrations/` (100 files) | 11 of them import `benefits.registry`. |
| `benefits/lines.py` (197) | 27-line vocabulary and four per-line maps. |
| `benefits/stages.py` (118) | Stage ladder, `advance`, `sync_stage`. |
| `benefits/archive.py` (188) | Archive and restore, and the "live" read rule. |
| `benefits/renewal.py` (947) | Renewal carry and start warnings. |
| `benefits/versions.py` (2,589) | Snapshots, hashing, record and baseline, edit sessions, restore and guards. |
| `views/versions.py` (552) | Version, history and edit-session endpoints; `note_write(s)_or_409`. |
| `serializers/versions.py` (156) | History-rail payloads. |
| `benefits/history.py` (384) | Documents change-history feed, grouped by person in 30-minute spans. |
| `market/value_origin.write_hand_edit` | The one hand-edit writer. |
| `benefits/signals.py` (71) | Deleting a row deletes its file. |
| `demo_data.seed_case_fields` | Seeds the deal's account fields. |

**Views, payloads, URLs**

| File (lines) | What it is / what it taught |
|---|---|
| `serializers/case.py` (261) | List row, `summary_payload`, the deal payload. |
| `serializers/__init__.py` (87), `serializers/primitives.py` (360) | Barrel; document, field and job payloads. |
| `serializers/journey.py` (557) | `next_action_for`, `journey_payload`, prefetch and batch helpers. |
| `views/cases.py` (1,256) | Create, detail and PATCH, documents, case fields, notes, confirm, review, agency. |
| `views/shared.py` (297) | `_get_case`, prefetch sets, `_hand_edit_target`, `_confirm_value`. |
| `benefits/urls.py` (362), `backend/urls.py` (31), `users/urls.py` (25) | Every route; HTTP methods taken from every view class. |
| `serializers/radar.py` (814) | The work-queue feed row shape. |

**Jobs and settings**

| File (lines) | What it is / what it taught |
|---|---|
| `docscan/jobs.py` (189) | Reaper, progress writer, keepalive. |
| `benefits/ai/extraction.py` (846) | Job dispatcher: reap, running job, enqueue or start, start next queued. |
| `backend/settings.py` (489) | Every flag. |
| `backend/middleware.py` (26) | Gzip for JSON responses. |
| `backend/health.py` | Health check. |

**Users**

| File (lines) | What it is / what it taught |
|---|---|
| `users/models.py` (229) | `UserProfile`, `RoleAccess`, `PasswordResetToken`. |
| `users/permissions.py` (88) | Module gates. |
| `users/access.py` (530) | Role presets, modules, forced and fail-closed cells. |
| `users/views.py` (455), `users/serializers.py` (247) | Login, profile, user management. |
| `referrals/permissions.py` | IsProducer, IsAdmin, IsDeveloper. |
| `users/signals.py`, `users/apps.py` | Auto-created profile, memo reset. |

**Frontend shell (`frontend/src/…`)**

| File (lines) | What it is / what it taught |
|---|---|
| `main.jsx` (45) | Stylesheet load order. |
| `App.jsx` (368) | Every route; the pages without the app chrome. |
| `services/api.js` (28), `services/api/core.js` (403), `benefitsShared.js` (423), `benefitsRadar.js` (88) | How calls are made: token header, 401 → login. |
| `contexts/UserContext.jsx` (114), `EditSessionContext.jsx` (205), `GuideContext.jsx` (338), `BenefitsHomeContext.jsx` (123) | User, edit sessions, guides, home cache. |
| `RequireModule`, `RequireRole`, `RequireAuth`, `RoleRedirect`; `utils/home.js`, `utils/chromeless.js` | Route guards and the landing rule. |
| `components/Navbar.jsx` (210) | The top bar. |
| `shared/CaseWorkspace.jsx` (1,346, read in full) | The deal workspace. |
| `claudePages.js` (112); `useDealTabStore.js`, `useDealJobStore.js` (heads) | Per-page Claude wiring; hand-written per-deal stores. |
| `CaseOverviewTab.jsx` (imports); `overview/` listing | The Overview tab's parts. |
| `JourneyStepper.jsx` (61), `NewCase.jsx` (346), `CasesDashboard.jsx` (532) | Journey stepper, new deal page, home. |
| `shared/home/` (`homeRows.js` 287, `WorkQueueTable.jsx` 160, `NewClientsTable.jsx` 66, `HomeFilters.jsx` 184, `HomeCells.jsx` 244, `PlanTray.jsx` 96) | The home tables and filters. |
| `utils/download.js` (88), `utils/format.js` (198) | Downloads and formatting. |

**Styles**

| File (lines) | What it is / what it taught |
|---|---|
| `App.css` (4,357) | Tokens, section index, core rules. |
| `index.html` | Fonts. |
| `styles/*.css` (35 files, 23,053 lines) | Sizes. |
| `benefits.css` (6,275) | Head and section index. |
| `navbar.css`, `benefits-journey.css` | Heads. |

**Tests and specs**
- **Tests (class and test names):** `case_tests`, `versions_tests`, `archive_tests`, `implementation_tests` (stage ladder), `ai_tests` (job reaper), `radar_tests` (work queue), `docscan/tests`, `users/tests.py`; the source-reading test classes were counted.
- **Specs:** `PlanningDocs/Benefits/decisions.md` D-024; `PlanningDocs/Platform/audit-trail-and-versioning.md`.

## A.2 Old data model, in brief

**Deals and clients**
- **`BenefitsCase`** — the "deal", one employer-year:
  - Facts: name, stage, renewal date, requested lines, commission rates.
  - JSON configs for proposal, close-out, RFP, implementation and guide.
  - Fields: client guidance for Claude, AI budget, the Claude table lock, coverage-confirmation hash, BOR signature, marketed and lost stamps, carried (what a renewal copied), client-fold provenance, archive stamps.
  - Metric methods for proposal, census, hub and intake.
- **`Client`:** the employer across years — owner, service owner, primary contact, logo and brand colours, archive stamps.

**How values were stored**
- **Layered values:**
  - `CaseField`, `PlanValue`, `CensusCell` and `QuestionnaireAnswer` store one row per value.
  - Effective value = edited ?? client ?? extracted.
  - Each value row carries:
    - a confirmation (`confirmed_value/by/at`);
    - a review mark (ignored/check with its value);
    - origin stamps (scan, import, carry, seed, typed, prefill; edit kind hand/approve/relay);
    - the source location.
  - A mark stops applying once the value moves.
  - Status: missing/na/client/low/high.
- **Field definitions:** `BenefitFieldDef` rows (85 plan fields, 45 census), seeded from the frozen `registry.py` by 11
  migrations.

**History and locks**
- **`DataVersion`:** append-only snapshots per surface (proposal, census, intake, questionnaire), with a content hash
  and 17 origins.
- **`EditSession`:** one open editor per surface — the lock and the attribution.

**Jobs**
- **`ExtractionJob`:**
  - kind (quote, census, intake, rank, qform, audit, correct, work), status, pct, log, params, mode (apply/staged),
    result, error, heartbeat;
  - one running per deal, the rest queued.

**Other models, one line each**

| Model | What it holds |
|---|---|
| `CaseContact` | 8 roles; primary flag. |
| `CoverageLine` | Current coverage per line with commission. |
| `CarrierTemplate` | A carrier's census file layout. |
| `AgencyProfile`, `AgencyCoverImage`, `AgencyTeamMember` | The firm. |
| `AdvisorMessage` | Chat turns: scan / advisor / unleashed threads. |
| `CaseNote` | Kinds, pinned. |
| `MarketingAttestation`, `ClientAskItem` | Checklist state and custom asks. |
| `CensusRow`, `CensusCell`, `CensusImport`, `CensusFieldRequirement` | Census. |
| `BenefitsClientRequest`, `BenefitsClientLink`, `ValueReviewBatch`, `ReviewNote`, `ReviewSeen` | Requests, links and review. |
| `Plan`, `PlanValue`, `HubSubmission`, `ProposalShareLink`, `ProposalSelection`, `CloseoutDelivery`, `AdvisorFilterSet`, `ProposalTemplate`, `BundleTemplate` | Quote to close. |
| `QuestionnaireResponse`, `QuestionnaireAnswer` | Questionnaire. |
| `ClientPlanYear`, `ClientEvent`, `ReminderResolution`, `DigestLog`, `ReminderRuleConfig`, `ReminderSettings`, `CustomReminderRule` | Radar and reminders. |
| `GuidePhoto`, `GuideExport` | Benefit guide. |
| `DealTask`, `StepMark` | Task mode (the Agenda). |
| `UnleashedCopy`, `UnleashedFile` | The Claude Unleashed sandbox. |
| `UserProfile` | Role, `claude_direct`, `commissions_access`, `agents_access`, `is_developer`. |
| `RoleAccess`, `PasswordResetToken` | Role matrix cells; password resets. |

## A.3 Functionality inventory and verdicts

### Sign-in, roles and access

| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| A1 | Login, logout, change password, request and reset password, profile | Keep, **fixed** (the old tokens never expired, survived a password change, and `PATCH profile` returned 500) | Django sessions plus CSRF (built in M0); Django's password views with `validate_password`; reset by an admin until Microsoft 365 sign-in |
| A2 | Role matrix: 9 presets × 11 modules, editable on Dev ▸ Roles | Drop: the new app is benefits-only | Two kinds: admin (`is_staff`) and producer |
| A3 | Per-person flags | Simplify | `claude_direct` (agent turns that write the plan table, Opus, budget override) and `commissions_access` (the commission book) on a `Profile`, served on `/api/auth/me/`; `is_developer` and `agents_access` dropped with their modules |
| A4 | Module gating in routes (RequireModule) and on the server | Simplify | `RequireAuth`, `RequireAdmin`, `RequireCommissions`; permission classes to match |
| A5 | Manage Users page | Simplify: Django admin (rule 6) | — |

### Top bar and home

| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| A6 | Top bar: fixed 56 px navy; links; username; Logout | Keep the look; links trimmed to modules in scope (Benefits, Commissions, Admin) | `AppShell` |
| A7 | Benefits home header (eyebrow, title, subtitle, ＋ New deal, Calendar) | Keep | — |
| A8 | Practice and story demo buttons; guide launchers; Reset demo | Drop: demo machinery; `seed_golden` replaces it | — |
| A9 | Home views New clients / Clients / Work queue (`?view=`), refresh chip, Archived link | Keep | `deals/selectors.home_feed`; the Work queue is detailed in Part I |
| A10 | Stat cards: New clients count, potential deal size total, client responses; Work queue cards (overdue, due this week, actions completed, sales this month) | Keep the cards with **real numbers**; Drop the decorative constant sparklines | `GET summary/` |
| A11 | Filters: type chips, "Responses first", due chips, client search with ranked dropdown, owner, stage, category, Clear | Keep | — |
| A12 | Work queue table columns (pick, client with avatar, deal size, type, next action chip, client response, stage/category with progress, due, owner, archive); Next step / All open steps; "Show N held until later"; Plan my day tray | Keep (detailed in Part I) | — |
| A13 | Client book (Clients view) and Archived page with Restore | Keep | `GET archived/` |

### Deals: creation, renewal, archive

| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| A14 | New deal page: two mode cards, "1 · Get to Market — start the intake" and "2 · Quote to Close — I already have carrier quotes" (the second opens Work with Claude, which creates the deal on the first upload); group name, renewal date, notes (becomes the first note) | Keep | `deals.services.create_deal`; the quote-first door in Part D |
| A15 | Renewal start from a client (`?client=`): banner, start warnings, carry checkboxes; referral prefill | Defer with renewals (open question A-Q1); referrals are out of scope | — |
| A16 | Renewal carry (documents, contacts, rules, checklist setup, coverage, intake values, sold plans as current, census and questionnaires on request; "values carry, assertions don't") | Defer with renewals; if in scope, one orchestrator calls each app's `carry_from(prior, new)` in its own savepoint and records failures in Activity (no silently swallowed errors) | — |
| A17 | Deal list endpoint (`GET cases/`) | Drop: only walkthrough guides call it | — |
| A18 | Archive and restore a deal or client; a sold deal refuses ("archive its client"); an archived client hides its deals; working lists show live rows only | Keep | `deals.services.archive/restore`; a `live()` queryset |
| A19 | Mark lost (reason) / reopen; lost is a label, not a lock | Keep (built) | — |

### Deal workspace shell

| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| A20 | Sidebar (232 px, sticky): ← Benefits, account name, description, renews date, ready chip, client block with year strip | Keep the look | Year strip deferred with renewals |
| A21 | Grouped nav: Overview, Agenda; **1 · Get to Market** Review & requests, Intake, Census, Questionnaire (only when the deal has a form), RFP, Commission; **2 · Quote to Close** Advisor, Proposal; **Shared** Documents. Plain-count badges; three-tone Review badge (violet, amber, rose); ↩ client returns; "?" open client questions | Keep for every tab in scope | `DealShell` |
| A22 | Close-out, Benefit guide, Implementation and Data Hub tabs | Drop from this build (not in Daniel's list). Data Hub's firm pages (team, covers, about) move to Django admin and feed the Proposal (Part J) | — |
| A23 | "Deal readiness" meters (Intake, Proposal, Census, Hand-off) | Keep Intake, Census, Proposal; Drop Hand-off (implementation) | Each app's `summary(deal)` |
| A24 | Journey stepper: 3 modules, 14 steps, states done/current/todo/skipped, module % | Simplify to Get to Market and Quote to Close; Implementation steps dropped; same look; quote-first deals skip module 1 | `deals/selectors.journey` |
| A25 | Claude strip on advisor, proposal, census, questionnaire and intake; Work with Claude button and drawer; review tray dock; toast | Keep (Parts D and L) | — |
| A26 | Tab in `?tab=` with deep-link parameters (`view`, `focus`, `form`, `claude=1`, `scan=`); an error boundary per tab | Keep | — |
| A27 | Hand-written per-deal stores (comparison, deal tab, jobs, review badges, tray) | Simplify: React Query with `staleTime: 0` for deal tabs; job polling as a query | — |
| A28 | A past year opens read-first and never asks the client anything (`historical`) | Defer with renewals | — |

### Workflow state

| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| A29 | Next action cascade (lost/complete → revalidate census → intake gate → census attention → read quotes → map census → fix census → approve client → review values → confirm selection → build proposal → share → mark sold → …); each `{key, label, tab, severity, view}` | Keep, minus implementation and renewal steps | `deals/selectors.next_action` composes each app's `summary(deal)` in the old order |
| A30 | Stage ladder. Old: intake → quoting → sold → enrollment → complete, plus lost. Forward-only automatic moves; manual moves except to and from lost | Simplify: 2Vantage's ladder intake → quoting → proposal → sold, plus lost (enrollment and complete belong to implementation) | `deals/stages.py` (built) |

### Values, history and locks

| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| A31 | Layered values with confirmations, review marks, origin stamps and source locations, one row per value | Simplify | Values as JSON on the row; `sources[key] = {origin, by, at, doc, page, cell, link, low, mark: {state, value, by, at}, confirmed: {value, by, at}}`; a mark or confirmation applies only while its stored value equals the current value (same behaviour, no extra columns) |
| A32 | Confirm values (single, by document, by scope; undo) and review marks (approve/ignore/check; bulk; revert a bulk action) | Keep the behaviour | One endpoint per app; bulk undo uses the Activity entry's before-values |
| A33 | Hand edit: an unchanged value writes nothing; `null` reverts our edit; `''` deliberately clears | Keep (rule 2) | — |
| A34 | Version history (rail, save a version, render, diff, restore with guards, archive a version; Documents change history grouped by person in 30-minute spans) | Simplify: Activity entries record before/after for the changed keys (no member values for census); "Revert this change" on an Activity row where safe (never on sold plans or signed forms); the change-history card reads Activity | — |
| A35 | Edit sessions (✎ Edit / Done, 409 naming the holder, takeover, 30-minute expiry, commit on tab change and page hide) | Drop: rows are locked per write, and each write returns what changed. Where the old screen showed ✎ Edit / Done ✓, keep the button as a client-side mode only (same look) | — |

### Jobs, notes, agency, everything else

| # | Functionality | Verdict | New implementation |
|---|---|---|---|
| A36 | Background jobs: one thread per job, 30-second keepalive, lazy reaper (45 min; 3 min under keepalive), one running job per deal with the rest queued, status poll, cancel, child jobs inherit the starter | Simplify | One `Job` model (kind, status, pct, log, params, result, error, heartbeat, started_by); a worker process (`manage.py run_jobs`, its own compose service) claims jobs with `select_for_update(skip_locked)`; keep the heartbeat and reaper rules; one running job per deal; tests run jobs inline |
| A37 | Deal notes: kinds note/call/email/meeting/internal, pinned first, edit and delete, earlier years' notes | Keep (earlier years deferred) | `deals.Note` |
| A38 | The personal notepad (`/api/notes/`) | Drop (no routed UI) | — |
| A39 | Agency profile, logo, cover images, stock images, team members and photos | Keep | Django admin plus read endpoints used by the Proposal |
| A40 | Walkthroughs (41 guides, 904 `data-guide` anchors); Ask Claude bubble; usage tracking; dev harness; DevRunner banner | Drop: not product features; anchors made the code rigid | — |
| A41 | Feature flags | Keep: AI budgets, limits and model names (AI app settings). Drop: flags that are off and dead (read checks, employee census links). `LINK_VERIFICATION` goes to Part L | — |
| A42 | Pages without the app chrome: `/b/` portal, `/p/` share link, `/s/` signing page, proposal print, document window | Keep each with its module (Parts L, J, H, E) | — |
| A43 | No per-deal access control (any benefits user can open any deal) | Keep as is (matches how the firm works) | Open question A-Q3 |

## A.4 Cross-module seams

**How the old app crossed between modules**
- The deal payload computed every module's metrics on every read and after every write.
- `serializers/journey.py` and `serializers/overview.py` read everything.
- The work feed ran the whole metric chain for every open deal.
- Commissions was reached through six or seven guarded lazy imports.
- Version calls sat in 24 files.

**New rules**
- **One function per tab app.** Each exposes `summary(deal)`: readiness, open items, done steps, badge counts. It has a
  fixed shape and a fixed query count.
  - The `deals` app reaches these through a small registry filled in each app's `AppConfig.ready()`, so `deals` never
    imports to its right.
  - `overview` composes them.
- **A small deal header.** It carries header facts, journey, next action and nav badges. Each tab fetches its own data.

## A.5 Bugs and pain points found

- **Storage and history machinery:**
  - EAV storage forced SQL twins and parity tests: census requiredness was implemented 5 times.
  - The frozen registry needed 11 migrations to change a field.
  - `versions.py` is 2,589 lines with about 89 call sites; census snapshots run to about 600 KB each.
  - Edit sessions needed an ordering protocol, and an unwrapped lock error produced a 500.
- **Payload size:** the deal payload was rebuilt on every write. The comparison payload reached 3.78 MB, which is why
  gzip was added.
- **Tests and code health:**
  - 87 test classes read source files.
  - Dead endpoints (deal list, versions audit, carrier templates, advisor chat) and a dead notepad.
  - Swallowed exceptions in the renewal carry.
- **Sign-in and access:** token defects (never expire, survive a password change); no per-deal access control.
- **CSS problems:**
  - 1,066 raw hex colours.
  - Six tokens are used but never defined (`--accent`, `--muted`, `--ink-soft`, `--ink-3`, `--line`, `--red`).
  - `.btn-primary {width:100%}` is global, so many rows have to undo it.
  - `.btn-sm` is declared twice.

## A.6 New design

**Backend apps.** The chain is accounts → deals → documents → ai → intake → census → quotes → questionnaire →
commission → rfp → proposals → review → agenda → overview, plus a seed-only `golden` app (final placement and reasons
in Part O.1).
- **`accounts`:** sessions; `Profile(user, claude_direct, commissions_access)`; `/api/auth/me/`.
- **`deals`** (built):
  - Client, Deal, Contact (client-level), Note, Activity, AgencySettings (admin), stages.
  - Services: create, archive, lost, advance.
  - Selectors: home feed, header, next action, journey.
  - The `summary` registry.

**Frontend**
- **Shell:** an `AppShell` (56 px top bar) and a `DealShell`:
  - 232 px sticky sidebar with grouped nav and badges, readiness meters, journey stepper;
  - the tab outlet keyed by `?tab=` with a per-tab error boundary;
  - Claude strip, Work with Claude drawer, review tray dock, toast.
- **Data:** React Query replaces the hand-written stores.

**Look (decision).**
- **Stylesheets:** port the old global stylesheets verbatim into `frontend/src/styles/`, in the old load order and with
  the same class names (`bb-*`, `bnf-*`, `gk-*`, `rr-*`). New components use those class names, so every screen is
  pixel-identical. Include only the stylesheets for modules in scope.
- **CSS fixes:**
  - define the six missing tokens;
  - scope `.btn-primary`'s width;
  - remove the duplicate `.btn-sm`.
- **The screens built in M1–M6** move onto these classes, and their CSS modules are deleted.
- **Old tokens to restore** (the 2Vantage `tokens.css` today differs on every row):

| Token | Old value (keep) |
|---|---|
| Fonts | IBM Plex Sans / IBM Plex Mono, 400–700 (Google Fonts) |
| Body | 14 px, line-height 1.6, background `#f6f7f9` |
| Ink | `#1c2430`, `#5b6573`, `#9aa3b0`; muted label `#8b95a3` |
| Navy | `#173a63`; top bar `#0f2d4f` (56 px); nav links `#9db4cf` |
| Blue | `#2e6fc7` on `#e8f0fb` |
| Green | `#1f8a5b` on `#e7f4ee` |
| Amber | `#a9710a` on `#faf0d7` |
| Rose | `#c1352e` on `#fbeae7` |
| Violet ("the client") | `#6d4bb6` on `#efe9fb` |
| Borders | `#e6e8ec`, `#eef0f3`, `#f1f3f5`; inputs `#d4d8df` |
| Radii | buttons 9, inputs and nav 8, stat cards 12, table card 14, readiness 10, badges 5, pills 20/999 |
| Widths | page 1200, home 1120, workspace `min(100vw − 3rem, 1720px)`, sidebar 232 |
| Type | eyebrow 12/600/0.08em uppercase; title 26/600/−0.4 px; subtitle 13.5; table head 11/600/0.05em uppercase |

**Tests**
- Stage ladder, archive rules, next-action cascade order, journey states.
- Job claim, reaper and one-per-deal.
- Session expiry.
- `summary(deal)` shape and query count per app.

## A.7 Open questions for Daniel

- **A-Q1. Renewals:** is the renewal workflow (start from a client, carry last year's data, year strip, read-first past
  years) in this build? Several Defer verdicts depend on it.
- **A-Q2. Client page:** should the client page (all of a client's years, the client-level Overview and Agenda) be in
  this build, or only the deal workspace?
- **A-Q3. Access control:** should every producer keep access to every deal, as before?
