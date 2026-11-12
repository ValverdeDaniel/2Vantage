# 2Vantage — Developer Specification

**Version:** 2.0 draft for review · **Date:** 2026-11-11 · **Owner:** Daniel (project owner, approves every change)
**Audience:** a developer — or a Claude Code session — with **no knowledge** of the earlier system. Everything needed to
build 2Vantage is in this document, the porting plan in [`docs/porting/`](docs/porting/README.md) and the asset files
listed in [Appendix A](#appendix-a--assets-supplied-with-this-spec).
**Changes in 2.0:** rebuilt from the approved porting plan of 2026-11-11 and Daniel's answers to OQ1–OQ21. 2Vantage is
now a production port of the old Vantage benefits product (every important function, the same screens and client files)
instead of v1.1's redesign, and v1.1's four releases become the 69 slices of §13
([Appendix B](#appendix-b--background-why-2vantage-exists)).

---

## How to use this document

- **What this is.** plan.md is the normative core of 2Vantage and its build order. The porting plan in `docs/porting/`
  holds the detailed specifications: every function of old Vantage with its verdict and its home in the new code (each
  part's X.3 inventory), and each module's new design (X.6). This document states the rules and points to those items by
  ID (below) instead of repeating them.
- **Precedence.** plan.md v2.0 is the normative core and the build order; the docs/porting parts are the detailed
  specifications (their X.3 inventory rows and X.6 designs); where they disagree, plan.md wins, then Part O, then the
  module part; the old v1.1 text is superseded wherever the porting parts say otherwise.
- **The baseline.** M0, M1 and M3–M6 (sign-in, the dashboard, the deal header, a simplified Advisor, Proposal
  selection and preview, Documents v1) were built to v1.1 and are committed before slice 1 (§13.3); v1.1's M2, staging,
  was never built and becomes slice 69. Where the baseline differs from this document, for example in the 2V bugs that
  each part's X.5 lists (F.5 #27–38, J.5 B27–B36), the slice that owns the area retires the difference (§6, §13.3).
  The baseline is not the design.
- **Section numbers changed from v1.1.** The baseline's code cites v1.1 sections ("plan.md §7.7"). §1–§5, §7.1–§7.4,
  §8.1–§8.4, §9.1–§9.4 and §12.1–§12.6 keep their numbers; the code's other citations move: 6.6 → 6.7, 6.8 → 6.11,
  7.7 → 7.8, 7.9 → 7.12, 8.11 → 8.14, 8.12 → 8.15, 8.13 → 8.16, 8.14 → 8.19, 8.17 → 8.22. A slice that touches a file
  updates its § citations (slice 4 touches most of the frontend ones).
- Read [§1 Product overview](#1-product-overview) and [§2 Insurance primer](#2-insurance-primer) first. They explain
  the business and its vocabulary; nothing later makes sense without them. Then read §3 and §13.
- [§3](#3-technical-foundation) fixes the stack, repository layout and conventions that every part follows.
- [§4](#4-reference-data) lists the vocabularies (lines of coverage, plan fields, census columns, intake questions,
  carriers). Implement them **exactly** as listed: they are business data, not suggestions.
- [§5](#5-business-rules) states every business rule (validation, premium math, readiness, stages). Each rule is
  testable as written, most as a table-driven test of one pure function (Q.1).
- §6 to §10 specify the data model, API, screens (in the old look), generated files (in the old formats) and AI (the
  readers and Work with Claude). Each states the rules and points by item ID to Part O and to the parts' X.6 designs for
  field lists, endpoint tables and screen inventories.
- §11 and §12 cover deployment and testing (Part Q; verification.md). §14 is the working agreement and CLAUDE.md. §15
  says what is not rebuilt and what waits.
- §13 is the order of work: 69 slices in six phases (slice 50 waits under OQ6, so 68 are built), with two milestones
  (Part P, amended). Build one slice at a time;
  Daniel reviews and commits each before the next. A slice builds only the items its row names, in the apps Part O gives
  them, and is done when its tests and lanes pass and its "done when" has been walked in the browser on a golden deal
  (V.1). The document describes the whole product; a part of it is built only when a slice names it.
- §16 lists every question, answered or open, with its default, its status and the slice its answer changes. Where v1.1
  marked an item ▲ To confirm or ▲ To verify, this document cites the question's number instead (for example OQ53).
  Build a default as written until Daniel answers; each is isolated so a change is cheap. Some questions are for
  Stephanie or a developer, and §16 says so. [decisions.md](docs/porting/decisions.md) keeps the questions in full, with
  Daniel's answers in his own words.
- **MUST / MUST NOT / SHOULD / MAY** are used in their usual specification sense.
- **Old Vantage** (`Vantage/`, beside this repository) is read-only. The port follows its commit 891f1b3 (§13.3); later
  old-repo decisions are listed for Daniel before the slice that ports their area. Never open or copy anything under
  `Vantage/aBenefitsMeetings/`, or any real client file; paths there are citations only (Appendices A and C).

### The porting plan

| File | What it covers |
|---|---|
| [Porting plan README](docs/porting/README.md) | Summary, context, Daniel's twelve needs and their traceability to items and slices, how the review was done |
| [Decisions needed](docs/porting/decisions.md) | OQ1–OQ100 in full, each with its default; Daniel's answers of 2026-11-11 are the lines starting "A." |
| [Part A — Platform foundation](docs/porting/A-foundation.md) | Sign-in, home, deal shell, stages, values and history, jobs, the look |
| [Part B — Intake](docs/porting/B-intake.md) | The 56 questions, contacts, coverage intent, the marketing checklist, BOR, marketed |
| [Part C — Census](docs/porting/C-census.md) | The roster, import and matching, validation, rollups that price plans |
| [Part D — AI readers and Work with Claude](docs/porting/D-ai-readers-and-work-with-claude.md) | The Work with Claude drawer, quote and SBC readers, jobs, budgets |
| [Part E — Documents review station](docs/porting/E-documents-review-station.md) | Files, the viewer, Find, review mode, checks against the source |
| [Part F — Advisor](docs/porting/F-advisor.md) | The quote comparison board and everything on it |
| [Part G — Medical questionnaire](docs/porting/G-medical-questionnaire.md) | Florida Blue 51+, Warner large group, the SIIA disclosure |
| [Part H — Commissions](docs/porting/H-commissions.md) | Rates, splits, booking, the book, statements and reconciliation (statements wait: OQ6) |
| [Part I — Agenda](docs/porting/I-agenda.md) | Deal steps, tasks, marks, the work queue |
| [Part J — Proposal and export viewer](docs/porting/J-proposal-and-export-viewer.md) | The Proposal tab, the export viewer and the client files |
| [Part K — RFP](docs/porting/K-rfp.md) | Carriers, the packet, request forms, carrier census files, email drafts |
| [Part L — Review & requests, client portal](docs/porting/L-review-and-requests.md) | Review queues, requests and links, the client portal |
| [Part M — Overview](docs/porting/M-overview.md) | The deal Overview: header, banners, cards, feed, notes |
| [Part N — Cross-module data flow](docs/porting/N-cross-module-data-flow.md) | Every fact that crosses modules and who owns it |
| [Part O — Architecture of the new codebase](docs/porting/O-architecture.md) | The app chain, every app, shared frameworks, the stylesheet port, resolved conflicts |
| [Part P — Build order](docs/porting/P-build-order.md) | The 66 slices in six phases, with done-when and milestones; §13 is its amended copy |
| [Part Q — Testing approach](docs/porting/Q-testing.md) | Tests, golden deals, fidelity and visual-parity checks, performance budgets |
| [Verification](docs/porting/verification.md) | How each slice and the whole MVP are accepted; the top risks |

Each module part (A–M) has the same sections: X.1 files read, X.2 the old data model, X.3 every old function with its
verdict (Keep, Simplify, Drop, Defer or New) and its home in the new code, X.4 data flow, X.5 bugs found, X.6 the new
design and X.7 its questions (merged into decisions.md). Parts N–Q and Verification span the modules.

### Item IDs

| ID | Means | Where |
|---|---|---|
| F45 (A1 … M112) | One function of old Vantage: what it does, its verdict (Keep, Simplify, Drop, Defer or New) and its home in the new code. The letter names the part | The part's X.3 |
| O.3.2, J.6.4 | A section of a porting part | That part |
| F.5 #27, J.5 B22 | A bug found in old Vantage or in the 2V baseline | The part's X.5 |
| O.6 #24 | A conflict between parts and its ruling | Part O, O.6 |
| OQ13 | An open question, with the default built until it is answered | §16; decisions.md |
| A-Q2, C.6 #1 | A part's own question, merged into an OQ | The part's X.7; the tags in decisions.md |
| CL4 | A client lifecycle or client page item (OQ2). No porting part has them | §13.11; the rules in §5.1, the page in §8.5 |
| need 6 | One of Daniel's twelve Advisor and Proposal requirements | README, traceability |
| GD3, GD-Big | A golden deal: synthetic, seeded by `seed_golden`, with a key Stephanie signs | P.2, Q.4, §12 |
| slice 7 (ADV-1) | One step of the build | §13 |
| Gate B; Look | An acceptance gate; a test lane | V.2; Q.2 |
| D-219 | A decision in old Vantage's log, `Vantage/PlanningDocs/Benefits/decisions.md` | Old repository |
| X-84 | An item of old Vantage's experience review, `Vantage/PlanningDocs/Benefits/experience-review/` | Old repository |

### Contents

- [How to use this document](#how-to-use-this-document)
  - [The porting plan](#the-porting-plan)
  - [Item IDs](#item-ids)
  - [Contents](#contents)
- [1. Product overview](#1-product-overview)
  - [1.1 What the business does](#11-what-the-business-does)
  - [1.2 Users](#12-users)
  - [1.3 The workflow on one page](#13-the-workflow-on-one-page)
  - [1.4 Scope of this build](#14-scope-of-this-build)
  - [1.5 What "done" looks like](#15-what-done-looks-like)
- [2. Insurance primer](#2-insurance-primer)
- [3. Technical foundation](#3-technical-foundation)
  - [3.1 Stack](#31-stack)
  - [3.2 Repository layout](#32-repository-layout)
  - [3.3 App dependency chain](#33-app-dependency-chain)
  - [3.4 Local environment](#34-local-environment)
  - [3.5 Settings](#35-settings)
  - [3.6 API conventions](#36-api-conventions)
  - [3.7 Values, sources and Activity](#37-values-sources-and-activity)
  - [3.8 Security and PHI](#38-security-and-phi)
  - [3.9 Frontend conventions](#39-frontend-conventions)
- [4. Reference data](#4-reference-data)
  - [4.1 Lines of coverage — `deals/lines.py`](#41-lines-of-coverage--dealslinespy)
  - [4.2 Coverage tiers — `deals/lines.py` and
    `census/importer.py`](#42-coverage-tiers--dealslinespy-and-censusimporterpy)
  - [4.3 Plan fields — `quotes/fields.py`](#43-plan-fields--quotesfieldspy)
  - [4.4 Census columns — `census/fields.py`](#44-census-columns--censusfieldspy)
  - [4.5 Intake questionnaire — `intake/form.py`](#45-intake-questionnaire--intakeformpy)
  - [4.6 Other vocabularies](#46-other-vocabularies)
  - [4.7 Carriers — `deals/carriers.py` and `rfp/carriers.py`](#47-carriers--dealscarrierspy-and-rfpcarrierspy)
  - [4.8 Census header synonyms — `census/importer.py`](#48-census-header-synonyms--censusimporterpy)
- [5. Business rules](#5-business-rules)
  - [5.1 Deal stages and client status — `deals/stages.py`,
    `deals/lifecycle.py`](#51-deal-stages-and-client-status--dealsstagespy-dealslifecyclepy)
  - [5.2 Intake — `intake/form.py`, `values.py`, `validation.py`, `coverage.py`,
    `checklist.py`](#52-intake--intakeformpy-valuespy-validationpy-coveragepy-checklistpy)
  - [5.3 Census — `census/`](#53-census--census)
  - [5.4 Plans — `quotes/`](#54-plans--quotes)
  - [5.5 Premium math — `quotes/math/`](#55-premium-math--quotesmath)
  - [5.6 Commission — `deals/comp.py`, `commission/math.py`,
    `commission/rules.py`](#56-commission--dealscomppy-commissionmathpy-commissionrulespy)
  - [5.7 RFP — `rfp/request.py`, `rfp/printed.py`; the headcount in
    `quotes/facts.py`](#57-rfp--rfprequestpy-rfpprintedpy-the-headcount-in-quotesfactspy)
  - [5.8 Review & request — `review/rules/`](#58-review--request--reviewrules)
  - [5.9 Next step and agenda — `agenda/steps/`, `agenda/rows.py`](#59-next-step-and-agenda--agendasteps-agendarowspy)
  - [5.10 Deal facts for Agenda and Overview —
    `<app>/summary.py`](#510-deal-facts-for-agenda-and-overview--appsummarypy)
- [6. Data model](#6-data-model)
  - [6.1 accounts](#61-accounts)
  - [6.2 deals](#62-deals)
  - [6.3 documents](#63-documents)
  - [6.4 ai](#64-ai)
  - [6.5 intake](#65-intake)
  - [6.6 census](#66-census)
  - [6.7 quotes](#67-quotes)
  - [6.8 questionnaire](#68-questionnaire)
  - [6.9 commission](#69-commission)
  - [6.10 rfp](#610-rfp)
  - [6.11 proposals](#611-proposals)
  - [6.12 review](#612-review)
  - [6.13 agenda](#613-agenda)
  - [6.14 overview](#614-overview)
  - [6.15 golden](#615-golden)
- [7. API](#7-api)
  - [7.1 Platform](#71-platform)
  - [7.2 Accounts — `auth/`](#72-accounts--auth)
  - [7.3 Clients and deals — `deals/`](#73-clients-and-deals--deals)
  - [7.4 Documents — `documents/`](#74-documents--documents)
  - [7.5 AI — `ai/`](#75-ai--ai)
  - [7.6 Intake — `intake/`](#76-intake--intake)
  - [7.7 Census — `census/`](#77-census--census)
  - [7.8 Quotes (Advisor) — `quotes/`](#78-quotes-advisor--quotes)
  - [7.9 Questionnaire — `questionnaire/`](#79-questionnaire--questionnaire)
  - [7.10 Commission — `commission/`](#710-commission--commission)
  - [7.11 RFP — `rfp/`](#711-rfp--rfp)
  - [7.12 Proposal — `proposals/`](#712-proposal--proposals)
  - [7.13 Review & requests — `review/` (staff)](#713-review--requests--review-staff)
  - [7.14 Client portal — `portal/{token}/` (public)](#714-client-portal--portaltoken-public)
  - [7.15 Agenda and work queue — `agenda/`](#715-agenda-and-work-queue--agenda)
  - [7.16 Overview — `overview/`](#716-overview--overview)
- [8. Screens (the old look)](#8-screens-the-old-look)
  - [8.1 Top bar and routes](#81-top-bar-and-routes)
  - [8.2 Sign-in and account pages](#82-sign-in-and-account-pages)
  - [8.3 Home views](#83-home-views)
  - [8.4 Deal page](#84-deal-page)
  - [8.5 Client page](#85-client-page)
  - [8.6 Overview (`overview`)](#86-overview-overview)
  - [8.7 Agenda (`agenda`)](#87-agenda-agenda)
  - [8.8 Review & requests (`review`)](#88-review--requests-review)
  - [8.9 Intake (`intake`)](#89-intake-intake)
  - [8.10 Census (`census`)](#810-census-census)
  - [8.11 Questionnaire (`questionnaire`)](#811-questionnaire-questionnaire)
  - [8.12 RFP (`rfp`)](#812-rfp-rfp)
  - [8.13 Commission (`commission`)](#813-commission-commission)
  - [8.14 Advisor (`advisor`)](#814-advisor-advisor)
  - [8.15 Proposal (`proposal`)](#815-proposal-proposal)
  - [8.16 Documents (`documents`)](#816-documents-documents)
  - [8.17 Work with Claude drawer and strip](#817-work-with-claude-drawer-and-strip)
  - [8.18 Commissions page (`/commissions`)](#818-commissions-page-commissions)
  - [8.19 Admin pages](#819-admin-pages)
  - [8.20 Client portal (`/portal/:token`)](#820-client-portal-portaltoken)
  - [8.21 The grid](#821-the-grid)
  - [8.22 Loading, empty and error states](#822-loading-empty-and-error-states)
- [9. Generated files (the old formats)](#9-generated-files-the-old-formats)
  - [9.1 Blank census template (`census/template.py`)](#91-blank-census-template-censustemplatepy)
  - [9.2 Census export (`census/template.py`)](#92-census-export-censustemplatepy)
  - [9.3 Plan template (`quotes/template.py`)](#93-plan-template-quotestemplatepy)
  - [9.4 Client spreadsheet (`proposals/workbook/`)](#94-client-spreadsheet-proposalsworkbook)
  - [9.5 Client PDF and PowerPoint: one layout (`proposals/story/`,
    `proposals/layout/`)](#95-client-pdf-and-powerpoint-one-layout-proposalsstory-proposalslayout)
  - [9.6 PowerPoint (`proposals/paint/pptx/`)](#96-powerpoint-proposalspaintpptx)
  - [9.7 PDF, Paper and the Letter PDF (`proposals/paint/`)](#97-pdf-paper-and-the-letter-pdf-proposalspaint)
  - [9.8 Carrier census files (`rfp/formats/`, `rfp/xlsx/`)](#98-carrier-census-files-rfpformats-rfpxlsx)
  - [9.9 Warner quote request form and cover page (`rfp/forms/`,
    `rfp/cover.py`)](#99-warner-quote-request-form-and-cover-page-rfpforms-rfpcoverpy)
  - [9.10 RFP packet (`rfp/packet.py`)](#910-rfp-packet-rfppacketpy)
  - [9.11 Email drafts (`rfp/drafts.py`, `rfp/eml.py`)](#911-email-drafts-rfpdraftspy-rfpemlpy)
  - [9.12 Questionnaire PDFs (`questionnaire/pdf/`)](#912-questionnaire-pdfs-questionnairepdf)
  - [9.13 Stop-loss analysis workbook
    (`quotes/stop_loss_workbook.py`)](#913-stop-loss-analysis-workbook-quotesstop_loss_workbookpy)
  - [9.14 Advisor board export (`quotes/board_export.py`)](#914-advisor-board-export-quotesboard_exportpy)
  - [9.15 Commission files (`commission/exports.py`,
    `commission/disclosure.py`)](#915-commission-files-commissionexportspy-commissiondisclosurepy)
- [10. AI and Work with Claude](#10-ai-and-work-with-claude)
  - [10.1 Principles](#101-principles)
  - [10.2 The `ai` app and the worker](#102-the-ai-app-and-the-worker)
  - [10.3 The Claude client, models and budgets](#103-the-claude-client-models-and-budgets)
  - [10.4 Readers](#104-readers)
  - [10.5 Landing, review and Undo](#105-landing-review-and-undo)
  - [10.6 Work with Claude: chats and tools](#106-work-with-claude-chats-and-tools)
  - [10.7 The Documents review station](#107-the-documents-review-station)
  - [10.8 Member data, PHI and the BAA](#108-member-data-phi-and-the-baa)
- [11. Deployment](#11-deployment)
  - [11.1 Stages](#111-stages)
  - [11.2 Google Cloud](#112-google-cloud)
  - [11.3 Release gate](#113-release-gate)
  - [11.4 The PHI gate (slice 47)](#114-the-phi-gate-slice-47)
- [12. Testing](#12-testing)
  - [12.1 Tools and layout](#121-tools-and-layout)
  - [12.2 Speed budget](#122-speed-budget)
  - [12.3 Tests that MUST exist](#123-tests-that-must-exist)
  - [12.4 Tests we never write](#124-tests-we-never-write)
  - [12.5 Frontend checks](#125-frontend-checks)
  - [12.6 Golden deals](#126-golden-deals)
  - [12.7 Parity with the old app](#127-parity-with-the-old-app)
  - [12.8 AI reader tests](#128-ai-reader-tests)
  - [12.9 PHI and client-safety canaries](#129-phi-and-client-safety-canaries)
- [13. Build order](#13-build-order)
  - [13.1 How slices work](#131-how-slices-work)
  - [13.2 What the answers, and the check against v1.1, change in Part
    P](#132-what-the-answers-and-the-check-against-v11-change-in-part-p)
  - [13.3 Before slice 1](#133-before-slice-1)
  - [13.4 Golden deals](#134-golden-deals)
  - [13.5 Phase 0 — Ground](#135-phase-0--ground)
  - [13.6 Phase 1 — The Advisor without Claude](#136-phase-1--the-advisor-without-claude)
  - [13.7 Phase 2 — Documents, Work with Claude and staging](#137-phase-2--documents-work-with-claude-and-staging)
  - [13.8 Phase 3 — The Proposal](#138-phase-3--the-proposal)
  - [13.9 Phase 4 — Get to Market](#139-phase-4--get-to-market)
  - [13.10 Phase 5 — The rest](#1310-phase-5--the-rest)
  - [13.11 Client lifecycle and client page items](#1311-client-lifecycle-and-client-page-items)
  - [13.12 Parallel work and risks](#1312-parallel-work-and-risks)
  - [13.13 Milestones](#1313-milestones)
- [14. Working agreement and CLAUDE.md](#14-working-agreement-and-claudemd)
  - [14.1 The working agreement](#141-the-working-agreement)
  - [14.2 CLAUDE.md](#142-claudemd)
- [15. Deliberate non-goals and deferrals](#15-deliberate-non-goals-and-deferrals)
  - [15.1 Not rebuilt](#151-not-rebuilt)
  - [15.2 Deferred](#152-deferred)
- [16. Decisions](#16-decisions)
- [Appendix A — Assets supplied with this spec](#appendix-a--assets-supplied-with-this-spec)
- [Appendix B — Background: why 2Vantage exists](#appendix-b--background-why-2vantage-exists)
- [Appendix C — Where each rule came from](#appendix-c--where-each-rule-came-from)

---

## 1. Product overview

### 1.1 What the business does

Vantage Risk Solutions is an insurance brokerage. Its **employee-benefits team** helps employers ("groups") buy
health insurance and related coverage for their employees. For each employer the team:

1. collects facts about the company and its current coverage (**intake**);
2. collects a list of the employees and their dependents (**census**);
3. has the employer answer and sign the carriers' **medical questionnaire** when the group needs one (Florida Blue 51+,
   Warner large group, the SIIA stop-loss disclosure);
4. sends that package to insurance companies (**carriers**) asking for prices (**RFP**, request for proposal);
5. receives price quotes back, reads them and the plans' benefit summaries (**SBCs**) with **Work with Claude** or by
   hand, and lines them up side by side (**Advisor**, quote comparison);
6. presents the best options to the employer, with the firm's recommendation (**proposal** — the client spreadsheet, the
   PowerPoint and the client PDF, in the formats old Vantage built);
7. records which plans the employer bought (**sold**), books the commission the agency expects and splits it between the
   producers (**commission**).

The order is not strict. Quotes often arrive before intake, census and questionnaire are done ("just a quick example of
a quote"), so the Advisor and the Proposal work from typed summary tier counts until a census arrives (§1.3).

2Vantage is the team's internal web application for steps 1–7, for **prospects** (employers the agency is working to
win) and **new clients** (employers in their first plan year with the agency). A client moves from Prospect to New
client to Existing client (§1.3); work that only existing clients need, from their second plan year on, is deferred
(OQ1, OQ2). "For prospects and new clients" is a label more than a limit: a renewal for a group the firm already serves
can be run by hand through the same current / renewal / alternate model, with the client created as an Existing client.
What is deferred is carrying a deal over from one plan year to the next (A15, A16), which will depend on each plan
recording its funding (§4.3).

### 1.2 Users

| User | Who | What they do |
|---|---|---|
| Producer | Account managers / producers on the benefits team (3–10 people) | Everything in the workflow |
| Admin | One or two senior producers (`is_staff`) | Everything producers do, plus manage users, their flags and agency settings in Django admin (`/admin/`), with carrier notes for Claude (D119); the firm pages, team and cover images are edited in the app since slice 34 (J155) |
| Client contact | Someone at the employer (HR, owner) | No account. Opens a secure link to answer intake questions and census cells, upload files, sign the BOR, and fill and sign a medical questionnaire as the company's officer (Part L). A phoned PIN is asked where the link shows people or medical information (OQ80) |

Each person has two flags on `accounts.Profile`, set in Django admin (A3):
- `claude_direct`: Claude's quote reads and chat changes land at once, with Undo, instead of waiting for review (§10);
  the person may pick the Opus model and may "Run anyway" past the deal's AI budget (D24, D71, D77, D91). Admins have
  these powers without the flag.
- `commissions_access`: none, own or all, for the commission records on `/commissions` (H101, H102; OQ73). Admins see
  all; a producer defaults to own.

All signed-in users see all clients and every deal (OQ3, A43). There is no per-user data restriction, except that
commission records follow `commissions_access`; every deal's Commission tab is open to all (H102).

### 1.3 The workflow on one page

```
Home:  Prospects · Clients · Work queue                                     (A9, OQ2)
          │           │
          │           ▼
          │        Client page: Overview · Agenda · Commissions · Notes      (slices 67–68)
          │           │
          ▼           ▼
       Deal workspace: one deal per client; the sidebar keeps old Vantage's order and groups (A21, OQ9)
   ┌──────────────────────────────────────────────────────────────────────────────────────────┐
   │ Overview       where the deal stands, what to do next, notes, activity                   │
   │ Agenda         the deal's steps and tasks: what is next, what waits and on whom          │
   │ 1 · Get to Market                                                                        │
   │ Review &       send the client a link for missing answers/files; approve what returns    │
   │  requests                                                                                │
   │ Intake         company facts, contacts, current coverage, lines to quote, checklist, BOR │
   │ Census         upload the employee list, fix errors, see enrollment by tier              │
   │ Questionnaire  the carrier's medical form, answered and signed (if the deal has one)     │
   │ RFP            pick carriers, download carrier census files + forms, email drafts        │
   │ Commission     commission rate per line, expected revenue, producer split, booking       │
   │ 2 · Quote to Close                                                                       │
   │ Advisor        every plan (current / renewal / alternates) side by side, priced; views   │
   │                for stop-loss, the proposal builder and the export viewer                 │
   │ Proposal       the presented plans and the packet → issue the client spreadsheet,        │
   │                PowerPoint and PDF → mark plans sold                                      │
   │ Shared                                                                                   │
   │ Documents      every file on the deal; view it and check where each value came from      │
   └──────────────────────────────────────────────────────────────────────────────────────────┘
   Work with Claude: a drawer beside the tabs to chat, read quotes and SBCs, and change the board
Stage:  Intake ──► Quoting ──► Proposal ──► Sold        (or Lost; the reason is optional)
Client: Prospect ──► New client ──► Existing client     (the last step waits with renewals)
```

- **Home** (A9). **Prospects** is the landing view, which old Vantage called New clients (I86; OQ101): each prospect
  once, with the one thing it needs next. A sale moves the client to **Clients**, which lists new and existing clients
  in the old client book's look (A13). The **Work queue** lists every open step and task (I70–I85). Archived clients
  have their own page (A13).
- **Client page** (OQ2; slices 67–68). The client's own Overview, Agenda, Commissions and Notes, in the old client
  page's look, with links into its deal's tabs (§8). Each client has one deal for now.
- **Deal workspace.** The sidebar keeps old Vantage's order and groups exactly (A21; OQ9). The code's app chain orders
  imports, not screens (§3.3). Questionnaire shows only when the deal has a form (G7). The Work with Claude pill opens
  its drawer beside the page, with that tab's context (D1, M106).
- **Stage** moves forward by itself: to Quoting when the first quote read is applied or the RFP is first sent, to
  Proposal at Issue, to Sold when a plan is marked sold (§5.1). People can also move it by hand. Lost takes an optional
  reason (OQ48), and Reopen undoes it.
- **Client status** (§5.1; OQ2, OQ101). A client starts as a Prospect. Marking a plan sold makes it a New client, and
  "Convert to client" does the same by hand. "Back to prospect" undoes either while no plan is sold; un-selling the last
  sold plan undoes a conversion the sale made. A New client becomes an Existing client when its first plan year ends or
  its first renewal starts, which waits with renewals (OQ1); until then Existing client is picked by hand, for a group
  the firm already serves. The status is not the deal type: a won prospect's deal stays New business (M14).
- **Quotes first** (need 6; N.2). "I already have carrier quotes" creates the deal and opens the Advisor with Work with
  Claude (A14, D43). Typed summary tier counts then price every plan, the size band, expected revenue and the Proposal,
  so a missing intake, census or questionnaire never stops quotes (OQ9). When the census arrives it takes over from
  counts typed before its import, with "Keep my typed counts" (F91; OQ18).

### 1.4 Scope of this build

This build ports old Vantage's benefits product for prospects and new clients: every important function, the same
screens and the same client files, in small tested code. Its modules are those of the approved porting plan (README,
"Modules in scope"), plus the client status and the client page that Daniel's OQ2 answer adds. His answers of 2026-11-11
to OQ1–OQ21 (seven left blank and built to their defaults) settle what each module includes; every other question is
built to its default until he answers it (§16). All twelve of his Advisor and Proposal needs are in scope (README,
"Traceability"). Each client has one deal.

**In this build**

| Module | What is built | Decisions (§16) | Part | Slices |
|---|---|---|---|---|
| Foundation | Sign-in, the home views, the deal shell in old Vantage's sidebar order, stages, Lost, archive, contacts and notes, change history with Revert, the old look; staging | OQ3, OQ9, OQ10, OQ45–OQ49, OQ105–OQ107 | A, O | 1–6, 38, 47, 69 |
| Client status | Prospect → New client at the first sale or with Convert to client; Back to prospect; Existing client set by hand | OQ2, OQ101 | §5.1 | 6; 4, 49, 61, 62, 67 |
| Client page | Overview, Agenda, Commissions and Notes, for prospects and new clients | OQ2 | §8.5 | 67–68 |
| Overview | The deal Overview: header, banners, cards, feed, notes | OQ96 | M | 62–64 |
| Agenda | Deal steps, tasks, Later and Done; the Work queue and the home figures | OQ8, OQ90–OQ95 | I | 60–61 |
| Review & requests | Review queues, requests and links, the client portal | OQ80–OQ89 | L | 53–59 |
| Intake | The 56 questions, contacts, current coverage, coverage intent, the marketing checklist, BOR, Mark as marketed; Required or Waived per question | OQ15, OQ17, OQ50–OQ53 | B | 11, 39–40 |
| Census | Import and matching, validation, the roster grid, rollups that price plans; Required or Waived per column; SSN optional and masked | OQ16, OQ17 | C | 12, 41 |
| Questionnaire | Florida Blue 51+, Warner large group and the SIIA disclosure: prefilled, answered, signed, filed | OQ5, OQ54–OQ58 | G | 42–43, 52, 58 |
| RFP | Carrier picks, the packet, Warner's request form and cover, carrier census files, email drafts | OQ59–OQ69, OQ109 | K | 26, 44–46 |
| Commission | Rates, splits, booking at the sale, the Book | OQ6, OQ70–OQ77 | H | 48–49 |
| Advisor | Search, budget filter, stars, several current plans, replaces, slot picks, Transpose; typed tier counts, so quotes never wait for intake, census or a questionnaire; priced versions; saved setups (Mine, Shared); stop-loss analysis with saved settings and its workbook; stop-loss plans reorder like any line | OQ7, OQ9, OQ11–OQ14, OQ18–OQ21, OQ43, OQ104 | F | 7–10, 13–14, 35–36 |
| Proposal | The builder with templates, Pages, the Export viewer, Issue; the client spreadsheet, PowerPoint and PDF in the old Presentation format, with a Florida Blue pair printed as one column (D-219) | OQ7, OQ35–OQ42, OQ102, OQ103 | J | 25–34 |
| Documents | The review station: viewer, Find, review mode, checks against the file, archive and restore | OQ14, OQ22–OQ28, OQ97–OQ99 | E | 15–17, 23, 65 |
| Work with Claude | The chat drawer and the job worker; quote, SBC, census, intake and questionnaire readers; "As quoted"; quote reads by admins and direct people land at once with Undo, the rest wait for review; Rank; carrier notes; voice input | OQ4, OQ29–OQ34, OQ44 | D | 16, 18–22, 24, 37, 51–52, 59, 66 |

**Deferred.** Not in this build. Each is isolated so it can return as its own change; §15.2 says what each waits for.

| What waits | Items | Decisions |
|---|---|---|
| **Renewals**: starting one from a client and carrying last year's data into it; past years opened read-first; revalidation and re-signing; renewal history; earlier years' chats, notes and files | A15, A16, A28, B30, B44, C26, D11, E102, G119–G121, H16, H21, H111, I43, J44, J129, K112, L128, M22, M31, M32, M47, M78, M84, M98 | OQ1 |
| **Existing-client work**: New client → Existing client after year 1; the client page's Plan years, Notifications and Deals & history; year pages, the year strip and the past-year band; Start renewal; reminders, the Radar, its calendar and the daily digest; client-only tasks | A20 (year strip), CL7, CL27, H104, I9, I72, I88, I104–I108, I109 (Notifications), M102 | OQ1, OQ2 |
| **The commission ledger**: statements, receipts, reconciliation, gaps, statement reading and the client statement (slice 50) | H59–H93 except H68; H103, H105, H123 | OQ6, OQ78, OQ79 |
| **Pay paperwork**: comp agreements, producer profiles and W9s, payouts, the Book split | H14, H69, H99, H107 | OQ77 |
| **Claude Unleashed, lessons and saved readers** (admin carrier notes stand in) | D2, D10, D30, D33, D101–D103, F4, G105, J144 | OQ4 |
| **Claude's chat tools for the census and questionnaires** (their files are still read and staged) | D111, G103, G104, L127 | The plan (PHI; not one of the needs) |
| **Classic, the `/p/` share link, the status report, Plan my day** and its task bar | I91–I102, J25, J26, J36, J37, J40, J95, J113, J143, J156, M63, M95–M100 | OQ8 |
| **Census filter sets and bundle templates** | F30 and C27's saved filter setups, F79 | OQ7 |
| **The Acrobat original** of the Florida Blue form | G58, K44 | OQ57 |

Smaller deferrals, such as copying a plan design from an earlier deal (v1.1's R2.1, which no porting part lists;
OQ110), range copy and paste (F75) and antivirus on uploads (E104), are in §15.2 or in each part's X.3, with their
reasons.

**Outside this build.**

- Work outside the modules in scope, which would need its own porting part if Daniel asks (§15.1): property and
  casualty insurance, with its referral records and client badge (H34, H119, M19); post-sale implementation tracking
  and close-out, benefit guides and the contribution model (A22, E9, H122, I61, I62, J99, J168, M41, M64; OQ26).
- Not rebuilt (§15.1): Data Hub (A22, M66), the role matrix (A2; there are two kinds of user, §1.2), walkthroughs, the
  Ask Claude bubble, usage analytics and demo machinery (A8, A40), and old Vantage's machinery: one row per value,
  version snapshots, edit sessions and tests that read source.
- Email sending: the app drafts emails and copies links, and people send them (OQ82; L65).

**Real member data** waits for the PHI gate (slice 47), which includes Anthropic's written confirmation that the BAA
covers Claude's use (OQ29). Until then every census, medical answer and claims file, and every file Claude reads, is
synthetic.

### 1.5 What "done" looks like

A slice is done when its tests and lanes pass and its "done when" has been walked in the browser on a golden deal (§13;
V.1). The product is proven at two milestones (§13.13), each with three gates (V.2):

| Gate | Run by | Passes when |
|---|---|---|
| A | The lanes, on a fresh database with the production image | Every lane is green; Fidelity for the four client outputs on GD1, GD2, GD3 and GD5 and the secondary outputs on GD6; every MVP screen labelled in Look; Eval at its thresholds with the chosen default model; the release gate (`check --deploy`, `/api/health/`, and at Milestone 2 the staging canary scan) |
| B | Daniel, on staging | Each of the twelve needs passes its walk on the golden deal V.2 names |
| C | Stephanie, on staging | She builds one real deal beside her own spreadsheet and old Vantage; the outputs are compared line by line and her time is noted. Each finding is labelled a port bug, an intended difference or a new request |

The two milestones, what each must show and what each leaves out, are in §13.13.

**The MVP is accepted** only at Milestone 2, when no port bug in the twelve needs is open; every figure agrees to the
dollar; the golden keys, the register of intended differences and the Look labels are signed; Gate B has passed at both
milestones; and the PHI checklist is complete before any real member data is used (V.2).

---

## 2. Insurance primer

Read this once. These terms appear everywhere.

| Term | Meaning |
|---|---|
| **Group** / employer / client | The company buying coverage for its employees |
| **Client status**: Prospect, New client, Existing client | Where a client stands with the agency (OQ2). A **prospect** is a group the agency is quoting but has not won. It becomes a **new client** when a plan on its deal is marked sold, or by hand with "Convert to client". A new client becomes an **existing client** after its first plan year, with its first renewal; that move waits with renewals (OQ1), so for now Existing client is chosen by hand for a group the firm already serves. Prospects and new clients are built in this version; existing-client work waits (§1.4, §5.1) |
| **Deal** | One client's purchase for one plan year. (The old system called it a "case"; 2Vantage says deal everywhere.) |
| **Deal type**: New business or Renewal | Whether a deal wins a group the agency does not serve yet (New business) or renews one it does (Renewal). A deal copies its client's status when it opens (`opened_as`) and follows it until a plan on the deal sells, then freezes; it is Renewal only for an existing client (M14). So a won prospect's deal stays New business while its client becomes a new client. Commission's first-year and renewal rates follow it (H30) |
| **Plan year / effective date** | The date the new coverage starts, usually the 1st of a month |
| **Line of coverage** ("line") | A type of insurance: medical, dental, vision, life, disability, and ~20 smaller ones (§4.1) |
| **Lines to quote** (coverage intent) | For each line, what the client wants this year: shop it (ask carriers for quotes), keep it as it is, or leave it off. The shopped lines are the deal's lines to quote; only Intake's coverage intent writes them (B16, B17, B24) |
| **Carrier** | The insurance company (Aetna, Cigna, Florida Blue, UnitedHealthcare, …) |
| **GA (general agency)** | A wholesaler between broker and carriers. Warner Pacific is the GA this team uses; one request to Warner reaches many carriers |
| **Plan** | One specific product from one carrier on one line (e.g. "Aetna Open Access HDHP 3300") |
| **Plan design** | The plan's benefits: deductible, out-of-pocket maximum, copays, coinsurance, prescription tiers |
| **SBC** | Summary of Benefits and Coverage — a standard 4–8 page plan summary every carrier publishes |
| **Current plan** | A plan the employer has in force today |
| **Renewal** | The current carrier's offer to keep the same plan design next year, at new rates |
| **Alternate** | A competing plan from any carrier, meant to replace a current plan |
| **Tier** | Who a person covers: **EE** employee only, **ES** employee + spouse, **EC** employee + child(ren), **FAM** family. A person may also **waive** (decline) a line |
| **Composite rate** | One monthly price per tier. Monthly premium = Σ (tier rate × people enrolled in that tier) |
| **Unit rate** | A price per unit of benefit, used by life and disability (per $1,000 of coverage, per $10 of weekly benefit, per $100 of payroll) |
| **PEPM** | Per employee per month — a flat price times the number of employees |
| **Contribution** | What the employer pays toward each tier's rate; the employee pays the rest |
| **Census** | The list of employees and dependents with birth dates, ZIP codes and tier elections. Carriers price from it |
| **Enrollment** | How many employees are in each tier of each plan |
| **Typed summary tier counts** | Enrollment typed in the Advisor per tier (EE, ES, EC, FAM) when there is no census: on a current plan, or as one figure for the whole line (`LineEnrollment`) (F85, F88). Quotes often arrive before intake, a census or a questionnaire; on such a **quote-first** deal these counts price every quote. A later census import replaces counts typed before it, unless someone chooses "Keep my typed counts" (F91, OQ18) |
| **RFP** | Request for proposal — the package sent to carriers asking for quotes |
| **Quote** | A carrier's priced offer |
| **BOR** | Broker of record letter — the employer's signed authorization for this agency to represent it |
| **Funding** | *Fully insured* (fixed premium), *level-funded* (fixed monthly payment, employer funds claims with a stop-loss backstop) or *self-funded* (employer pays claims, buys **stop-loss** insurance against large claims) |
| **Level-funded split** | Each fixed monthly payment of a level-funded plan splits into a claims fund and fixed costs (administration and stop-loss premium). The Advisor shows the share that funds claims as "% to claims" (F107) |
| **Stop-loss** terms | **Specific** stop-loss pays one person's claims above the **specific deductible**; **aggregate** stop-loss pays the group's claims above the **attachment** (expected claims times a corridor, never below a quoted minimum). A **laser** is a higher specific deductible a carrier sets for one named claimant; `sl_lasers` is claimant data (§3.8). **MAL** (maximum annual liability) is the most the employer can pay in a year: stop-loss premium, administration, the aggregate attachment and the extra laser liability. A **TPA** (third-party administrator) pays the claims and quotes beside the stop-loss carrier (F98–F107, J94) |
| **Small / large group** | Fewer than 51 / 51 or more enrolled employees. Changes which carriers and forms apply: the team sends small groups through Warner Pacific and goes direct to carriers for large groups. The app counts one **headcount** for every band, tier and printed count: the Advisor's medical enrollment, else intake's enrolled count, else eligible or total employees as an estimate (`quotes.facts.enrolled_headcount`; O.6 #24, OQ21, OQ53). Carriers check ATNE near the threshold |
| **ATNE** | Average total number of employees in the prior year — decides small vs large group under insurance rules |
| **Medical questionnaire** | A carrier's health questionnaire about the group, signed by an officer of the employer before large-group or self-funded quotes. Three forms are built: Florida Blue 51+ (chosen by the size band), Warner Pacific's large-group form (a producer's pick) and the SIIA stop-loss disclosure (opt-in) (G1, OQ5). Its medical answers are PHI |
| **Commission** | What the carrier pays the agency: a percentage of premium, a flat amount, or PEPM |
| **Split** (party, house share) | Who shares the agency's commission on a deal. A **party** is a producer (someone on the team) or an outside partner such as a referral agent. The **house**, the agency itself, keeps its percent; partners and other producers take their shares of the rest, and the **primary producer** keeps what is left (H10–H12, H.6) |
| **Quote-blocking** | An intake answer carriers need before they will quote |
| **PHI** | Protected health information. In this app: anything identifying a census member (name, SSN, date of birth, address, salary), medical answers on a questionnaire, stop-loss lasers, and the files that carry such data (§3.8). Strict handling rules apply |
| **Recommendation** ("the firm's pick") | For each current plan, the option or options the agency puts forward to replace it — sometimes two or three, for the client to choose between — or the current plan itself, "Keep this plan" (OQ37, as the old app did). Every shopped line on an issued proposal carries one; a line kept as it is needs none (J52, OQ37; §5) |
| **Star** (★) and **presented plans** | ★ puts a plan on the proposal. A line's presented plans are its current plans, its recommended plans and its starred plans, or every plan when none is starred. A line presents at most 16 columns, current plans included (`presented()`, `room()`; F50, F119, J1–J3) |
| **Package** | A set of plans on one line that the client would buy together, totalled and compared with what they have today — only when it covers the same people (§5) |
| **Priced version** | A copy of a quote at other terms (a % or $ concession, a bundling condition, a premium holiday), kept behind its original and priced for the same people. It shows one plan at several premiums (F76–F84) |
| **Option number** | The number client files print over each renewal and alternate ("Option 3"), counted per line in page reading order, stamped when the proposal is issued and never reused. Current plans and priced versions have none (J159, OQ35, OQ36) |
| **One-column pair** | Two plan numbers a carrier sells as one plan, such as Florida Blue 5182 and 5183: two plans in the data and on working screens, one column in client files, priced together by `package()` (D-219, J15, O.6 #4, OQ42) |
| **Work with Claude** | The AI assistant on each deal (✦ Work with Claude). It reads quotes, renewals and SBCs into the Advisor and holds chats that propose changes. A quote read by an admin or a direct person (`claude_direct`) lands at once, with Undo; anyone else's waits for review (D1, D71, OQ4; §10) |
| **Agenda step** and **next step** | One thing a deal needs next (import the census, read the quotes, issue the proposal…), worked out from the deal's facts. The first live step is the deal's next step. People can hold a step until later, count it done, or add their own tasks (Part I; I42) |

**Words that look alike.**
- *New client* is a client status; *New business* is a deal type. The old app's "New clients" home list showed open
  new-business deals, which are prospects in these terms, so 2Vantage calls that view **Prospects** (§8). v1.1's
  client values `new` and `existing` are retired.
- *Renewal* is a plan's role (the current carrier's offer for next year), a deal type (a deal for an existing
  client), and the workflow that carries a client into its next plan year, which is deferred (OQ1).

---

## 3. Technical foundation

Part O fixes where everything lives, and this section states it as rules. The M0–M6 baseline was built before the
port was planned. Where its code differs from this section (the 50 MB upload cap, slice 15; content types from
`mimetypes`, slice 15; Activity rows without before and after, slice 5; CSS modules, slice 4), this section is the
design, and the slice named changes the code (E.5 #27–42, F.5 #27–38, J.5 B27–B36, M.5 B33–B36; §6 and §13.3 list
the rest). "Slice N" says when a piece arrives (§13). Untagged text in §3 is the design, not a claim that it is built:
§6's "Built in 2Vantage today" column, §7's "built" cells and §13 say what exists.

### 3.1 Stack

| Layer | Choice | From | Notes |
|---|---|---|---|
| Language | Python 3.12 | built | |
| Web framework | Django 5.2 (LTS) | built | |
| API | Django REST Framework 3.16 | built | Django session authentication (§3.8) |
| Database | PostgreSQL 15 | built | JSONB for value dictionaries |
| Server | gunicorn 23 (production), `runserver` (local) | built | |
| Job worker | `manage.py run_worker`, the backend image run as its own service | slice 16 | Runs every job (reads, chat turns, re-checks, Rank, locate, the Issue build), so no long call runs inside a web request (§3.4, §10; O.3.3) |
| Spreadsheets — writing | XlsxWriter 3.3.0 | slice 15 | Generated workbooks (the client proposal workbook, the stop-loss workbook, the Book export) go through `documents/xlsx_safe.py` (§3.8); every formula is written with the app's number as its stored result (§9) |
| Spreadsheets — reading, templates | openpyxl 3.1; xlrd 2.0.1 (the old app's) for `.xls` | built; xlrd: slice 15 | Reading imports and the sheet viewer; the plan template and census templates. Carrier templates are filled by XML patching, never re-saved by openpyxl (§9). A legacy `.xls`, which openpyxl cannot open, reads through xlrd (E29) |
| PDF — writing | reportlab 4.2.5 | slice 29 | The client PDF, through platypus's public API with our own flowables (J122); `deals/pdfkit.py` (letterhead, RFP cover); questionnaire stamps (G.6) |
| PDF — reading | pypdf 5 | slice 15 | Page counts at upload; the locator's page text; Paper and Letter placement at 75% (J114); AcroForm read-back (G.6). No server OCR (D-122) |
| PowerPoint | python-pptx 1.0.2 | slice 31 | Replays the PDF's recorded frames (J141) |
| Images | Pillow | built (logo re-encoding in `deals/admin.py`; `documents/images.py` for covers and photos, slice 34) | Logo, cover and photo re-encoding, metadata stripped |
| AI | anthropic SDK (Python) 2.8.0 (API version 2026-10-21, httpx2) | slice 18 (built) | Only `ai/client.py` imports it: Messages API only, streamed, structured outputs, adaptive thinking with effort per job kind; no beta features, no Files API (§10; D.6, O.3.3). The client is built only from `settings.ANTHROPIC_API_KEY`, passed explicitly, so the SDK never falls back to an environment variable or an `ant` profile |
| Frontend | React 19, React Router 7, Vite 6 | built | |
| Data fetching | TanStack Query 5, axios 1 | built | |
| Styles and fonts | The old app's stylesheets; IBM Plex Sans and IBM Plex Mono, 400–700 | slice 2 | §3.9; O.5, A.6 |
| Viewers | pdfjs-dist 5 (legacy build, bundled worker); tesseract.js 7.0.0 with tesseract.js-core 7.0.0 and @tesseract.js-data/eng 1.0.0 (the old app's 7) | slice 15 (OCR: 65, built) | One pdf.js build serves the Documents viewer and the Export viewer (E22, J105). tesseract.js's worker, LSTM cores and English data are served from our own origin (`frontend/ocrFiles.js`: Vite in development, `/static/ocr/` in a build), never a CDN, and OCR only draws on scanned pages and images (E25) |
| Tests | pytest 8, pytest-django; Vitest | built (Vitest: 6) | §12, Part Q. pytest-xdist joined in slice 39, when the serial run passed 45 s (Q.2): the whole suite runs `pytest -n 8 --dist loadfile`. Vitest covers pure frontend modules only |
| Lint | ruff; import-linter (`lint-imports`); ESLint 9 with react-hooks; stylelint | built (import-linter: 6; stylelint: 2) | import-linter holds the chain contract (§3.3); stylelint refuses undefined custom properties (§3.9) |
| Acceptance harnesses | `browser/`: playwright-core driving the installed Chrome. `tools/parity/`: a tools image with headless LibreOffice, poppler and the Python readers | slice 3 | The Look, Walk, Recalc and Fidelity lanes (§12; Q.2, Q.5). Never in the app image |
| Production serving | WhiteNoise 6.12; django-storages[google] 1.14 (Cloud Storage) | slice 69, staging (§11; built, Google Cloud not connected) | WhiteNoise serves `.mjs` as JavaScript, which pdf.js needs (E.6); Google's libraries load only when a bucket is named |
| Microsoft 365 sign-in | PyJWT 2.15 (with cryptography and requests, already pinned) | slice 47 (built, Microsoft 365 not connected) | `accounts/oidc.py`: OpenID Connect's code flow with PKCE, our own (one module); PyJWT verifies the ID token (RS256, Entra's published keys, issuer, audience, expiry). mozilla-django-oidc 5.0 was weighed and left: it skips the audience and issuer checks, and its sessions ignore `is_active` (§3.8) |
| Containers | Docker Compose (local) | built | Cloud Run later (§11) |

Versions are pinned exactly in `requirements.txt` (`==`) and `package-lock.json`. A library is added in the slice that
first needs it, never earlier. The old app's file writers keep its versions (reportlab 4.2.5, python-pptx 1.0.2 and
XlsxWriter 3.3.0), so the Fidelity lane compares our code, not library versions (O.3.6, Q.5). They move only after
cutover.

### 3.2 Repository layout

```
2Vantage/
  plan.md  CLAUDE.md  README.md
  docs/porting/   the approved porting plan: Parts A–Q, decisions.md (the open-question register), verification.md
  .gitignore  .gitattributes  .dockerignore  .env.example
  docker-compose.yml  Dockerfile  start.sh  requirements.txt  manage.py
  pytest.ini  ruff.toml  .importlinter (the chain contract; slice 6)
  conftest.py     root fixtures: users, clients and deals (built); the golden deals and the socket guard (slice 3);
                  the Q.3 contract helpers (slice 5)
  backend/        Django project package; the composition root (§3.3)
                  settings.py  settings_test.py  urls.py  wsgi.py  asgi.py
                  health.py  checks.py  middleware.py  meta.py
  accounts/       sign-in API over Django's sessions (built); Profile (claude_direct, commissions_access; slice 6)
  deals/          built: Client, Deal, Activity, AgencySettings; lines, stages, clock, values, activity, services,
                  selectors, downloads, admin. Later: Contact, Note (38); lifecycle, rules, carriers, providers (6);
                  comp (11); contacts (38); pdfkit (29)
  documents/      built: Document; kinds. Later (slice 15 unless named): review_rules (17), screening, pages, sheets,
                  locate/ (16), images (34), xlsx_safe
  ai/             Job, DealAi, Chat, ChatMessage, CarrierNote; registry, client, reading, ranges, turn, land,
                  budget, pricing, worker, testing (the fake client), eval/ (slices 16–24)
  intake/         Intake, CurrentCoverage; form (the questions), values, validation, coverage, checklist, providers
  census/         Member, CensusImport, CensusSettings, CensusFacts; fields, importer, pivot, matching,
                  validation, rollup, template
  quotes/         Plan, Package, LineEnrollment, SavedView, QuoteLayout; fields, values (cleaning), packages
                  (`package()`), template (§9.3); services/ (plans, marks, roles, ordering, priced, review, enrollment,
                  saved_views; today services.py and marks.py; slice 7, F.6); selectors/ (today selectors.py);
                  math/ (math.py until slice 7); presented, order, slots, facts, signals (7); labels (25);
                  providers (36); the reader modules (18), revert (5), the board export (9), the stop-loss workbook (36)
  questionnaire/  Questionnaire; forms/, engine/, prefill, choice, checks, pdf/
  commission/     Party, Settings, Commission, ClientSplit, Record; math, rules, visibility, booking
  rfp/            RfpRequest; carriers, formats/, forms/, xlsx/, cover, packet, drafts, eml, check/
  proposals/      ProposalConfig, ProposalIssue, ProposalTemplate, FirmPages, TeamMember, CoverImage; catalog,
                  config, pages, client_facts/, ready, checks, story/, layout/, paint/, workbook/, viewer/.
                  Built today: selection, preview and formatting (retire in slice 25); golden and golden_data
                  (move to golden/ in slice 3)
  review/         ClientRequest, ClientLink, ReviewNote, Seen; rules/, owners, portal/ (the public client portal)
  agenda/         StepMark, Task; catalogue, rules, steps/, marks, rows, queue/ (the Work queue)
  overview/       no models: the Overview payload for one deal, and for one client (slice 67)
  golden/         seed only: seed_golden, one JSON spec per golden deal with its parity profile, the signed keys
  assets/         binary assets (Appendix A): carrier templates, the ZIP crosswalk, questionnaires/, stock covers
  tools/parity/   old Vantage as its own Compose project, the tools image, old_loader.py, files.py, intended.yaml
  browser/        the Look and Walk harnesses (playwright-core): look/ (dropped.yaml, accepted.json), walk/
  frontend/
    Dockerfile.dev  vite.config.js  eslint.config.js  package.json  index.html   (built; the production SPA build
                    is a stage of the root Dockerfile, slice 69, §11.2)
    src/
      main.jsx  App.jsx
      api/        client.js (CSRF), query keys, one module per backend app
      auth/       AuthProvider, LoginPage, RequireAuth (built); RequireAdmin and RequireCommissions arrive with
                  the first page that needs each (`/commissions`: slice 48)
      pages/      Layout/ (AppShell from slice 4), DashboardPage/ (home views), DealPage/ (DealShell from slice 4),
                  NotFoundPage/ (built); ArchivedPage/ (38), CommissionsPage/ (48), ClientPage/ (67)
      deal/       one folder per tab: overview/ agenda/ review/ intake/ census/ questionnaire/ rfp/ commission/
                  advisor/ proposal/ documents/; claude/ (Work with Claude); shared/
      portal/     the client portal, with its own axios instance
      viewer/     PDF, image and sheet viewers
      grid/       the shared grid (O.3.5)
      valuereview/  review lists, the bulk bar, review hotkeys, marks
      exportcheck/  the check before a carrier file or form downloads
      voice/      dictation into the Claude composer (slice 66)
      ui/         shared components, on the old class names
      lib/        format.js, download.js, errors.js, useDebouncedValue.js (built); findText.js (slice 23)
      styles/     the old stylesheets: <old sheet>/NN-topic.css (≤ 300 lines each) and one manifest (slice 2;
                  today tokens.css and base.css, which go in slice 4)
```

Apps arrive in the slices §3.3 lists. A tab folder takes its app's name, except `advisor/` (quotes) and `proposal/`
(proposals). From slice 4 its `index.js` exports only what other tabs mount (O.4).

**Every backend app has the same shape:**

| File | Holds | Rule |
|---|---|---|
| `models.py` | Models | No business logic beyond trivial properties. Plan, Member, Task, Note and Document hide removed rows in their default manager; `all_objects` serves links and history (O.3.7) |
| `services.py`, or a `services/` package re-exported from its `__init__` (OQ9 d) | Every write | Runs in a transaction, locks in the lock order (§3.7), takes the acting user, writes values only through `deals/values.apply()`, records Activity with before and after, registers its area's reverter, and returns only what changed |
| `selectors.py` | Reads and response payloads | No writes. A one-to-one row that does not exist yet reads as its defaults; only a write creates it (O.2) |
| domain modules (`rules.py`, `validation.py`, `math/`, …) | Pure functions | No database access; table-driven tests (Q.1) |
| `summary.py` | `summary.facts(deal_ids) -> {deal_id: dict}` | Counts, dates and flags only, in a fixed number of queries. Read by agenda, overview and golden (O.2) |
| `providers.py`, `signals.py` | The seams a left app owns (§3.3) | Each provider has a default answer |
| `views.py` | DRF `APIView`s | Thin: parse request → call a service or selector → respond |
| `apps.py`, `urls.py`, `admin.py`, `tests/` | | `apps.ready()` fills the seams of apps to the left (§3.3) |

### 3.3 App dependency chain

```
accounts → deals → documents → ai → intake → census → quotes → questionnaire
         → commission → rfp → proposals → review → agenda → overview → golden
```

An app MAY import from apps to its left and MUST NOT import from apps to its right. Migrations follow the same
direction. An import-linter "layers" contract fails the Lint lane on any import to the right (slice 6); each later app
joins it in the slice that creates it. `backend/` (settings, URLs, `/api/meta/`) is the composition root and may
import any app. Only `seed_golden` and the root `conftest.py` import `golden`.

Examples: `census` reads `intake` (requested lines decide required columns); `quotes` reads `census` (rollups price
plans) and owns `facts.py`, which `questionnaire` and `rfp` read; `rfp` prints questionnaire files and commission's
requested rates; `proposals` prints "Markets checked" from `rfp`; `agenda` and `overview` read every app, and nothing
reads `overview`. O.1 gives the reason for each app's place.

A fact read by an app MUST live in that app or one to its left. So the firm's recommendation lives on `Plan`
(`quotes`), not in `proposals`: the Advisor and `commission` read it.

**Crossing to the right.** A left app never imports a right app. It owns a seam that the right app fills in
`AppConfig.ready()`:
- a **provider slot**: one function with a default answer, so the left app runs and passes its tests before the right
  app exists;
- a **registry**: many entries of one shape;
- an **on-commit signal**, sent with `transaction.on_commit(..., robust=True)` and `send_robust`. A receiver that fails
  leaves visible state ("not booked"), never a hidden error (N.3 #6).

| Seam (owner) | Filled by | Used for |
|---|---|---|
| `intake.providers`: `headcount`, `census_state`, `questionnaire_items`, `quote_lines` | quotes, census, questionnaire | the checklist tier, "Census OK", form rows, line states and the lines off the proposal; `quote_lines` also gives each line's current carrier and funding (`current`), which a coverage row shows read-only (§6.5; slice 11); `headcount` is quotes' `facts.headcount` (§5.7; slice 13) |
| `census.providers.carrier_required` | rfp | carrier-required census columns |
| `intake.signals.coverage_changed` | census | sent inside intake's write when the lines to quote or a coverage row changed; census rewrites `CensusFacts` in that transaction, because the required columns follow the lines and medical's in-force answer (§5.3.3; slice 12) |
| `quotes.providers.disclosure_state` | questionnaire | the stop-loss workbook's Binding Notes (G117) |
| `quotes.signals.sold_changed`, `plans_changed` | commission, proposals | booking a sale; clearing the Plans card marks |
| `rfp.checks.providers` | review | the export check and its `?ack=` digest |
| `ai.registry` | intake, census, quotes, questionnaire, proposals, review | readers, job kinds, context, chat tools, locate hooks (§10) |
| `deals.activity.reverters` | every app that writes | Undo and Revert (§3.7) |
| `deals.providers.client_has_sold` | quotes | Back to prospect's refusal while a plan is sold (§5.1; slice 6) |

O.1 gives each seam's shape. A left app's pure rules take the right app's fact as an argument, for example
`checklist.tier(headcount)`; only its services and payloads call the provider. Calls from right to left are ordinary
imports: rfp calls `census.refresh_facts`, review calls the owners' services, a landing calls the owner's `apply`,
Issue calls `stamp_option_numbers` and `advance`, and quotes' `set_sold` calls `deals.services.sale_changed`, which
moves the client status (§5.1). Agenda, overview and golden import each app's `summary.facts` directly; `deals` has
no summary registry (O.6 #3).

**The chain orders imports, not screens** (OQ9). The deal sidebar keeps old Vantage's order and groups exactly (A21):
Overview, Agenda; **1 · Get to Market**: Review & requests, Intake, Census, Questionnaire (only when the deal has a
form), RFP, Commission; **2 · Quote to Close**: Advisor, Proposal; **Shared**: Documents. Because `quotes` sits left of
`questionnaire`, and every enrollment and headcount read falls back to typed summary tier counts (O.6 #24), the
Advisor and Proposal work with no intake, census or questionnaire at all (F85–F92, need 6).

**When each app arrives.** Built in M0–M6: accounts, deals, documents, quotes, proposals. Then golden (slice 3, moved
out of proposals), intake (11), census (12), ai (16), rfp (26, holding only `RfpRequest` and `asked_by_line` until
slice 44), questionnaire (42), commission (48), review (53), agenda (60) and overview (62).

### 3.4 Local environment

| Service | URL / port | Image |
|---|---|---|
| frontend (Vite dev server) | http://localhost:4001 | `frontend/Dockerfile.dev` (Node 22) |
| backend (Django) | http://localhost:8004 (container 8000) | `Dockerfile` (Python 3.12-slim) |
| worker (`manage.py run_worker`, built in slice 16) | no port | the backend image |
| db (Postgres) | localhost:5436 (container 5432), database `vantage2` | `postgres:15` |

These ports deliberately differ from the older Vantage app (4000 / 8003 / 5435) and other local stacks
(5432–5434, 8000–8002, 3000–3001) so everything can run side by side.

**docker-compose.yml** (shape):

```yaml
services:
  db:
    image: postgres:15
    command: ["postgres", "-c", "recovery_init_sync_method=syncfs"]   # quick crash recovery (built)
    stop_grace_period: 60s
    ports: ["5436:5432"]
    environment:
      POSTGRES_DB: ${DB_NAME:-vantage2}
      POSTGRES_USER: ${DB_USER:-vantage}
      POSTGRES_PASSWORD: ${DB_PASSWORD:-vantage-dev}
    volumes: [pgdata:/var/lib/postgresql/data]
    healthcheck: {test: ["CMD-SHELL", "pg_isready -U ${DB_USER:-vantage} -d ${DB_NAME:-vantage2}"],
                  interval: 5s, timeout: 5s, retries: 10, start_period: 60s}
  backend:
    build: .
    ports: ["8004:8000"]
    volumes: [".:/app", "media:/data/media"]
    environment: &backend-env
      ENVIRONMENT: local
      MEDIA_ROOT: /data/media
      DJANGO_DEBUG: "True"
      DJANGO_SECRET_KEY: ${DJANGO_SECRET_KEY:-dev-only-not-secret}
      DB_NAME: ${DB_NAME:-vantage2}
      DB_USER: ${DB_USER:-vantage}
      DB_PASSWORD: ${DB_PASSWORD:-vantage-dev}
      DB_HOST: db
      DB_PORT: "5432"
      FRONTEND_URL: http://localhost:4001
      AGENCY_TIME_ZONE: ${AGENCY_TIME_ZONE:-America/New_York}
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:-}      # empty: no Claude (slice 18)
    depends_on: {db: {condition: service_healthy}}
    restart: unless-stopped
  worker:                                         # slice 16: runs queued jobs (O.3.3)
    build: .
    entrypoint: ["python", "manage.py", "run_worker"]
    volumes: [".:/app", "media:/data/media"]
    environment: *backend-env
    depends_on: {db: {condition: service_healthy}, backend: {condition: service_started}}
  frontend:
    build: {context: ./frontend, dockerfile: Dockerfile.dev}
    ports: ["4001:4001"]
    volumes: ["./frontend:/app", "/app/node_modules"]
    environment: {VITE_API_PROXY: "http://backend:8000"}
    depends_on: [backend]
volumes:
  pgdata:
  media:
```

**The worker** claims jobs from the database, so it needs no port. It does not reload when code changes: run
`docker compose restart worker` after changing code it runs. Tests never need it; they run jobs inline (§3.5). Built
in slice 16 as above, with `restart: unless-stopped`; SIGTERM ends it at the running job's next step and puts that job
back in the queue, so a worker restart loses nothing, and a backend restart never touches a running job.

**Old Vantage beside 2Vantage (slice 3).** `tools/parity/` runs the old app (Django 4.2) as its own Compose project:
its code at the commit the port follows (891f1b3, §13.3), mounted read-only; its own database and media volumes; an
internal network; a dummy AI key; its own ports, never 2V's. It holds synthetic data only: `tools/parity/old_loader.py`
loads each golden spec's parity profile through `manage.py shell`, and `seed_golden` loads the same spec into 2V
(Q.5). The tools image (headless LibreOffice, poppler and the Python readers) recalculates, rasterizes and reads back
both apps' files for the Recalc and Fidelity lanes; `browser/` drives the installed Chrome against both apps for the
Look and Walk lanes. Neither harness opens `aBenefitsMeetings/` or any real client file (Appendix A). The old app is
switched off at cutover (OQ100).

**Where the repository lives.** Today the repository sits in a OneDrive-synced folder. A synced folder can corrupt
`.git`, and anything written under the repository is copied to the sync service, so moving the repository out of it
is RECOMMENDED. Either way, nothing the app or its tests write goes under the repository: uploaded files live in the
`media` Docker volume, test media in a temporary directory (§3.5), harness output (screenshots, recalculated and
rasterized files) outside the repository (Q.2); pytest runs without its cache folder and Python writes no `.pyc`
files.

**vite.config.js:** dev server on port 4001 (`strictPort: true`, `host: true`); **file watching by polling**
(`watch: {usePolling: true, interval: 300}`) because file-change events from a Windows host do not reliably reach
containers; proxy `/api`, `/admin`, `/accounts` and `/static` (Django admin's styles) to `VITE_API_PROXY` (default
`http://localhost:8004`). The proxy
keeps the SPA and the API on one origin, so the session cookie works unchanged (§3.8).

**Dockerfile (backend):** `python:3.12-slim`; `PYTHONDONTWRITEBYTECODE=1`, `PYTHONUNBUFFERED=1`; a non-root user
`appuser` (uid 1000); create `/data/media` owned by `appuser` (a new named volume inherits that owner); install
`requirements.txt`; `COPY --chown=appuser:appuser . .`; `EXPOSE 8000`; `ENTRYPOINT ["/app/start.sh"]`. No compiler
or Postgres client is needed (`psycopg2-binary` ships wheels).
The worker runs the same image with the entry point `python manage.py run_worker`. LibreOffice and poppler stay out of
this image; they live in the tools image (§3.1). Since slice 69 the Dockerfile has stages: `python` and `backend` make
this image, the default target (`local`) that Compose builds; `spa` builds the SPA on Node 22 (`vite build
--base=/static/`); `production` (`docker build --target production --build-arg GIT_SHA=<commit>`) is `python` plus
the code without `frontend/`, the built SPA in `/app/spa`, static files collected at build, `ENVIRONMENT=production`
and `GIT_SHA` (§11.2; deploy/README.md).

**start.sh:** if `ENVIRONMENT=production` (slice 69), by its first argument: `web` (the default) `exec gunicorn
backend.wsgi:application --bind :${PORT:-8000} --workers 2 --threads 4 --timeout 60 --access-logfile - --logger-class
backend.gunicorn_log.TokenSafeLogger --forwarded-allow-ips '*'`; `worker` runs `run_worker` and answers on `$PORT`
from an empty folder for Cloud Run's start-up probe; `migrate` runs `check --deploy --fail-level WARNING`, then
`migrate --noinput` (the migrations job, §11.2); anything else is run as given. A web instance never migrates or
collects static files at start. Otherwise: `migrate`, then `exec python manage.py runserver 0.0.0.0:8000`.

**.dockerignore** (built): `.git`, `.gitignore`, `.env*` (keep `.env.example`), `media/`, `staticfiles/`, `frontend/`,
`*.md` (keep `README.md`) and `**/CLAUDE.md`, `**/__pycache__/`, `**/*.pyc`, `.pytest_cache/`, `.ruff_cache/`, `.venv/`,
`venv/`. Slice 3 adds `browser/` and `tools/`. Slice 69 names `docs/` (Docker's `*.md` matches root files only) and
lets the production build stage read `frontend/` (§11.2): only `frontend/node_modules/`, `frontend/dist/` and
`frontend/.vite/` stay out.

**.env.example** lists every variable in §3.5 with safe local defaults and no secrets.

**Everyday commands** (all from the repository root):

```bash
docker compose up --build -d
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py createsuperuser
docker compose exec backend python manage.py seed_golden        # the golden deals (golden app from slice 3)
docker compose exec backend pytest                              # Fast lane: whole suite (≤ 60 s)
docker compose exec backend pytest census                       # one app (≤ 10 s)
docker compose exec backend ruff check .
docker compose exec backend lint-imports                        # the chain contract (slice 6)
docker compose exec backend python manage.py makemigrations --check --dry-run
docker compose exec backend python manage.py rebuild_facts      # rewrites stored counts, reports differences (17, 12)
docker compose exec frontend npm run lint
docker compose exec frontend npm run build
docker compose exec frontend npm test                           # Vitest (slice 6)
docker compose exec frontend npx stylelint "src/**/*.css"       # (slice 2)
node frontend/scripts/port-proof.mjs                            # CSS port proof, on the host; reads ../Vantage (slice 2)
docker compose logs -f backend
docker compose logs -f worker                                   # (slice 16)
docker compose restart worker                                   # after changing code the worker runs
```

The acceptance lanes (§12; Q.2) run less often:

```bash
docker compose exec backend pytest -m perf                      # Perf, on GD-Big (slice 7)
docker compose exec backend python manage.py reader_eval --set all   # Eval: live reads, about $20 a run (slice 18)
npm --prefix browser run look -- --screens <key>                # Look, on the host's Chrome (slice 3)
npm --prefix browser run walk -- --need <n>                     # Walk, on the host's Chrome (slice 3)
pytest -m recalc                                                # Recalc, in the tools image (slice 27)
python tools/parity/files.py --deals all                        # Fidelity, in the tools image (slice 28)
```

### 3.5 Settings

`backend/settings.py` is the only module that reads environment variables. Application code reads
`django.conf.settings`.

| Variable | Default | Meaning |
|---|---|---|
| `DJANGO_SECRET_KEY` | `dev-only-not-secret` | Secret key (a deploy check refuses the default in production) |
| `DJANGO_DEBUG` | `False` | `true`, `1` or `yes` turn debug on |
| `ENVIRONMENT` | `local` | `local` or `production` |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma-separated; whitespace stripped. Debug allows all |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | see compose | Postgres connection. `CONN_MAX_AGE = 60` |
| `FRONTEND_URL` | `http://localhost:4001` | Base for client-portal links |
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL` | empty | SMTP; when `EMAIL_HOST_USER` is empty, mail prints to the console |
| `MEDIA_ROOT` | `/data/media` | Where uploaded and issued files are stored locally: a Docker volume, never a folder inside the repository (§3.4) |
| `AGENCY_TIME_ZONE` | `America/New_York` | The agency's time zone. Decides "today" (`deals/clock.py`) and every date printed on a screen or in a file |
| `SESSION_COOKIE_AGE` | `43200` (12 hours) | Sign-in lifetime in seconds (built). OQ107's default; signing the PHI-gate checklist settles it (slice 47, `deploy/phi-gate.md` item 3) |
| `AUTH_OIDC_TENANT_ID`, `AUTH_OIDC_CLIENT_ID`, `AUTH_OIDC_CLIENT_SECRET` (slice 47, built) | empty: off | Microsoft 365 sign-in against the firm's Entra ID app registration (§3.8, §7.2). On when all three are set; the redirect URI is `FRONTEND_URL` + `/api/auth/microsoft/callback/`. `AUTH_OIDC_ISSUER` names another OpenID provider in place of `https://login.microsoftonline.com/<tenant>/v2.0` (a local stand-in) |
| `AUTH_PASSWORD_SIGNIN` (slice 47, built) | `true` | Username and password on the sign-in page and in Django admin. The PHI gate sets it `false`, so Microsoft 365 is the only way in (§11.4 item 3) |
| `GIT_SHA` | `unknown` | Build commit shown by `/api/health/` |
| `GS_BUCKET_NAME` (slice 69) | empty | Set: files live in this private Cloud Storage bucket (`backend/storage.py`, django-storages, whose Google libraries load only then); its `url()` names a path nothing serves, never a signed or public link. Empty: the filesystem under `MEDIA_ROOT` |
| `CLOUD_SQL_INSTANCE` (slice 69) | empty | `project:region:instance`: connect through Cloud Run's Cloud SQL socket at `/cloudsql/<instance>` |
| `DB_SSLMODE`, `DB_SSLROOTCERT` (slice 69) | empty | Staging's private-IP connection: `verify-ca` against the instance's server CA file (§11.2) |
| `ANTHROPIC_API_KEY` | empty | Claude's key: only the Foobalabs organization's key (OQ29). Empty means no Claude: `/api/meta/` has no `ai` section and nothing calls out |
| `AI_MODEL` (slice 18, built) | `claude-sonnet-5-5` | The default model. Reads never use Haiku; Opus 5.5 (`claude-opus-5-5`) is kept to admins and direct people (D91). The golden-deal trial sets the default (OQ31) |
| `AI_EFFORT_<KIND>` (slice 18, built: `AI_EFFORT_READ`, `_RECHECK`, `_TURN`) | turn `low`; read and recheck `high` | Effort for each job kind that calls Claude, until the trial sets them (D.6, OQ31) |
| `AI_READ_LIMIT_USD` (slice 18, built) | `3` | A run's cost cap: past it, a read keeps what it finished and waits; admins and direct people may Run anyway (D53, D24) |
| `AI_DEAL_BUDGET_USD` (slice 18, built) | `25` | A deal's AI budget; admins change it per deal in the drawer (D99, D100, OQ34) |
| `AI_TOTAL_BUDGET_USD` (slice 18, built) | empty: no cap | The cap on the sum of every Claude call this database has recorded (`ai.Call`, the ledger): each call is reserved at its worst case (its input plus every output token it may write, at the model's rates) under one lock before it is sent, and refused with a sentence when that could pass the cap; nothing overrides it. `manage.py ai_spend` shows the total. The development stack passes `20` (Daniel's build-time rule, 2026-11-12); production leaves it unset |
| `AI_MEMBER_DATA_SCREEN` (slice 18) | `False` | On: Claude reads leave out the pages the member-data screen flagged at upload. Off: files are read whole, as the old app does since D-225 (OQ22) |
| `AI_PHI_READERS` (slice 47, built) | `False` | The PHI-gate switch: the census, intake and questionnaire readers (`ai.kinds.PHI_TARGETS`) register only while it is on, after the PHI gate (`ai.registry.register_reader`; OQ29, O.3.3). `settings_test.py` turns it on: test data is synthetic |

Built in slice 18: `settings.py` reads every `AI_*` row above with its default (the PHI-gate switch waits for slice 47),
and `.env.example` lists them in place of its old "Release 2 only" block. Fixed settings: `AI_READ_PARALLEL = 4` (a
read's ranges in flight at once, D51; 1 in tests) and `AI_JOBS_INLINE`.

Other fixed settings: `TIME_ZONE = 'UTC'` and `USE_TZ = True` (storage and API timestamps stay UTC; dates people see use
`AGENCY_TIME_ZONE`); default file storage is the local filesystem (Cloud Storage on Cloud Run is a settings change only,
§11); `DEFAULT_AUTO_FIELD = BigAutoField`; Django admin mounted at `/admin/` for staff; Django's `PasswordChangeView`
and `PasswordChangeDoneView` mounted at `/accounts/password_change/` (nothing else from `auth.urls`). Uploads are capped
at 30 MB (`FILE_UPLOAD_MAX_BYTES`), under Cloud Run's 32 MiB request limit (E7, OQ24; built in slice 15).

**Sessions and CSRF:** `SESSION_COOKIE_HTTPONLY = True`, `SESSION_COOKIE_SAMESITE = 'Lax'`, `CSRF_COOKIE_SAMESITE =
'Lax'`; in production `SESSION_COOKIE_SECURE = CSRF_COOKIE_SECURE = True`. `CSRF_TRUSTED_ORIGINS` is `FRONTEND_URL` plus
`https://` for each of `ALLOWED_HOSTS`, in every environment (built). The CSRF cookie stays readable by the page
(`CSRF_COOKIE_HTTPONLY = False`) so the SPA can send it back as the `X-CSRFToken` header.

**DRF settings:** authentication `accounts.auth.SessionAuth` (DRF's `SessionAuthentication`, which enforces CSRF on
writes, with a named scheme so a signed-out request answers 401, not 403); default permission `IsAuthenticated`;
throttles: anonymous 200/hour, user 5,000/hour, scope `login` 10/minute, and scope `ai_poll` 3,600/hour for the AI
state polls (built in slice 16: the state and job GETs use this throttle alone), so `useAiState` polling every 2 s on
two tabs never uses up the user rate (E.6). The portal
(slice 54) has no authentication classes and its own throttles, keyed by token: `portal_read` 300/hour, `portal_write`
3,600/hour, `portal_poll` 600/hour and `portal_pin` 10/hour on top of the five-try PIN lock. The anonymous rate never
applies to it (L.6). They replace the baseline's single `portal` scope (1,000/hour), which slice 54 removed
(`review/portal/throttles.py`; the count is keyed by the token's hash).

**`backend/settings_test.py`** imports settings and overrides: MD5 password hasher (fast), throttles off,
`ANTHROPIC_API_KEY = ''` and `AI_TOTAL_BUDGET_USD = ''` (slice 18: no test reaches Claude, even with the key in the
container), `MEDIA_ROOT` = a temporary directory, locmem email backend, `django.request` logging at
ERROR. `pytest.ini` points `DJANGO_SETTINGS_MODULE` at it.
The root `conftest.py` adds a socket guard (slice 3), so a test can open only the database socket (Q.2), and jobs run
inline with the fake Claude client of `ai/testing.py` (slice 16; Q.6): `settings.AI_JOBS_INLINE` (a fixed setting,
False; True in `settings_test.py`) runs a started job at once in the request, and `ai.testing.run_jobs()` runs queued
ones when a test turns it off. The fake client joined `ai/testing.py` in slice 18: `FakeTransport`, installed by the root
fixture `fake_claude`, stands where the SDK stands and replays recorded replies keyed by (reader, file hash, range).

**Logging:** one console handler at WARNING. Loggers `anthropic`, `httpx` and `httpcore`, and `httpx2` and `httpcore2`,
which the 2.x SDK uses (built in slice 18), pinned at WARNING: their DEBUG output contains document contents. App loggers at INFO (they
still print only WARNING and above). Never configure the `django` or `django.server` loggers. `disable_existing_loggers
= False`. In production, request logs and error reports drop the `/api/portal/`, `/portal/` and `/b/` paths, whose URLs
carry link tokens (§11, L.6). Built in slice 69: `backend.logs.DropTokenPaths` on the console handler drops a record
whose request or message names one, and gunicorn's `backend.gunicorn_log.TokenSafeLogger` skips a request on one or
from one (its Referer); the SPA's page for a token path answers `no-referrer`, `no-store` and `noindex`.

**Production (slice 69; §11.2):** with `ENVIRONMENT=production`, WhiteNoise follows `SecurityMiddleware` and serves
`/static/` from `CompressedStaticFilesStorage` (`WHITENOISE_MIMETYPES` types `.mjs` as `text/javascript`; Vite's
hashed `assets/` are immutable); `SECURE_PROXY_SSL_HEADER` trusts Cloud Run's `X-Forwarded-Proto`; `SECURE_SSL_REDIRECT`
(except `/api/health/`); HSTS a year with subdomains and preload. `backend/spa.py` answers the SPA's `index.html`
(`no-cache`) for every path outside `/api/`, `/admin/`, `/accounts/` and `/static/`; locally nothing is built and it
answers 404.

**`backend/health.py`** — `GET /api/health/`, plain Django view (not DRF, no throttle), no auth, never cached:
runs `select 1`, counts unapplied migrations (cached once zero), returns
`{"ok": true, "database": "ok", "commit": "<GIT_SHA>", "migrations_pending": 0}` or
`503 {"ok": false, "database": "<ExceptionClassName>", "commit": "…"}`. It reveals nothing else.

**`backend/checks.py`** — Django system checks registered with `deploy=True`, active only when
`ENVIRONMENT == 'production'`: E001 DEBUG on; E002 default secret key; E003 console email backend; E004 the
`ANTHROPIC_LOG` environment variable set to `debug` or `info`; E005 (slice 69) running on Cloud Run (`K_SERVICE` or
`CLOUD_RUN_JOB` set) with no `GS_BUCKET_NAME`, where files would stay on the instance; the PHI gate's order (slice 47):
E006 `AI_PHI_READERS` on while Microsoft 365 sign-in is off or passwords still work, E007 no way left to sign in,
E008 a Microsoft 365 provider not reached over HTTPS. `manage.py check --deploy
--fail-level WARNING` must pass before a release.

**`backend/middleware.py`** — `JsonGZipMiddleware`: Django's `GZipMiddleware`, applied only when the response
`Content-Type` starts with `application/json`. File downloads are never compressed.

### 3.6 API conventions

- Everything lives under `/api/`. Requests and responses are JSON unless uploading or downloading a file.
- **Authentication:** Django's session cookie, set by `POST auth/login/` (§7.2). Every write (`POST`, `PUT`, `PATCH`,
  `DELETE`) carries the `X-CSRFToken` header; a write without it answers `403`. The client portal uses neither: its
  token is in the URL, and its verification travels in the `X-Link-Verification` header (§3.8, L.6).
- **URLs.** Deal-owned collections nest under the deal (`/api/deals/{id}/<area>/`); single objects have flat URLs
  (`/api/plans/{id}/`). The firm-level roots are `/api/auth/`, `/api/clients/`, `/api/activity/{id}/revert/`,
  `/api/archived/`, `/api/documents/{id}/`, `/api/ai/jobs/{id}/`, `/api/plans/{id}/`, `/api/saved-views/`,
  `/api/commissions/`, `/api/proposal/`, `/api/links/{id}/`, `/api/portal/{token}/`, `/api/tasks/{id}/` and
  `/api/work-queue/` (O.2). Each action has one door, in the app that owns the fact (O.6). Trailing slashes everywhere.
- **Ids** in paths and bodies are parsed as integers; a bad one answers 400, never 500 (L.6, H.6).
- **Status codes:** 200 OK · 201 created (a row, or a queued job with its id) · 202 accepted (Issue, whose files
  build in a job; J.6.6) · 204 deleted · 400 validation failed · 401 not signed in · 403 not allowed (missing CSRF
  header; a non-admin on an admin endpoint; a commission tier too low; a staff session writing on the portal) ·
  404 not found · 405 not allowed on this URL (`DELETE clients/{id}/`: clients are archived, never deleted; M104) ·
  409 conflict: a refused action, with its sentence (a lost deal's refusals below; Revert after a later write; a stale
  `expect`; issuing while a shopped line has no recommendation) · 410 gone (an expired, revoked or closed client
  link; a portal write on a lost or archived deal) · 413 file too large · 428 the portal's PIN is needed first (L.6) ·
  429 throttled.
- **Error bodies** use DRF's standard shapes: `{"field_name": ["message", …]}` for validation,
  `{"non_field_errors": ["…"]}` for whole-request problems, `{"detail": "…"}` otherwise. The frontend helper
  `lib/errors.js` turns any of these into display text.
  A refusal's `detail` is a sentence written for the person, and the screen shows it as it is (M10).
- **Pagination** (lists that can grow): `?page=N`, 25 per page unless stated; response
  `{"count": n, "next": url|null, "previous": url|null, "results": [...]}`.
- **Formats:** dates `YYYY-MM-DD`; timestamps ISO 8601 UTC (`2026-11-10T15:04:05Z`). Stored field values are
  strings. Computed money is a JSON number: whole dollars for premiums and totals, two decimals for rates.
- **Writes return only what changed** — the updated object, or a small payload for the tab. Never a whole-deal
  payload.
  A write that can be undone also returns its `activity_id`, which the Undo toast reverts (E54). A value PATCH MAY carry
  `expect`, the values the browser last saw; if a stored value differs, nothing is written and the answer is 409
  naming the keys. The grid's Undo always sends it (J74, O.6 #33).
- **Downloads** are `GET`s that stream a file through `deals.downloads.file_response`. The content type comes from an
  explicit map by extension (xlsx, xlsm, docx, csv, pdf, zip, eml), never from the upload or Python's `mimetypes`
  (built in slice 15, with E17 and K63: `deals.downloads.CONTENT_TYPES`).
  Headers: `Content-Disposition: attachment` (or `inline` under a sandbox CSP for the viewer, E17),
  `X-Content-Type-Options: nosniff`, `Cache-Control: private, no-store`. Zips and `.eml` drafts stream in chunks, so a
  large file never meets Cloud Run's 32 MiB limit (K.5 #39). File names come from `safe_filename` (characters outside
  `[A-Za-z0-9 ._-]` removed) in the patterns of J104 and K.6, such as `<Client> - <year> Benefits Proposal` and
  `<Client> - <Carrier> census.xlsx`. A PHI file downloads under a name built from the client and its kind, never the
  name it was uploaded with (Q.8). A download response is never compressed.
- **A `GET` writes nothing**: it moves no stage, stamps nothing and creates no row. Anything that records an event
  (issuing a proposal, marking a link sent) is a `POST`. The only exceptions are the portal's open stamp and the
  `downloaded` and `viewed` rows of §3.8. A test calls every GET and checks its SQL (Q.3 #2).
- No query parameter may be named `format` (DRF reserves it).
- **Lost deals.** A lost deal keeps its internal edits but refuses what `deals.rules.refuses(deal, action)` lists:
  sending to market, signing, marking sold, booking, portal writes, client asks, automatic AI landing, and Convert to
  client. Each refusal answers 409 with a sentence ("This deal is marked lost — reopen it before …"), and the deal
  shows a banner (§8; O.3.7, A19).
- **Archived clients** leave the lists (`live()` in list selectors only); their pages still open, and their client
  links stay readable but refuse writes (O.3.7, OQ46).

### 3.7 Values, sources and Activity

Values entered about a deal live in JSON on their row, with a parallel `sources` dictionary holding one entry per key
that has a value: `Plan.values`, `LineEnrollment`, `Intake.answers`, `Member.values`, the `Questionnaire` answers, and
the values of commission's `Commission` and `Record` (O.3.1). `deals/values.py` defines the one entry shape:

```json
{
  "deductible_single": {
    "origin": "ai",               // typed | relay | client | ai | import | prefill | sale | in_force | agency
    "by": 3,                      // user id (null for the client)
    "at": "2026-11-20T15:04:40Z",
    "doc": 41,                    // document id, when the value was read from a file
    "page": 2,                    // PDF page, when known
    "cell": "Medical!D12",        // sheet cell, for spreadsheet imports and reads
    "line": "Deductible $3,300 / $6,600",   // the printed line it came from (≤ 300 characters)
    "link": 7,                    // client link id, for origin client
    "low": "two figures for one tier",      // why the reader doubted it, or null
    "loc": {"state": "found", "page": 2, "hits": 1, "printed": "$3,300", "v": 3, "at": "2026-11-20T15:05:02Z"},
    "mark": {"state": "check", "by": 5, "at": "2026-11-21T09:10:00Z"},
    "confirmed": {"by": 5, "at": "2026-11-21T09:12:00Z", "via": "recheck"},
    "read_value": "3300"          // what the reader read
  }
}
```

Origins: `typed` (a person typed it), `relay` (a person entered the client's answer for them), `client` (the client's
answer, approved), `ai` (Claude read it), `import` (a spreadsheet import), `prefill` (filled from the deal's facts,
then frozen; G27), `sale` (booking at the sale; H27), `in_force` (the current coverage's commission; H26) and `agency`
(the agency's default rate). `line` is never kept on census or questionnaire values, and `read_value` only on plans the
reader made (F141). `loc` is the locator's result: found, derived, weak, absent or nocheck, with where and why (E81).
`mark` is a person's review mark (ignored or check); `confirmed` is a person's approval.

Rules:
- **`deals/values.apply()` is the only writer** of these dictionaries (O.3.1).
- **Writing a value equal to the stored value, after cleaning, changes nothing:** not the value, not its source, not
  the Activity log. Re-importing an exported template or an unchanged census therefore stamps nothing and confirms
  nothing. Import dry runs report `cells_changed` as well as people or plans.
  The row's `updated_at` does not move either (Q.3 #1).
- Writing a changed value replaces its source entry, with one exception: a typed value over a read one keeps `doc`,
  `page`, `cell`, `line` and `read_value`, so the value still opens its file, and drops `low` and `loc` (E66, F141).
  Any change drops `mark` and `confirmed`, so a mark or an approval never outlives the value it was given for.
- An empty string clears a value and its source entry. `null` reverts a typed value to the one that was read (A33).
- **Client answers wait.** A client's answer waits in the row's `client` JSON,
  `{value, confirm, link, at, status, by, decided_at}`, with status pending, approved, rejected or replaced; census and
  questionnaire entries add `prior`. Only approval moves an answer into the values, with origin `client`, and a typed
  write closes a pending entry as `replaced`. Rollups, readiness, exports and printed PDFs read approved values only
  (O.3.1, L.6).
- Values are stored as strings, normalized by the field's type on write (§5).
- **Status is computed on read:** `missing` (required and blank, with no client answer pending) · `blank` (optional
  and blank) · `to_check` (an open warning: a person marked it "check", or Claude read it and doubted it (`low`) or
  the locator could not find it in its file (`loc` absent or weak), and no one has approved or ignored it;
  `documents.review_rules.open_warning` is the one rule, OQ28) · `ok` (everything else). Only Claude's values need a
  person's look (OQ28, answered 2026-11-11): a typed or imported value the file does not print is never `to_check`,
  though the station lists it under "Not in the file". An open warning never blocks anything: it is a count ("N to
  review") and a colour.
- **Stored counts** are one exception (OQ9 c): `census.CensusFacts`, and `flags` (open warnings) on Plan, Intake
  and Questionnaire. The owner rewrites them in the same transaction as the write; `manage.py rebuild_facts` and a test
  rebuild them and compare (O.3.7, Q.3 #9). `rebuild_facts [--deal ID] [--fix]` lives in the composition root
  (`backend/`): it checks census's facts (slice 12) and every count an owner registers in `deals.stored_counts` from
  `AppConfig.ready()` (slice 17: `Plan.flags`, which `Plan.save()` stamps; `Intake.flags`), and exits 1 on a
  difference it did not fix. The client status is the other (§5.1, OQ2): a hand conversion has no
  sale to compute it from.
- **Concurrent writes.** Two requests that each read a row's dictionary, set one key and write the whole dictionary back
  would erase each other's key, and a transaction at Postgres's default isolation does not prevent it. A service that
  changes `values`, `answers`, `enrollment`, `client` or their `sources` MUST load the row with `select_for_update()`
  inside its transaction, or apply the change as a single SQL JSONB merge. Two concurrent writes to different keys of
  one row both survive (a required test, §12).
- **Lock order.** A write that spans rows or owners locks the Deal row first, then owner rows in chain order (§3.3),
  each by id; a single-row edit locks only its row. Review's `mark_document`, the portal save and every Revert follow
  it (O.3.7, N.3 #3).

**Activity log.** Every service write is recorded in `Activity` (O.3.2; built in slice 5):
- One row holds `deal` (null for a firm row, which names its `subject`), `area`, `action`, `actor`, `actor_kind`
  (user, client, claude or system), a one-line `summary`, `changes`, `document_id`, `coalesce_key`, `count`, `reverts`
  and `reverted_at`/`by`, plus `revertible`, the stored hint lists read without loading `changes` (values kept, no
  key-only entry, an action Revert can undo). It is indexed on (deal, created_at) and (area, created_at); list
  selectors defer `changes`.
- `changes` holds the value before and after for each changed key (null: no value):
  `[{"t": "plan:41", "k": {"rate_ee": ["612.50", "640.00"]}}]`. Census rows, sensitive questionnaire slots and lasers
  record keys only (`{"t": "member:7", "k": ["dob"]}`); commission values are hidden from viewers below the all tier
  (H.6).
- A summary reads like "Edited 3 intake answers", "Imported census: 152 people (38 dependents)" or "Marked Aetna HMO
  1500 sold". It MUST NOT contain census values, person names or file names; a row about a file carries its
  `document_id` (§3.8).
- A burst of writes by the same actor with the same `coalesce_key` within 10 minutes merges into one row that keeps
  each key's first "before" and last "after" and counts the writes ("Edited 14 plan values"). Review marks, imports,
  issues, sales, stage changes and client status changes never merge.
- **Revert.** `POST activity/{id}/revert/` calls `deals.activity.reverters[area]` in one transaction, in the lock
  order. It writes the old values back through the owner's services, records a new row with `reverts` set, and works
  only once. It answers 409, naming the keys, when a later write changed them. Sold plans, signed forms, issued
  proposals, a client status a sale set, and key-only rows refuse it with a sentence; for key-only edits the grid's
  in-session undo, which holds the old value in the browser, still works. A job's Undo reverts the job's row (D73).
- `deals.activity.log_access(deal, user, action, what, document_id)` writes the `downloaded` and `viewed` rows of
  §3.8. "Last updated" and the feed skip them.

### 3.8 Security and PHI

- **PHI in this app** is anything identifying a census member (names, SSNs, dates of birth, addresses, phone, email,
  salary), medical answers on a questionnaire and stop-loss lasers (`sl_lasers`), **and every file or value that
  carries them**: documents of the PHI kinds (`census`, `claims`, `questionnaire`, `stop_loss`, `stop_loss_quote`,
  flagged `phi` in `documents/kinds.py`; E.6); any other file the member-data screen found people in
  (`Document.screen.lists_members`); census exports and carrier census files; signed questionnaire PDFs; and the RFP
  packet and `.eml` drafts that carry any of these. Invoices are not a PHI kind (OQ27); a list bill that names
  members is caught by the screen. Rules:
  - never written to logs, error text, Activity (`changes` included), Job steps and results, chat messages, file names
    or URLs; values are never sent in query strings, so a search posts its value (E28, Q.8);
  - downloadable only through authenticated endpoints, or by a client through its own link's allowlist;
  - **every download and view is recorded:** `log_access` writes a `downloaded` or `viewed` row with the document id,
    never the file's name; views coalesce per file; these rows never move "Last updated" (E99);
  - SSNs are optional and shown masked (`***-**-1234`); the portal never asks for one (OQ16);
  - never present in test fixtures or seed data: test data is synthetic, and the PHI canaries of Q.8 check every path.
- **Client files** print only `client: True` fields (§4.3) and nothing on J.4's list: commission figures, client
  guidance, star reasons, internal notes, sources, document names, review marks, `sl_lasers` and birth dates (N.3 #10).
  Laser liability, a computed amount, may print on the stop-loss cost rows and workbook; the claimant ids in
  `sl_lasers` never do (§4.3, OQ104). Client-safety canaries read every client file back (Q.8).
- **Before real PHI enters the app** comes the PHI gate, slice 47: signed BAAs with every service that stores or
  processes it (Google Cloud; Anthropic for Claude's reads), sign-in through the firm's Microsoft 365 accounts (so MFA
  and offboarding live there), a check that every PHI download writes its access row, Claude's key confirmed under the
  BAA, and a log scan of staging after a scripted walk with the canary census (OQ29, Q.8, §11). Until then the app
  holds synthetic data and plan templates only.
- **Claude and PHI** (§10; O.3.3):
  - files are read whole, as the old app reads them since D-225. `ai/ranges.py` always leaves out pages that carry
    only the running header and footer, and leaves out the pages the member-data screen flagged only while
    `AI_MEMBER_DATA_SCREEN` is on (OQ22). The screen (`documents/screening.py`) still runs at upload and stores
    `Document.screen`, which drives access logging and the file chip;
  - the SSN scrub, counts-only census context and the questionnaire's answered-or-blank sensitive slots stay; the
    census mapping assist sends column headers and value shapes only (D109);
  - the readers that see member data (census, intake, questionnaire) register only while `AI_PHI_READERS` is on, after
    the PHI gate;
  - only the Foobalabs organization's key is used, and real files are read only after Anthropic confirms in writing
    that the features the readers use are covered by the BAA (OQ29). Until then readers run on synthetic files.
- **Access.** Every signed-in user sees every client and deal; there is no per-deal access control (OQ3, A43). Admins
  (`is_staff`) also reach Django admin and the admin endpoints. Commission ledger figures follow the user's commission
  tier, `Profile.commissions_access`: none, own or all, by default own for a producer and all for an admin (H.6,
  OQ73). Each app keeps a table of endpoint × actor → status code that its tests check (Q.3 #3).
- **Sign-in** uses Django's session framework: `POST auth/login/` calls `django.contrib.auth.login`, the session
  cookie is `HttpOnly` (out of reach of page scripts) and expires after `SESSION_COOKIE_AGE`. Logging out flushes the
  session. Deactivating a user in Django admin ends their access at their next request. No token is stored in the
  browser. **Microsoft 365** (slice 47, built; not connected): `GET auth/microsoft/` sends the browser to the firm's
  Entra ID (OpenID Connect, code flow with PKCE, `accounts/oidc.py`), and the callback verifies the ID token and signs
  in the one active user with the account's email, case ignored (`accounts/firm.py`). Nobody is created at sign-in;
  an unknown email, a user turned off, or an email two active users share is refused with a sentence on the sign-in
  page. The session is Django's, so the same lifetime and deactivation rules hold. At the gate
  `AUTH_PASSWORD_SIGNIN=false` turns passwords off, here and in Django admin.
- **Passwords** go through Django's password validators on every path that sets one. A member changes their own
  password on Django's built-in page (`/accounts/password_change/`); an admin resets one in Django admin. There is no
  self-service reset by email in version 1 (Microsoft 365 sign-in replaces passwords before real PHI).
- **Client links** (`review`, slices 53–54; L.6):
  - one link per person under a request; a token is 32 random-looking bytes, URL-safe (43 characters), and is never
    stored: the row keeps a random seed and the token's SHA-256, the token is the seed signed with the server's key
    (`review.tokens`; slice 53), and the portal finds a link by the hash. Rotating SECRET_KEY ends every open link;
  - a link lasts 7 days, sliding on each save (at most once a day), under a ceiling of 30 days from creation, and can
    be revoked (OQ81);
  - an unknown token answers 404; an expired, revoked or closed link 410, with the agency's contact; a write on a lost
    or archived deal 410; a page that needs a PIN answers 428 until the PIN is given;
  - a phoned PIN is needed when `review.rules.policy.floor(asks)` says so: when the page shows census people or
    questionnaire answers, and for medical or claimant send-backs; an upload-only ask opens with the link alone
    (OQ80). A PIN is shown once, stored hashed, and locks after five tries;
  - the portal has no authentication classes, throttles by token (§3.5), sends only allowlisted payloads, and answers
    with `Cache-Control: private, no-store`, `Referrer-Policy: no-referrer` and `X-Robots-Tag: noindex`. Its GETs
    write only the open stamp. A staff session sees the page but gets 403 on every write;
  - a client's answers wait for staff approval (§3.7).
- **Uploads** go through `documents.services.upload`, the only door (E6, E7, E15, E96):
  - one file per request; the kind is required (a blank kind answers 400), the extension must be on the kind's accept
    list (`documents/kinds.py`), and the file's first bytes must match its extension; at most 30 MB (OQ24); a PDF's
    page count is stored at upload (built in slice 15);
  - stored through Django's storage API under `deals/<deal_id>/<uuid>-<name>` in `MEDIA_ROOT`, never served by a
    public URL;
  - bytes an upload stored are removed if its transaction fails, and a deleted row's bytes go only after commit;
  - Remove archives a file (restorable; values keep their link), and only an admin purges (OQ23). Files that Issue or
    signing marked `protected` refuse both (O.3.7);
  - downloads follow §3.6.
- **Spreadsheet injection.** Text written into a generated workbook stays text. `documents/xlsx_safe.py` is the one
  guard: under XlsxWriter it turns string-to-formula, URL and number conversion off, writes text with `write_string`
  and writes links explicitly (J153); under openpyxl (the plan and census templates) text is a string cell with the
  quote prefix (D114). Carrier templates filled by XML patching write inline strings (K90). In a generated CSV, text
  that begins with `=`, `+`, `-`, `@`, a tab or a carriage return gets a leading `'` (K107). Formulas the code writes
  on purpose are exempt.

### 3.9 Frontend conventions

- **Routing:** `BrowserRouter`; every page component is lazy-loaded (`React.lazy`), so each tab is its own bundle.
  Tabs live in the path (`/deals/:id/:tab`); in-tab state lives in the query string (`?view=`, `?line=`, `?file=`,
  `?doc=&ref=&page=&back=&list=`, `?focus=`, `?form=`, `?claude=read&docs=…`, and the Advisor board's config:
  `?find=&budget=&rule=&slider=&preset=&sort=…`, slice 10). §8.1 lists the routes (O.4).
- **API client** (`src/api/client.js`): one axios instance with `baseURL: '/api'` and `withCredentials: true`, using
  axios's built-in `xsrfCookieName: 'csrftoken'` / `xsrfHeaderName: 'X-CSRFToken'`. The app calls `GET auth/csrf/`
  once at start-up so the cookie exists. A response interceptor, on 401 from any endpoint except `auth/login/`,
  `auth/me/`, `auth/csrf/` and the portal, sends the browser to `/login`; a CSRF 403 refetches the cookie and retries
  once (built). Nothing about the session is kept in `localStorage`.
  The portal has its own axios instance, which sends the link's `X-Link-Verification` token (L.6).
- **Data fetching:** TanStack Query only — no hand-built caches or stores (A27). Query keys follow
  `['deal', dealId, '<area>', …]`, and the client page's `['client', clientId, '<area>']` (slice 67). `/api/meta/` is
  fetched once (`staleTime: Infinity`). **Deal-tab and client-page queries use `staleTime: 0`**, so a tab refetches
  whenever it is opened: a census edit changes Advisor premiums, a plan edit changes the proposal, and no mutation has
  to know which other tabs it affects. Heavy queries (the Documents station, sheet windows, previews) skip refetch on
  focus; previews use `staleTime: Infinity`, keyed on their stamps and enabled only while shown (J107). A write's
  answer holds only what changed: its hook writes it into the cache with `setQueryData` and invalidates its own area;
  `invalidateDeal(id)` refetches only the header and the journey (E53, slice 17; today it refetches every deal query
  but the header, and the client list); N.4 lists what each write refreshes. There are two
  pollers: `useAiState` (every 2 s, slowing to 10 s while jobs run; a finished job invalidates the areas it landed in)
  and review's `usePollStamp` (O.4).
- **Vocabulary** (lines, fields, questions, choices) always comes from `/api/meta/`. The frontend MUST NOT
  hard-code a backend list.
- **No business math in the frontend.** Premiums, totals, readiness and statuses are displayed as the server
  returns them.
- **The look** (O.5; slice 2). Every screen looks exactly as the old app's did, keeping what it rendered (OQ10):
  - the old app's global stylesheets are copied whole, in the old `main.jsx` order and with the old class names
    (`bb-*`, `bnf-*`, `gk-*`, `rr-*` and the rest), and cut at their own section comments into files of at most 300
    lines under `src/styles/<old sheet>/NN-topic.css`. One manifest, imported once from `main.jsx`, lists every file
    in order. A lint script (not a test) proves that each sheet's files, joined, equal the old sheet minus the listed
    edits;
  - sheets of out-of-scope modules stay out; a rule that a kept screen borrows from a left-out sheet is ported at
    that sheet's old position;
  - no CSS modules and no per-route sheets, because either would change the cascade. Every component, new ones too,
    uses the old classes; a part lists the classes it uses and never copies CSS. 2V's `*.module.css` files and
    `tokens.css` go in slice 4;
  - App.css's `:root` block replaces 2V's tokens. Each use of an undefined custom property (`--muted`, `--accent` and
    others) is rewritten to what it rendered, and stylelint refuses unknown properties. Two button rules are fixed:
    `.btn-primary {width: 100%}` moves to the selectors that rely on it, and the first `.btn-sm` goes;
  - fonts are IBM Plex Sans and IBM Plex Mono, 400–700 (A.6). At Milestone 2 a class-usage sweep deletes the rules no
    component uses.
- **Shared kit** (O.4): `src/ui/` on the old classes (Modal, ConfirmDialog, Toast, ErrorBoundary, FactRow, …);
  `FieldInput` (intake, questionnaire, portal); `CellInput` (census, portal); `deal/shared/BuilderCard` (proposals,
  rfp); `src/grid/` (selection, keys, sizes, freeze panes, windowed rows, the write queue and a 50-step per-cell undo
  that writes with `expect`), which serves the Advisor, Proposal, Documents and Census grids (O.3.5); `src/viewer/`;
  `src/valuereview/`.
- **Files stay under 300 lines**, CSS included. Split a component before it grows past that, by responsibility, never
  by line count: each new file holds one idea (the grid's keys, the batch bar, edit mode), and a file that is only
  "part 2" of another is a bug (agreed by Daniel 2026-11-11). Ported stylesheets are cut at their own section comments
  (O.5). **Data modules are exempt**: a module that is only a vocabulary or table (`intake/form.py`, `quotes/fields.py`,
  `rfp/formats/definitions.py`, the header synonym table, `proposals/catalog.py`) stays whole however long it is;
  splitting data by line count is churn.
- **Tests:** Vitest covers pure modules only (for example `gridKeys`, `finder`, `findText`, `pageRows`); screens are
  proved by the Look and Walk lanes (§12, Q.5).
- **Accessibility basics:** every input has a label; keyboard reachable; visible focus; colour is never the only
  signal (pair it with an icon or text).
- No walkthrough or tour code inside product components, and no `data-guide` anchors (A40).

---

## 4. Reference data

These lists are business data. Implement them as Python constants in the module named in each heading. They are
served to the frontend by `GET /api/meta/` (§7.1) and are **never** stored in database tables or created by
migrations. Changing one is a one-line code change.

**Where each list lives.** Each subsection names its source of truth: the module that holds the list once built. Until
the module is built, the table here is normative. When the slice that builds it is committed, the table is replaced by
one line naming the module, and the module is changed from then on (§14). §4.1, the codes and labels of §4.2, §4.3,
and §4.6's stages, funding, document kinds and roles are built already, in the M0–M6 baseline (`deals/lines.py`,
`deals/stages.py`, `quotes/fields.py`, `documents/kinds.py`). A table becomes a pointer once the last slice that changes
it is committed: §4.1 after slice 13 (the `proxy` flag), §4.3 after slice 36 (laser liability and the client flags),
the §4.6 lists after the slices their entries name.

**Generate, don't retype.** Each module is generated once by a script from the old module named in Appendix C (the old
repository at commit 891f1b3), then diffed against its table here; every difference is resolved before the slice is
done (§14; K93, G124). Data modules are exempt from the 300-line rule.

**The data modules**, in chain order (§3.3):

| Module | Holds | Built in | Specified in |
|---|---|---|---|
| `deals/lines.py` | Lines, tiers, funding, enrollment shapes (`ENROLLMENT_KEYS`, `TIER_CODES`; today `quotes/math.py` repeats them, until slice 7 reads them from here) | baseline | §4.1, §4.2, §4.6 |
| `deals/stages.py` | Deal stages | baseline | §4.6, §5.1 |
| `deals/lifecycle.py` | Client status and its moves | slice 6 | §4.6, §5.1 |
| `deals/carriers.py` | Carrier names, aliases and the name matcher | slice 6 | §4.7 |
| `documents/kinds.py` | Document kinds with their flags; document roles | baseline; flags in slice 15 | §4.6 |
| `intake/form.py` | Intake questions and help; the questionnaire catalogue | slice 11 | §4.5 |
| `census/fields.py` | Census columns, groups, choices and help | slice 12 | §4.4 |
| `census/importer.py` | Tier spellings, waiver words, header synonyms | slice 12 | §4.2, §4.8 |
| `quotes/fields.py` | Plan fields | baseline | §4.3 |
| `quotes/board_presets.py` | The Advisor's column presets, sliders and budget rungs | slices 9–10 | §4.3; F20, F31 |
| `questionnaire/forms/` | The three form specs and their layouts | slice 42 | Part G (G.6, G124, G125) |
| `commission/vocab.py` | Commission's own words | slice 48 | §4.6; Part H (H.6) |
| `rfp/carriers.py` | What an RFP needs per carrier; the Warner inbox | slice 44 | §4.7 |
| `rfp/formats/definitions.py` | The four carrier census formats | slice 45 | §9; K93 |
| `rfp/forms/maps.py` | The Warner quote request form variants (`VARIANTS`) | slice 46 | §9; K99 |
| `proposals/catalog.py` | Builder cards and parts, row presets, key rows, card stats, summary blocks, covers, layouts, limits | slice 25 | §4.3; Part J (J.6.3) |
| `proposals/rows.py` | The client files' house row maps | slice 27 | §4.3; Part J (J133) |
| `agenda/catalogue.py` | Agenda steps, sections and their words | slice 60 | §4.6; Part I (I.6) |

### 4.1 Lines of coverage — `deals/lines.py`

**Source of truth:** `deals/lines.py`, built in the baseline from this table. Its `proxy` flag marks the lines that
borrow medical counts; slice 13 makes `enrollment_for` use it (J.5 B35).

27 lines, in this display order. **Field set** chooses the plan fields (§4.3). **Rate basis** chooses the premium
formula (§5.5). **Priced from** says what the formula counts when nothing typed applies; typed counts, volume or lives
come first, in `enrollment_for`'s order (§5.5, O.6 #24).

| Key | Label | Short | Field set | Rate basis | Priced from |
|---|---|---|---|---|---|
| `medical` | Medical | Med | medical | composite | `medical_tier` counts |
| `dental` | Dental | Den | dental | composite | `dental_tier` counts |
| `vision` | Vision | Vis | vision | composite | `vision_tier` counts |
| `basic_life_add` | Basic Life & AD&D | Life | life | volume_1000 | Σ `basic_life_amount` |
| `voluntary_life` | Voluntary Life | Vol Life | life | volume_1000 | Σ `vol_life_amount` |
| `std` | Short-Term Disability | STD | disability | weekly_10 | Σ `std_amount` |
| `ltd` | Long-Term Disability | LTD | disability | payroll_100 | Σ `annual_salary` |
| `voluntary_worksite` | Voluntary / Worksite | Worksite | generic | composite | medical tier counts (borrowed) |
| `hsa` | HSA | HSA | generic | pepm | employee count |
| `fsa` | FSA | FSA | generic | pepm | employee count |
| `hra` | HRA | HRA | generic | pepm | employee count |
| `eap` | EAP | EAP | generic | pepm | employee count |
| `telehealth` | Telehealth | Telehealth | generic | pepm | employee count |
| `voluntary_std` | Voluntary STD | Vol STD | disability | weekly_10 | Σ `std_amount` |
| `voluntary_ltd` | Voluntary LTD | Vol LTD | disability | payroll_100 | Σ `annual_salary` |
| `accident` | Accident | Accident | generic | composite | medical tier counts (borrowed) |
| `hospital` | Hospital Indemnity | Hospital | generic | composite | medical tier counts (borrowed) |
| `critical_illness` | Critical Illness | CI | generic | composite | medical tier counts (borrowed) |
| `legal` | Legal | Legal | generic | pepm | employee count |
| `identity_theft` | Identity Theft | ID Theft | generic | pepm | employee count |
| `gap` | Gap | Gap | generic | composite | medical tier counts (borrowed) |
| `dependent_care_fsa` | Dependent Care FSA | DCFSA | generic | pepm | employee count |
| `ichra` | ICHRA | ICHRA | generic | pepm | employee count |
| `pet` | Pet | Pet | generic | pepm | employee count |
| `individual_life` | Individual Life | Ind Life | life | volume_1000 | Σ `vol_life_amount` |
| `stop_loss` | Stop-Loss | Stop-Loss | stop_loss | stop_loss | medical enrolled employees |
| `pbm` | PBM (Pharmacy) | PBM | generic | pepm | employee count |

**Borrowed** (the worksite tier-rated lines): the line has no tier column of its own, so it borrows the medical tier
counts: the census's, as the old app did, and typed medical counts too (OQ19's default). The screens label them
"Borrowed from medical" (F86, J48). Dental and vision never borrow.

**Employee count** (the PEPM lines): every employee on the roster, because these lines have no tier column of their
own. Where a line does have one, an enrolled count counts only employees whose tier is EE, ES, EC or FAM, never Waived
or blank (C43). Typed lives come first (F92).

**Medical enrolled employees** (stop-loss): lives typed on the stop-loss plan, else on its current contract; else the
current medical plans' enrollment from any source, else the medical line's typed figure, else the census medical EE +
ES + EC + FAM total, else the employee count. The basis names its source, so a quick quote never reads 0 (F98, C44).

The Warner form columns are RFP data; they moved to §4.7 (K.6).

### 4.2 Coverage tiers — `deals/lines.py` and `census/importer.py`

**Source of truth:** the codes and labels are `deals/lines.py` `TIERS`, built in the baseline. The accepted spellings
and waiver words go with the census importer, `census/importer.py` (slice 12; C12, C16); the same cleaning stores a
typed tier (§5.3.1).

| Code | Label | Accepted spellings (case-insensitive, trimmed) |
|---|---|---|
| `EE` | Employee only | EE, EMP, EMPLOYEE, EMPLOYEE ONLY, SINGLE |
| `ES` | Employee + Spouse | ES, E+S, EMPLOYEE + SPOUSE, EMPLOYEE+SPOUSE, EMP+SP |
| `EC` | Employee + Child(ren) | EC, E+C, EMPLOYEE + CHILD, EMPLOYEE + CHILDREN, EMPLOYEE + CHILD(REN), EMP+CH |
| `FAM` | Family | FAM, F, FAMILY, EF, E+F |

**Waiver words** (an explicit decline — valid, but not a tier and never counted as enrolled):
WAIVE, WAIVED, WAIVER, W, DECLINE, DECLINED, NONE, N/A, NA. Stored as the word `Waived`.

The census grid offers these choices for every tier column: `EE`, `ES`, `EC`, `FAM`, `Waived`.

### 4.3 Plan fields — `quotes/fields.py`

**Source of truth:** `quotes/fields.py`, built in the baseline from this table, with each field's `client` flag.

96 fields. **Type** controls storage and display (§5.4). **Req.** marks fields whose blank value counts as missing.
The table order within each group is the display order. Each field also carries `client` (default `True`): whether it
may print on a client document (see the list under the table).

**Which groups a line shows** (groups in this display order):

| Lines | Groups |
|---|---|
| medical | info (all), deduct, copay, rx, lf, rates (4 tiers + quoted premium), contrib |
| dental | info (universal only), den_ben, rates, contrib |
| vision | info (universal only), vis_ben, rates, contrib |
| basic_life_add, voluntary_life, individual_life | info (universal only), life_ben, rates (unit rate + quoted premium) |
| std, voluntary_std, ltd, voluntary_ltd | info (universal only), dis_ben, rates (unit rate + quoted premium) |
| voluntary_worksite, accident, hospital, critical_illness, gap | info (universal only), gen_ben, rates (4 tiers + quoted premium), contrib |
| hsa, fsa, hra, dependent_care_fsa, ichra, eap, telehealth, legal, identity_theft, pet, pbm | info (universal only), gen_ben, rates (unit rate + quoted premium) |
| stop_loss | info (universal only), sl_terms, rates (quoted premium only) |

"Universal" fields are `network`, `plan_type`, `plan_number` and `group_premium_monthly`. `plan_number` is stored as a
column on `Plan` (§6), not in `values`: it is listed here for its label only and is never a value row.

| Group | Key | Label | Type | Req. | Lines |
|---|---|---|---|---|---|
| info — Plan info | `network` | Network | text | | all |
| | `plan_type` | Plan Type | text | | all |
| | `plan_number` | Plan Number | text | | all |
| | `funding` | Funding | choice: §4.6 funding | ✓ | medical |
| | `metal_level` | Metal Level | text | | medical |
| | `minimum_value` | Meets Minimum Value (ACA) | yesno | | medical |
| | `part_d_creditable` | Medicare Part D Creditable | yesno | | medical |
| | `sbc_url` | Summary of Benefits (SBC) link | url | | medical |
| deduct — Deductibles & maximums | `deductible_type` | Deductible Type | text | | medical |
| | `deductible_single` | Deductible (Single) | amount | ✓ | medical |
| | `deductible_family` | Deductible (Family) | amount | | medical |
| | `deductible_single_oon` | Deductible (Single) — OON | amount | | medical |
| | `deductible_family_oon` | Deductible (Family) — OON | amount | | medical |
| | `oop_max_single` | OOP Max (Single) | amount | ✓ | medical |
| | `oop_max_family` | OOP Max (Family) | amount | | medical |
| | `oop_max_single_oon` | OOP Max (Single) — OON | amount | | medical |
| | `oop_max_family_oon` | OOP Max (Family) — OON | amount | | medical |
| | `coinsurance` | Coinsurance (member share) | percent | | medical |
| | `coinsurance_oon` | Coinsurance — OON | percent | | medical |
| copay — Copays & services | `pcp_copay` | PCP Copay | amount | ✓ | medical |
| | `specialist_copay` | Specialist Copay | amount | | medical |
| | `telehealth` | Telehealth | text | | medical |
| | `urgent_care_copay` | Urgent Care Copay | amount | | medical |
| | `er_copay` | ER Copay | amount | | medical |
| | `inpatient` | Inpatient Hospital | text | | medical |
| | `outpatient_surgery` | Outpatient Surgery | text | | medical |
| | `diagnostic_test` | Diagnostic Tests (X-ray & Blood) | text | | medical |
| | `advanced_imaging` | Advanced Imaging (CT / MRI) | text | | medical |
| | `mental_health_outpatient` | Mental Health (Outpatient) | text | | medical |
| rx — Prescription | `rx_deductible` | Rx Deductible | amount | | medical |
| | `rx_t1` | Rx Tier 1 | amount | | medical |
| | `rx_t2` | Rx Tier 2 | amount | | medical |
| | `rx_t3` | Rx Tier 3 | amount | | medical |
| | `rx_t4` | Rx Tier 4 / Specialty | amount | | medical |
| | `rx_mail_order` | Rx Mail Order | text | | medical |
| lf — Level-funded split | `lf_claim_funding` | Claim Funding / Aggregate (monthly) | rate | | medical |
| | `lf_stop_loss_premium` | Stop-Loss Premium (monthly) | rate | | medical |
| | `lf_admin_fee` | Admin Fee (monthly) | rate | | medical |
| | `lf_tro` | Terminal Reserve / TRO (monthly) | rate | | medical |
| | `lf_surplus_share` | Surplus Share | text | | medical |
| rates — Monthly rates | `rate_ee` | Rate — EE | rate | ✓ | composite lines |
| | `rate_es` | Rate — EE + Spouse | rate | ✓ | composite lines |
| | `rate_ec` | Rate — EE + Child(ren) | rate | ✓ | composite lines |
| | `rate_fam` | Rate — Family | rate | ✓ | composite lines |
| | `unit_rate` | Unit Rate | rate4 | ✓ | life, disability, PEPM lines |
| | `group_premium_monthly` | Group Premium / mo (quoted) | rate | | all |
| contrib — Employer contribution | `contrib_ee` | Employer Contrib — EE | rate | | composite lines |
| | `contrib_es` | Employer Contrib — ES | rate | | composite lines |
| | `contrib_ec` | Employer Contrib — EC | rate | | composite lines |
| | `contrib_fam` | Employer Contrib — FAM | rate | | composite lines |
| den_ben — Dental benefits | `den_annual_max` | Annual Maximum | amount | ✓ | dental |
| | `den_deductible` | Deductible (Individual) | amount | ✓ | dental |
| | `den_deductible_family` | Deductible (Family) | amount | | dental |
| | `den_preventive` | Preventive & Diagnostic | percent | ✓ | dental |
| | `den_basic` | Basic Services | percent | | dental |
| | `den_major` | Major Services | percent | | dental |
| | `den_ortho` | Orthodontia | percent | | dental |
| | `den_ortho_max` | Ortho Lifetime Max | amount | | dental |
| | `den_waiting` | Waiting Periods | text | | dental |
| vis_ben — Vision benefits | `vis_exam_copay` | Exam Copay | amount | ✓ | vision |
| | `vis_materials_copay` | Materials Copay | amount | | vision |
| | `vis_frame_allowance` | Frame Allowance | amount | ✓ | vision |
| | `vis_contacts_allowance` | Contacts Allowance | amount | | vision |
| | `vis_exam_frequency` | Exam Frequency | text | | vision |
| | `vis_frame_frequency` | Frame Frequency | text | | vision |
| life_ben — Life benefits | `life_schedule` | Benefit Schedule | text | ✓ | life lines |
| | `life_benefit_max` | Benefit Maximum | amount | | life lines |
| | `life_guarantee_issue` | Guarantee Issue | amount | | life lines |
| | `life_add_included` | AD&D Included | yesno | | life lines |
| | `life_age_reduction` | Age Reduction Schedule | text | | life lines |
| | `life_waiver_premium` | Waiver of Premium | yesno | | life lines |
| dis_ben — Disability benefits | `dis_elimination` | Elimination Period | text | ✓ | disability lines |
| | `dis_benefit_pct` | Benefit Percentage | percent | ✓ | disability lines |
| | `dis_max_benefit` | Maximum Benefit | amount | ✓ | disability lines |
| | `dis_benefit_duration` | Benefit Duration | text | | disability lines |
| | `dis_own_occupation` | Own-Occupation Period | text | | disability lines |
| | `dis_pre_existing` | Pre-Existing Limitation | text | | disability lines |
| gen_ben — Plan benefits | `benefit_summary` | Benefit Summary | text | ✓ | generic lines |
| | `plan_notes` | Notes | text | | generic lines |
| sl_terms — Stop-loss terms | `sl_spec_deductible` | Specific Deductible (per person) | rate | | stop_loss |
| | `sl_spec_rate` | Specific Premium PEPM | rate | | stop_loss |
| | `sl_agg_rate` | Aggregate Premium PEPM | rate | | stop_loss |
| | `sl_other_load` | TLO / Other SL Load PEPM | rate | | stop_loss |
| | `sl_agg_factor` | Expected Claims Factor PEPM | rate | | stop_loss |
| | `sl_agg_corridor` | Aggregate Corridor | number | | stop_loss |
| | `sl_agg_floor` | Min Annual Aggregate Deductible | rate | | stop_loss |
| | `sl_contract_basis` | Contract Basis (incurred/paid) | text | | stop_loss |
| | `sl_run_in_months` | Run-In Period (months) | number | | stop_loss |
| | `sl_run_in_limit` | Run-In Dollar Limit | amount | | stop_loss |
| | `sl_run_out_months` | Run-Out / Paid Window (months) | number | | stop_loss |
| | `sl_tlo` | TLO Included / Terms | text | | stop_loss |
| | `sl_lasers` | Lasers (ID amount, ID amount) | text | | stop_loss |
| | `sl_collateral` | Collateral / Captive Fees (annual) | amount | | stop_loss |
| | `tpa_name` | TPA | text | | stop_loss |
| | `tpa_admin_fee` | Admin / TPA / Network PEPM | rate | | stop_loss |
| | `tpa_rate_guarantee` | TPA Rate Guarantee | text | | stop_loss |

"Composite lines" = medical, dental, vision, voluntary_worksite, accident, hospital, critical_illness, gap.
Coinsurance is the **member's** share after the deductible: an 80/20 plan stores `20`. `sl_lasers` holds claimant
IDs or initials only, never names.

**`funding`** records what a medical plan is (fully insured, level-funded or self-funded). It prints as a design row,
"Create renewal" copies it, and when a plan is sold the deal keeps a record of the funding bought.

**Fields that never print on a client document** (`client: False`): `sl_lasers` (claimant data — never, in any client
file) and `mental_health_outpatient` (the team removed it on 2026-11-05; the old files printed it, so the parity
profiles label the difference). Client files (§9: the workbook, the PDF, the PowerPoint and the stop-loss workbook)
print only `client: True` fields; among fields, this flag is the only rule that decides it. Nor do they print the rest
of J.4's "never" list, which is not fields: commission figures, birth dates, status sentences, `star_reason`, intake's
`client_guidance`, internal `Plan.notes`, sources, source and document names, and review marks (O.3.6).

The stop-loss contract and cost rows **print**, including `sl_collateral` and the TPA rows (`tpa_name`,
`tpa_admin_fee`, `tpa_rate_guarantee`): Stephanie (2026-09-03) — a client is shown "what the current in-force
stop-loss contract is and costs, and then what we got back in the market", not plan details. `plan_number` prints (in
the plan header, §9). `plan_notes`, `telehealth` and `rx_mail_order` print, as the old formats do, until Stephanie
decides them (OQ40, slice 27).

**Lasers.** Laser liability is a computed figure, not a field: what each laser adds above the specific deductible, and
the total, which the maximum annual liability includes (F98–F107). The Proposal tab's cost rows (J94) and the
stop-loss workbook (J166) show it. The claimant IDs or initials in `sl_lasers` never print on a client file. The old
stop-loss workbook printed them in its laser rows; the new one lists lasers by position, and GD5's parity profile
labels the difference (OQ104's default, slice 36). `sl_lasers` prints only on internal files, such as the
plan-template export (§9; J98), whose download is logged. Activity records its key only (O.3.2).

**Lists of fields** live beside the screens that use them and name fields from this table only: the Advisor's column
presets (Primary for each field set, Cost sharing, Rx, Rates & contributions, All columns), sliders and budget rungs
in `quotes/board_presets.py` (F20, F31); the Proposal's key rows, row presets and card stats in `proposals/catalog.py`
(J16); the client files' house row maps in `proposals/rows.py` (J133). A list meant for a client never names a
`client: False` field (J.5 B3). `/api/meta/` serves the presets and key rows.

**Plan columns are not fields.** `Plan` keeps its own columns beside `values`: among them the carrier, the name,
`plan_number`, internal notes, `client_name` (J14), `codes` (F143), `star_reason`, `option_number` (J159), `pair_of`
(O.6 #4) and `derived` (priced versions, F76–F84). §6 lists them (`Plan`; O.2).

### 4.4 Census columns — `census/fields.py`

**Source of truth once built:** `census/fields.py` (slice 12), generated from the old `benefits/registry.py`; it also
holds each column's group, choices, help and `is_required` (C.5).

45 columns, in display order. **Required** codes: **A** every person · **E** employees only · **L:x** employees only,
when line *x* is requested on the deal · **M** employees only, when medical is requested **and** the deal has medical
coverage in force today · blank = optional. Dependents are never required to fill employment or enrollment columns
(they inherit the employee's election). A column is **also** required when a file the deal's RFP will send requires
it. rfp's `required_columns(deal)` answers `{key: {employee: [carriers], dependent: [carriers]}}` through census's
`carrier_required` provider; it covers the picked carriers' own formats, formats ticked by hand, and the universal
format when a picked carrier or "Other carriers" takes it (K124; §5.3.3). So "Census OK" means "the files you are
about to send are complete". Until slice 45 fills the provider, its answer is empty.

**Per-deal rules** (OQ17; C27): `CensusSettings.rules` holds an Auto, Required or Waived choice for each column on one
deal. Waived wins over every other reason; §5.3.3 gives the order.

**SSN is optional** (OQ16's default). The column is kept and validated when present, but nothing requires it by
default and the client portal never asks for it: it is the most sensitive field in the system, and the team agreed
(2026-10-06) that no real SSNs enter the app before a BAA is signed. Stephanie (2026-09-22): carriers "want them, but
they don't need them" to quote. The portal shows a stored SSN masked to its last four digits (L89). Open as OQ16
(slice 12): Rebecca (2026-09-29) said dependent SSNs are required to quote, and Stephanie wants SSNs collected for
later use.

**Gender** is required for everyone: Warner Pacific's minimum census and three of the four carrier templates require
it. **Hours per week** is required for employees: the team (2026-09-22 and 09-24) needs it to tell full-time from
part-time eligibility and to count FTEs (§5.3.7).

| Group | Key | Label | Type | Required |
|---|---|---|---|---|
| Identity | `ext_emp_id` | Emp ID | text | |
| | `first_name` | First Name | text | A |
| | `middle_name` | Middle Name | text | |
| | `last_name` | Last Name | text | A |
| | `relationship` | Relationship | text | |
| | `subscriber_ssn` | Employee SSN | ssn | |
| Demographics | `dob` | Date of Birth | date | A |
| | `ssn` | SSN | ssn | |
| | `gender` | Gender | text | A |
| | `address1` | Address | text | |
| | `address2` | Address 2 | text | |
| | `city` | City | text | |
| | `state` | State | text | |
| | `zip` | ZIP | text | E |
| | `county` | County | text | |
| | `phone` | Phone | text | |
| | `email` | Email | text | |
| Employment | `division` | Division | text | |
| | `emp_class` | Class | text | |
| | `job_title` | Job Title | text | |
| | `hire_date` | Hire Date | date | |
| | `employment_status` | Employment Status | text | |
| | `hours_per_week` | Hours / Week | number | E |
| | `annual_salary` | Annual Salary | money | |
| | `work_state` | Work State | text | |
| | `term_date` | Termination Date | date | |
| | `rehire_date` | Rehire Date | date | |
| Medical | `medical_plan` | Medical Plan | text | M |
| | `medical_tier` | Medical Tier | tier | L:medical |
| | `effective_date` | Medical Effective Date | date | |
| | `waiver_reason` | Waiver Reason | text | |
| Dental | `dental_plan` | Dental Plan | text | |
| | `dental_tier` | Dental Tier | tier | L:dental |
| | `dental_effective_date` | Dental Effective Date | date | |
| Vision | `vision_plan` | Vision Plan | text | |
| | `vision_tier` | Vision Tier | tier | L:vision |
| | `vision_effective_date` | Vision Effective Date | date | |
| Life | `basic_life_amount` | Basic Life Amount | money | |
| | `basic_life_effective_date` | Basic Life Effective Date | date | |
| | `vol_life_amount` | Voluntary Life Amount | money | |
| | `vol_life_effective_date` | Vol Life Effective Date | date | |
| Disability | `std_amount` | STD Benefit Amount | money | |
| | `std_effective_date` | STD Effective Date | date | |
| | `ltd_amount` | LTD Benefit Amount | money | |
| | `ltd_effective_date` | LTD Effective Date | date | |

`ltd_amount` is collected and written to carrier census files only; LTD is priced from `annual_salary` (§4.1).

**Columns in scope for a deal.** The grid shows them by line chips (C2): Identity, Demographics and Employment are
always on; Medical, the groups of requested lines and any group that holds data are on by default (Life:
basic_life_add, voluntary_life or individual_life; Disability: std, ltd, voluntary_std or voluntary_ltd). The blank
template (§9; C38) has every column except those of lines not requested, plus any column the deal requires.

**Accepted values** offered as choices (other spellings are still read by the rules in §5.3):

| Column | Choices |
|---|---|
| every tier column | EE, ES, EC, FAM, Waived |
| `gender` | M (Male), F (Female) |
| `relationship` (dependents) | Spouse, Child, Domestic Partner |
| `employment_status` | Full-time, Part-time, COBRA, Retiree |
| `state`, `work_state` | the 50 state codes plus DC |

### 4.5 Intake questionnaire — `intake/form.py`

**Source of truth once built:** `intake/form.py` (slice 11), generated from the old `benefits/market/intake.py`
(`INTAKE_FIELD_SEED`, `FIELD_HELP`). It also holds the questionnaire catalogue (below; G1).

**Sections:** `employer` Employer information · `eligibility` Eligibility & workforce · `goals` Goals & preferences ·
`compliance` Compliance & regulatory.

**Need:** **Q** quote-blocking (counts toward "Ready to market", §5.2, B33) · **C** counts when shown · blank =
optional.
**Types:** text, number, money, percent, date, yesno, choice (one of the options), multi (several options, stored as a
list; B3).

| Section | Key | Label | Type | Options / hint | Need | Shown when |
|---|---|---|---|---|---|---|
| employer | `legal_name` | Legal Company Name | text | | Q | |
| | `dba` | DBA | text | hint: Doing business as | | |
| | `fein` | FEIN | text | hint: XX-XXXXXXX | Q | |
| | `entity_type` | Business Structure | choice | LLC · S-Corp · C-Corp · Partnership · Non-profit · Sole proprietorship | | |
| | `sic_code` | NAICS / SIC Code | text | hint: e.g. 3441 — Fabricated Structural Metal | Q | |
| | `years_in_business` | Years in Business | number | | | |
| | `website` | Website | text | hint: https://… | | |
| | `address_physical` | Physical Address | text | hint: Street, city, state, ZIP | Q | |
| | `address_mailing` | Mailing Address | text | hint: If different from physical | | |
| | `situs_state` | Situs State | choice | state codes · hint: e.g. TX | Q | |
| | `states_operating` | States of Operation | multi | state codes · hint: Every state with employees | Q | |
| | `location_count` | Number of Locations | number | | | |
| eligibility | `total_employees` | Total Employees | number | | Q | |
| | `atne` | ATNE (prior-year average) | number | | | |
| | `employee_count` | Eligible Employees | number | | Q | |
| | `enrolled_count` | Currently Enrolled — Medical | number | | | |
| | `enrolled_life_count` | Currently Enrolled — Basic Life | number | | | |
| | `waiving_count` | Waiving Coverage | number | | | |
| | `waive_reason` | Main Waive Reason | choice | Spouse's plan · Medicare · Other coverage · Cost · Other | C | `waiving_count` > 0 |
| | `contractor_count` | 1099 Contractors | number | | | |
| | `payroll_frequency` | Payroll Frequency | choice | Weekly · Bi-weekly · Semi-Monthly · Monthly | | |
| | `payroll_vendor` | Payroll Vendor | text | | | |
| | `payroll_vendor_contact` | Payroll Vendor Contact | text | | | |
| | `payroll_processing` | Payroll Processing | choice | API · Manual | | |
| | `multi_location` | Multiple Locations | yesno | | | |
| | `locations_list` | Locations | text | hint: List each location | | `multi_location` = Yes |
| | `commission_employees` | Commission-Based Employees | yesno | | | |
| | `classes_divisions` | Classes / Divisions | text | hint: List classes or divisions, if any | | |
| | `waiting_period` | Waiting Period | choice | Immediately · 1st of the month following hire date · 1st of the month following 30 days · 1st of the month following 60 days · 90 days | | |
| | `hours_threshold` | Hours/Week for Eligibility | number | hint: 1–40 | | |
| | `union` | Union Employees | yesno | | | |
| | `employee_class_1` | Employee Class 1 | text | | | |
| | `employee_class_2` | Employee Class 2 | text | | | |
| | `contribution_by_class` | Contribution Strategy by Class | text | | | |
| | `child_age_limit` | Dependent Child Age Limit | number | hint: e.g. 26 | | |
| | `domestic_partner` | Domestic Partner Coverage | yesno | | | |
| | `reinstatement` | Reinstatement Rule | choice | No Reinstatement · Standard (3 Months) · Other | | |
| goals | `budget_target` | Monthly Budget Target | money | | | |
| | `acceptable_increase_pct` | Acceptable Increase | percent | hint: % over current | | |
| | `network_priorities` | Network Priorities | text | hint: Must-keep providers / networks | | |
| | `contribution_philosophy` | Contribution Philosophy | text | hint: e.g. ER pays 75% EE-only | | |
| | `pain_points` | Pain Points Today | text | | | |
| | `decision_date` | Decision Date | date | | | |
| | `target_effective_date` | Target Effective Date | date | | | |
| | `client_guidance` | Client guidance | text | ≤ 4,000 characters (†) | | |
| compliance | `self_funded` | Are you self-funded? | yesno | hint: The company pays claims itself (incl. level-funded) | | |
| | `section_125` | Section 125 (POP / WRAP) | yesno | hint: Required for any group with pre-tax premiums | | |
| | `section_125_handler` | Section 125 — Who Handles It? | text | hint: Vendor, TPA, CPA, or in-house | | `section_125` = Yes |
| | `ale_status` | ACA ALE (50+ FTE) | yesno | hint: Applicable Large Employer under the ACA | | |
| | `form_5500_required` | Form 5500 Filing Required | yesno | hint: 100+ participants on the first day of the plan year | | |
| | `form_5500_handler` | Form 5500 — Who Handles It? | text | hint: Vendor, TPA, CPA, or in-house | | `form_5500_required` = Yes |
| | `aca_1095c` | 1095-C / 1094-C Filing (ALE) | yesno | | | |
| | `aca_1095c_handler` | 1095-C — Who Handles It? | text | hint: Vendor, TPA, CPA, or in-house | | `aca_1095c` = Yes |
| | `aca_1095b` | 1095-B / 1094-B Filing | yesno | hint: Small employers with level-funded plans (except Aetna) | | |
| | `aca_1095b_handler` | 1095-B — Who Handles It? | text | hint: Vendor, TPA, CPA, or in-house | | `aca_1095b` = Yes |
| | `pcori_filing` | PCORI Filing | yesno | hint: Self- and level-funded plans; IRS Form 720, due July 31 | | |
| | `pcori_handler` | PCORI — Who Handles It? | text | hint: Vendor, TPA, CPA, or in-house | | `pcori_filing` = Yes |

**56 questions:** employer 12, eligibility 25, goals 7, compliance 12; 8 are **Q**, 1 is **C** and 47 are optional
(B1). A per-deal rule in `Intake.rules` (Auto, Required or Waived) can require or waive any question on one deal, and
Waived wins (B37, OQ17).

**`target_effective_date`** is a door onto `Deal.effective_date`: answering it writes the deal's one effective date,
which every app reads (B1, N.1).

**† `client_guidance`** holds what the client wants, in free text (budget, networks, lines, deductible or benefit
levels), for Rank (F111) and Claude's context (N.1). It is edited in the Goals card and in the Work with Claude
drawer's guidance box, both through intake's service, and Claude's `update_client_guidance` tool proposes changes to
it (O.6 #16, D98, O.3.3). It is not one of the 56 questions: it never counts toward readiness, is never asked on the
portal and never prints on a client file (J.4).

**Blocks** (non-question parts of the intake page; Part B gives their look): **Contacts** (client-level, §6.2; B13) ·
**Current coverage** (§6, `CurrentCoverage`): line, carrier, funding, dates, in-force commission and its source, on
proposal, rate guarantee (B14) · **Coverage and marketing intent** (B16–B24), whose medical row holds the
questionnaire and stop-loss form pickers (below; B22, G2) · **Lines to quote** (`Deal.requested_lines`, written only
by `intake.set_intent`, which these chips and the deal header's Lines picker both call; B17, B32) · **Marketing
readiness checklist**, COBRA included (B25–B28; O.6 #2) · **Authorizations & documents** (the BOR e-signature, B29,
plus uploads of kind `bor`, `carrier_auth`, `claims`, `form_5500` and `plan_doc`; B31). The coverage subcards and the
intent card both stay, editing the same rows through one service (OQ15).

**Client-facing help text** (shown beside the question on the client portal and as a tooltip in the app):

| Key | Help |
|---|---|
| `legal_name` | Your exact registered business name — as it appears on your IRS documents or business license, not a nickname or DBA. |
| `dba` | Any name you operate or bill under that's different from your legal name. Leave blank if they're the same. |
| `fein` | Your 9-digit federal Tax ID (XX-XXXXXXX). It's at the top of your IRS CP-575 confirmation letter, or on any payroll tax form (Form 941) or a W-2 you've issued. |
| `entity_type` | How your business is organized (LLC, S-Corp, etc.) — on your business tax return or formation documents. |
| `sic_code` | Your industry code. It's on your business tax return, your workers'-comp policy, or search your industry at naics.com. |
| `address_physical` | The street address where your business physically operates (not a PO box). |
| `situs_state` | The state where your business is headquartered and files its taxes — this drives which plans carriers can offer you. |
| `states_operating` | Every state where you have employees working — check your payroll records if you're unsure. |
| `total_employees` | Everyone on payroll today, full- and part-time — your payroll system's headcount is the quickest source. |
| `atne` | Your average total number of employees over the PRIOR calendar year — not today's headcount. Carriers use it to decide whether you are a small or large group, so it matters most near 50. Payroll can usually run it. |
| `employee_count` | How many employees are eligible for benefits (usually full-time). Your payroll or HR system can total this. |
| `enrolled_count` | How many employees are actually signed up for medical today — on your latest carrier invoice or bill. |
| `enrolled_life_count` | How many employees have basic life coverage — often everyone, even those who waived medical. It's on your life carrier's invoice. |
| `payroll_frequency` | How often you run payroll (weekly, bi-weekly, etc.). |
| `waiting_period` | How long a new hire waits before benefits start — it's in your current plan summary or new-hire paperwork. |
| `child_age_limit` | The age a dependent child ages off your plan (commonly 26). |
| `target_effective_date` | The date you'd like new coverage to start — usually the day after your current plan renews. |
| `self_funded` | Does your company pay employee claims itself rather than paying a carrier a fixed premium? Level-funded plans count as self-funded. If you just pay a monthly premium, answer No. |
| `section_125` | Do you take employee premiums out of pay pre-tax? Almost all groups do — if unsure, leave it and we'll confirm. |
| `section_125_handler` | The vendor, TPA, CPA, or person at your company who maintains your Section 125 plan document. Leave blank if you'd like us to help place it. |
| `ale_status` | Did you average 50+ full-time (and equivalent) employees last year? If yes, ACA employer rules apply. |
| `form_5500_required` | Do you have 100+ people enrolled across your benefit plans? If unsure, leave it — we verify this for you. |
| `form_5500_handler` | The vendor, TPA, CPA, or person at your company who files your Form 5500. Leave blank if you'd like us to help place it. |
| `aca_1095c_handler` | The vendor, payroll company, or person at your company who prepares and files your 1095-C forms. Leave blank if you'd like us to help place it. |
| `aca_1095b_handler` | The vendor, carrier, or person at your company who prepares and files your 1095-B forms. Leave blank if you'd like us to help place it. |
| `pcori_filing` | Self-funded and level-funded plans owe a small annual PCORI fee, filed with IRS Form 720 by July 31. If unsure, leave it — we'll verify this for you. |
| `pcori_handler` | The vendor, TPA, CPA, or person at your company who files your PCORI fee. Leave blank if you'd like us to help place it. |

**Questionnaire catalogue** (G1). The checklist's form items and the form pickers name the carrier questionnaires by
these keys. Their specs live in `questionnaire/forms/` (slice 42; Part G), and a start-up check keeps the two in step.

| Key | Checklist item | Name on pickers and chips | Title | Default by group size |
|---|---|---|---|---|
| `fl_blue_51` | `medical_questionnaire` | Florida Blue 51+ | Florida Blue Underwriting Questionnaire | 51 or more enrolled |
| `wp_lg` | `medical_questionnaire` | Warner Pacific 51+ | Large Group Coverage Form | — (picked by hand) |
| `stop_loss_siia` | `stop_loss_disclosure` | Stop Loss Disclosure (SIIA) | Standard Stop Loss Disclosure Form | — (opt-in; OQ58) |

The group size is `quotes.facts.enrolled_headcount` (§5.7; OQ21). Below 51 the medical item has no fillable form, and
the carrier's own form is uploaded (B26). The first answer on a form freezes the band's pick, so a later headcount
never swaps it silently (G133).

**Form choices** (G4) are stored as the item's `form_key` in `Intake.checklist` (N.1), with a long label for the
checklist and the Overview and a short one for the coverage card's narrow column (G3):

| Item | Stored value | Long label | Short label |
|---|---|---|---|
| `medical_questionnaire` | `auto` | Auto by group size — Florida Blue 51+ (51 or more enrolled), or Auto by group size — upload only (below 51) | Auto by group size |
| `medical_questionnaire` | `fl_blue_51`, `wp_lg` | the form's name | the form's name |
| `medical_questionnaire` | `upload` | No fillable form — upload only | No fillable form |
| `stop_loss_disclosure` | `''` | Not needed for this group | Not needed |
| `stop_loss_disclosure` | `stop_loss_siia` | Needed — Stop Loss Disclosure (SIIA) | Stop Loss Disclosure (SIIA) |
| `stop_loss_disclosure` | `upload` | Needed — upload only | Upload only |

`upload` on the stop-loss item is new: the old coverage card saved "Upload only" as "not needed" (G4). A choice cannot
move away from a signed form (409; G9).

### 4.6 Other vocabularies

**Source of truth:** the module named with each list. `/api/meta/` serves every list the browser shows (§7.1).

**Deal stages** (`deals/stages.py`): `intake` Intake · `quoting` Quoting · `proposal` Proposal · `sold` Sold · `lost`
Lost. Order: intake → quoting → proposal → sold. `lost` is off the ladder. The stage pill (`bb-stage-pill`) gains a
class for `proposal`, a stage the old ladder lacked (M15).

**Client status** (`deals/lifecycle.py`, slice 6): `prospect` Prospect (the default) · `new_client` New client ·
`existing_client` Existing client. A sale or "Convert to client" makes a prospect a New client; New client → Existing
client waits with renewals (§5.1; OQ2). The field keeps its name, `Client.relationship`, and `/api/meta/` serves it as
`relationships`; screens say "Status". It replaces the baseline's `new` and `existing`.

**Deal type** (`deals/rules.py` `deal_type`, slice 6): `new_business` New business · `renewal` Renewal. It is worked
out over `Deal.opened_as`, which copies the client's status when the deal is created and follows it until a plan on
the deal is sold, then freezes; it is Renewal only when that status is `existing_client` (M14, H30). Deal type is not
client status: a won prospect's deal stays New business while its client becomes a New client.

**Contact roles** (`deals/contacts.py`, slice 38; B13): `owner` Owner · `decision_maker` Decision Maker · `hr_admin`
HR Admin · `benefit_admin` Benefit Administrator · `payroll_contact` Payroll Contact · `billing` Billing ·
`prior_broker` Prior Broker. Every role but `prior_broker` is on the client's side, and `contacts.primary` reads them
(M30). The old app's eighth role, `partner_agent`, is not kept, which overrides B13's "role (8)" (OQ106's default): a
split partner who works the account is marked on its split row and shows in the commission card's "who gets what"
(H13, M81).

**Note kinds** (`deals`, `Note`, slice 38): `note` Note · `call` Call · `email` Email · `meeting` Meeting · `internal`
Internal (A37, M73).

**Funding** (`deals/lines.py`; current coverage and the medical plan field `funding`): `fully_insured` Fully insured ·
`level_funded` Level-funded · `self_funded` Self-funded · blank = unknown.

**Commission types** (`deals/comp.py`, slice 11): `pct` percentage of premium · `flat` flat dollars per year · `pepm`
dollars per employee per month. A commission is `{type, value}`, the value kept as an exact decimal string (H1; §5.6).

**Value origins** (`deals/values.py`, slice 5; O.3.1): `typed` a person typed it · `relay` staff typed what the client
said ("From the client", C4) · `client` the client's own answer, once approved · `ai` read by Claude · `import` a
mapped file (a census file, the plan template) · `prefill` filled from the deal's facts (questionnaire, G.6) · `sale`,
`in_force`, `agency` the basis of a commission record: the sold plans, the in-force commission, the agency default
(H.6).

**Actor kinds** (`Activity.actor_kind`, slice 5; O.3.2): `user` · `client` (through a portal link) · `claude` ·
`system`.

**Document kinds** (`documents/kinds.py`; flags from slice 15; E.6, O.6 #12):

| Key | Label | Bucket | File as | Asks role | PHI |
|---|---|---|---|---|---|
| `quote` | Carrier quote | proposal | ✓ | ✓ | |
| `renewal` | Renewal / rates | proposal | | ✓ | |
| `sbc` | SBC / plan summary | proposal | ✓ | ✓ | |
| `census` | Census | census | ✓ | | ✓ |
| `invoice` | Current invoice | intake | | | |
| `bor` | BOR / signed authorization | intake | | | |
| `carrier_auth` | Carrier authorization | intake | | | |
| `claims` | Claims experience | intake | | | ✓ |
| `plan_doc` | Plan document / SPD | intake | | | |
| `proposal` | Proposal / presentation | — | | | |
| `other` | Other | intake | ✓ | | |
| `form_5500` | Prior 5500 | intake | | | |
| `questionnaire` | Medical questionnaire | questionnaire | ✓ | | ✓ |
| `stop_loss` | Stop-loss disclosure | questionnaire | ✓ | | ✓ |
| `stop_loss_quote` | Stop-loss quote | proposal | | ✓ | ✓ |
| `tpa_proposal` | TPA proposal | proposal | | ✓ | |
| `plan_template` | Plan template | proposal | | | |

The first eleven keep their baseline labels; the six added take the old app's words. **Bucket** is the tag the
Documents tab files a kind under (E1). **File as** marks the six on the quick "File as" menu (Daniel, 2026-10-15; E5);
the File panel offers every kind. **Asks role** marks the kinds that ask what the file is (below; E13). **PHI** kinds
have their downloads and views logged (`log_access`, E99), and real files of these kinds wait for the PHI gate (slice
47); invoices are not PHI (OQ27). Each kind also lists the file types it accepts, checked against the file's magic
bytes (E7); `questionnaire` and `stop_loss` take PDFs and images only (G.6). Issued proposals are stored as kind
`proposal`: protected and never screened (J.6.4). `commission_statement`, a firm-level kind, waits with the ledger
(OQ6); the wrap, POP and sold-paperwork kinds wait with close-out and implementation (OQ26).

**Document roles** (only for the kinds that ask one — quote, renewal, sbc, stop_loss_quote and tpa_proposal; E13 —
"what is this document?"): `current` Current plans in force · `renewal` Renewal of the current plans · `alternates`
Alternate quotes · blank = not said.

**In-force commission source** (`intake`, `CurrentCoverage`, slice 11; B14): `client` Client told us · `carrier`
Carrier told us · `aor_letter` From the AOR letter · blank = unknown.

**Questionnaire forms and form choices** (`intake/form.py`): §4.5.

**Commission's own words** — party kinds, split-row roles and bases, record statuses — live in `commission/vocab.py`
(slice 48; H.6). The commission access tiers `none`, `own` and `all` are `accounts.Profile.commissions_access` (A3).

**Funding requested on an RFP** (`rfp`, served under `/api/meta/`'s `rfp`; K.6): `fully_insured` Fully insured ·
`level_funded` Level funded · `aso` ASO / self-funded, the old chips' words. An empty pick is kept (K21).

**RFP route** (`RfpRequest.route`; K.6): `''` follows the band — through Warner below 51 enrolled, direct at 51 or
more — until the first send pins it (K20, K64) · `warner` Through Warner Pacific · `direct` Direct to carriers.

**RFP form** (`RfpRequest.form`; K.6): `''` the Simplified form (the default) · `small_group` · `large_group`. Their
labels come from `VARIANTS` in `rfp/forms/maps.py` (K99).

**Proposal issue states** (`ProposalIssue.state`, slice 32; J.6.2): `building` · `issued` · `failed` (Retry builds it
again; J.6.4).

**Agenda sections** (`agenda/catalogue.py`, slice 60; I4): Up next · Waiting on · Later · Blocked · Done. The
catalogue also holds their descriptions and empty words, and each step's title, tab, track and banner words (I.6).

### 4.7 Carriers — `deals/carriers.py` and `rfp/carriers.py`

**Source of truth once built:** `deals/carriers.py` (slice 6) holds each carrier's key, name, group and aliases, and
the matcher (`match`, `identity`, `display_name`, `norm`, `split_names`). `rfp/carriers.py` (slice 44) holds, under
the same keys, what an RFP needs: the census format, the Warner form columns at each size, `on_form`, the note and the
Warner inbox. Both are generated from the old `benefits/market/rfp_carriers.py`, and a test proves every rfp key
exists in deals (K105, K.6). The identity half sits in deals because the Advisor's finder (F14), Find on Documents
(E64), intake, commission and rfp all match carrier names (H.6).

25 carriers. **Key**, **Name**, **Group** and **Aliases** are `deals/carriers.py`; the rest is `rfp/carriers.py`.
**Census format** names a carrier-specific census file (§9; formats in `rfp/formats/definitions.py`); blank means the
carrier accepts the universal Warner census. **Small / Large** list the Warner form columns (below) offered at each
size band (§5.7); "—" means the carrier is not offered at that size.

| Key | Name | Group | Aliases | Census format | Small | Large | Note |
|---|---|---|---|---|---|---|---|
| `aetna` | Aetna | medical | Aetna Funding Advantage, Aetna AFA, AFA | `aetna_gateway` | medical, dental, vision | medical, dental, vision | Own census file |
| `angle_health` | Angle Health | medical | Angle | `angle` | medical | medical | Own census file, uploaded to their portal as CSV |
| `avmed` | AvMed | medical | Amed | | medical | medical | Needs a signed 51+ questionnaire |
| `cigna` | Cigna | medical | | | medical, dental, vision | medical, dental, vision | Wants each member's current plan election on the census |
| `curative` | Curative | medical | | | — | medical | 51+ only |
| `florida_blue` | Florida Blue | medical | FL Blue, BCBS, BlueCross BlueShield, BCBS FL, Blue Cross Blue Shield of Florida, BCBS of Florida | | medical, dental, vision, life_add | same | Requires its own medical questionnaire |
| `gravie` | Gravie | medical | Gravie Level Funded | | medical | medical | Wants each member's current plan election |
| `nationwide` | Nationwide | medical | Nationwide Level Funded | | medical, dental, vision, life_add, std, ltd | same | |
| `optimyl` | Optimyl Benefits | medical | Optimyl | | medical | medical | |
| `sidecar_health` | Sidecar Health | medical | Sidecar | | — | medical | 51+ only |
| `trustmark` | Trustmark | medical | | | medical | medical | Not on the Warner form matrix; goes on its "Additional carriers" line |
| `unitedhealthcare` | UnitedHealthcare | medical | UHC, United Healthcare, United | `uhc` | medical, dental, vision, life_add, std, ltd | same | Own census file |
| `guardian` | Guardian | ancillary | Guardian Life | | dental, vision, life_add, std_ltd, acc_ci_hi | same | |
| `the_hartford` | The Hartford | ancillary | Hartford | | life_add, std_ltd, acc_ci_hi | same | |
| `humana` | Humana | ancillary | | | dental, vision, life_add, std_ltd | same | |
| `metlife` | MetLife | ancillary | | | dental, vision, life_add, std_ltd, acc_ci_hi | same | |
| `mutual_of_omaha` | Mutual of Omaha | ancillary | | | dental, vision, life_add, std_ltd, acc_ci_hi | same | |
| `principal` | Principal | ancillary | | | dental, vision, life_add, std_ltd, acc_ci_hi | same | |
| `sun_life` | Sun Life | ancillary | SunLife | | dental, vision, life_add, std_ltd, acc_ci_hi | same | |
| `united_concordia` | United Concordia | ancillary | | | dental, vision | same | |
| `unum` | Unum | ancillary | | | dental, vision, life_add, std_ltd, acc_ci_hi | same | |
| `apl` | APL | ancillary | | | gap | gap | |
| `morgan_white_group` | Morgan White Group | ancillary | Morgan White | | gap | gap | |
| `transamerica` | Transamerica | ancillary | | | gap | gap | |
| `wellfleet` | Wellfleet | ancillary | | | gap | gap | |

**`on_form`** is false only for Trustmark, which rides the form's "Additional carriers" line (its note).

**Warner form columns.** Warner Pacific's quote request forms group lines into checkbox columns:

| Column | Our lines |
|---|---|
| `medical` | medical |
| `dental` | dental |
| `vision` | vision |
| `life_add` | basic_life_add, voluntary_life |
| `std` | std, voluntary_std |
| `ltd` | ltd, voluntary_ltd |
| `std_ltd` | std, ltd, voluntary_std, voluntary_ltd (the ancillary grid pairs them) |
| `acc_ci_hi` | accident, critical_illness, hospital |
| `gap` | gap |

**Warner Pacific quoting inbox:** `FLQuoting@WarnerPacific.com`.

**Reps.** Each carrier's rep, who would fill a direct draft's To line, is not known yet: OQ59 (slice 44; default: the
25 on Warner's forms, with the To line left blank, K60).

**Matching a carrier name** (`deals/carriers.match`; K105), for text from a document, a quote or a person. Text is
squashed to lower-case letters and digits. Three tiers, each tried only when the one before finds nothing:

1. **Exact:** the squashed name equals a carrier's squashed key, name or alias ("UHC", "SunLife" for Sun Life, "BCBS
   FL").
2. **Normalized:** the same after `norm` drops punctuation, "and", and these corporate words: incorporated, inc, llc,
   lp, llp, corporation, corp, company, co, the, insurance, life, health, plan, plans, group, of, america, usa ("Aetna
   Life Insurance Co." is Aetna).
3. **Leading words:** the longest run of leading words that squashes to a key, name or alias ("UHC Level-Funded",
   "UnitedHealthcare of Florida", "United Concordia (Dental)").

Otherwise there is no match. The generic aliases United, BCBS, BlueCross BlueShield, AFA and Amed match only in the
exact tier, so "United of Omaha" matches nothing. The tiers loosen one step at a time because a wrong match would put
a false "quoted" on a client file.

**`identity(name)`** gives one token per carrier, for grouping quotes and rows: the key when the name matches, else
`n:` and the normalized, squashed name (≤ 120 characters), so "VSP" and "VSP Inc." are one carrier; a blank name or
"Unknown carrier" belongs to no carrier. **`display_name(name)`** is the registry's spelling for a matched carrier,
else the name as given. **`split_names(text)`** reads the RFP's "Other carriers" box as names: it splits on commas,
semicolons, slashes and new lines, and on a spaced "and" or "&" when both sides are names; each name is at most 60
characters, and repeats of one carrier collapse (K104).

**Nicknames.** `/api/meta/` serves each carrier's key, name and aliases, so the Advisor's finder (F14) and Find on
Documents (E64) match "UHC" to UnitedHealthcare (OQ14).

### 4.8 Census header synonyms — `census/importer.py`

**Source of truth once built:** `census/importer.py` (slice 12), generated from the old
`benefits/market/census_reader.py` (`HEADER_SYNONYMS`). This table feeds the offline mapper (C14), unchanged. Claude's
mapping assist (slice 51) sees column shapes only and never replaces it (D109).

Used to map an uploaded census file's column headers to census columns (§5.3.2). Headers are normalized first:
lower-case, every character outside `a–z 0–9 space` becomes a space, runs of spaces collapse. Each column's own key
with underscores as spaces, **and its label** (§4.4), are also exact synonyms.

| Key | Synonyms |
|---|---|
| `ext_emp_id` | emp id, employee id, emp no, employee number, eid, id |
| `first_name` | first name, fname, first, employee first name, member first name, given name |
| `last_name` | last name, lname, last, employee last name, member last name, surname |
| `relationship` | relationship, rel, relation, rel code, relationship code, member type |
| `dob` | dob, date of birth, birth date, birthdate, birthday |
| `ssn` | ssn, social, social security, social security number, ss, ssn no dashes, emp ssn, dependent ssn, member ssn |
| `gender` | gender, sex, m f |
| `address1` | address, street address, address 1, addr, home address, street |
| `city` | city, home city |
| `state` | state, st, home state |
| `zip` | zip, zip code, postal code, postal, home zip, home zip code, home postal code, zipcode, residence zip |
| `division` | division, div, location, department, dept |
| `emp_class` | class, emp class, employee class, occupation class, job class |
| `hire_date` | hire date, date of hire, doh, start date, employment date |
| `medical_plan` | medical plan, plan, plan name, plan selection, med plan, plan election, current medical plan, current plan, current plan election, current medical, medical plan name |
| `medical_tier` | tier, coverage tier, coverage, med tier, coverage level, election, coverage election |
| `effective_date` | medical effective date, medical eff date, effective date, eff date, coverage effective date, coverage start, benefit start date |
| `subscriber_ssn` | employee ssn, subscriber ssn, ee ssn, primary ssn, employee social security number |
| `middle_name` | middle name, middle, mi, middle initial |
| `address2` | address 2, address2, address line 2, apt, suite, unit |
| `phone` | phone, phone number, telephone, cell, mobile, home phone |
| `annual_salary` | annual salary, annual base salary, base salary, salary, annual income, wages |
| `job_title` | job title, title, occupation, position |
| `work_state` | benefit work state, work state, work location state, employment state |
| `term_date` | termination date, term date, termination, separation date, end date |
| `rehire_date` | rehire date, rehire, re hire date |
| `dental_plan` | dental plan, dental, dental plan name, dental election |
| `dental_tier` | dental tier, dental coverage, dental coverage tier, dental level, dental coverage level |
| `dental_effective_date` | dental effective date, dental eff date, dental effective |
| `vision_plan` | vision plan, vision, vision plan name, vision election |
| `vision_tier` | vision tier, vision coverage, vision coverage tier, vision level, vision coverage level |
| `vision_effective_date` | vision effective date, vision eff date, vision effective |
| `basic_life_amount` | basic life amount, basic life, basic life benefit, basic life volume, life amount, life insurance amount |
| `basic_life_effective_date` | basic life effective date, basic life eff date, life effective date |
| `vol_life_amount` | voluntary life insurance, voluntary life amount, voluntary life, vol life amount, vol life, supplemental life |
| `vol_life_effective_date` | vol life effective date, voluntary life effective date, vol life eff date |
| `std_amount` | std benefit amount, std amount, std, short term disability, short term disability amount |
| `std_effective_date` | std effective date, std eff date, short term disability effective date |
| `ltd_amount` | ltd benefit amount, ltd amount, ltd, long term disability, long term disability amount |
| `ltd_effective_date` | ltd effective date, ltd eff date, long term disability effective date |
| `employment_status` | employment status, employee status, employment type, ft pt, full time part time, fte status, work status |
| `hours_per_week` | hours per week, hours week, hrs per week, hrs week, weekly hours, hrs wk, hours wk, hours, hrs, scheduled hours, avg hours per week, average hours per week |
| `email` | email, email address, e mail, employee email, work email, email addr |
| `county` | county, home county, county of residence, county name |
| `waiver_reason` | waiver reason, waive reason, valid waiver, medical waiver reason, reason for waiving, reason waived, waiver, decline reason, reason for declining |

**Line-scoped keys.** Keys containing `medical`, `dental`, `vision`, `life`, `std` or `ltd` may be claimed by the
fuzzy pass (§5.3.2) only if that word appears in the header.

**Bare effective-date headers** (`effective date`, `eff date`, `effective`) take their line from the column
immediately before them, checking these phrases in order: basic life → `basic_life_effective_date`; vol life,
voluntary life, supplemental life → `vol_life_effective_date`; life → `basic_life_effective_date`; short term
disability → `std_effective_date`; long term disability → `ltd_effective_date`; std → `std_effective_date`;
ltd → `ltd_effective_date`; dental → `dental_effective_date`; vision → `vision_effective_date`;
medical → `effective_date`.

**Employee relationship words** (a row with one of these, or a blank relationship, is an employee): ee, emp,
employee, self, subscriber, primary, e.

---

## 5. Business rules

Every rule here lives in a pure function (no database access) inside the named module. Each has a table-driven test
that covers every row of the rule, plus one service test showing that the screens and files call that function, not a
copy (§12; Q.1). A rule that needs another app's fact takes it as an argument; only services and payloads call the
provider that supplies it (O.1). Each subsection ends with the porting parts and item IDs that hold the full rules,
and the slices that build them (§13).

### 5.1 Deal stages and client status — `deals/stages.py`, `deals/lifecycle.py`

**Stages.**
- Ladder: `intake → quoting → proposal → sold`. Automatic moves only go **forward**; a move to an earlier stage is
  ignored. They go through `deals.services.advance(deal, user, stage, reason)`, which reloads and locks the Deal row
  first (slice 6). Every stage change writes one Activity row that never merges.

| Event | Moves the deal to |
|---|---|
| Deal created | `intake` |
| The first quote read lands (§10.1; D75), or the first RFP email draft is marked sent (§5.7; K68) | `quoting` |
| The `issue` job stores an issued proposal's files (§7.12; J.6.4) — never a draft download | `proposal` |
| A plan marked sold (`quotes.set_sold`, §5.4) | `sold`; a Prospect client becomes a New client (below) |

- A user may also set the stage by hand to `intake`, `quoting` or `proposal` (forward or backward), never to or from
  `lost` (A30). `sold` is reached only by marking a plan sold. Un-selling the last sold plan on a deal returns it to
  `proposal`.
- **Lost:** "Mark lost" takes an optional reason (at most 300 characters; OQ48), records `lost_at` and
  `lost_from_stage`, and sets `lost`. It answers 409 on a deal that is already lost, and on a sold deal (un-sell
  first) (M3). "Reopen" restores `lost_from_stage` and clears the three lost fields.
- **What a lost deal refuses** is one list, `deals.rules.refuses(deal, action)`: sending to market, signing, marking a
  plan sold, booking, portal writes, client asks, automatic AI landing, and Convert to client (below). Each refusal
  answers 409 with a sentence. Internal edits pass: a lost deal is not locked (A19, O.3.7).
- **Deal type** (`deals.rules.deal_type(deal)`: New business or Renewal; M14, O.6 #25): `Deal.opened_as` copies the
  client's status when the deal is created, follows status changes while no plan on the deal is sold, then freezes.
  The type is Renewal only when `opened_as` is `existing_client`. One rule feeds the RENEWAL chip (J22), the home
  views, the Work queue, the Overview and commission's year (§5.6). It is not the client's status: a won prospect's
  deal stays New business while its client becomes a New client.
- **Archive** (`deals.services.archive_client`, `restore_client`; A18, M9, M103–M105; OQ46, OQ47 defaults): clients
  are archived, never deleted (`DELETE clients/{id}` answers 405). Archiving hides the client and its one deal from
  every list, even a sold deal; their pages still open, the Book keeps their records, and portal writes answer 410
  (`deals.rules.client_asks_open`). `deal.archived` is computed from the client (O.6 #17). Archive and Restore each
  write one Activity row and change neither the stage nor the client's status.

**Client status** (OQ2, answered). Daniel: "first they start off as prospects and we need to be able to transfer them
over to new clients and then existing clients". Prospects and New clients are built now; Existing-client work (year 2
on: plan years, renewals, reminders) waits with renewals (OQ1). This replaces v1.1's rule that a client becomes
`existing` when a deal sells.
- `Client.relationship` (the name is kept; screens say "Status") holds `prospect` (the default), `new_client` or
  `existing_client`, labelled Prospect, New client and Existing client. `client_since` is the agency date it became a
  client (the day of the sale or of the conversion; cleared on a return to Prospect). `converted_by_sale` is true when
  a sale made it a client. The status is stored, not computed: a hand conversion has no sale to compute it from.
- Only three things write it: the pure transition table in `deals/lifecycle.py` (the moves and their sentences), the
  status door `deals.services.set_status(user, client_id, to)` (§7.3), and `deals.services.sale_changed(user, deal,
  any_sold)`, which `quotes.set_sold` calls inside the sale's transaction, after `advance`. Lock order: the Deal, then
  the Client; the status door locks only the Client row.
- `deals` sits left of `quotes`, so the status door asks whether a plan is sold through a provider slot,
  `deals.providers.client_has_sold(client_id) → bool`, which quotes fills in `AppConfig.ready()` (§3.3). Its default
  answers `False`, which is true while no app can sell a plan.
- **Invariant** (tested): a client with a sold plan is never a Prospect.
- Daniel did not say when a prospect becomes a new client. The moves below are OQ101's default, built until he
  confirms them (§16).

| Move | How | Activity (area `client`) | Refused when (409, with the sentence) |
|---|---|---|---|
| create → Prospect | New client dialog, the default | the "Created …" row | — |
| create → Existing client | Dialog choice for a group the firm already serves; its deal opens as a Renewal | the "Created …" row | — |
| Prospect → New client, automatic | A plan on its deal is marked sold | `converted`, "Now a new client (a plan was sold)", on the sold deal; never merged; Revert refused: "Un-sell the plan to undo this." | — (a sale on a lost deal is already refused, H124) |
| Prospect → New client, by hand: "Convert to client" (the old "Link to client") | The status door | `converted`, "Converted to a client", on its deal (a firm row with `subject` = the client when it has none); Revert allowed | Its deal is lost: "This deal is marked lost — reopen it before converting the client." |
| New client → Prospect, automatic | The last sold plan across the client's deals is un-sold, and `converted_by_sale` is true | `prospect`, "Back to a prospect (no plan is sold now)" | — |
| New or Existing client → Prospect, by hand: "Back to prospect" (also fixes a wrong Existing pick) | The status door | `prospect`, "Moved back to a prospect" | Any plan is sold (`client_has_sold`): "A plan is marked sold — un-sell it first." |
| Prospect → Existing client | By hand, a classification fix | `status`, "Marked as an existing client" | — |
| New client → Existing client | Deferred with renewals (OQ1): when the first plan year ends or the first renewal starts | — | "A new client becomes existing with its first renewal, which this version doesn't build yet." |
| Existing client → New client | Never | — | "An existing client is past its first year." |

- A move to the current status writes nothing. Each row's `changes` holds the before and after of `relationship` and
  `client_since` under `client:<id>` (§3.7). A sale writes three rows: "Marked X sold", "Moved to Sold (a plan was
  sold)" and "Now a new client".
- **Un-selling.** `set_sold(False)` passes `any_sold`: whether any plan on any of the client's deals is still sold (v1
  has one deal per client). With none left and `converted_by_sale` true, the client is a Prospect again and
  `client_since` clears. A hand conversion, an Existing client and a client with another sold plan are left alone.
  Selling again converts again, with the new date. The deal's return to `proposal` and commission's void (H32) are
  unchanged.
- A client is created as a Prospect or an Existing client; New client is reached only through a sale or Convert to
  client. A lost prospect stays a Prospect. Archive never changes the status.

**Full rules:** Part A (A18, A19, A30); Part M (M3, M9, M14, M103–M105); O.3.7; O.6 #17, #25 and #42. The client
status has no porting part: this section, §6.2 (fields), §7.3 (endpoints) and items CL1–CL9 (§13) are its
specification. **Slices:** 6 (`advance`, `refuses`, the client status, `opened_as` and `deal_type`), 38 (archive,
the Archived page, Mark lost's 409 on a lost deal).

### 5.2 Intake — `intake/form.py`, `values.py`, `validation.py`, `coverage.py`, `checklist.py`

**Cleaning an answer** (`clean_value(question, raw) → (value, error)`; one cleaner for the producer, Claude and
portal paths, B.6). Leading/trailing spaces are removed. An empty answer is stored as "no answer" (the key is
removed from `answers`).

| Type | Accepts | Stored as | Error text |
|---|---|---|---|
| text | anything | trimmed text | — |
| text, key `fein` | `NN-NNNNNNN` or 9 digits (spaces ignored) | `NN-NNNNNNN` | `FEIN takes XX-XXXXXXX, not "<raw>"` |
| number, money, percent | a number after removing `$`, `,` and `%` (regex `-?\d+(\.\d+)?`) | the number as text (`"1500"`, `"7.5"`) | `<Label> takes a number, not "<raw>"` |
| date | any common date (month-first when ambiguous) | `YYYY-MM-DD` | `<Label> takes a date, not "<raw>"` |
| yesno | yes, y, true, 1 / no, n, false, 0 (any case) | `Yes` / `No` | `<Label> takes Yes or No, not "<raw>"` |
| choice | one option, matched without case | the option as written in §4.5 | `<Label> takes one of: <options> — "<raw>" is not one of them` |
| multi | a list, or options separated by commas, semicolons, slashes or spaces | a list: `["FL", "GA"]` (options as written, de-duplicated, in input order; B3) | `<Label> takes <first 12 options>…; not: <bad parts>` |

**Shown-when conditions.** `{"field": key, "op": "gt"|"gte"|"eq"|"nonempty", "value": x}`: `eq` compares the stored
text exactly; `gt`/`gte` compare numbers (false if either side is not a number); `nonempty` is true for any answer.
A hidden question keeps its stored answer but is not shown and never counts toward readiness.
It is never asked either; the portal gets it with its rule and reveals it live (B2).

**Effective date.** The answer `target_effective_date` writes `Deal.effective_date`, the date every app reads (B1,
N.1).

**Validation** (`validate_intake(deal) → {key: [issue]}`; issue = `{code, severity, message}`; severity `error` or
`warning`). Issues are advisory: they show beside the question and never block saving or "Ready to market"
(OQ50 default).

| Code | Severity | Rule | Message |
|---|---|---|---|
| `fein_format` | error | `fein` present and not `\d{2}-?\d{7}` | `FEIN "<v>" is not in XX-XXXXXXX format` |
| `counts_order` | error | `employee_count` > `total_employees` | `Eligible employees (<e>) exceeds total employees (<t>)` |
| `counts_sum` | warning | `enrolled_count` + `waiving_count` > `employee_count` (either present) | `Enrolled + waiving is more than the eligible count — check the numbers` |
| `state_format` | warning | `situs_state` not 2 letters; or any `states_operating` entry not 2 letters | `"<v>" is not a 2-letter state code` |
| `ale_suggest` | warning | `total_employees` ≥ 50 and `ale_status` blank | `<n> employees — likely an ACA Applicable Large Employer; please confirm` |
| `form_5500_contradiction` | error | max(`enrolled_count`, `enrolled_life_count`) ≥ 100 and `form_5500_required` = No | `<n> enrolled on at least one benefit line but Form 5500 is marked "No" — did you make a mistake, or is the group out of compliance? (100+ participants triggers a filing)` |
| `pcori_contradiction` | warning | `self_funded` = Yes and `pcori_filing` = No | `Self-funded groups owe a PCORI filing (IRS Form 720, due July 31) — please double-check this answer` |
| `funding_contradiction` | warning | `self_funded` answered, and the medical current-coverage row's `funding` says otherwise (Yes against `fully_insured`; No against `level_funded` or `self_funded`) | `The medical coverage is recorded as <funding> — check "Are you self-funded?"` |
| `hours_range` | warning | `hours_threshold` outside 1–40 | `Hours/week is usually between 1 and 40` |
| `child_age_range` | warning | `child_age_limit` outside 18–30 | `Dependent child age limit is usually 26 (allowed 18–30)` |
| `email_format` | error | a contact's email not `^[^@\s]+@[^@\s]+\.[^@\s]+$` (key `contact:<id>`) | `"<v>" is not a valid email address` |
| `renewal_past` | warning | a current-coverage row's renewal date before today (key `coverage:<id>`) | `Renewal date is in the past` |
| `renewal_far` | warning | a current-coverage row's renewal date more than 12 months away | `Renewal date is more than 12 months out` |

**Readiness** (`intake/values.py`; B33).
- *Needed questions* = every **Q** question, plus every **C** question that is currently shown. The deal's rule for a
  question in `Intake.rules` changes this: **Required** adds it, **Waived** removes it (B37; OQ17). The "Missing"
  badge and the rose star use this one rule (B6).
- *Contacts OK* = at least one client contact with role `hr_admin` or `benefit_admin` that has both a name and an email.
- **BOR on file** = `bor_signed_at` is set (typed signature) **or** a document of kind `bor` exists on the deal.
- *Census OK* comes from census (§5.3.5), through `intake.providers.census_state` (O.1).
- **Ready to market** = every needed question answered with no open warning (§3.7: a value Claude doubted counts once
  a person approves or ignores it) **and** contacts OK **and** census OK **and** BOR on file **and** the marketing
  checklist clear (below). The badge reads **Sent to market** once the deal is marked as marketed, **Ready to market**
  when ready, else **Blocked** (B10, B33).
- Readiness % = round(answered needed ÷ needed × 100); 100 when nothing is needed.

**Coverage intent** (`intake/coverage.py`, `intake.services.set_intent`; B14–B24; OQ15).
- Each line with coverage or requested gets a row: in force; this year Shop it, Keep as-is or Leave off; on the
  proposal. `set_intent` is the only writer of `Deal.requested_lines`: it calls `deals.services.set_lines` in the same
  transaction, and the header's Lines chips and the Lines-to-quote chips call it too (B17, B32).
- The coverage subcards and the intent card edit the same `CurrentCoverage` rows through one service (B14; OQ15).
- **Confirm** stores the confirmed decisions as readable JSON (`Intake.intent_confirmed`). The intent is confirmed
  while the decisions still equal today's; any change shows "⚠ Changed since confirmed" (B20).
- `line_states` (shopped, presented, gap, dormant) and the lines kept off the proposal are pure functions of the
  intent and quotes' `quote_lines` provider (B24, O.1). A line kept as-is needs no recommendation (§5.4); the Advisor
  flags a line kept off the proposal (F13).

**Marketing checklist** (`intake/checklist.py`; B25–B28, O.6 #2).
- The tier comes from the one headcount (`intake.providers.headcount`, filled by quotes' `enrolled_headcount`, §5.7):
  micro (10 or fewer enrolled), small (11–50), mid (51–99) and 100+. The census asks ZIP codes below 51 and home
  addresses from 51 (B25).
- Items (B26), each auto, attested or a document: coverage intent (auto, done when confirmed, never waived), census
  (auto: census OK), COBRA, salary and occupation (life or disability requested), the medical questionnaire (a
  document, an "on file" tick or the signed in-app form), the stop-loss disclosure (optional until picked), the
  renewal and invoice per line (auto "not needed" when nothing is in force or shopped), claims (100+, or level- or
  self-funded, the intake answer included) and custom asks.
- Each item's state lives in `Intake.checklist` (B27). The COBRA tick lives there too, and the Census tab shows the
  same tick (O.6 #2). One card serves Intake, the RFP tab and the Overview (B28).
- Built in slices 41 (the COBRA tick, which the census page reads through `intake.selectors.checklist_item`) and 40:
  `intake/checklist.py` (pure: `tier`, `items`, `meter`, `card`; the words in the data module
  `intake/checklist_words.py`, the old app's), `intake/readiness.py` (pure: contacts OK, BOR on file, the gaps and the
  state), `intake/gate.py` (the one read of a deal's gate) and `set_checklist_item` for every attested item: the
  "On file" / "Confirmed" tick and the requirement (Waived "Not needed"; Required "Still needed ▸" with a note the
  client sees, not done even when satisfied; '' Undo); the two derived items take neither. Medical marketed = medical
  requested, or nothing requested yet (the old rule). The questionnaire rows read their form and signature from
  `intake.providers.questionnaire_items` (slice 42); custom asks are Review's (slice 53). A file a person marked the
  wrong one counts for nothing (old `document_rows`). `intake.summary.facts(deal_ids)` gives Agenda and the Overview
  the ready state, its gaps and the counts (§5.10; its provider calls are per deal until agenda's batch slots, 60).

**Mark as marketed** (`intake.services.mark_marketed`; B34, K33). While the deal is not Ready to market it answers 409
listing the gaps (`{detail, keys, gaps: [{kind, key, label}]}`: the needed questions blank or to check, HR contact,
Signed BOR, Census, then the checklist's missing items); "Market anyway" (`override`) confirms and records the skipped
items in Activity (the summary names six and "N more"; `changes` keeps every gap's words under `skipped`). It keeps
the first `marketed_at`; a repeat changes nothing; Undo reverts it, and `unmark_marketed` takes it off by hand. A lost
deal refuses it (§5.1). It moves no stage (OQ52 default): the deal reaches `quoting` on the first quote read or RFP
send. The BOR's typed signature (`sign_bor`, `clear_bor`; B29) records who signed, when and who recorded it; a lost
deal refuses signing (`refuses(deal, 'sign')`), not clearing.

**Full rules:** Part B (B1–B37; B.6), O.1's `intake.providers`, O.6 #2. **Slices:** 11 (models, the cleaner, coverage
and intent), 39 (the form and validation), 40 (contacts, checklist, BOR, readiness, Mark as marketed).

### 5.3 Census — `census/`

#### 5.3.1 Storing a value
Every census value is stored as text after this cleaning; an empty value removes the key.

| Column type / key | Stored as | If it can't be read |
|---|---|---|
| tier | `EE`/`ES`/`EC`/`FAM` via §4.2, or `Waived` for a waiver word | kept as typed (a `tier_unknown` error shows) |
| date | `YYYY-MM-DD` (parsed month-first) | kept as typed (`dob_unparseable` for DOB) |
| ssn | `NNN-NN-NNNN` when it has 9 digits | kept as typed (`ssn_format` shows) |
| money, number | the number with `$` and `,` removed | kept as typed |
| `gender` | `M` or `F` when the text starts with M or F | kept as typed |
| `zip` | 4 digits get a leading zero; 5 or 9 digits keep their form (`12345`, `12345-6789`) | kept as typed |
| `state`, `work_state` | upper-case | — |
| anything else | trimmed text | — |

The grid displays dates as `MM/DD/YYYY`.

A hand edit stores origin `typed`, or `relay` while "From the client" is on (C4). A client's own answers wait for
approval (§5.8).

#### 5.3.2 Importing a census file — `census/importer.py`, `census/pivot.py`, `census/matching.py`

1. **Read the file.** `.csv`: decode UTF-8 (with or without BOM), else Latin-1. `.xlsx`/`.xlsm`: the chosen worksheet
   (default the first; when the first has no header row, the first sheet that has one), read-only, cached values
   (formulas never run). `.xls`: the chosen sheet via xlrd. Every cell becomes text: dates `MM/DD/YYYY`, whole-number
   floats without `.0`, everything else trimmed text. Anything else → 400 `This file is not a spreadsheet or CSV census
   file.` (the words never name the file: a census file's name may carry a person's, §3.8; slice 12).
2. **Find the header row:** the first of the top 10 rows with at least 3 cells that are non-empty and not made only of
   `0-9 / . , $ -`. None → 400 `Could not find a header row in this file.` Drop trailing blank header cells. Data rows
   start on the row below by default; fully blank rows are dropped; each kept row remembers its sheet row number. A row
   with nothing in any mapped column is no one (Warner's template numbers its empty rows down column A).
   **The user may override the sheet, the header row and the first data row** in the mapping dialog (a census
   returned on Warner's own template has its header on row 3 and data from row 7, §9.8; rows 4–6 are not people).
3. **Reshape a one-row-per-benefit file** (`census/pivot.py`; C13). The file's shape is scored: at 0.80 or more it is
   pivoted to one row per person automatically; from 0.55 to 0.80 it is flagged "needs attention". It is refused when
   more than 40% of rows have no person key, more than 20% of benefits are unknown, more than 10% of identities
   conflict, or no employee is found. Of two duplicate rows the first is kept. Only the recipe is stored on the
   import; rows are rebuilt from the file. The mapping screen shows the reformat: before → after, lines found, things
   to check, "use the original file instead" (C15).
4. **Propose a mapping**, column by column, left to right. Each census key may be used by one column only (the first
   to claim it):
   - **Positional hint** (§4.8 bare effective dates) → confidence 0.70.
   - **Exact:** the normalized header equals the key with spaces, the column's label, or a synonym → 0.95.
   - **Fuzzy:** among unused keys (respecting the line-word guard), the synonym or key sharing the most words with the
     header, where the synonym has no more than one word beyond the overlap → 0.60.
   - No match → unmapped.
   - `low` = mapped and confidence < 0.85. Low entries are highlighted for review.
   - **Sample values** (up to 3 per column) are read from the stored file each time the mapping is shown, **never
     stored**: names, SSNs and birth dates must not outlive the import that needed them.
   - Claude's mapping assist (slice 51) sends column shapes only, never sample values (D109).
5. **Review.** The user sees every column, its samples and its proposed target, and may change a target or set it to
   "Ignore". Assigning one key to two columns → 400.
6. **Build people** from the rows under the confirmed mapping:
   - **A cell matching `***-**-NNNN` (a masked SSN)** stands for the SSN on file for that person when its last four
     digits agree, and is blank otherwise (C16). It is never used to match a person or link a dependent.
   - A row is an **employee** if its relationship is blank or one of the employee words (§4.8); otherwise a
     **dependent**.
   - An employee with no `ssn` but a `subscriber_ssn` gets `ssn` copied from it.
   - A dependent's employee is found by: the digits of its `subscriber_ssn` matching an employee's SSN (or that
     employee's `subscriber_ssn`), else its `ext_emp_id` matching an employee's, else the last employee above it.
     A dependent with no employee above it stays unlinked (a `dep_orphan` error shows).
   - Values are cleaned (§5.3.1). Sources: `origin: import`, the document id, and `cell` = sheet name + column letter +
     row number (e.g. `Census!D12`).
7. **Match to the existing roster** (`census/matching.py`; C17; empty for a new deal). An employee matches by the
   employer's own id (`ext_emp_id`), else SSN digits, else last name + first name + date of birth (case-insensitive),
   strongest first; an identity two rows share is never used. A dependent matches only inside its matched employee's
   family: by SSN, else name + date of birth, else relationship and order.
   - Matched: a value the file states differently replaces the stored value only when the stored value came from a
     file (origin `import` or `ai`). Values people entered (typed, relayed, or a client's approved answer) stay, so a
     re-import never undoes a person's work. An equal value changes nothing, not even its source (§3.7). Blanks in the
     file keep the existing value.
   - Unmatched incoming: created.
   - Existing people missing from the file: removed softly (`removed_at`), with their dependents, and restored by
     identity if a later file brings them back. Someone a person worked on (a typed, relayed or client value, or added
     through a link) is kept instead, and reported (C17, L112).
8. **Dry run first.** `apply?dry_run=1` lists who would be added, changed, removed and kept, and writes nothing;
   `cells_changed` lists, per changed person, the columns that would change (labels only, no values). The screen shows
   them and asks for confirmation when anyone would be removed. The real apply runs in one transaction, marks the
   import `applied`, rewrites `CensusFacts` (§5.3.5), and logs `Imported census: <n> people (<d> dependents)`. A
   census file a client uploads becomes a staged import that staff apply (L.6, slice 59); a PDF roster Claude reads
   arrives the same way (`CensusImport.job`, slice 51).
   **Built in slice 51:** the read's people wait on the import (`CensusImport.read`: the columns read and each person
   with kind, employee, file, page per value and the values Claude was unsure of), never on the job; the mapping dialog
   shows them as columns mapped to themselves (no sheet or rows to choose: 400), its dry run and Apply build people
   from them (`census.reader.staged`), each value `origin: ai` with its file and page and `low` where Claude was unsure,
   and Apply uses the read too. Applying or discarding empties `read` (D74, B13); a new import sets a waiting read
   aside with its job.

#### 5.3.3 Is a cell required? — `census/fields.py: is_required(key, member, deal, rules, carrier_required)`
One function; nothing else decides this. The first step that applies decides:
1. Dependent and the key is in Employment, Medical, Dental, Vision, Life or Disability, or is `zip` → **not
   required**. No override reaches past this.
2. The deal's rule for the column (`CensusSettings.rules`: Auto, Required or Waived; C27, OQ17): **Waived** → not
   required; **Required** → required. Both beat every step below, carrier files included.
3. Key marked **A** or **E** in §4.4 → **required**.
4. Key marked **L:x** → required when line *x* is in `deal.requested_lines`.
5. Key marked **M** (`medical_plan`) → required when `medical` is requested **and** the deal has a current-coverage
   row for medical with `in_force = true`.
6. Key in `carrier_required` → **required** for an employee when a picked carrier's file needs it for employees, and
   for a dependent when one needs it for dependents.
7. Otherwise → not required.

`carrier_required` is `{key: {employee: [carrier], dependent: [carrier]}}`: the columns marked required by the census
files the deal's RFP will send (the picked carriers' own formats, hand-ticked formats, and the universal format when a
picked carrier or "Other carriers" takes it; K124). The carrier names say whose file needs the cell. `rfp` is to the
right of `census` (§3.3), so census never imports it: `census.providers.carrier_required` is a provider slot whose
default answers `{}`, and rfp fills it at start-up (O.1). rfp's answer is pure over the request, the format
definitions and the requested lines; it reads no census. Built in slice 45 (`rfp.formats.required`): a column counts
when the carrier requires it (our flag or the carrier's asterisk) and holds a census key, its own or what a required
derived column reads by value (UHC's "Out of Area" reads the ZIP); a carrier, "Other carriers" or tick change rewrites
census's stored counts on commit (`census.services.refresh_facts`).

#### 5.3.4 Validation — `census/validation.py: validate(members, deal) → {(member_id, key): [issue]}`

Severity is one word, `error` or `warning`, everywhere (C21; the old app's `warn` hid duplicate-person warnings, C3).

| Code | Severity | Rule | Message |
|---|---|---|---|
| `ssn_format` | error | SSN present, not 9 digits | `SSN "<v>" is not 9 digits` |
| `ssn_invalid` | error | 9 digits starting 000, 666 or 9 | `SSN "<v>" is not a valid SSN range` |
| `ssn_duplicate` | error | two people with the same SSN digits (both flagged) | `Duplicate SSN — another person in this census has the same SSN` |
| `person_duplicate` | warning | same last name + first name + DOB on two rows (both flagged on last name) | `The same person twice? Another row has this name and date of birth` |
| `dob_unparseable` | error | DOB present but not a date | `Could not read "<v>" as a date` |
| `dob_future` | error | DOB after today | `Date of birth is in the future` |
| `dob_age` | error | age over 110 | `Age <n> — check the birth year` |
| `dob_young` | warning | employee younger than 14 | `Employee is <n> years old — check the date of birth` |
| `zip_format` | warning | ZIP not `\d{5}(-\d{4})?` | `ZIP "<v>" is not a 5-digit ZIP` |
| `state_format` | warning | state not 2 letters | `State "<v>" is not a 2-letter code` |
| `tier_unknown` | error | any tier column not a tier code and not `Waived` | `<Label> "<v>" is not one of EE / ES / EC / FAM / Waived` |
| `dep_relationship` | error | dependent with no relationship | `Dependent is missing a relationship` |
| `dep_orphan` | error | dependent not linked to an employee | `Dependent is not linked to an employee` |
| `tier_ee_deps` | warning | employee medical tier EE but has dependents | `Tier is Employee Only but dependents are listed` |
| `tier_ec_no_child` | warning | tier EC, no dependent whose relationship contains child, son, daughter, dependent child or stepchild | `Tier is EE + Child(ren) but no child dependent is listed` |
| `tier_es_no_spouse` | warning | tier ES, no dependent whose relationship contains spouse, wife, husband, partner or dp | `Tier is EE + Spouse but no spouse dependent is listed` |
| `tier_fam_no_deps` | warning | tier FAM, no dependents | `Tier is Family but no dependents are listed` |
| `hire_after_effective` | warning | hire date after medical effective date | `Hire date is after the coverage effective date` |
| `missing_required` | error | a required cell (§5.3.3) is blank | `Required` |

Age = whole years between date of birth and today.

#### 5.3.5 Census summary
`employees`, `dependents`, `errors`, `warnings`, `required_total` (required cells), `required_filled`,
`missing_required` = total − filled, and `readiness_pct` = round(filled ÷ total × 100) (100 when total is 0), capped
at 99 while any error exists. **Census OK** = at least one employee, no missing required cells and no errors.

These counts are stored in `census.CensusFacts`. Census's services rewrite them in the same transaction as the write
that changes them, and they must equal a fresh rebuild (`manage.py rebuild_facts`, and a test after every service):
with row `flags`, the one exception to "computed on read" (OQ9 c, O.3.7, Q.3 #9). An RFP pick that changes
`carrier_required` refreshes them on commit (K.6). Pending client answers and people added through a link count only
once approved (L.6). Intake reads Census OK through `intake.providers.census_state` (O.1).

#### 5.3.6 Enrollment rollup — `census/rollup.py`
For each requested line with a composite basis (and always for medical): count employees by their value in the line's
tier column (§4.1): `EE`, `ES`, `EC`, `FAM`, `waived`, `blank` (and `unknown` for a word that is none of them, so the
buckets add up to the employees). Dependents are never counted. Worksite tier-rated
lines have no tier column of their own, so they count `medical_tier`, shown as "Borrowed from medical" (C39, F86). For
volume lines: the sum of the volume column over employees (§4.1; C42). **Enrolled employees** (`rollup.enrolled`;
C43): employees whose value in the line's own tier column is a tier code (`Waived` and blank never count); a line with
no tier column of its own counts every employee. PEPM lines are priced from it. For stop-loss: the medical
EE+ES+EC+FAM total, else the employee count (C44).

**By plan.** For medical, dental and vision the rollup also counts tiers per distinct text in the line's plan column
(`medical_plan`, `dental_plan`, `vision_plan`): `{"Aetna HDHP 3300": {EE: 40, …}, "": {…}}`. The census holds each
employee's plan *and* tier — exactly the per-plan counts a user would otherwise count and retype. Census does not
know the deal's plans (`quotes` is to its right); matching the texts to current plans is done in `quotes` (§5.5).

**Stored.** The rollups by line and by plan text are kept in `CensusFacts.rollup` with the counts (§5.3.5), so
`enrollment_for` (§5.5) reads them without a census query per plan (N.1). They count approved values only.

**Census against typed counts.** The census prices a plan only where nothing typed comes first in `enrollment_for`
(§5.5), with one exception: counts typed before the latest census import give way to it, with "Keep my typed counts"
(F91; OQ18, answered). The census's last import time is what that rule compares against. Worksite tier-rated lines
also borrow typed medical counts when there is no census (§5.5 step 8; OQ19 default); dental and vision never borrow.

#### 5.3.7 Derived census facts
- **Full-time count (FTE):** employees whose `hours_per_week` ≥ the intake `hours_threshold` (default 30). Blank hours
  are not counted. Blank when the roster has no employees.
- **Age at effective date** (carrier exports): whole years from DOB to the deal's effective date; blank if outside
  0–120 or either date is missing.
- **In contiguous US:** a ZIP whose first three digits are **not** 006–009, 090–099, 340, 962–969 or 995–999.
- **Aged 65 or more** (Medicare-eligible; C46, J66): people whose age at the effective date is 65 or more, dependents
  on their own date of birth. Only the count leaves the server.
- **COBRA** is a checklist tick in `Intake.checklist`, shown on the Census tab too (C25, O.6 #2).

**Full rules:** Part C (C1–C47; C.5), with L.6 (client answers, soft removal, staged client files) and K124
(carrier-required columns). **Slices:** 12 (import, matching, validation, rollups, `CensusFacts`), 41 (the roster
grid, COBRA), 51 (Claude's mapping assist and PDF rosters).

### 5.4 Plans — `quotes/`

**Storing a plan value** (types from §4.3):

| Type | Accepts | Stored as | Refused with |
|---|---|---|---|
| text | anything | trimmed text | — |
| amount | anything | a number (`$`/`,` removed) when it is one, otherwise the carrier's text as typed | — |
| percent | anything | a number (`%` removed) when it is one, otherwise text | — |
| rate | a number (`$`, `,` removed), or N/A, NA, `-`, blank (= empty) | number text with up to 2 decimals | `<Label> takes a number, not "<raw>"` · more than 2 decimals: `<Label> takes dollars and cents, not "<raw>"` |
| rate4 | as rate | the number as typed, up to 4 decimals (`0.185` stays `0.185`) | as rate, with "up to 4 decimals" |
| number | a number, or blank | number text | `<Label> takes a number, not "<raw>"` |
| yesno | as intake (§5.2) | `Yes`/`No` | `<Label> takes Yes or No, not "<raw>"` |
| choice | one option of the named vocabulary (§4.6), matched without case on key or label | the option's key | `<Label> takes one of: <labels>` |
| url | `http://…` or `https://…` | as typed | `<Label> takes a web address starting with http:// or https://` |

Display: amounts as currency (`$1,500`) when numeric, percent as `20%`, rates as `$512.34`, rate4 values as typed
(`$0.185`), choices by label.

Why two rate types: life and disability unit rates are commonly quoted to three decimals, and rounding them to two
moves the premium by several percent (0.185 → 0.19 is +2.8%; 0.035 → 0.04 is +14.1%). Tier rates, contributions and
quoted premiums are always dollars and cents, and the client workbook's total formula is exact only for whole cents
(§9.4). The team's own proposals carry life rates to 3 decimals (0.142) and disability rates to 2; 4 leaves headroom,
as the earlier system did (D-077).

**Writes.** `PATCH plans/{id}/` changes only the carrier, name, plan number, notes, `client_name` and values; roles,
links, stars, recommendations, order and the sale each have their own service (F71, J14). A value write may carry
`expect`, the value the user last saw, and answers 409 when the stored value has changed since (O.6 #33, J74). A typed
value over a read one keeps its link to the file and the read value (F141, §3.7).

**Roles and links.**
- `current` — in force today. Has no `renews` or `replaces` link.
- `renewal` — the current carrier's new rates for a current plan. `renews` MUST point to a current plan on the same
  deal and line. At most one renewal per current plan.
- `alternate` — a competing plan. `replaces` names **zero, one or several** current plans on the same deal and line:
  - **one** — a plan offered in place of that current plan. Several alternates may replace the same current plan,
    either as **options** the client chooses between, or as plans **bought together** (two plans offered to employees
    side by side in place of one, or one carrier plan filed under two plan numbers, such as Florida Blue's HSA 5182
    for employee-only and 5183 for the dependent tiers, paired to print as one column, below);
  - **several** — a **consolidation**: one plan taking the place of two or three current plans (three plans become
    two);
  - **none** — a plan **added** beside the current plans, or any plan on a line with no current plans.

  Options and plans bought together differ only in their enrollment: each option carries the current plan's whole
  enrollment (as if everyone took it), while plans bought together split it between them (§5.5). The flexibility is
  deliberate (Daniel, 2026-11-10): the user decides what replaces what.
- A line may hold **several current plans** (a group can offer two or three plans today). Each is its own slot, and
  its renewal and the quotes that replace it group under it (F44, F120). A line with two or more prices from per-plan
  counts or the census by plan name, never from one line-wide figure (§5.5).
- **Roles change** only through `plans/role/` (Mark current, Remove current; F53). A sold plan or a priced version
  never becomes current; a copy may. A plan that turns current loses its star and its links; a recommendation stays
  and now means "Keep this plan" (OQ37, as in the old app).
  Changing a role clears links that no longer apply; a current plan that stops being current turns its renewal into an
  alternate and leaves every `replaces` list. On a line with two or more current plans, "Replacing:" shows beside
  every presented quote, and "Several…" makes a consolidation (F52).
- **"Create renewal"** on a current plan creates a `renewal` with the same carrier, name, plan number and every value
  except the rate and contribution groups (§4.3 `rates`, `contrib`, and `lf`), with their sources copied. `funding`
  is in the info group, so it is copied.
- **Copy** (`copy_plan`; F81, D-049): a standalone peer with every value, rates included, and its sources, without
  marks, confirmations or a read value; the user names it (unnamed: "<name> — copy", as in the old app). It is an
  `alternate` replacing what the original replaces (a current plan's copy replaces that plan; a renewal's copy replaces
  its current plan), arrives right behind its original (the old app's "side by side"), and records
  `derived_from` with `derived.kind` "duplicate". A star, a recommendation and a sale never ride. It replaces v1.1's
  rate-less "Copy as alternate" (F77).
- **Priced versions** (`plans/priced/`; F76–F84; kept by OQ7): a concession (% or $ off or up, or set to, on all rates
  or per rate), a bundle (per line, naming the quote that must sell) or a premium holiday (a $ credit a year, or free
  months) is a copy of a quote with its rates, then the operations, with `derived_from` and a `derived` record. This
  is how one plan is shown at several premiums, e.g. as quoted and as negotiated. A version rides right behind its
  original on every screen (F120), prices its original's people (§5.5; F87), takes no option number, and never becomes
  current. Its dry run equals the commit (F76). Bundle templates wait (F79). Built in slice 35, as in the old app:
  - only the premium moves: the line's rate keys and the quoted group premium (`priced_kinds.premium_keys`); a % on
    all rates also reaches the quoted premium, a $ amount or a set-to does not; a bundle composes as
    rate × (1 − pct/100) − flat, its dollars never on the quoted premium; rates round half up to the cent, a unit rate
    to the decimals it was stated in (two to four); a rate below zero is refused (`math/pricing.py`);
  - a changed rate takes a typed source without the file; every other value keeps its original's source, without
    marks, approvals or a read value; a star, a recommendation and a sale never ride;
  - the in-force plan takes only a premium holiday; a sold plan none; a bundle is refused on a quote whose rates
    already include it (`Plan.bundling`, set by PATCH); a dollar credit belongs to one plan (free months batch);
  - one request may price several plans of one line (a bundle opens on every quote of the carrier), one Activity row;
    a new version is starred when its line has stars and room (F83), never on a line with no stars (the old bug 17),
    and past the room it is added unstarred with a warning;
  - ✎ re-prices a version from its original (cells typed on it since are replaced), keeping its kind; ✕ removes it
    through the delete door, and Undo restores it;
  - a credit in free months is that many months of the version's own premium, worked out on read (the old app froze
    it at creation), so it follows the people; the net after the credit is `credit` on the comparison (F80).
- **Move to another line** (`move_line`; F59): the plan keeps its id; values outside the new line's fields are dropped
  (kept in Activity); its star, recommendation, links, enrollment and packages clear (a renewal arrives as an
  alternate); the plans it leaves lose their link to it, as when a plan stops being current; a current plan joins the
  end of the target's current plans; option numbers renumber (J159). Refused, in words, for sold plans, priced
  versions and copies, originals that have them, and plans a bundle requires. Revert puts it all back.
- **Delete** (F60): soft (`Plan.removed_at`), with Restore. Deleting a current plan turns its renewal into an
  alternate and removes it from every `replaces` list; these are real writes in the same Activity row, and Revert
  undoes them together. Restore is that Revert (the old app restored a version); it refuses, in words, when a rule now
  blocks it. A removed plan keeps its package memberships, hidden, so Restore brings them back. A sold plan cannot be
  deleted: in a batch it stays and is named, "… is sold, so it stays. Unmark sold first." (H.6; the old app's
  `kept_reason`), and a call that names only sold plans is refused with that sentence. **Clear line** soft-deletes
  every plan on the line except current and sold ones (F61).
- **Merge** (F142; O.6 #32): one quotes service joins two columns that are one plan (a rate page's row and an SBC's
  column); Claude's `merge_plans` tool and the reader's combine call it. As in the old app, the kept plan takes each
  value it lacks with its source (a named key takes the merged value even where it has one), and the merged plans'
  codes and file; the merged plans are then removed, in one revertible Activity row. A sold plan on either side, or a
  plan of another line, is refused in words. Pairing is not merging: a pair's halves stay two plans.

**Stars and the presented set** (F50–F55, F119, J1–J3; OQ11 default).
- ★ means **on the proposal** (D-210). `quotes/presented.py: presented(line)` is the one membership rule: the line's
  current plans, its recommended plans and its starred plans, or every plan when none is starred. A line the coverage
  intent keeps off the proposal presents nothing (J2). The cap, slots, Pages, client files and proposals all call it;
  `ProposalConfig.lines` holds per-line settings only, never membership.
- Once a line has stars, its renewal prints only with its own star or a recommendation, as in the old app (OQ11
  default).
- `room(line)` allows **16 columns a line**, counting every presented column and a pair once (below). A star or a
  recommendation past it is refused with a sentence, under the Deal-row lock. With no stars a line can present more
  than 16: the PDF and PowerPoint then refuse; the workbook never does (J3).
- A current plan takes no star. A star records `star_reason` ("Hand-picked", or Rank's reason) and `starred_by/at`;
  reasons never reach client files (F50, J.4).
- A fresh star on an unlinked quote, on a line with two or more current plans, links it to the nearest current plan
  (`closeness`) in the same write (F51).
- "Clear shortlist" clears one line's stars, with one Activity row and Revert (F55).

**Order and slots** (F43–F49, F120, J4–J11; OQ13, answered).
- One order per line: `Plan.sort_order`, one sequence per line, read only through the pure `order.layout(plans)`
  (`quotes/order.py`): current plans first; quotes grouped under the plan they replace (a renewal first, a
  consolidation under the first plan it replaces, each priced version right behind its original, copies as peers);
  unlinked plans last; hand order inside a group (F120, J4). Values never sort it, so a rate edit moves nothing. The
  board, Pages, the PowerPoint, the workbook, the Documents grid and the questionnaire's plan rows all read it (N.1).
- Plans read from a quote arrive in the quote's column order (F138).
- **Transpose** (⇄; F34, F35) swaps the board's rows and columns; it is kept per browser, refused above 60 plans
  (`TRANSPOSE_MAX`), and never changes the order.
- ▲▼, ◀▶ and ‹ › move a plan within its group, passing hidden plans; current plans move as slots, and their groups
  follow; "Back to the default order" resets the line. Each write locks the Deal row, saves `sort_order` with
  `bulk_update` and records one Activity row (F43–F48, J5, J6). A refused move says why.
- **Slot picks** (Pages and its PlanPicker; F45, J10): picking plan X into plan P's place gives X P's place, star and
  links, and P takes X's; a plan off the proposal may replace one on it; the star count never changes; a swap trades
  whole `replaces` sets; the plan that leaves the proposal loses its recommendation; a warning comes before a
  renewal's page comes down. "＋ Add a plan" beside a current plan puts a quote in its group (F46, J11).
- **Stop-loss is ordered like every line** (OQ13, Daniel: "yes"): its plans take the arrows, slot picks and reset.
  This reverses the old app, which kept stop-loss quotes in the order added (F49, now Drop) and refused arrows and
  slot picks (J7); O.6 #26's exception goes.

**Recommended** (the firm's pick; OQ37, answered: "allow it as the old app did"). Any plan may be marked recommended,
several per line, within `room()`: the firm often puts forward two or three options for one plan, sometimes the same
plan design at different premiums, and decides with the client (Daniel, 2026-11-10). A current plan may be recommended
too, as in the old app: it means "Keep this plan", answers for itself, takes no column beyond the one it already has,
shows no change and prints "Keep this plan" (old app 891f1b3, `proposal_ready`, `_several_recommendations_page`). The
line's **recommendation** is its recommended plans. A shopped line is **covered** when every current plan on it is
recommended itself or renewed or replaced by at least one recommended plan (a line with no current plans: at least one
recommended plan). A line the coverage intent keeps as-is needs no
pick and never blocks Issue (J52; J.5 B36). Each recommended plan shows its own premium and change against what it
replaces (§5.5); totals for combinations come from packages made only of recommended plans (§5.5). The written reasons
live in `ProposalConfig.reasons`, per line (J56). A recommended plan is always presented on the proposal. A slot pick
that takes its place clears the recommendation (J10); turning it current keeps it, as "Keep this plan" (F53, OQ37).

**Sold** (`quotes.set_sold`; F123, H124; OQ12 default). Any number of plans on a line may be sold, in any combination:
three plans for three, two plans for three, two plans for one. Marking a plan sold sets `sold_at`, moves the deal to
`sold` and makes a Prospect client a New client (§5.1), in one transaction; on commit, `sold_changed` books its
commission (§5.6). A lost deal refuses it (H124). A sold plan cannot be deleted, made current or moved to another
line, and its Activity row refuses Revert (O.3.2). Un-selling the last sold plan returns the deal to `proposal`, voids
the line's commission record (H32) and returns a client the sale converted to Prospect (§5.1). The line's **sold set**
is its sold plans, totalled as a package (§5.5).

**Option numbers** (`Plan.option_number`, per line; J159; OQ35, OQ36 defaults). A plan's number is its place in
reading order: the order it first appears on the pages of the chosen layout (`proposals.pages`). Numbers are stamped
at Issue under the Deal lock and never reused (`quotes.labels.numbers`, `services.stamp_option_numbers`;
`proposals.line_layout.reading_ids` gives Issue the order; slice 25). Renewals are numbered; current plans and priced
versions are not; a move to another line renumbers (Revert of the move is refused once its number went to another
plan). Until Issue, drafts show the numbers Issue would stamp, and wear Draft (J102). They
replace v1.1's C/R/P labels; `option_label` goes (O.6 #15).

**One plan under two plan numbers** (Florida Blue's 5182 for employee-only and 5183 for the dependent tiers; D-219;
O.6 #4). Entered as two plans, bought together, then paired with `Plan.pair_of`: "⧉ One column with… · Split" on
Pages, or Claude's `pair_plans` (J15, J161, F137). Working screens show both plans; `room()` counts a pair once;
client files print one column under the first plan's id and option number, each row worked out by code, and the
column's total is `package()` of the pair (O.3.6). How the in-network single deductible prints is OQ42 (default: both
figures, "EE $2,500 / PP $5,000"). This replaces v1.1's one-plan "5182 / 5183" entry. **Built (slice 33):** the pair
is stored on its second half (`pair_of` names the first), one live pair per plan; `quotes.pairs.found` is the one rule
for which pairs print as one (both halves presented, one kind: two current plans or two quotes; a current pair's two
renewals follow it, derived on read); `presented.room()`/`added()` count a pair once, and Split is refused on a full
line as a star is; `quotes.packages.folded` prices the column as `package()` of the halves and measures every column
against it; `proposals.pair_fold` folds the line inside `line_layout.lay_out`, so Pages, the builder, Issue's numbers
and the three files read one column (the old `plan_merge` rules for each value). The halves, like any plans bought
together, are priced on their own typed counts (§5.5 step 1); GD1 carries the pair (FB1 + FB2 under B).

**Other fields.** `client_name` ("Name on client documents") prints in client files in place of the plan name and
rides with copies (J14). `codes` identify a plan for re-reads and SBCs, and the finder searches them (F143).

**Plan value status:** `missing` when the field is required (§4.3) and blank; `to_check` while
`documents.review_rules.open_warning` holds: a value Claude read and doubted, or the locator could not find in its
file, until a person approves or ignores it, or a value marked ⚑ Needs checking (OQ28, answered; E.6). Otherwise per
§3.7. A plan's open warnings are counted in `Plan.flags`, rewritten in the same transaction (O.3.7): `Plan.save()`
stamps it, and the writes that `bulk_update` (moves, marks, the locator's answers) stamp it themselves (slice 17).
Nothing waits on them: Issue, exports and edits go ahead with values still to review (OQ28).

**Full rules:** Part F (F34, F35, F43–F61, F76–F84, F119–F124, F137–F144), Part J (J1–J15, J52, J56, J159, J161),
O.3.6, O.6 #4, #9, #15, #26 (as OQ13 settles it), #27, #32 and #33; OQ102 (the "+ Plan" prompt for options or
plans bought together, and the "+ Package" dialog). **Slices:** 7 (stars, the presented set, order, roles, sold),
8 (copy, move, delete, merge), 9 (Transpose), 14 (slots), 25 (option numbers, `client_name`), 33 (pairs), 35
(priced versions).

### 5.5 Premium math — `quotes/math/`

All money is computed with `Decimal` and rounded **half away from zero** by `quotes/math/round_decimal`, after reading
any float at 15 significant digits: exactly what Excel's `ROUND` does. It is the only rounding of money: commission
rounds its shares through it (§5.6), and the browser does no money math (O.3.7, H.6). Stored values are read as
`Decimal`.

```python
def round_decimal(amount, places=0):
    if amount is None:
        return None
    if isinstance(amount, float):
        if not math.isfinite(amount):
            return None
        amount = format(amount, '.15g')
    return Decimal(amount).quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
```

`round_money` stays only as a thin wrapper for callers that print (H.6). `quotes/math/` is a package (OQ9 b):
`premium.py`, `enrollment.py`, `pricing.py` (priced-version operations, bundle parts, `net_after_credit`) and
`stop_loss.py` (F.6).

**Comparison base.** The current plan or plans a plan is measured against:
- a renewal → its current plan;
- an alternate with `replaces` → the plans it replaces (a consolidation's base is the sum of them);
- an alternate without `replaces` on a line with exactly one current plan → that plan;
- otherwise none (an added plan, or a line with no current plans).

**Typed enrollment** has the shape of the line's rate basis: `{EE, ES, EC, FAM}` for composite lines; `{volume}` for
`volume_1000` and `weekly_10` (the total benefit volume in dollars) and `payroll_100` (the annual covered payroll);
`{lives}` for `pepm` and `stop_loss`. Integers or dollar amounts ≥ 0.
- It is kept per plan (`Plan.enrollment`) and once per line (`LineEnrollment`: the line figure, `on` and `typed_at`,
  one row per deal and line). One service writes both: the Advisor's counts card and the Proposal builder's
  EnrollmentStrip are two doors to it (F85, F88, J48; OQ18 keeps the strip).
- Saving writes the line's whole typed set and stamps `typed_at`; an unchanged save writes nothing.
  `LineEnrollment.on` switches the line's typed counts on or off; `Plan.enrollment_on` goes (F88, O.6 #10).
- The card offers the line figure where the line has no current plan. A stored figure keeps applying when a current
  plan arrives later, so no price vanishes (F88).
- Counts Claude reads from a quote are proposed unticked, as the line figure or per current plan when the quote prints
  them per plan; once accepted they are typed counts (D67; OQ30 default).

**Which enrollment prices a plan** (`math/enrollment.py: enrollment_for(plan, line, census)` → `(enrollment, source)`
or a reason), for every basis. The first step that gives figures wins (O.6 #24):

1. The plan's own typed counts → `typed`.
2. A **priced version**: its original's enrollment, so "5% off" prices the same people (F87) → `from original plan`
   (built in slice 35).
3. A **renewal**: its current plan's typed counts → `from current plan`. An **alternate** with a comparison base: the
   sum of its base plans' typed counts → `from replaced plan` (a consolidation carries the people of every plan it
   replaces). Plans **bought together** in place of one plan must have their own counts typed (step 1), splitting the
   current plan's people between them; until then each carries all of them, and a package that holds them both says so
   (below).
4. **Census by plan**, on medical, dental and vision: when every enrolled employee's plan text on the line (§5.3.6) is
   matched to a current plan, the census counts of the texts matched to the plan's comparison base (a current plan:
   its own texts) → `census`. The matches are kept on the current plans (`Plan.census_names`, §6.7): exact name or
   plan-number matches are proposed automatically, and the user confirms the rest in the Advisor's counts card, once
   per deal (C41, F90).
5. If the line has **two or more current plans**, stop → no price, reason `per_plan_counts_needed`. A line-wide figure
   would spread everyone across every plan. The Advisor names the plans that lost their price and opens the split,
   offering the quote's per-plan counts; unlinked quotes on the line ask what they replace (F88; OQ20, answered: no).
6. The line figure (`LineEnrollment`) → `line`, "Typed for the whole line" (built in slice 13: a key of its own, so
   the words tell it from a plan's own `typed` counts).
7. The census rollup for the line (§5.3.6): tier counts, volume, payroll or lives by basis → `census`. A worksite
   tier-rated line's census counts are the medical tier counts → `proxy`, shown as "Borrowed from medical".
   **Stop-loss** lives: the medical enrolled employees (the current medical plans' enrollment from any source, else
   the medical line figure, else the census) → `medical`, shown as "From medical enrollment" (F98); with no medical
   people, the census's own stop-loss lives → `census`.
8. A worksite tier-rated line with nothing above borrows medical's typed tier counts → `proxy`, "Borrowed from
   medical" (OQ19 default; F86, J48). Dental and vision never borrow.
9. Nothing → no price, reason `no_enrollment`.

Every source is named in words on the screens that show a premium (F86, J83).

**Typed counts against a later census** (F91; OQ18, answered "yes keep the strip"). Counts typed before the latest
census import give way to the census wherever the census can price the plan (steps 4 and 7): a typed figure saved
when the deal had fewer applied census imports than it has now (`LineEnrollment.census_seen` below the count) yields to
the census figure for the same plan. The counts card
says "Priced from the census now · Keep my typed counts"; Keep stamps the typed counts as typed now, so they win
again. Counts typed after the import win. `typed_at` is the line's (`LineEnrollment`), so one save stamps the line's
whole typed set, per-plan counts and line figure alike, and records `census_seen`. Pricing compares that with the
deal's applied imports on every read, so an import re-prices the Advisor with no signal between census and quotes
(slice 13). The count decides, never the clock: comparing `typed_at` with `last_import_at` let a clock that stepped
back put a save and an import in the wrong order (the slice-13 F91 flake); `typed_at` is only shown. Nothing changes silently: a booked deal shows "Out of date · Update" (H120),
a started questionnaire shows its band notice (G133), and mapping becomes Agenda's lead step (N.2). v1.1's "typed
enrollment always wins" goes.

**Monthly premium by rate basis** (`monthly_premium(plan, line, enrollment) → (dollars | None, reason, quoted)`, where
`quoted` says the quoted premium was used):

| Basis | Formula | No price when |
|---|---|---|
| composite | round_decimal(Σ over tiers with count > 0 of rate × count) | counts sum to 0 → `no_enrollment`; an enrolled tier has no rate → the quoted `group_premium_monthly` if present, else `missing_rate` |
| volume_1000 | round_decimal(volume ÷ 1,000 × unit_rate) | volume blank or 0 → `no_enrollment`; no unit rate → quoted premium, else `missing_rate` |
| weekly_10 | round_decimal(volume ÷ 10 × unit_rate) | as volume_1000 |
| payroll_100 | round_decimal(volume ÷ 12 ÷ 100 × unit_rate), volume = annual covered payroll | as volume_1000 |
| pepm | round_decimal(unit_rate × lives) | lives blank or 0 → `no_enrollment`; no unit rate → quoted premium, else `missing_rate` |
| stop_loss | round_decimal((sl_spec_rate + sl_agg_rate + sl_other_load) × lives); blank agg/other count as 0 | lives blank or 0 → `no_enrollment`; no `sl_spec_rate` → quoted premium, else `missing_rate` |

"Quoted premium" = the plan's `group_premium_monthly`, rounded. It is **never** used when nobody is enrolled — a price
with no enrollment is "no price", never $0. The rule is the same for every basis: no enrollment, no price.

All six bases are built. The composite, PEPM and stop-loss figures are pinned by Stephanie-signed golden keys (Q.4);
`volume_1000`, `weekly_10` and `payroll_100` each get a worked example Stephanie checks and signs as a key (OQ103).

**Age-banded medical.** About 95% of medical quotes are composite; carriers quote groups under 10 employees by age
instead. The team presents those with **the total monthly premium only**, not rate by rate (Stephanie, 2026-10-27).
Such a plan is carried on the quoted-premium path: `group_premium_monthly` holds the total and prints with †. When a
plan has a quoted premium and no tier rate at all, its tier rates are not flagged `missing`. Per-person costs (the
team keeps them on a hidden tab of their own spreadsheet) are not part of version 1.

**Derived figures:**
- Annual = monthly × 12 (blank when monthly is blank).
- Change vs base: `delta` = annual − base annual; `pct` = round_decimal((annual − base) ÷ base × 100, 1); `pct` is blank
  when the base is 0 or blank. A consolidation's base annual is the sum of the plans it replaces. **The change is
  shown only when the plan carries the same people as its base** (its enrollment equals the base's, tier by tier):
  a plan bought together with another carries part of its base's people, so it shows "Part of HDHP 3300's
  enrollment — see packages" instead.
- Renewals also report per-tier rate change: for each tier, `rate − current rate` and the percentage as above.
- Employee cost per tier = max(0, round_decimal(rate − contribution, 2)); blank if either is blank.
- Net after credit (a premium holiday; F80): `net_after_credit` takes the credit, a dollar amount a year or free
  months, off the annual premium. The workbook's Compare tab takes its contribution modes from the same contribution
  math (J148).

**Packages** — `package(plan_ids, line, results, key='', label='', missing_renewals=None) → {key, label, plan_ids,
priced, monthly, annual, enrollment, same_people, change, reason}`, where `results` holds each plan's priced result:
one pure function over an **explicit list** of plans on one line. A sale, a recommendation and a package are all
*sets* of plans; the rule that keeps their totals honest is about **people**, not plan counts:

- **Total:** when every plan in the package has a price, `monthly` = Σ of its plans' monthly premiums (each already
  rounded) and `annual` = monthly × 12. Otherwise no total, and the reason names the plan ("Aetna HMO 1500 has no
  price: enter enrollment").
- **Same people as today:** the package's enrollment — summed over its plans, tier by tier for composite lines,
  volume or lives otherwise — equals the Current package's. **Only then is a change against Current shown**
  (`delta` and `pct` as above). Otherwise the reason says how it differs, in words: "Enrollment differs from today
  (EE 20 vs 10, ES 6 vs 3) — are two options counted together?" or "No renewal entered for PPO 1500" when current
  plans are missing from it. This one rule refuses a sum across a choice (people counted twice) and a partial set
  (people missing), and it lets a consolidation, an added plan and plans bought together compare correctly once each
  person is counted once (Stephanie, 2026-10-29: enrollment must match, "apples to apples").
- Packages shown per line, in this order — the Advisor and the proposal call the same function with the same lists:
  - **Current** — the line's current plans. A line with no current plans (new coverage) has no Current package and
    no changes.
  - **Renewal** — the renewal plans, shown with a total only when it covers the same people as today. Its `pct` is
    the "average increase" printed on proposals.
  - **One per carrier** — that carrier's alternates, offered automatically only when the line has current plans and
    the carrier's alternates cover the same people as today. A carrier with two options for one plan offers none:
    its options are a choice, not a set.
  - **Packages a user builds** (`Package`, §6.7) — any plans on the line, named by the user ("UHC —
    consolidated", "Cigna with HDHP", "Florida Blue HSA 5182 + 5183"). This is how a carrier's second combination, a
    consolidation, an added plan and plans bought together are totalled (Rebecca, 2026-10-08: a carrier's extra
    options become "another alternate package"). Total when priced; change when the same people as today.
  - **Sold** — the sold set, once any plan on the line is sold; total when priced, change when the same people.
- **The recommendation** is plan by plan (§5.4): each recommended plan shows its own change against its base. Its
  totals are the packages made **only** of recommended plans.
- **A pair** printed as one column (§5.4) is totalled as `package()` of its two plans (O.3.6, J15).

**Worked examples** (each MUST be a unit test):

| Case | Inputs | Expected |
|---|---|---|
| Composite | rates EE 500.00, ES 1000.50, EC 900.25, FAM 1500.75; counts 10/3/2/5 | 5,000 + 3,001.50 + 1,800.50 + 7,503.75 = 17,305.75 → **17,306** |
| Half-up | 2642.5 | **2643** (Python's `round` gives 2642) |
| Half-up, cents | round_decimal(2.675, 2) | **2.68** |
| Missing enrolled rate, quoted premium 15,000 | rates EE only; counts EE 10, ES 2 | **15,000** (quoted) |
| Missing enrolled rate, no quoted premium | same, no `group_premium_monthly` | no price, `missing_rate` |
| No enrollment | counts all 0, quoted premium 9,000 | no price, `no_enrollment` |
| Volume per $1,000 | volume 1,250,000; unit 0.12 | **150** |
| Unit rate with three decimals | volume 2,000,000; unit 0.185 | **370** (rounded to 0.19 it would be 380) |
| No volume | volume blank; unit 0.12; quoted premium 400 | no price, `no_enrollment` |
| Payroll per $100 | payroll 3,000,000; unit 0.45 | 3,000,000 ÷ 12 ÷ 100 × 0.45 = **1,125** |
| PEPM | unit 3.50; 42 lives | **147** |
| Stop-loss | spec 85.20, agg 12.10, other blank; 40 lives | (97.30) × 40 = **3,892** |
| Change | annual 120,000 vs base 100,000 | delta **20,000**, pct **20.0** |
| Two current plans, no typed counts | medical line, 2 current plans | no price, `per_plan_counts_needed` |
| Unlinked alternate, one-plan line | current D typed 10/3/2/5; alternate E with no `replaces` | E uses D's counts (`from replaced plan`); E's comparison base is D |

**Enrollment examples** (each MUST be a unit test; GD3's script follows them, Q.4). One medical line unless a case
says otherwise.

| Case | Inputs | Expected |
|---|---|---|
| Quote-first line | no current plan; ten alternates; line figure 20/5/3/2 | every alternate prices 20/5/3/2 (`line`, the line figure) |
| A current plan arrives | as above, then current plan D | D and every alternate still price 20/5/3/2; no price vanishes |
| A second current plan arrives | as above, then current plan F | D, F and the unlinked alternates have no price (`per_plan_counts_needed`); the Advisor names them and opens the split; each unlinked alternate asks what it replaces |
| The split | D typed 12/3/2/1, F typed 8/2/1/1; alternate E linked to D | D and F price their own counts; E prices 12/3/2/1 (`from replaced plan`) |
| Priced version | a "5% off" version of E | prices E's people, 12/3/2/1 |
| Census after typed counts | D's and F's counts typed Nov 2; a census imported Nov 5 whose plan texts match D and F | D, F and E price from the census; the card shows "Priced from the census now · Keep my typed counts" |
| Typed after the census | as above, then counts typed Nov 6 | the typed counts win again |
| Borrowed | an accident line, no census, no accident counts; medical line figure 20/5/3/2 | accident prices 20/5/3/2, "Borrowed from medical" |
| Never dental | a dental line, no census, no dental counts; medical typed | no price, `no_enrollment` |
| Stop-loss lives | no lives typed on the stop-loss plan, no current contract; current medical plans enrolled 20/5/3/2 | 30 lives, "From medical enrollment" |

**Package examples.** One medical line. Current plans A "HDHP 3300" $10,000/mo and B "PPO 1500" $8,000/mo, each
with typed enrollment. Renewals A′ $10,800 and B′ $8,640. Cigna alternates C1 $9,500 and C2 $9,200 replacing A, and
C3 $7,900 replacing B. Every alternate carries its base's enrollment unless the case says otherwise.

| Case | Package | Expected |
|---|---|---|
| Current | A, B | annual **216,000** |
| Renewal, complete | A′, B′ | annual **233,280**; change **+17,280**, **+8.0%** |
| Renewal, partial | A′ only | no total: "No renewal entered for PPO 1500" (summing A′ alone would print −40.0%) |
| A carrier's two options for one plan | Cigna's alternates C1, C2, C3 | no Cigna package offered: A's people are counted twice |
| A package a user builds | "Cigna" = C1, C3 | annual **208,800**; change **−7,200**, **−3.3%** |
| Recommendation with options | C1, C2 and C3 recommended | covered; C1 shows 114,000 (−6,000, −5.0%) and C2 110,400 (−9,600, −8.0%) against A's 120,000 |
| Recommendation not covered | C1 only recommended | not covered: "Nothing recommended for PPO 1500"; issuing refuses (§7.12) |
| Consolidation, three plans to two | U1 $17,000/mo replaces A and B and carries both plans' people | U1's base is A + B: annual **204,000**; change **−12,000**, **−5.6%**; the package "U1" shows the same |
| Plans bought together | H1 $4,800/mo and P1 $5,600/mo both replace A, enrollment typed to split A's people; package H1, P1, B′ | annual **228,480**; change **+12,480**, **+5.8%**; H1 and P1 each show "Part of HDHP 3300's enrollment" instead of a change |
| Bought together, enrollment not split | as above, but H1 and P1 each still carry all of A's people | total shown; no change: "Enrollment differs from today …" |
| One-plan line, unlinked alternate | current D $5,000; Aetna alternate E $4,750, no `replaces` | E's base is D; Aetna package offered: annual **57,000**; **−3,000**, **−5.0%** |
| New line | no current plans; two Cigna dental options | no Current package, no Cigna package; a user-built package totals with no change |

**Full rules:** Part F (F85–F92, F98, F116–F118), O.6 #10 and #24, Part J (J15, J48, J83), D67, H.6 (rounding).
**Slices:** 7 (`quotes/math/` and `round_decimal`), 13 (`LineEnrollment`, `enrollment_for`, the arrival rule, the
headcount), 19 (counts landing from a read), 35 (priced versions), 36 (stop-loss).

### 5.6 Commission — `deals/comp.py`, `commission/math.py`, `commission/rules.py`

- **Parsing** (`deals/comp.py: parse_comp(raw)`; H1), one parser for the deal's agreed rates, intake's in-force
  commission and the agency default: a bare number or text (`5`, `"5%"`) means a percentage; a dict
  `{"type": "pct"|"flat"|"pepm", "value": …}` names its type. `$`, `%` and `,` are ignored. Errors: unknown type
  `Type must be percentage, flat, or PEPM`; not a number `Must be a number`; negative `Must not be negative`;
  percentage over 100 `Must be between 0 and 100`. Stored as
  `{"type": t, "value": "<the exact decimal>"}`: `1000000` and `12345.67` stay exact, never `%g`.
- **Label:** pct `5%`; flat `$5,000/yr`; pepm `$32 PEPM` (cents shown only when not whole).
- **Effective rate per requested line:** the deal's agreed rate for the line (`Commission.rates`; H5), else the agency
  default (`AgencySettings.default_commission`; H8), else none.
- **Basis package per line** (§5.5; H6; OQ74 default): before the sale, Renewal, else Current, else the first starred
  plan as a one-plan package labelled "estimate": the first that has a total. Once the line has a sold plan, only the
  Sold package counts; with no total, its reason shows. (A recommendation with several options per plan has no single
  total, so it is not a basis.)
- **Expected annual revenue:** pct → round_decimal(basis package's annual premium × value ÷ 100); flat →
  round_decimal(value); pepm → round_decimal(value × the employees in the basis package's enrollment × 12), so each
  line uses its own employees (H7). Blank when the needed figure is missing; the note names where the enrollment came
  from. Deal total = sum of the lines that have a figure.
- **Worked example** (a unit test): three sold medical plans with annual premiums 25,644, 26,064 and 24,384 at 5% →
  basis 76,092 → **3,805**. (Counting only one sold plan would show 1,282.)
- **Split** (H10–H22, H.6): rows `{party, role, amount, renewal_amount, basis, expires_after_years, works_it}` on the
  deal (`Commission.split`) or the client (`ClientSplit`); role primary, secondary, split or referral; the amount a
  comp; basis pool or gross. The split that applies: the deal's, else the client's, else the deal owner's producer
  party, else the client owner's, else the house at 100% (H10). Exactly one appointed primary; each role takes only
  its kinds of party; a % is at most 100 (H19). Saving a primary who has a login sets `Deal.owner` (a client split,
  `Client.owner`) through `deals.services.set_owner` (H22). All-tier users and the deal's owner save a split (OQ70
  default).
- **Shares** (`compute_shares`; H.6) are integer millionths (100% = 1,000,000), worked out in the old order: gross
  rows come off the top; the house takes its % of the rest; flat and PEPM rows come off the pool; % rows take their
  share of what is left; the primary keeps the rest; every row is capped. The rounding residual goes to the primary,
  else the house, so shares total exactly 100% and dollars sum to the revenue. From year 2 a row's `renewal_amount`
  applies; past `expires_after_years` it pays nothing (H15, H121).
- **Booking** (H25–H37): `quotes.set_sold` sends `sold_changed` on commit, so a booking error never undoes the sale;
  the tab then shows "Sold — not booked · Book now". Commission books one record per line and carrier that has sold
  plans (OQ75 default), plus Keep-as-is lines with an in-force commission. A record freezes the sale's facts (carrier,
  plan, rate, the Sold package's premium, employees, effective date, year) as `sale` keys; a change to the sold set,
  or Rebook, refreshes them, and typed keys never change. Un-selling a line's last sold plan voids its record, never
  deletes it (H32). A lost deal never books (H124). Counts that change after booking show "Out of date: $X → $Y ·
  Update" (H120). Holes are listed, never guessed (H37).
- **Year** (H30; OQ72 default): with earlier records, 1 + the number of distinct earlier effective years among the
  client's records that are not void, hand-added ones included. With none, a deal opened for a Prospect or a New
  client is the first year; one opened for an Existing client (`opened_as`, §5.1) takes the typed "year with us", else
  books at the renewal % with a "year unknown" hole.
- **Who sees what** (`accounts.Profile.commissions_access`: none, own or all; H102; OQ73 default): admins see all; a
  producer defaults to own. Every deal user sees and edits the agreed rates, and sees the expected figure and the
  split chips. Booked shares and the Book follow the tier: own sees only its own share; none sees no ledger figures.
  Commission values in Activity are hidden below the all tier (O.3.2). Client files never carry commission (H125).
- The ledger (statements, receipts, reconciliation, gaps and statement reading) waits: OQ6 is answered No.

**Full rules:** Part H (H1–H37, H95–H102, H106, H120–H124) and H.6 (models, `compute_shares`, `year_terms`, booking,
visibility). **Slices:** 48 (rates, splits, parties, settings), 49 (booking, the Book, the disclosure); slice 50, the
ledger, waits (OQ6).

### 5.7 RFP — `rfp/request.py`, `rfp/printed.py`; the headcount in `quotes/facts.py`

- **Headcount** (`quotes.facts.enrolled_headcount(deal)` → `{count, source, estimate}`; K17, O.6 #24; OQ21 default):
  the medical enrollment the Advisor prices with (typed per-plan counts, the line figure, or the census by plan name
  or by line; employees only, waivers skipped), else the intake `enrolled_count`, else the intake eligible or total
  employee count, marked "estimate". The old app put intake first. This one number sets the size band, the intake
  checklist tier (§5.2), the questionnaire band and every printed enrolled count.
- **Size band:** `large` when the headcount is 51 or more, else `small`. Stephanie (2026-09-08): "the under 50
  enrolled is where we're going to go to Warner"; over 50 the team goes direct to the carriers. At exactly 50 the band
  is small, and the request form's choice is the only override (OQ53 default); a hand override of the band waits
  (K30).
- **Enrollment cross-check** (`quotes.facts.enrollment_check`; K19, M67): the intake `enrolled_count`, the census
  medical rollup total and the Advisor's medical enrollment are three answers to one question. When two or more are
  known and they differ, the RFP tab and the Overview show one warning naming all three and the one the band used,
  saying so when it is an estimate (`Enrolled: intake 42 · census 40 · Advisor 41`). Every file that prints the count
  lists the same warning in its check. The app never picks one silently.
- **Route:** `warner` (one request to Warner Pacific, who forwards it to the carriers) or `direct` (one email per
  carrier). By default the route follows the band (Warner under 51, direct from 51) until the first send pins it
  (`RfpRequest.route = ''`; K20, K64).
- **Lines:** the deal's requested lines. The RFP keeps no line list of its own (K16).
- **Funding requested:** default = the funding of the medical incumbent (`quotes.facts.incumbent`: the current medical
  plans, else the medical current-coverage row; F144): `fully_insured`→fully insured, `level_funded`→level-funded,
  `self_funded`→`aso`; unknown → fully insured **and** level-funded. A picked empty list is kept, with "Pick at least
  one funding type" (K21, K22).
- **Form** (Warner quote request form): default `simplified` for every group size; `small_group` (2–50) and
  `large_group` (51+) MAY be chosen; they add the carrier × line matrix, funding boxes and notes.
- **Carrier eligibility** (advice, never a block): a carrier is *eligible* when its Warner columns for the band (§4.7)
  cover at least one requested line; otherwise it shows the reason ("Not on the 51+ form", "None of the lines you
  picked"; K24).
- **Commission request text** (one cell on the form, one line in emails): the effective commission label for each RFP
  line (§5.6), built in `deals/comp.py` (K106). If all lines share one label, print it (`5%`); otherwise group
  lines by label, larger groups first: `5% Med · 15% Den/Vis` (short labels from §4.1). Built in slice 44 as
  `rfp.request.commission_text(lines, rates, default)` over `deals.comp`'s parser and labels (K29). From slice 48 each
  line's rate is `commission.selectors.requested_rates(deal)`: the deal's agreed rate, else the agency default (H109);
  the RFP card says which and links "Commission ▸". The builder moves to `deals/comp.py` when a left app needs it.
- **Group facts** (`quotes.facts.group_facts` and `rfp/printed.py`, built once per request; K101) used to fill forms,
  cover pages and emails:

| Fact | Source |
|---|---|
| `group.legal_name` | intake `legal_name`, else client name |
| `group.address_street`, `group.city_state_zip`, `group.zip` | intake `address_physical`, split at the first comma |
| `group.sic`, `group.fein` | intake |
| `group.total_employees`, `group.eligible`, `group.waiving`, `group.atne` | intake counts |
| `group.enrolled` | the headcount above, the same on every file (K17, K101) |
| `group.fte` | census FTE count (§5.3.7) |
| `group.years_in_business`, `group.waiting_period`, `group.locations` | intake |
| `group.current_carrier`, `group.current_funding` | `quotes.facts.incumbent(deal, 'medical')`: the medical current plans when there are any, else the medical current-coverage row (F144) |
| `group.contact_first`, `group.contact_last`, `group.contact_email` | `deals.contacts.primary`: the contact marked primary on a client-side role, else an HR admin or benefit administrator, else the first client-side contact; never a prior broker (M30) |
| `deal.effective_date`, `deal.due_date` | deal (intake's target effective date writes it, B1); RFP due date |
| `broker.agent` | `deals.rules.agent_name`: the deal's agent of record (from slice 38), else the owner, else the agency's producer name (O.6 #21, M27) |
| `broker.agency`, `broker.email`, `broker.address`, `broker.city_state_zip` | agency settings |
| `broker.commission` | commission request text |
| `broker.is_bor` | BOR on file (§5.2) |
| `funding.fully_insured`, `funding.level_funded`, `funding.aso` | requested funding |

The cover's return-to address is `AgencySettings.rfp_return_email`, else the deal owner's email (OQ65 default). Files
print approved values only: a client's pending answer never prints (OQ85 default).

- **Sent** (`rfp.services.mark_sent`; K64–K68, K120): each email draft (§9.11) can be marked sent or un-sent. A send
  stores its date (agency time), who, the route and who was asked (`RfpRequest.sends`); un-marking removes it. The
  first send pins a route that was following the band and moves the deal to `quoting` (`advance`, forward only). A
  lost or past deal refuses a send (409). A send whose draft no longer exists (the route or picks changed) stays
  listed under "Sent earlier", with Undo. Sends are the one record of who was asked: the proposal's Markets checked
  reads them (`rfp.asked_by_line`; J63, K117). Once a draft is sent, the Emails card offers intake's Mark as marketed
  (K33), which moves no stage (OQ52 default).

**Full rules:** Part K (K16–K33, K64–K68, K100–K106, K117–K124) and K.6 (`RfpRequest`, `request.py`, `printed.py`,
`audience.py`, `drafts.py`). **Slices:** 44 (request, band, cross-check), 45 (carrier census files; fills
`carrier_required`), 46 (forms, cover, packet, drafts, sends).

### 5.8 Review & request — `review/rules/`

Review owns requests, links, the client portal and the review queues; intake, census, questionnaire and the document
upload slots each expose one owner contract (O.3.4, L.6). The rules:
- A **request** (`ClientRequest`) holds the asks (intake questions or blocks; census cells, columns or a file;
  questionnaire forms; document slots) and an optional message (≤ 1,000 characters). Each person asked gets their own
  **link** (`ClientLink`).
- `review.rules.requests.carries(asks, ref)` is the one rule for what a link asks; the portal's allowlist, the ask
  rail, the tray and the board all call it.
- **Second factor** (`review.rules.policy.floor(asks)`; OQ80 default): a phoned PIN when the page shows census people
  or questionnaire answers, and for medical or claimant send-backs; upload-only asks and intake need only the private
  link (L64). A link's security never drops below the floor. An emailed code waits for outbound mail (L65).
- **Expiry** (OQ81 default): 7 days, sliding forward on a save at most once a day, never past 30 days from creation; a
  picked date stops the slide; submitting does not slide it (L61, L62). Revoke ends a link at once; Restore reopens
  the same URL within its ceiling (L60).
- **Copying a link marks it sent;** the app sends no email (OQ82 default).
- **Client answers** wait in the owner row's `client` JSON as pending, cleaned by the owner's rules (§5.2, §5.3.1). An
  answer equal to the stored value is ignored; a newer save replaces the pending one; a staff edit of the same slot
  closes it as `replaced`. Contacts, coverage and lines wait the same way (OQ84 default). Only **approval** moves an
  answer into the values, with origin `client` and the link; rejecting changes nothing (O.3.1). Rollups, readiness,
  carrier files and printed PDFs read approved values only (OQ85 default).
- **Client uploads** become documents to review: staff accept them or mark them "wrong file". A client's census file
  becomes a staged import that staff apply (§5.3.2).
- **SSN is never asked** on a link, and a masked SSN is blank wherever it arrives (§5.3.2; OQ16 default).
- Portal writes answer 410 on a lost or archived deal and on a closed request (`deals.rules.client_asks_open`, §5.1).

**Built (slice 53):** `review/rules/` `asks` (the shape and its refusals), `ask_words`, `requests` (`request_state`,
`link_state`, `carries`, `ready`, `in_progress`, `soonest_first`), `policy` (`floor`, the life rules, `nudge_open`)
and `badges`; the request and link services with the PIN (shown once, hashed, five tries); `review.summary.facts`.

**Built (slice 54):** the portal for intake, census and documents (§7.14): `review/portal/` (`guard`, `asked`, the
payload and its parts, the views, per-link throttles), `rules/portal.py` (the lock rule `editable`, `we_read`,
`form_stamp`, the to-do `rail`), the client's writes in `review/services/answers.py`, `client_adds.py` and `stamps.py`,
through the owners' doors `intake.services.save_client` / `sign_from_link` and `census.services.save_client` /
`add_people`. Contacts, coverage and lines wait as pending entries (OQ84); nothing prints a pending answer (OQ85); the
portal keeps link stamps and key-only Activity rows, and an IP only on a BOR signed there (OQ86).

**Full rules:** Part L (L.3; L.6: models, the owner contract, `rules/`, portal security) and O.3.4. **Slices:** 53–59.

### 5.9 Next step and agenda — `agenda/steps/`, `agenda/rows.py`

The deal's **next step** is the first live lead step in agenda's step list, worked out on read (I42, I67). The same
answer feeds the Waiting banner, the journey stepper and its badges, the Agenda tab and the Work queue (O.6 #3, I68).
v1.1's `overview/next_action.py` cascade is retired.
- Steps come from pure `agenda/steps/` over one facts dict per deal, built from every app's `summary.facts` (§5.10),
  in catalogue order, each on a track: intake, enrollment, quotes, close, after the sale, asks (I41, I.6). Only marks
  (`StepMark`: Later until a day, or Done anyway) and hand-added tasks (`Task`) are stored.
- **Quote-first deals** (N.2; OQ90 default): the intake, questionnaire and RFP steps are listed but lead only until
  quotes are in (I44, I46–I48). "Import the census" does not lead while typed tier counts drive the Advisor (I50).
  Once quotes are in and no enrollment source exists, the enrollment step leads as **"Add the census, or type
  enrollment in the Advisor"**, linking to the Census tab and to the Advisor's tier counts (I50). A census that
  arrives later makes mapping lead (I49).
- **Waiting:** "Waiting on the client" only when an open ask asked for those items (I45). Follow-ups open after 3 days
  for a client ask, 7 for a decision and 10 for carriers (`agenda.rules.FOLLOW_UP_DAYS`; I54, I58, I65).
- A lost deal has no steps and shows its lost state (I66, M34). After the sale the commission step leads ("Enter the
  commission for N sold lines"), then "Sold" (I60, I63; OQ91 default).

**Full rules:** Part I (I41–I69: the step catalogue and the next step; I.6: catalogue, rules, marks, rows,
`facts_for`) and review's ask predicates (`review.rules.next`, L4). **Slices:** 60 (steps, marks, tasks, the Agenda
tab), 61 (the shell's journey and badges, the Work queue).

### 5.10 Deal facts for Agenda and Overview — `<app>/summary.py`

Every app exposes `summary.facts(deal_ids) → {deal_id: dict}`: counts, dates and flags only, the same for every
viewer, in a fixed number of queries however many deals are asked (O.2; Q.3 #4). Readers:
- **agenda** builds steps, the journey, badges and the Work queue from them (`facts_for`; I.6);
- **overview** assembles the deal Overview (`overview.payload.overview(deal, viewer, today)`; M.6), and from slice 67
  the client page over a client's deals;
- **golden** checks Agenda and the Overview at each step of its deals (Q.4).

There is no registry in `deals`: agenda, overview and golden import each app's `summary` directly (O.6 #3, overruling
A.4). Commission adds `summary.card(deal, viewer)`, the figures the viewer's tier may see (H.6). An empty deal returns
every block, and no GET creates a row (O.2, M.6). Census's and quotes' counts come from their stored counts
(`CensusFacts`, `flags`; O.3.7), so the Work queue reads every open deal cheaply. The Overview's own rules are pure
(`overview/rules.py`: last contact, tiles, the Get to Market groups, Quote to Close; M37, M.6).

| App | Facts (where defined) |
|---|---|
| intake | answered and needed, missing labels, contacts OK, BOR, census OK, the ready state, checklist rows, `marketed_at` (B.6, M.6) |
| census | `CensusFacts`: employees, dependents, errors, required blanks, readiness, the last import (§5.3.5) |
| quotes | per line: plans quoted, to review, missing, starred, recommended and sold; covered; the headcount and the enrollment check (F.6, M.6) |
| questionnaire | per form: armed, started, progress, signed (G.6, O.1) |
| commission | the expected total, lines with a rate, the booking state; `card` adds the tier's figures (H.6) |
| rfp | cards done, carriers picked, sends, `first_sent_on`, carriers still awaited (K123) |
| proposals | the latest issue: version, date, by (J164) |
| review | requests and what they ask, pending and ready counts, open questions, the response state, nudges, the tray (L.6) |
| documents | live files by kind |

**Full rules:** O.2, M.6 (the Overview payload and its query keys), I.6 (`facts_for`) and each part's `summary.facts`.
**Slices:** each app's facts arrive with the app; agenda reads them from slice 60, the Overview from 62.

---

## 6. Data model

Django models, by app. Every model has an auto `id` (BigAutoField). "FK" = `ForeignKey`. `created_at` uses
`auto_now_add`, `updated_at` uses `auto_now`. JSON fields default to `{}` or `[]` as shown.

Models are listed by app in chain order (§3.3). Each subsection gives the key fields and JSON shapes and says what the
M0–M6 baseline has built. Part O, O.2, and each part's X.6 design have the full detail.

**Rules every model follows.**
- **Rows are created on the first write.** A one-to-one row (`Intake`, `CensusSettings`, `Commission`, `RfpRequest`,
  `ProposalConfig`, `DealAi`) or a per-form `Questionnaire` is created by its own app's first write, never by a GET. A
  missing row reads as its defaults (O.2; M.5 B34; J.5 B27).
- **Values and sources** follow §3.7: `Plan`, `LineEnrollment`, `Intake`, `Member`, `Questionnaire`, `Commission` and
  `Record` keep values in JSON with a parallel `sources` dict, written only by `deals/values.apply()`. A client's
  answer waits in its row's `client` JSON until a person approves it (O.3.1, L.6).
- **Soft removal.** `Plan`, `Member`, `Task`, `Note` and `Document` are removed softly. The default manager hides
  removed rows, and `all_objects` serves links and history (O.3.7, N.3 #8). Archived clients are filtered by `live()`
  in list selectors only, so their pages still open.
- **Stored counts.** Status is worked out on read, with two exceptions. The first is `census.CensusFacts` and the
  `flags` (open warnings) on `Plan`, `Intake` and `Questionnaire`: their owners rewrite them in the same transaction,
  and `manage.py rebuild_facts` and a test rebuild and compare them (O.3.7, OQ9 c). The second is the client status
  (below).
- **Stored on purpose.** Besides those counts: the client status (`Client.relationship`, `client_since`,
  `converted_by_sale`) and the frozen `Deal.opened_as`, because a hand conversion has no sale to compute it from
  (§5.1; this departs from O.3.7's single exception because of OQ2); frozen records (commission `Record`s,
  `ProposalIssue` files, signed questionnaire copies, `RfpRequest.sends`), file evidence (`QuoteLayout`,
  `Document.screen`, `Document.protected`) and one-time stamps (`Plan.option_number`) (N.3 #4).
- **Activity.** Every write records an `Activity` row with before and after per key (§6.2).

**Models by app.**

| App | Models | Built in 2Vantage today | Slices |
|---|---|---|---|
| accounts | `Profile` | none: Django's `User` only | 6 |
| deals | `Client`, `Deal`, `Contact`, `Note`, `Activity`, `AgencySettings` | all six (slice 38 added `Contact`, `Note` and the archive and header fields) | 5, 6, 38 |
| documents | `Document` | `Document`, hard-deleted | 15 |
| ai | `Job`, `DealAi`, `Chat`, `ChatMessage`, `CarrierNote` | — | 16, 24 |
| intake | `Intake`, `CurrentCoverage` | — | 11, 39, 40 |
| census | `Member`, `CensusImport`, `CensusSettings`, `CensusFacts` | — | 12, 51 |
| quotes | `Plan`, `Package`, `LineEnrollment`, `SavedView`, `QuoteLayout` | `Plan`, `Package` | 7–36 |
| questionnaire | `Questionnaire` | — | 42, 43 |
| commission | `Party`, `Settings`, `Commission`, `ClientSplit`, `Record` | — | 48, 49 |
| rfp | `RfpRequest` | — | 26, 44 |
| proposals | `ProposalConfig`, `ProposalIssue`, `ProposalTemplate`, `FirmPages`, `TeamMember`, `CoverImage` | `ProposalConfig`, in v1.1's shape | 25, 29, 32, 34 |
| review | `ClientRequest`, `ClientLink`, `ReviewNote`, `Seen` | — | 53 |
| agenda | `StepMark`, `Task` | — | 60 |
| overview | none | — | — |
| golden | none: deal specs and answer keys | `seed_golden` with GD1 and GD2, inside `proposals` | 3 |

**The baseline is not the design.** M0–M6 still carries v1.1 shapes that the parts list as defects. Each retires in
the slice named, and the subsections below describe the design, not these:
- the per-role `sort_order` and the carrier sort (slice 7; F.5 #27–32);
- `ProposalConfig.lines` as a list of presented plans (7 and 25; J.5 B28);
- `Plan.enrollment_on` (13; F88) and `Plan.option_label` (25; J.5 B29);
- hard deletes of plans (8), documents (15) and clients (38) (F.5 #36, E.5 #28, M.5 B36);
- the GET that creates `ProposalConfig` (25; J.5 B27);
- the summary-only `Activity` (5), and `update_plan` saving the row even when nothing changed, so `updated_at` moves
  (5; Q.3 #1);
- `Client.relationship` as `new` or `existing`, flipped at a sale, and `PATCH clients/{id}/` accepting it (6; OQ2);
- `set_sold` locking the Plan before the Deal, against §3.7's lock order (6–7);
- quotes' writes in `marks.py` and `template.apply` instead of a `services/` package (7);
- ids in request bodies read with a bare `int()`, so a bad id answers 500, and refusals answering 400 with
  `{"detail": ["…"]}` instead of 409 with a sentence (7 for quotes, 25 for proposals; §3.6);
- the golden deals inside `proposals` (3).

### 6.1 accounts
Django's `User` (username, email, first/last name, password, `is_active`, `is_staff` = **admin**,
`is_superuser`), managed in Django admin. Sessions use Django's database session backend.
There are two kinds of person: admin and producer (A2).

**Profile** — the per-person flags, edited in Django admin (A3; slice 6). Not built.

| Field | Type | Notes |
|---|---|---|
| `user` | OneToOne User | A user with no row reads the defaults |
| `claude_direct` | Bool, default false | A "direct" person: Claude's quote reads land at once with Undo, Opus may be picked, and the deal's AI budget can be overridden (D71, D91, D24) |
| `commissions_access` | `none`, `own` or `all` | The commission tier for the Book and ledger figures. A producer defaults to `own`; an admin is always `all` (H101, H102, OQ73) |

`accounts` exposes `can_direct(user)` and `commission_tier(user)` (O.2); `/api/auth/me/` serves both flags (§7.2).

### 6.2 deals

Built: `Client`, `Deal`, `Contact`, `Note`, `Activity` and `AgencySettings`, with the services (`deals/services/`)
`create_client`, `update_client`, `delete_client` (the seeders' and tests' only; HTTP answers 405), `update_deal`,
`advance`, `mark_lost`, `reopen`, `set_lines` (called only by intake), `set_status` and `sale_changed` (§5.1), and from
slice 38 `set_archived` (Archive and Restore), `set_owner` (a deal's or a client's), `set_facts` (Potential deal size,
Agent of record), `add_note`, `update_note`, `delete_note`, `create_contact`, `update_contact` and `delete_contact`.
Reverters: `client` (status), `deal_facts` (owner, deal size, agent of record), `archive` and `notes`; stage, date and
lost rows stay in area `deal`, which has none. Other apps call these `deals` modules: `values`,
`activity` (`log_access`, the reverter registry), `lines`, `selectors` (`person`, `deal_header`), `services` (`advance`,
`sale_changed`), `carriers`, `comp`, `clock`, `stages`, `lifecycle`, `rules` (`refuses`, `deal_type`, `agent_name`,
`is_past`, `client_asks_open`), `contacts.primary`, `downloads` and `pdfkit` (O.2); quotes fills `providers`.

**Client** — with its status: Prospect → New client → Existing client (OQ2; §5.1)

| Field | Type | Notes |
|---|---|---|
| `name` | Char(200), indexed | Employer name as the team refers to it |
| `relationship` (screens say "Status") | Char(20): `prospect` (default), `new_client`, `existing_client` | Labels Prospect, New client, Existing client. Replaces `new`/`existing` (slice 6) |
| `client_since` | Date, null | The agency date it became a client: the day of the sale or of the conversion. Cleared on a return to Prospect |
| `converted_by_sale` | Bool, default false | True when a sale made it a client. Un-selling undoes only this kind of conversion |
| `owner` | FK User, null, SET_NULL | |
| `notes` | Text, blank | The client's standing brief (the client page's Notes, slice 67) |
| `archived_at`, `archived_by` | DateTime, null; FK User, null, SET_NULL | Archive hides the client and its deal from every list; nothing is deleted and the status does not change (A18, M9, OQ46; slice 38) |
| `created_by` | FK User, PROTECT | |
| `created_at`, `updated_at` | DateTime | |

- **Who writes the status.** Only `deals/lifecycle.py` (the pure transition table and its sentences),
  `deals.services.set_status(user, client_id, to)` and `deals.services.sale_changed(user, deal, any_sold)`. quotes'
  `set_sold` calls `sale_changed` inside the sale's transaction, and fills `deals.providers.client_has_sold`, which
  `set_status` asks before Back to prospect. §5.1 gives the moves and their refusals; they are
  OQ101's default until Daniel answers (§16).
- **Invariant** (tested): a client with a sold plan is never a Prospect. Lock order: Deal, then Client; the status
  service locks only the Client row.
- **Migration** (slice 6): widen the field to 20 characters; `new` → `prospect`; `existing` with a sold plan →
  `new_client`, with `converted_by_sale` set and `client_since` = the first `sold_at`; any other `existing` →
  `existing_client`. 2Vantage holds no production data, so this only keeps dev and golden data consistent.
  `quotes/marks.py` lines 52–54, the flip to `existing`, go.
- **No delete.** A client is archived, never deleted: `DELETE clients/{id}/` answers 405 (M104, OQ47; slice 38). The
  `delete_client` service stays for `seed_golden`, GD-Big and tests only (M.5 B36).
- **A client may have no deal.** Commission's Add to book creates an outside client without one, with Status Existing
  client by default (H58; slice 49).

**Deal**

| Field | Type | Notes |
|---|---|---|
| `client` | FK Client, CASCADE, `related_name='deals'` | |
| `effective_date` | Date, null | Plan year start. Intake's `target_effective_date` writes it (B1, N.1) |
| `stage` | Char(10), default `intake` | §4.6. Automatic moves go only through `advance`: reload, lock, forward only (§5.1) |
| `lost_reason` | Char(300), blank | Optional (OQ48) |
| `lost_at` | DateTime, null | |
| `lost_from_stage` | Char(10), blank | |
| `requested_lines` | JSON list of line keys, default `[]` | Validated against §4.1. The only home of "lines to quote"; written only by `deals.services.set_lines`, which only intake's `set_intent` calls (B17; slice 11) |
| `deal_size` | Decimal, null | "Potential deal size", typed in the header; `$` and commas are stripped and blank clears (M29, OQ49; slice 38) |
| `opened_as` | Char(20), the status values | The client's status when the deal opened. It follows status changes while no plan on this deal is sold, then freezes. `rules.deal_type` reads it: Renewal only for `existing_client`, else New business (M14, H30; slice 6) |
| `agent_of_record` | Char, blank | The printed agent; blank shows the default in grey. `rules.agent_name` gives this, else the owner, else `AgencySettings.producer_name` (M27, OQ45, O.6 #21; slice 38) |
| `owner` | FK User, null, SET_NULL | Changed through `set_owner`, which writes one Activity row; saving a split's primary sets it (H.6, OQ45) |
| `created_by` | FK User, PROTECT | |
| `created_at`, `updated_at` | DateTime | `updated_at` moves only when the deal row itself is saved; "last updated" on screens is the latest `Activity` time |

Index `(client, effective_date)`. `archived` is worked out from the client's `archived_at`; there is no
`Deal.archived_at` while a client has one deal (O.6 #17, M9). A won prospect's deal stays New business while its
client becomes a New client (§5.1). The one-to-one rows owned by later apps (`Intake`, `Commission`, `ProposalConfig`,
`RfpRequest`, `DealAi`, `CensusSettings`) are created by **their own app** on its first write, never by a GET, and
`deals` never imports them (§3.3). Intake does not prefill `legal_name` (M.5 B34).

**Contact** — client-level (built in slice 38)

| Field | Type | Notes |
|---|---|---|
| `client` | FK Client, CASCADE, `related_name='contacts'` | |
| `role` | Char(20), default `hr_admin` | §4.6 |
| `name`, `title` | Char(200), blank | |
| `email` | Char(254), blank | Validated by `email_format` |
| `phone` | Char(50), blank | |
| `is_primary` | Bool, default false | Unique per client when true (partial unique constraint); setting one clears the others |
| `sort_order` | PositiveInt | |

`deals.contacts.primary` is the one primary-contact rule: `is_primary` on a client-side role, else an hr_admin or
benefit_admin, else the first client-side role; never `prior_broker`. The first edit creates an hr_admin when no
client-side contact exists (M30). RFP, the questionnaire's officer, review and the Overview read it (N.1). The roles
are §4.6's seven; the old eighth, `partner_agent`, is not kept, because a split row marks the partner who works the
account (H13, M81). Each write locks the Client row, then the contact; a bad email or role answers 400, and so does
marking a prior broker primary (B32). A contact's details name a person, so its Activity rows (area `contacts`) keep
the keys alone and Revert refuses them (§3.8).

**Note** (built in slice 38)

| Field | Type | Notes |
|---|---|---|
| `deal` | FK Deal, CASCADE, `related_name='notes'` | |
| `body` | Text | 1–8,000 characters (M.6) |
| `kind` | Char(10): `note`/`call`/`email`/`meeting`/`internal`, default `note` | Five kinds (A37, M73) |
| `pinned` | Bool | |
| `author` | FK User, null, SET_NULL | Only the author or an admin edits or deletes (M76, M77) |
| `deleted_at` | DateTime, null | A soft delete, undone through Revert (M77); the default manager hides deleted notes |
| `created_at`, `updated_at` | DateTime | Ordering: pinned first, newest first (by id) |

Earlier years' notes wait with renewals (A37, M78). Activity (area `notes`) never holds a note's words: an edit of the
body keeps the key alone; pins, kinds and deletes (action `removed`) keep before and after and revert.

**Activity** — one row per write or burst (O.3.2; slice 5). Built today with a summary and a count only.

| Field | Type | Notes |
|---|---|---|
| `deal` | FK Deal, CASCADE, null, `related_name='activity'` | Null for a firm row, which carries a `subject` |
| `subject` | Char, blank | What a firm row is about: for example a client with no deal (§5.1) or commission settings (H.6) |
| `actor` | FK User, null, SET_NULL | Null for the client portal and the system |
| `actor_kind` | Char: `user`, `client`, `claude` or `system` | |
| `actor_label` | Char(200), blank | e.g. "Client via link to J. Smith" |
| `area` | Char(20) | The writing app: v1.1's `deal`, `intake`, `census`, `documents`, `quotes`, `commission`, `proposal`, `rfp`, `review`, plus `client` (the status, §5.1), deals' `deal_facts`, `archive`, `notes` and `contacts` (slice 38), `questionnaire` and each new app that writes. Revert calls the area's reverter |
| `action` | Char(20) | v1.1's `created`, `updated`, `deleted`, `imported`, `approved`, `rejected`, `sent`, `sold`, `lost`, `reopened`, `issued`, `downloaded`; plus `viewed` (E99), `archived`, `restored`, `opened`, `returned`, `signed`, `read`, `staged`, `failed`, `logged`, `marketed` (M.6), the status moves `converted`, `prospect`, `status` (§5.1), and quotes' `removed`, `moved` and `merged` (F59, F60, F142; revertible, unlike `deleted`) |
| `summary` | Char(300) | No PHI (§3.8) |
| `changes` | JSON list | Before and after per key: `[{"t": "plan:41", "k": {"rate_ee": ["612.50", "640.00"]}}]`. Census rows, sensitive questionnaire slots and lasers keep keys only; commission values are hidden below the all tier. List reads defer it |
| `document_id` | Integer, null | The file a `downloaded` or `viewed` row is about, never its name (E99). A plain integer, because documents sits to the right |
| `coalesce_key` | Char(60), blank | What consecutive writes must share to merge into this row; blank = never merged (built) |
| `count` | PositiveInt, default 1 | How many writes this row stands for. A burst merges into one row that keeps the first before and the last after; review marks, imports, issues, sales, stage changes and status changes never merge (§3.7) |
| `reverts` | FK Activity, null | Set on the row a Revert writes |
| `reverted_at`, `reverted_by` | DateTime, null; FK User, null | Revert works once (§7.3) |
| `created_at` | DateTime, default now | Indexes `(deal, created_at)` and `(area, created_at)` |
| `updated_at` | DateTime | Time of the latest write the row stands for |

`deals.activity.log_access(deal, user, action, what, document_id)` writes the `downloaded` and `viewed` rows for PHI
kinds and for files whose screen lists members; "Last updated" and the feed skip them (O.3.2).
`deals.activity.reverters` holds one `revert(activity, user) -> changed` per area, registered by the app that writes
it (O.1).

**AgencySettings** — single row, `pk = 1`, read through `AgencySettings.get()`, edited in Django admin

| Field | Type | Default |
|---|---|---|
| `name` | Char(200) | `Vantage Risk Solutions` |
| `address`, `city_state_zip` | Char(300) / Char(200) | blank |
| `phone` | Char(50) | blank |
| `email` | Email | blank |
| `brand_color` | Char(7) `#rrggbb` | `#173a63` |
| `logo` | File (PNG, re-encoded on upload, metadata stripped, max 2 MB) | blank |
| `default_commission` | JSON `{type, value}` | `{}` |
| `rfp_return_email` | Email | blank — CC'd on every RFP draft |
| `producer_name`, `producer_npn` | Char | blank — the agency producer, printed when a deal has no agent of record and no owner (`rules.agent_name`; M27; slice 6) |

Logo and brand colour stay here, edited in Django admin (O.6 #20).

### 6.3 documents

Built (slice 15): E.6's design below. Remove archives; only an admin's DELETE purges, and a deleted row's bytes go
once the deletion commits; `manage.py sweep_orphan_files [--delete]` finds bytes no row names (E98).

**Document**

| Field | Type | Notes |
|---|---|---|
| `deal` | FK Deal, CASCADE, `related_name='documents'` | Required while OQ6 is No; firm statements would make it nullable (O.6 #5) |
| `file` | File, `upload_to` = `deals/<deal_id>/<uuid4>-<safe name>` | Bytes go only after commit: a failed upload leaves none, and a purge or cascade removes them once it commits (E7, E96); `sweep_orphan_files` finds strays (E98) |
| `original_name` | Char(255) | |
| `size` | PositiveBigInt | bytes |
| `content_type` | Char(100) | from the extension |
| `page_count` | PositiveInt, null | PDFs only (pypdf), read at upload (E7) |
| `page_labels` | JSON, e.g. `{"3": "2"}` | Printed page labels, from the quote reader (E94). Built in slice 21: the reader finds them in the PDF it read (`documents.pages.printed_labels`, the old D-149 rules: /PageLabels, else a bare number on a page's first or last lines; only pages that differ) and the landing keeps them (`documents.services.set_page_labels`); derived from the bytes like `page_count`, so no Activity and Undo leaves them |
| `kind` | Char(20), required | `documents/kinds.py`: each kind has `label`, `bucket`, `accept`, `file_as`, `asks_role` and `phi` (§4.6, E.6). A blank kind answers 400 (E6) |
| `role` | Char(12), blank | §4.6; asked of quote, renewal, sbc, stop_loss_quote and tpa_proposal files (E13) |
| `carrier` | Char(200), blank | Who the document is from |
| `lines` | JSON list | Lines it covers; empty = not said |
| `label` | Char(200), blank | Display name; blank shows `original_name` |
| `source` | Char(10): `staff`/`client`, default `staff` | |
| `review_state` | Char(10): blank/`accepted`/`wrong` | Client uploads only |
| `link_id`, `slot` | Integer, null; Char, blank | The client link and the ask slot (`invoice@medical`, `claims`, `custom:7`) a portal upload answered. A plain integer, because review sits to the right (G.6, L93) |
| `screen` | JSON | The member-data screen run at upload: `{version, left_out_pages, image_pages, lists_members}` (D52, O.6 #45) |
| `protected` | Bool, default false | Set by Issue and by signing; archive and purge refuse protected files with a sentence (O.3.7, G135) |
| `archived_at`, `archived_by` | DateTime, null; FK User, null, SET_NULL | Remove archives a file, and its values stay linked; "Show removed files" restores it (E15, OQ23) |
| `uploaded_by` | FK User, null, SET_NULL | |
| `uploaded_at` | DateTime | Index `(deal, uploaded_at)` |

`objects` hides archived files; `all_objects` serves value links, opening files and "Show removed files" (E.6).
`upload` is the only door: kind required, magic bytes checked, 30 MB at most (E7, OQ24). Only an admin purges (OQ23).
PHI kinds are census, claims, questionnaire, stop_loss and stop_loss_quote (E99, §3.8). There is no stored page text
and no layout field; a scanned quote's printed table is quotes' `QuoteLayout` (§6.7).

### 6.4 ai

`ai` holds jobs, the worker, chats and the Claude client, but no business data: owners register readers, job kinds,
context providers, chat tools and locate hooks in `ai.registry` from `apps.ready()` (O.1, O.3.3, §10).

Built (slice 16): `Job` (every field below; no `chat` until slice 24's Chat, and `worker` names the worker that
claimed it), `DealAi` (its fields; nothing writes it until slice 24's lock and budget, and reads return the defaults),
`ai.registry` (`job_kinds`, `locate_hooks`; `readers`, `context` and `tools` empty until slices 18–24), the worker and
reaper, the `locate` job and quotes' locate hooks. Chat, ChatMessage and CarrierNote are slice 24's.

Built (slice 18): the `read` job kind (`ai/reading.py`), `registry.readers` with quotes' reader, the `Call` ledger
below, and the change set. `Job.land` is `staged` (the change set waits for review: in slice 18 every read waits) or
`budget` (the read waits past its run cap or the deal's budget, D53); `wait_reason` says why in a sentence; Discard
sets `resolution` to `discarded` and empties `result` to its summary and counts (D74). `Job.usage` holds the run's
token totals and call count, `Job.cost_usd` the sum of its calls.

**Call** — the ledger of Claude calls (slice 18): `job` and `deal` (null for the Eval lane; SET_NULL, so the total
outlives them), `purpose` (read, recheck, turn, rank, eval), `model` asked and `answered`, `status` (pending, done,
failed, stopped), `estimate_usd` (the worst case reserved before the call), `cost_usd` (priced from the model that
answered), `usage` (tokens), `stop_reason`, times. Never a file name, a file's text or a value. The total cap reads it
(§3.5); `manage.py ai_spend [--calls N]` and the admin show it.

**Job** — one row per read, chat turn, re-check, rank, locate or issue (D.6, O.3.3; slice 16)

| Field | Notes |
|---|---|
| `deal` | FK Deal. Required while OQ6 is No; firm statement reads would make it nullable |
| `lane`, `kind`, `target` | Lanes `work` (read, recheck, rank), `chat` (turn) and `system` (locate, issue). `target` names the reader: `quotes`, `sbc`, `intake`, `census` or `questionnaire` |
| `documents`, `params`, `chat` | What it reads, its settings, and the chat a turn belongs to |
| `status`, `progress`, `steps` | `steps` holds at most 50 short lines, never file text or names |
| `result` | The change set, below |
| `land`, `wait_reason`, `resolution`, `activity` | The landing decision (D71), why it waits, how it ended, and its Activity row; a job's Undo reverts that row |
| `model`, `usage`, `cost_usd`, `error`, `cancel_requested_at` | |
| `created_by`, `actor_label` | `created_by` null means the portal |
| times, `heartbeat_at` | The worker beats on stream events; the reaper takes jobs silent for 10 minutes (D105) |

A partial unique constraint allows one running job per (deal, lane). `manage.py run_worker` claims jobs as its own
Compose service; tests run jobs inline with a fake client (O.3.3). Starting or stopping a job records no Activity (a
job is the AI's working record, not deal data); what a job changes on the deal is one Activity row, `Job.activity`.
A locate job writes only `loc` (bookkeeping, through `deals.values.set_loc`): one non-revertible `ai`/`checked` row
per file with counts and the document id, and no per-key changes, so a check never blocks a later Revert (slice 16).

**Change set** (`Job.result`), one shape for every target (D.6, O.3.3):

```
{v, target, documents, summary,
 items: [{id, op, plan|ref, line, role, renews, replaces, carrier, name, plan_number,
          values: [{key, new, old, page, cell, loc, low, why, line}], tick, stale}],
 layout, kept, left_alone, findings: [{text, hard}], failed_parts, left_out_pages,
 landed: {plan_ids, areas}}
```

As built for quotes (slice 18): plan items (`create_plan`, `set_values`, `pick_current`) carry `plan` (the matched
plan's id or null), `codes`, `read_ref` (the reader's key for the plan, stored when it lands), `docs`, `matched` (read,
number, codes, name, renewal), `renews` (`{item|plan, label}`), `replaces` (`{to: [{item|plan, label}], text, tick,
why}`), `unmapped` (rows printed with no field: `{label, printed, page, doc}`), `frozen` (a sold plan), `options` (a
pick's current plans); each value adds `doc`, `tick` and `loc` (the locator's answer in the read's own bytes, E79).
`summary_counts` items carry `for` (`{item|plan}`, or null for the line's figure), `counts`, `text`, `doc`, `page`;
`add_lines` items `lines`. Left-alone values sit in `values` with `tick: false` and `why`, so there is no separate
`left_alone`. The set adds `counts {items, values, unticked, findings}`, `model`, `cost_usd`, `estimate_usd`,
`partial` and `halted`. `layout` is `[{doc, line, where, columns: [item ids], rows: [{label, keys, printed}]}]`, with
no printed text for PHI kinds; slice 21 turns it into `QuoteLayout` (`where` is the first page the table's cells name)
and adds `page_labels` (`{document id: {"<pdf page>": "<printed>"}}`, E94).

Ops: `create_plan`, `set_values`, `set_plan`, `pick_current`, `combine`, `summary_counts`, `add_lines`, `remove_plan`,
`confirm`, `table_note`, `rows`. Census and intake jobs hold only a pointer.

**DealAi** — one per deal, created on the first write: `locked_by`, `locked_at`, `budget_usd`, `next_chat` (D100,
D104). Client guidance is intake's `client_guidance` answer, not a field here (O.6 #16).

**Chat** — `deal`, `number`, `title`, `tab`, `created_by`, `created_at`, `last_used_at`, `last_used_by` (D7; slice
24). **ChatMessage** — `chat`, `role`, `text`, `author`, `job`; no context and no cost (slice 24).

**CarrierNote** — `carrier`, `text`, `updated_by`, `updated_at`; edited in Django admin and added to Claude's notes
for that carrier (D119, OQ4; slice 24). Built in slice 24 (`ai/migrations/0003_chats_notes.py`, with `Job.chat`):
`carrier` is a key of `deals.carriers`, unique, picked from the carriers' list in the admin form.

### 6.5 intake

Built in slices 11, 39 and 40 (the BOR, the checklist, readiness and the marketed stamp). B.6 and O.2.

**Intake** — one per deal, created on the first write

| Field | Type | Notes |
|---|---|---|
| `deal` | OneToOne Deal, CASCADE, primary key, `related_name='intake'` | |
| `answers` | JSON `{key: value}` | §5.2 |
| `sources` | JSON `{key: source}` | §3.7 |
| `client` | JSON `{key: entry}` | Client answers waiting for review (O.3.1): a question key, or `block:contacts`, `block:coverage`, `block:lines` (OQ84; slice 54). The entry's shape and its base rule are `intake/client_entries.py`, which census shares |
| `rules` | JSON `{key: rule}` | Per-deal Auto, Required or Waived per question (B37, OQ17) |
| `checklist` | JSON `{item: {checked, by, at, note, requirement, client_note, form_key}}` | The marketing checklist, COBRA included (B26, B27, O.6 #2). `form_key` is the questionnaire choice (B22) |
| `intent_confirmed` | JSON | The confirmed coverage-and-intent decisions, kept readable: `{decisions: {line: {in_force (null when unanswered), this_year, rate_guarantee_through}}, by, by_name, at}`, `{}` when never confirmed; "confirmed" means they still equal today's (B20) |
| `bor_name` | Char(200), blank | Typed signature |
| `bor_signed_at` | DateTime, null | |
| `bor_signed_by` | FK User, null, SET_NULL | Who recorded it |
| `bor_via` | JSON `{link, ip, agent}` | A BOR signed on the client portal: the link, the signer's IP and browser (L86; OQ86: the one place the portal keeps an IP); `{}` for a person's signature, a clear or a revert (slice 54) |
| `marketed_at`, `marketed_by` | DateTime, null; FK User, null | Mark as marketed; the first date is kept (B34, N.1) |
| `flags` | stored count | Open warnings, rewritten with each write (O.3.7) |
| `updated_at` | DateTime | |

`answers` holds §4.5's questions and `client_guidance`; a multi answer is a list (B3). `target_effective_date` writes
`Deal.effective_date` (B1) and lives only there: `answers` never holds it, `sources` keeps its entry, and the payload
reads it from the deal (slice 39). Nothing is prefilled when the row is created (M.5 B34). `flags` counts the open
warnings (`documents.review_rules.open_warning`) on the shown answers; `rebuild_facts` checks it (`intake/flags.py`).

**CurrentCoverage**

| Field | Type | Notes |
|---|---|---|
| `deal` | FK Deal, CASCADE, `related_name='coverage'` | |
| `line` | Char(20) | §4.1 |
| `carrier` | Char(200), blank | |
| `funding` | Char(20), blank | §4.6 |
| `effective_date`, `renewal_date`, `rate_guarantee_through` | Date, null | |
| `in_force` | Bool, default true | false = a gap the deal proposes to fill |
| `notes` | Char(300), blank | |
| `sort_order` | PositiveInt | |
| `on_proposal` | Bool | Whether the line shows on the proposal: the intent card's third fact (B17) |
| `commission`, `commission_source` | JSON Comp `{type, value}`; Char | In-force commission (pct, flat or PEPM) and where it came from (B14, `deals/comp.py`) |
| the renewal letter's four facts | | Asked for on every deal; the proposal's renewal blocks read them (J65, OQ38) |

**One home for carrier and funding.** Once a line has current plans in the Advisor, its coverage row shows their
carriers and funding **read-only** (from the plans) and keeps only the dates, `in_force` and notes. Before the plans
exist, the row's own `carrier` and `funding` are the record.
`quotes.facts.incumbent(deal, line)` is the one read of it, and RFP, commission and the Overview call it (F144). The
coverage subcards and the intent card edit these rows through one service (B14, OQ15).

### 6.6 census

C.5, L.6 and O.2. Built in slice 12 (all four models); slice 51 adds `CensusImport.job` (FK `ai.Job`, null, SET_NULL:
the Claude read that staged it) and `CensusImport.read` (JSON: a PDF roster read's people while it waits, emptied once
applied or discarded; `census.0002_import_job`). The default manager
hides removed people and people a client added who are still pending (`client['*'].status == 'pending'`, L.6);
`all_objects` serves matching and history. `CensusFacts` holds `employees`, `dependents`, `errors`, `warnings`,
`required_total`, `required_filled`, `missing` (blanks by column), `pending_answers`, `pending_people`, `rollup` and
`last_import_at`; `census.facts.compute` rebuilds it and `manage.py rebuild_facts [--fix]` (backend) compares.

**Member** — one row per person

| Field | Type | Notes |
|---|---|---|
| `deal` | FK Deal, CASCADE, `related_name='members'` | |
| `kind` | Char(10): `employee`/`dependent` | |
| `employee` | FK self, null | Dependents only: the employee they belong to (was `parent`) |
| `position` | PositiveInt | File order (was `sort_order`) |
| `values` | JSON `{key: value}` | §4.4, §5.3.1 (was `data`) |
| `sources` | JSON `{key: source}` | O.3.1; never the reader's `line` text |
| `client` | JSON `{key: entry}` | Client answers waiting for review, each with `prior` (O.3.1, O.6 #14) |
| `added_by_link` | Integer, null | The link of a client who added this person; approved or rejected whole (L.6). A plain integer, because review sits to the right |
| `removed_at` | DateTime, null | Soft removal; a re-import restores the person by identity (C17, L.6) |
| `created_at`, `updated_at` | DateTime | |

The default manager hides removed people and people a client added who are still pending (O.6 #13). Removing an
employee removes its dependents too (C7). `ReviewNote.member` is PROTECT, so a person is never hard-deleted (L.6).

**CensusImport**

| Field | Type | Notes |
|---|---|---|
| `deal` | FK Deal, CASCADE, `related_name='census_imports'` | |
| `document` | FK Document, null, SET_NULL | |
| `sheet_name` | Char(100), blank | Chosen by the member, default the first sheet |
| `header_row` | PositiveInt | 1-based; proposed, may be changed |
| `first_data_row` | PositiveInt | 1-based; default `header_row + 1`, may be changed |
| `headers` | JSON list | |
| `mapping` | JSON list `[{column, header, field, confidence, low}]` | `field` = census key or blank. **No sample values** (§5.3.2) |
| `status` | Char(10): `proposed`/`applied`/`discarded` | |
| `stats` | JSON | `{rows, employees, dependents, created, updated, removed}` |
| `created_by` | FK User, null | |
| `created_at`, `applied_at` | DateTime (applied_at null) | |
| the pivot recipe | JSON | How a one-row-per-benefit file is reshaped; only the recipe is stored, and rows are rebuilt from the file (C13) |
| `job` | FK ai.Job, null | The read that proposed it (slice 51) |

The dry run lists who is added, changed, removed and kept: a dropped person someone worked on is kept and reported
(C17).

**CensusSettings** — one per deal, created on the first write: `rules` `{column: rule}`, the per-deal Auto, Required
or Waived per column; waived beats forced (C27, OQ17). COBRA lives in `Intake.checklist` (O.6 #2). If OQ88 keeps
census sends by contact, `rules` also stores each column's contact (O.6 #46).

**CensusFacts** — one per deal, rewritten by every census write in the same transaction: the counts other apps read
(employees, dependents, errors, required blanks by column, pending client answers and added people; N.1, I.6, L.6) and
`rollup`, the tier counts by line and by plan name that `enrollment_for` reads. rfp calls `census.refresh_facts` on
commit after a carrier pick (K.6, N.3 #6); `manage.py rebuild_facts` checks it (O.3.7).

### 6.7 quotes

Built: `Plan` and `Package` in v1.1's shapes. Slice 7 adds O.2's Plan fields; the behaviour behind each arrives in the
slice named in its row. The rules live in pure modules (`presented`, `order`, `slots`, `facts`, `labels`, `math/`) and
the writes in a `services/` package (F.6, OQ9 b and d).

**Plan**

| Field | Type | Notes |
|---|---|---|
| `deal` | FK Deal, CASCADE, `related_name='plans'` | |
| `line` | Char(20) | Moved only by `move_line`, which keeps the id (F59; slice 8) |
| `role` | Char(10): `current`/`renewal`/`alternate` | Changed only through `plans/role/` (F52, F53) |
| `carrier` | Char(200) | |
| `name` | Char(200) | |
| `plan_number` | Char(100), blank | |
| `client_name` | Char(200), blank | The name on client documents (J14; slice 25) |
| `renews` | FK self, null, SET_NULL, `related_name='renewal_set'` | Unique when not null and not removed (one renewal per current plan; F.6) |
| `replaces` | ManyToMany self (`symmetrical=False`), blank, `related_name='replaced_by'` | Alternates only: the current plans on the same deal and line it takes the place of — none, one or several (§5.4) |
| `values` | JSON `{key: value}` | §4.3, §5.4 |
| `sources` | JSON `{key: source}` | O.3.1; `read_value` only on plans the reader made (F141) |
| `codes` | JSON list | The plan's codes, part of its identity (F143; slice 18) |
| `read_ref` | JSON | The reader's match reference (D.6's `Plan.read`); never copied (O.6 #9; slice 18) |
| `enrollment` | JSON, shape by the line's rate basis (§5.5): `{EE, ES, EC, FAM}`, `{volume}` or `{lives}`; numbers ≥ 0 | The plan's own typed counts, first in `enrollment_for` (O.6 #24) |
| `census_names` | JSON list of texts, default `[]` | Current plans only: the census plan-column texts that mean this plan (§5.5 step 4; C41) |
| `starred` | Bool, default false | ★ = on the proposal; at most 16 columns a line, through `room()` (F50, F119) |
| `star_reason`, `starred_by`, `starred_at` | Char; FK User, null; DateTime, null | Why and by whom (F51, O.6 #9; slice 7) |
| `recommended` | Bool, default false | Any plan, within `room()`; on a current plan it means "Keep this plan" (§5.4, OQ37) |
| `sold` | Bool, default false | Any number per line, in any combination (§5.4, OQ12). Refused on a lost deal; a sold plan cannot be deleted (H.6) |
| `sold_at` | DateTime, null | |
| `option_number` | PositiveInt, null | "Option n" per line, stamped at Issue in page reading order and never reused; none for current plans or priced versions. Unique per deal and line. Replaces `option_label` (J159, OQ35, OQ36; slice 25) |
| `pair_of` | Plan, null, SET_NULL | On the second half of a pair printed as one column: the first half, under whose id, place and option number it prints; one live pair per plan (constraint `one_pair_per_first_plan`); written only by `services.pairs` (D-219, O.6 #4; built in slice 33) |
| `derived_from`, `derived` | FK self, null, SET_NULL; JSON | A priced version and how it was made: `{kind: concession, bundle, holiday or duplicate; label, note, ops: [{key, op, value}], credit: {annual} or {months}, requires: [plan ids], conditional, by, at}` (F76–F84; built in slice 35). A concession also keeps the request it was made from, `all` and `each` (✎ reopens it); a bundle keeps `parts: [{line, op, value, plan_id, plan_label} or {line, op, value, carrier}]` (the label frozen beside the id, so a requirement still reads after a rename) and its totals `pct` and `flat` |
| `bundling` | Char: blank, `included` or `unbundled` | Whether the carrier's quoted rates already include the bundling discount; set by PATCH; an `included` quote takes no bundled version (F78; built in slice 35) |
| `flags` | stored count | Open warnings (`review_rules.open_warning`, OQ28), rewritten with each write: `Plan.save()` stamps it, bulk writes stamp it themselves; `rebuild_facts` checks it (O.3.7; built in slice 17) |
| `source_document` | FK Document, null, SET_NULL | The file it was read from, if any |
| `notes` | Text, blank | Internal |
| `sort_order` | PositiveInt | One sequence per line, read through `order.layout`; stop-loss reorders like every line (F43, F120, OQ13; slice 7) |
| `removed_at` | DateTime, null | Soft delete with restore and Revert (F60; slice 8); the default manager hides removed plans |
| `created_at`, `updated_at` | DateTime | Index `(deal, line, role, sort_order)` |

Gone: `enrollment_on`, replaced by `LineEnrollment.on` (O.6 #10; slice 13), and `option_label` (slice 25).

**Package** — a set of plans the member builds on one line (§5.5)

| Field | Type | Notes |
|---|---|---|
| `deal` | FK Deal, CASCADE, `related_name='packages'` | |
| `line` | Char(20) | §4.1 |
| `name` | Char(100) | Unique per `(deal, line)` |
| `plans` | ManyToMany Plan, `related_name='packages'` | Plans of the same deal and line; a removed plan's membership is hidden and comes back with Restore; a move to another line takes it out |
| `sort_order` | PositiveInt | |
| `created_by` | FK User, null, SET_NULL | |
| `created_at`, `updated_at` | DateTime | |

Totals and the same-people check are computed on read by `package()`, never stored.

**LineEnrollment** — one per deal and line (F88; built in slice 13, quotes 0007; `Plan.enrollment_on` went in 0008):
`enrollment` (`{}` or the basis's figures:
`{EE, ES, EC, FAM}`, `{volume}` or `{lives}`), `on` (one switch per line), `typed_at` (shown) and `census_seen` (the
deal's applied census imports when the counts were saved; quotes 0010). Counts typed before the
latest census import give way to the census, with "Keep my typed counts" (F91, OQ18). The Advisor's counts card and
the builder's EnrollmentStrip write it through one service (J48, O.6 #10).

**SavedView** — the Advisor's saved setups, Mine and Shared (F28, F29, OQ7; slices 10 and 36): `owner`, `shared`,
`view` (`quotes` or `stop-loss`), `line` (blank = any), `name`, `description`, `config`, `sort_order`; unique per
owner, view and name. The quotes `config` holds `find`, `budget_pct`, `rules` (`[{key, op, value, line?}]`),
`sliders`, `ee_rate_max`, `copay_max`, `hide`, `starred_only`, `needs_check`, `to_review`, `carriers`, `preset`,
`sort` and `layout`, cleaned by `board.clean_config`, which refuses any other key (slice 10). A setup is a firm row:
its writes record Activity with no deal (subject `saved_view:<id>`, area `saved_views`), and an Update reverts.
Census filter sets wait (OQ7).

**QuoteLayout** — one printed table of a scanned quote (O.3.5; slice 21): `deal`, `document`, `line`, `where`
(`{"page": 3}` or `{"sheet": "Medical"}`), `columns` (`[{"col": 0, "plan": 41, "head": "Gold PPO 1500"}]`), `rows`
(each `{label, keys}`; an unmapped row is `{"label": "Chiro visits", "keys": [], "printed": ["20/yr"]}`), `job` and
`written_at`. `read_apply` writes it while landing, and a re-read replaces it. `printed` is never kept for PHI kinds.
It orders nothing. **Built in slice 21:** one per file and line (unique); `services/layouts.write` maps each column to
the plan its item landed on, else the plan the read matched (a re-read that changes nothing), and leaves out a column
whose plan is not on the deal; two printed rows in a row under one label become one row with both keys; `printed` has
one cell per column. An equal table writes nothing; a new or replaced one is recorded in the landing's `quote_read` row
as `{"t": "layout:<doc>:<line>", "k": {"layout.job": [earlier job, this job]}}` (never the table's text in Activity),
and the table it replaced goes in the job's `landed.layouts`, so ↶ Undo this run (and the row's Revert) puts it back,
or removes it; a table a later read replaced refuses the Undo (409) and Undo anyway leaves it.

### 6.8 questionnaire

Built in slice 42 (the model, `forms/`, `engine/`, values, cleaning, prefill, choice, the services and the tab) and
slice 43 (the PDFs, the check, the filed signed copy, the RFP rules and `disclosure_state`). G.6, with L.6's client
entries (O.6 #14). The catalogue of forms
and choices lives in `questionnaire/forms` (served as /api/meta/ `questionnaires`), not as a copy in intake: intake
stores the choice (`intake.services.set_form_choice`) and reads the forms through
`intake.providers.questionnaire_items`.

**Questionnaire** — one row per (deal, form), created on the first write and never deleted

| Field | Type and notes |
|---|---|
| `deal`, `form`, `form_version` | FK; Char(40); Char(20), set at creation — a mismatch shows a warning |
| `answers` | JSON `{slot: value}`, flat. A slot is `field` or `block.<row id>.field`, so `deals/values.apply` serves it |
| `sources` | JSON `{slot: source}`; origins `typed`, `relay`, `client`, `ai`, `prefill` |
| `rows` | JSON `{block: [{id, origin, by, link, doc, plan, key}]}`; list order is the row number, and `plan` ties a prefilled row to its Advisor plan |
| `client` | JSON `{slot: entry}`, each with `prior` (O.3.1) |
| `cleared` | JSON list of slots a person emptied on purpose; it hides live prefill only |
| `last_row_id` | PositiveInt; row ids are never reused |
| `officer_name`, `officer_signed_at`, `officer_signed_by`, `officer_link`, `officer_authorized` | `officer_link` is a plain integer, because review sits to the right |
| `agent_name`, `agent_signed_at`, `agent_signed_by` | The agent's signature |
| `signed_document` | FK Document, null: the copy filed, protected, at the officer's signature (G135) |
| `signed_copies`, `reopens` | JSON lists: every copy this app filed; `{at, by, reason}` per reopen |
| `flags` | Stored open-warning count (O.3.7) |
| `created_at`, `updated_at` | Unique (deal, form) |

Each slot's status is worked out on read: missing, blank, prefill, client, to_check or ok (G.6). The forms are data
modules under `questionnaire/forms/`, and the bundled blanks sit in `assets/questionnaires/`.

**StagedRead** — a Claude read of a filled form waiting for a person (slice 52; G99, D74, D113): `deal`, `form`, `job`
(FK ai.Job, null), `document` (FK, null), `status` (waiting, applied, discarded, undone; constants, not choices),
`read` (JSON: `{answers: {field: {value, page, low}}, rows: {block: [{values, page, low: [fields]}]}, documents,
counts}`, cleaned by the form's own cleaner; emptied once used or discarded), `landed` (JSON: each slot the landing
wrote with its value and source before and after, the rows it added, the Activity ids; what ↶ Undo this run puts back,
sensitive answers included, without Activity holding a value; emptied by the Undo), `created_by`, `created_at`,
`resolved_by`, `resolved_at`. The read job's change set only points at it (§10.5).

### 6.9 commission

H.6. v1.1's `Commission` (rates and a split list totalling 100) is replaced. The ledger models (`Statement`,
`Receipt`, `GapNote`, `Alias`) are not built while OQ6 is No (slice 50 waits).
Built in slice 48 (`commission.0001`): `Party`, `Settings` (without `gap_grace_days`, which waits with the ledger, OQ6),
`Commission` and `ClientSplit`, with no `choices` (rule 1: `commission/vocab.py`). A split row stored names its `party`
by id; the API also takes `user` for a producer with a login and no Party yet, whose Party the save creates. Built in
slice 49 (`commission.0002`): `Record`, as below; its facts are the values plus four columns (`carrier`,
`effective_date`, `term_end`, `status`), each with its `sources` entry through `deals.values.apply`; a record's expected
revenue is worked out at cents (891f1b3 `record_expected`), so a line booked as two carriers' records adds up to the
tab's line figure. `Record.client` and `Record.deal` are PROTECTed, so `seed_golden` drops a golden client's records
first (`commission.services.forget_client`, for the seeders only).

- **Comp** (`deals/comp.py`): `{type, value}`, with exact decimal strings (H1).
- **Row**: `{party, role, amount, renewal_amount, basis, expires_after_years, works_it}`. `role` is primary,
  secondary, split or referral; `amount` is a Comp and `renewal_amount` a Comp or null; `basis` is pool or gross;
  `expires_after_years` is a whole number or null.
- **Party**: `kind` (producer or partner; the house is implicit), `name`, `user` (one-to-one, null), `email`, `phone`,
  `npn`, `appointed`, `default_split` (Comp), `first_year_pct` and `renewal_pct` (null = the firm default), `active`.
  A producer's Party is created on the first split save or booking (H95).
- **Settings** (pk 1): `first_year_pct` 40, `renewal_pct` 30, `gap_grace_days` 45, `confirmed_by`, `confirmed_at`.
- **Commission** — one per deal, the deal as primary key: `rates` `{line: Comp}`, `sources` `{line: source}`, `split`
  `{rows: [Row]}` or null, `year_number` (typed, null), `updated_by`, `updated_at`.
- **ClientSplit** — the client as primary key: `rows`, `updated_by`, `updated_at` (H106).
- **Record**: `client` (PROTECT), `deal` (null, PROTECT), `line`, `carrier`, `effective_date`, `term_end`;
  `year_number` (null = unknown), `is_renewal`; `status` (booked, active, renewed, terminated, lost_bor or void);
  `values` `{premium_annual, rate, employees, plan_label, plan_ids, policy_number}`; `sources` (origins `sale`,
  `typed`, `in_force`, `agency`); `terms` `{house_pct, rows, from, shares: null or [{party, role, pct}], reason}`;
  `party_ids`, an integer array with a GIN index written with the terms; `notes`, `booked_by`, `booked_at`. Unique
  (deal, line, carrier) when the deal is set. Booked from quotes' `sold_changed` (H25–H37) and frozen at booking.

Money is a Decimal at cents, rounded half up by `quotes.math.round_decimal`. Shares are integer millionths (100% =
1,000,000), so they always total exactly; the residual goes to the primary, else the house (H.6, §5.6). The year rule
reads `Deal.opened_as`: a deal opened for a prospect or a new client books as first year (H30).

### 6.10 rfp

Built in slice 26: the app with only `RfpRequest` (every field below; no service writes it yet) and
`selectors.asked_by_line(deal)` → `{line: [{id, name, on}]}` from `sends` ({} until a draft is marked sent), so the
proposal's Markets checked can read who was asked (J63, K117). Slices 44–46 bring the rest of K.6.
Built in slice 44 (no migration): `rfp.services.update` (the settings, carriers and funding as `{add, remove}`, the
owning card's mark cleared in the same write, Activity coalesced as `rfp:request:<deal>`, notes key-only) and
`set_done` (`done[card] = {by: user id, at}`); intake's `coverage_changed` takes the coverage card's mark off; the
reverter `rfp`; `rfp/carriers.py`, `request.py`, `cleaners.py`, `page.py`, `meta.py` (`/api/meta/` `rfp`).
Built in slice 45 (no migration): `include` written by `update` (only the ticks that differ from the default, worked
out against the request as the write leaves it; `'reset'`; stale keys pruned; the packet card's mark cleared);
`rfp/formats/` (the four definitions, generated from a migrated old database, the bundled workbooks and their drift
guard, the row builder, the fill, the scope, census's `carrier_required`, the lens), `rfp/xlsx/` (the old `fill_xlsx`),
`rfp/printed.py`, `rfp/cards/` (the packet's census rows and ticks).
Built in slice 46 (no migration): `rfp/context.py` (`Request`: the request read once), `rfp/forms/` (`VARIANTS` and
the filler; the three Warner workbooks in `assets/forms/`), `rfp/cover/`, `rfp/cards/` (every row of the one key space:
`forms.py`, `docs.py`, `packet.py`), `rfp/audience.py`, `rfp/drafts.py`, `rfp/members.py`, `rfp/packet.py`,
`rfp/eml.py`, `rfp/check/` (report, pills, `checks_stamp`), `rfp/summary.py` (`facts(deal_ids)`, K123) and
`rfp/services/sends.py` (`mark_sent`; `services` became a package, OQ9 d). `form` is a PATCH setting (the packet
card's), `include` covers the whole key space (a key the deal's packet lacks answers 400), and a send also stores the
questionnaires it carried (`forms: {form: sent_with}`, G113), shown as "changed since" on the draft.

**RfpRequest** — one per deal, created on the first write (it replaces v1.1's `RfpConfig`): `route` (blank follows the
band until the first send pins it, `warner` or `direct`), `carriers` (JSON list of carrier keys, in registry order),
`other_carriers` Char(300), `funding` (JSON list, or null for the default; `[]` is a real pick), `form` (blank =
Simplified, `small_group` or `large_group`), `due_date`, `notes` (≤ 2,000), `include` (`{file_key: bool}`, only
differences from the default), `done` (`{card: {by, at}}` for coverage, request, checklist, packet and emails),
`sends` (`{draft_key: {on, at, by, route, asked: [{key or null, name, lines}]}}`), `updated_at`. There is no line
list: the lines are the requested lines (K16). One key space serves include, pills, checks, downloads and the lens
(K.6).

### 6.11 proposals

Built (slices 25, 26): `ProposalConfig(deal, config, marks, updated_by, updated_at)`, created on the first write.
`config` holds the keys below by path (`proposals/config.py`, values cleaned by `cleaners.py`; the paths built so far
are `title`, `intro`, `recommendation`, `reasons.<line>`, `order`, `next_steps`, `experience.{summary, rows}`,
`summary.{on, blocks}`, `markets.on`, `markets.lines.<line>.{notes.<carrier id>, hidden}`, `output.{layout,
package_summary, compare_tabs, disclaimers, compare_slots, pages.<page>}` and `lines.<line>.{parts.<part>, rows,
card_stats, table_note}`; slice 34 adds `output.cover.{on, image}`, `output.pictures.<place>` and `team`, and
`merged` (slice 33) joins with its slice);
`marks` is its own column so that what prints and the bookkeeping never mix. `markets.on` is deal-wide on a line card:
writing it takes the Markets checked mark off every line. Presentation pages (`output.pages`, `experience`) is an
optional card like Pictures: it takes a mark that never counts toward "n of N completed". `ProposalIssue` is built in
slice 32 (below); slices 29 and 34 add the rest (J.6.2). Built (slice 34, migration `0006_cover_image_template`):
`CoverImage` and `ProposalTemplate` below; `output.cover.image` is an upload's id (null for the Presentation cover's
stock pick), `output.pictures.<place>` a stock key, "upload:<id>" (any place but the cover) or null for no picture
(unset reads its default), `team` a list of member ids (null: everyone on by default). A deleted upload falls back
when a file is built (`proposals/pictures.py`): the cover to its stock pick, any other place to no picture. The firm's
rows are written by `firm_services` (pages, team, photos), `cover_services` (uploads) and `template_services`, each a
firm Activity row (no deal; areas `firm` and `proposal_templates`, with reverters for an edit); the Django admin forms
of slice 29 are gone.

**ProposalConfig** — one per deal, created on the first write; a GET reads the defaults. `notes` becomes `intro`.
`lines` holds per-line settings, never membership or pairs: `presented()` decides what prints (F119), and a pair is
`Plan.pair_of`. Keys, with the limits in J.6.2: `title`, `intro`, `recommendation`; `reasons` `{line: text}`; `order`
`[line]`; `lines` `{line: {parts: {comparison, cost, recommendation}, rows, card_stats, table_note}}`; `summary`
`{on, blocks}`; `markets` `{on, lines: {line: {notes, hidden}}}`; `next_steps`; `experience` `{summary, rows}`;
`team`; `output` (layout, package summary, cover, pictures, pages, compare tabs and slots, disclaimers); `marks`
`{card: {by, at}, lines: {line: {card: {by, at}}}}`.

**ProposalIssue** — `deal`, `version` (unique per deal), `state` (`building`, `issued` or `failed`), `pdf`, `pptx` and
`xlsx` (each FK Document, RESTRICT, null), `issued_by`, `issued_at` (slice 32). Issued files are immutable — a record
of what the client was sent. It is not version history: no snapshots of deal data, no diffs, no restore (§15). Built
(slice 32) with `job` (the `issue` job, SET_NULL), `error` (a failed build's sentence) and `created_by`/`created_at`.
RESTRICT, not PROTECT: a file an issue holds cannot be deleted alone, but the whole deal (its issues with it) can, so
`seed_golden` rebuilds an issued deal (`delete_client` deletes the unprotected files one by one and lets the cascade
take the rest). A version still `building` whose job has ended reads `failed` (worked out on read).

**ProposalTemplate** — `name`, `description`, `kind` (`layout`, `rows` or `summary`), `line` (blank = any), `config`
(cleaned by `config.clean`), `shared`, `owner`, `sort_order` (J68; slice 34).

**FirmPages** (one row) — `about_text` (≤ 900), `about_stats` (≤ 6), `service_calendar` (≤ 8). **TeamMember** (≤ 40) —
`name`, `title`, `group`, `phone`, `email`, `bio` (≤ 1,400), `photo`, `on_by_default`, `sort_order`. Both arrive in
slice 29; slice 34's Firm pages drawer edits them (J155). **CoverImage** (≤ 24; slice 34) — a JPEG with a long side
≤ 2,400 px and a thumbnail ≤ 600 px, no metadata (`documents.images`: PNG or JPEG only, ≤ 10 MB, ≤ 6,000 px a side);
`label`, `width`, `height`, `uploaded_by`. A person's photo goes through the same helper (≤ 5 MB, stored ≤ 800 px).

### 6.12 review

Built in slice 53 (all four models; services for requests and links); the portal, notes and seen with slices 54–59.
L.6. v1.1's `ClientValue` goes: client answers wait on the owners' rows (§6, O.3.1).

- **ClientRequest**: `deal`, `asks` (below), `message` (≤ 1,000), `created_by`/`at`, `closed_at`/`by`, `close_reason`,
  and `form_version`, which every change to the asks bumps. `rules/requests.carries(asks, ref)` is the one rule for
  what a link asks.
- **ClientLink** — one per person: `request`; `token_hash` (unique, the SHA-256 of the token) and `seed` (the token
  is the seed signed with the server's key, `review.tokens`, so it is never stored; §3.8); `contact` (`deals.Contact`,
  SET_NULL) with name and email snapshots; `security` (`link` or `pin`), `pin_hash`, `pin_tries`, `pin_version`;
  `blank`; `slides`; `expires_at` and `ceiling_at` (creation plus 30 days); `nudge` `{on, by, at, done_at, done_by}`
  (O.2, I.6); `sent_at`, `opened_at`, `last_opened_at`, `open_count`, `first_submitted_at`, `submitted_at`,
  `attested_form_version`, `last_saved_at`; `revoked_at`/`by`, `created_by`/`at`.
- **ReviewNote**: `deal`, `surface`, `key` (an intake key, a census column, `<form>:<slot>`, a form key, a document
  slot or `census_file`), `member` (RESTRICT: a person is never deleted under a note, while a deal's own delete still
  takes both; slice 53), `request` and `link` (SET_NULL), `parent`, `audience`, `kind`, `text` (≤ 1,000), `author`
  (null for the client), the time, `sent_at`, `resolved_at`/`by`. One open ask or send-back draft per (deal, surface,
  key, member), with nulls not distinct.
- **Seen**: `deal`, a user or a link, `seen_at`; it only moves forward.

`ClientRequest.asks`:

```
{"intake": {"scope": "selected|missing|required|all", "keys": [],
            "blocks": ["contacts", "coverage", "lines", "bor", "files"]},
 "census": {"scope": "none|selected|blank|missing|all", "columns": [], "cells": [[member_id, "column"]],
            "file": false},
 "questionnaires": [{"form": "<key>", "mode": "online|upload", "picks": {"fields": [], "blocks": []}}],
 "documents": {"slots": ["invoice@medical", "claims", "custom:7"], "missing": false}}
```

### 6.13 agenda

Not built (slice 60). I.6. Agenda never writes a module value or a stage (O.2); its steps, journey, badges and meters
are worked out on read.

- **StepMark**: `deal` (related `step_marks`), `step_key` Char(80), `kind` (`later` or `done`), `until` (Date, null),
  `sig` Char(40), `note` (≤ 1,000), `by`, `at`. Unique (deal, step_key); lapsed rows are ignored on read.
- **Task**: `deal` (related `tasks`), `title` Char(300), `due` (Date), `note` (≤ 2,000), `assigned_to` and `done_by`
  (FK User, SET_NULL), `done_at`, `deleted_at` and `deleted_by` (a soft delete), `created_by`, `created_at`,
  `updated_at`. Index (deal, done_at, due); ordering (due, id); the default manager hides deleted tasks.

### 6.14 overview

No models and no services. `payload.overview(deal, viewer, today)` reads each app's `summary.facts` once and applies
the pure `rules` (M.6). From slice 67, `client_payload(client, viewer, today)` assembles the client page's Overview
the same way, in a fixed number of queries (§7.16).

### 6.15 golden

No models. The seed-only app (O.1, P.2, Q.4) holds `seed_golden`; one JSON spec per golden deal (GD1–GD6), each with a
parity profile for the old app (Q.5) and each client's status (Prospect unless the spec says otherwise); and the
answer keys, each carrying `checked_by`, `checked_on` and `method`. It seeds through every app's services with
synthetic data only, so it sits last in the chain; only the seed command and the root `conftest.py` import it. GD-Big
exists in tests only. Today `seed_golden`, with GD1 and GD2, lives in `proposals` (`golden.py`, `golden_data.py`);
slice 3 moves it.

---

## 7. API

Conventions are in §3.6. Paths below omit the `/api` prefix. **Auth** column: *user* = any signed-in user,
*admin* = `is_staff`, *public* = no sign-in.
*owner* = the deal's or client's owner; *all tier* and *own tier* = the commission tiers (§6.1); *link* = the holder
of a client link's token (§7.14).

Endpoints are grouped by owning app, in chain order: each action has one door, in the app that owns the data (O.6).
§3.6 gives what every endpoint follows: the URL scheme and firm-level roots, status codes and error bodies, `expect`
on value writes, `activity_id` on undoable writes, downloads, the lost-deal refusals, and the rule that a GET writes
nothing. Built apps get full tables. For the others this section lists the paths, and the part named gives each
request and response.

| App | Path prefixes | Built in 2Vantage today | Detail |
|---|---|---|---|
| backend | `health/`, `meta/` | both | §7.1 |
| accounts | `auth/` | all four | §7.2 |
| deals | `clients/`, `deals/{id}/`, `contacts/`, `notes/`, `activity/`, `archived/`, `users/`, `agency/` | clients, deal header, lost, reopen, activity list, users, agency | §7.3 |
| documents | `deals/{id}/documents/`, `documents/{id}/` | list, upload, edit, delete, download | §7.4; E.6 |
| ai | `deals/{id}/ai/`, `ai/chats/{id}/`, `ai/jobs/{id}/` | — | §7.5; D.6 |
| intake | `deals/{id}/intake/`, `deals/{id}/coverage/`, `coverage/{id}/` | — | §7.6; B.6 |
| census | `deals/{id}/census/`, `census/members/{id}/`, `census/imports/{id}/` | — | §7.7; C.5 |
| quotes | `deals/{id}/plans/`, `plans/{id}/`, `packages/{id}/`, `saved-views/` | v1.1's table | §7.8; F.6 |
| questionnaire | `deals/{id}/questionnaires/`, `meta/questionnaires/{form}/` | — | §7.9; G.6 |
| commission | `deals/{id}/commission/`, `clients/{id}/commission/`, `commissions/` | — | §7.10; H.6 |
| rfp | `deals/{id}/rfp/` | — | §7.11; K.6 |
| proposals | `deals/{id}/proposal/`, `proposal/` | `GET`/`PUT deals/{id}/proposal/` | §7.12; J.6.6 |
| review | `deals/{id}/review/`, `deals/{id}/confidence/`, `links/{id}/`, `portal/{token}/` | — | §7.13, §7.14; L.6 |
| agenda | `deals/{id}/agenda/`, `deals/{id}/journey/`, `deals/{id}/tasks/`, `tasks/{id}/`, `work-queue/`, `clients/{id}/agenda/` | — | §7.15; I.6 |
| overview | `deals/{id}/overview/`, `clients/{id}/overview/` | — | §7.16; M.6 |

### 7.1 Platform

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `health/` | public | §3.5 |
| GET | `meta/` | user | Every vocabulary in §4 |
| GET | `meta/questionnaires/{form}/` | user | One form's spec: sections, flags, drivers, tables, legend and legal text; cached per version (G.6; slice 42) |

`GET meta/` response (shape). 2Vantage serves `lines`, `tiers`, `stages`, `relationships` (still New and Existing),
`funding`, `document_kinds`, `document_roles` and `plans` today; the rest arrives with the slice that adds each
vocabulary (rule 1).

```json
{
  "lines": [{"key": "medical", "label": "Medical", "short": "Med", "field_set": "medical",
             "rate_basis": "composite", "tier_field": "medical_tier", "proxy": false}],
  "tiers": [{"code": "EE", "label": "Employee only"}],
  "stages": [{"key": "intake", "label": "Intake"}],
  "relationships": [{"key": "prospect", "label": "Prospect"}, {"key": "new_client", "label": "New client"},
                    {"key": "existing_client", "label": "Existing client"}],
  "contact_roles": [{"key": "hr_admin", "label": "HR Admin"}],
  "funding": [{"key": "fully_insured", "label": "Fully insured"}],
  "document_kinds": [{"key": "quote", "label": "Carrier quote", "bucket": "proposal", "accept": ["…"],
                      "file_as": "quote", "asks_role": true, "phi": false}],
  "document_roles": [{"key": "current", "label": "Current plans in force"}],
  "comp_types": [{"key": "pct", "label": "Percentage"}],
  "intake": {
    "sections": [{"key": "employer", "label": "Employer information"}],
    "blocks": [{"key": "contacts", "label": "Contacts"}],
    "questions": [{"key": "waive_reason", "label": "Main Waive Reason", "section": "eligibility",
                   "type": "choice", "options": ["Spouse's plan", "Medicare"], "hint": "", "help": "",
                   "need": "C", "shown_when": {"field": "waiving_count", "op": "gt", "value": 0}}]
  },
  "census": {
    "groups": [{"key": "identity", "label": "Identity"}],
    "fields": [{"key": "dental_tier", "label": "Dental Tier", "group": "dental", "type": "tier", "required": "L:dental"}],
    "choices": {"tier": ["EE", "ES", "EC", "FAM", "Waived"], "gender": [["M", "Male"], ["F", "Female"]]}
  },
  "plans": {
    "groups": [{"key": "deduct", "label": "Deductibles & maximums"}],
    "fields": [{"key": "rate_ee", "label": "Rate — EE", "group": "rates", "type": "rate", "required": true,
                "applies": "composite lines", "client": true, "choices": []}],
    "line_groups": {"medical": [{"key": "rates", "label": "Rates", "fields": ["rate_ee", "rate_es", "rate_ec", "rate_fam"]}]}
  },
  "carriers": [{"key": "aetna", "name": "Aetna", "group": "medical", "aliases": ["…"]}]
}
```

Sections the later slices add, each served from its owner's constant:
- `relationships`: Prospect, New client and Existing client (§5.1; slice 6);
- `carriers` from `deals/carriers.py`, with aliases (K105; slice 6); the census formats move to `rfp`;
- `document_kinds` with their flags (E.6; slice 15);
- `ai`: `{targets, models, ladder}`, only when an API key is set (D.6; slice 16);
- the board presets, sliders and budget rungs of `quotes/board_presets.py` (F31; slice 9);
- `enrollment`: `{sources: [{key, label, mark}], keys: {basis: [keys]}, labels: {EE: "Employee only", lives: "Lives",
  volume: "Volume ($)"}}` from `quotes/math/enrollment.py`, the enrollment sources in words for every premium (F86, F92;
  slice 13);
- the questionnaire catalogue in `intake/form.py` (G1; slice 42); each form's spec is `meta/questionnaires/{form}/`;
- `commission/vocab.py` (H.6; slice 48);
- `rfp`: carriers, funding, forms, routes, and format keys and labels only. v1.1's `rfp_funding` moves here (K.6;
  slice 44);
- `proposal`: the catalogue, covers, pictures and key rows (J.6.6; slice 25);
- `agenda`: sections, step titles, follow-up days, Later picks, soon days, due buckets, type chips and categories
  (I.6; slice 60).

### 7.2 Accounts — `auth/`

| Method | Path | Auth | Request | Response |
|---|---|---|---|---|
| GET | `auth/csrf/` | public | — | `204`; sets the `csrftoken` cookie (`ensure_csrf_cookie`) |
| POST | `auth/login/` | public (throttle 10/min) | `{username, password}` | `200 user`, session cookie set · `400 {"non_field_errors": ["Invalid username or password."]}` (also for inactive users) |
| POST | `auth/logout/` | user | — | `204` (session flushed) |
| GET | `auth/me/` | user | — | `200 user` · `401` when not signed in (the SPA calls this at start-up) |
| GET | `auth/options/` (slice 47) | public | — | `200 {password: bool, microsoft: {start: "/api/auth/microsoft/", messages: {code: sentence}} or null}`: what the sign-in page offers |
| GET | `auth/microsoft/?next=<path>` (slice 47) | public (throttle 10/min) | — | `302` to the firm's Entra ID authorize page; `404` while Microsoft 365 sign-in is off. Keeps the pending sign-in (state, nonce, PKCE verifier) in the session |
| GET | `auth/microsoft/callback/?code=&state=` (slice 47) | public (throttle 10/min) | — | `302` to `next` (a path on this site; else `/`) with the session set · `302 /login?signin=<code>` when refused: `unknown`, `disabled`, `shared`, `no_email`, `cancelled`, `expired` or `failed`. `404` while off |

`user` = `{id, username, first_name, last_name, full_name, email, is_admin}`, plus the Profile flags `claude_direct`
and `commissions_access` (A3; slice 6).

Everything else about accounts is Django's own: users, their Profile flags and agency settings are managed in Django
admin (`/admin/`, staff only); a user changes their own password at `/accounts/password_change/` (Django's view, with
Django admin's registration templates); an admin resets a forgotten password in Django admin. Before real PHI, sign-in
moves to the firm's Microsoft 365 accounts (§3.8; slice 47, built), so no more password code is written. With
`AUTH_PASSWORD_SIGNIN=false`, `POST auth/login/` answers `400 {"non_field_errors": ["Sign in with your Microsoft 365
account."]}`. The two Microsoft GETs write the session, as every sign-in does, and nothing else.

### 7.3 Clients and deals — `deals/`

| Method | Path | Auth | Request | Response |
|---|---|---|---|---|
| GET | `clients/` | user | `?q=&relationship=<status>[,<status>]&stage=&owner=me\|<id>&ordering=-last_activity\|name&page=` | paginated client rows; archived clients are left out (`live()`) |
| POST | `clients/` | user | `{name, relationship?, effective_date?, owner_id?}`; `relationship` is `prospect` (default) or `existing_client` | `201 {client, deal}` — creates the client and its first deal · `400 {"relationship": ["A prospect becomes a new client when a plan is sold, or with Convert to client."]}` for `new_client` |
| GET | `clients/{id}/` | user | — | `{id, name, relationship, client_since, owner, notes, archived, deals: [{id, effective_date, stage}], contacts: [...], primary_id, moves}` |
| PATCH | `clients/{id}/` | user | `{name, owner_id, notes}` | client · `400` if `relationship` is sent, naming `clients/{id}/status/` |
| DELETE | `clients/{id}/` | user | — | `405 {"detail": "Clients are archived, never deleted."}` (M104; slice 38) |
| POST | `clients/{id}/status/` | user | `{to}`: `new_client` (Convert to client), `prospect` (Back to prospect) or `existing_client` | client detail · `409 {"detail": "…"}` with §5.1's sentence, e.g. "A plan is marked sold — un-sell it first." (slice 6) |
| POST | `clients/{id}/archive/` | user | `{archived: true\|false}` | the archive block `{client_id, archived: {at, by} \| null}` (M6, M7, M103; slice 38) |
| GET | `archived/` | user | — | `[{id, name, relationship, client_since, archived: {at, by}, deal: {id, stage, effective_date} \| null, deal_count}]`, latest archived first (M105; slice 38) |
| GET | `clients/{id}/activity/` | user | `?page=` | the client's feed: its deals' rows plus the status rows (slice 67) |
| GET / POST | `clients/{id}/contacts/` | user | `{role, name, title, email, phone, is_primary}` | `{contacts, primary_id}` / `201 contact`, an HR admin when no role is sent (slice 38) |
| PATCH / DELETE | `contacts/{id}/` | user | same fields | contact / `204` (slice 38) |
| GET | `deals/{id}/` | user | — | deal header |
| PATCH | `deals/{id}/` | user | `{effective_date, stage, owner_id, deal_size, agent_of_record}` | deal header · `400 {"stage": ["Mark a plan sold or use Mark lost."]}` for `sold`/`lost` |
| POST | `deals/{id}/lost/` | user | `{reason?}`, at most 300 characters | deal header · `409` if the deal is already lost or sold (M3, OQ48; slice 38) |
| POST | `deals/{id}/reopen/` | user | — | deal header |
| GET / POST | `deals/{id}/notes/` | user | `{body, kind, pinned}` | list (pinned first, newest first) / `201 note` (slice 38) |
| PATCH / DELETE | `notes/{id}/` | author or admin | same fields | note / `{id, activity_id}`, a soft delete whose Revert (that row) is the Undo (M77; slice 38) |
| GET | `deals/{id}/activity/` | user | `?page=` | paginated `[{id, at, actor, actor_kind, area, action, summary, count, document_id, can_revert, reverts_id, reverted: {at, by} \| null}]`, without `downloaded` and `viewed` rows; `can_revert` is the stored hint (values kept, not undone, an owner reverts), and the POST decides |
| POST | `activity/{id}/revert/` | user | — | what changed · `409` naming the keys a later write changed · refused with a sentence for sold plans, signed forms, issued proposals, a client status a sale set, and key-only rows (O.3.2, §3.7; slice 5) |
| GET | `users/` | user | — | `[{id, name}]` active users, for owner pickers |
| GET | `agency/` | user | — | settings + `has_logo` (edited in Django admin) |
| GET | `agency/logo/` | user | — | PNG |

Since slice 11, `POST clients/` and `PATCH deals/{id}/` answer `400 {"requested_lines": ["Change the lines to quote
through deals/{id}/intake/intent/."]}`: intake's `set_intent` is the only writer of the lines (B17), and the New client
dialog sends its Lines to quote there after the create. Slice 38 retired the last differences from this table: the
405, the optional lost reason with its 409s (M.5 B33), and the payloads' `contacts`, `deal_size` and `agent_of_record`.
Client rows carry `deal.deal_size` (decimal text) and `deal.deal_type`; archived clients are not listed. A note's DELETE
answers `{id, activity_id}` rather than 204, so the Undo toast (slice 63) can revert that row.

**Client row** (dashboard):

```json
{"id": 12, "name": "Example Co.", "relationship": "prospect", "client_since": null,
 "owner": {"id": 3, "name": "Dana Lee"},
 "deal": {"id": 31, "stage": "quoting", "effective_date": "2027-01-01"},
 "last_activity_at": "2026-11-20T15:04:05Z"}
```

`q` matches the client name case-insensitively anywhere in the name. `last_activity_at` is the time of the current
deal's latest `Activity` row (its `updated_at`), else the deal's creation time — so any write on any tab counts, not
only saves of the deal row. Default ordering newest first. The current deal is the open deal with the latest effective
date
(version 1 has one deal per client).
`last_activity_at` skips the `downloaded` and `viewed` rows (O.3.2).

`relationship` takes a comma list: the Prospects view reads `prospect`, and the Clients view
`new_client,existing_client` (§8.3). The home page's Work queue and its stats are agenda's (§7.15; O.6 #3).

**The client page** (slice 67; §8.5) reads `clients/{id}/` and `clients/{id}/activity/` here, `clients/{id}/overview/`
from overview (§7.16), `clients/{id}/agenda/` from agenda (§7.15, slice 68) and `clients/{id}/commission/split/` from
commission (§7.10).

**Deal header:** `{id, client: {id, name, relationship, client_since}, effective_date, stage, deal_type, lost_reason,
lost_at, requested_lines, owner, deal_size, agent_of_record, agent_default, archived: {at, by} | null, created_at,
updated_at}` (slice 38 added `deal_type`, which the builder's RENEWAL chip reads (J22), the two facts, the grey default
a blank agent of record prints, and the archive block). It carries deals facts only; the journey, next step, badges and
meters come from agenda's `journey/` (O.6 #3). `set_sold`'s answer includes it, so the Advisor can say "… is now a new
client" (§5.1).

### 7.4 Documents — `documents/`

| Method | Path | Auth | Request | Response |
|---|---|---|---|---|
| GET / POST | `deals/{id}/documents/` | user | `?archived=1` lists removed files / multipart: `file`, `kind` (required), `role`, `carrier`, `lines` (JSON array), `label` | `[document]` newest first / `201 document` · `400` no kind, or a file the kind does not accept · `413` over 30 MB (E6, E7) |
| PATCH | `documents/{id}/` | user | `{label, kind, role, carrier, lines}` | document; an unchanged PATCH writes nothing (E14) |
| POST | `documents/{id}/archive/`, `documents/{id}/restore/` | user | — | document · refused with a sentence for a protected file (E15, O.3.7) |
| DELETE | `documents/{id}/` | admin | — | `204`: the purge; refused for a protected file (OQ23; slice 15) |
| GET | `documents/{id}/download/` | user | `?inline=1` to view in the browser | the file (§3.8 headers; an inline PDF opens sandboxed, E17); PHI kinds write a `downloaded` or `viewed` row through `log_access` (E99) |
| GET | `documents/{id}/sheet/` | user | `?sheet=&start=&look=1` | a sheet window from `sheets.look()` |
| POST | `documents/{id}/sheet/find/` | user | `{value, line, hint}` | `{sheet, cell, state}` |

`document` = `{id, original_name, label, display_name, kind, bucket, role, carrier, lines, size, page_count, shape,
source, review_state, screen: {left_out_pages, image_pages, lists_members}, protected, archived_at, archived_by,
uploaded_by: {id, name} | null, uploaded_at}` (slice 15). `display_name` is the label, else "<effective year> <kind>"
for an unnamed renewal, invoice or claims file (E95), else the file name; `shape` (pdf, image, sheet or null) picks the
viewer. Issued files are `protected` (the baseline's `issued` is dropped). The sheet window also takes `cell`
("Medical!C7"), which opens its sheet around that cell and names it as the window's `match`.

Built in slice 15: every row above. Each value owner (intake, census,
quotes, questionnaire) serves the station's `sources/` and `marks/` (§7.6–§7.9), and "Check this file" starts a `locate`
job at `deals/{id}/ai/locate/` (§7.5). Full list: Part E, E.6.

### 7.5 AI — `ai/`

Built in slice 16: GET `deals/{id}/ai/` (PATCH waits for slice 24), POST `deals/{id}/ai/locate/`, GET `ai/jobs/{id}/`
and POST `ai/jobs/{id}/cancel/`. Built in slice 18: POST `deals/{id}/ai/reads/` `{document_ids, target? (quotes),
pages?, model?, budget_override?}` → 201 the read job, or 200 the same read already going; 409 without a key (D26), for
Opus or Run anyway by someone neither admin nor direct (D91, D24); 400 for files not this deal's or not of a kind the
reader reads, and for ids or pages that are not ints. POST `ai/jobs/{id}/discard/` → the job (`resolution:
discarded`; again: no change; an applied one: 409). The state's `waiting` lists change sets waiting for review on the
deal (at most 10): `[{job_id, target, documents, summary, counts, partial, created_by, finished_at}]`, and a job adds
`land` and `wait_reason`. `/api/meta/` serves `ai: {targets: [{key, kinds}], models: [{key, label, admins_only}],
ladder, read_limit_usd, failed_words, left_out_words}` only when Claude is set up. The state is `{deal, claude, jobs
(queued and running, oldest first, each with queue_position), recent (finished in the last 15 minutes, newest first, at most 10), waiting, news: [], lock,
spend: {usd, budget_usd}, can: {direct, budget}}`; a job is `{id, kind, lane, target, status, progress, step,
documents, stopping, queue_position, counts, landed: {areas, plan_ids}, error, resolution, activity_id, created_by,
created_at, started_at, finished_at}`, and `ai/jobs/{id}/` adds `steps`, `params` and `result`. `locate/` takes
`{document_ids, recheck?}` (this deal's files, removed ones too) and answers 201 with the new job, or 200 with the same
check already queued or running. Stop on a finished job answers 409 with a sentence; on a stopped one it changes
nothing. The two polled GETs use the `ai_poll` throttle alone. Built in slice 20: POST `deals/{id}/ai/sends/`
`{document_ids, model?, budget_override?}` (attaching is the request, D16, D17) → 201 `{jobs: [job, one per reader, in
the send order census → questionnaire → intake → quotes → sbc], not_read: [ids no reader reads]}`, 200 when nothing new
started; 409 without a key; 400 for ids not this deal's. POST `ai/jobs/{id}/retry/` `{model?, force?,
budget_override?}` (↻ Try again, D76; Run anyway, D24) → 201 the new read (`params.retry_of`), on the next model up the
ladder when the person may use it, else the same; a used read is undone first (409 with `can_force`, as Undo), a
waiting one discarded; 409 while it runs, for a job that is no read, or Opus or Run anyway by someone neither admin nor
direct. `reads/` takes `review: true` (the Re-read panel: the read waits even for a direct person, E75). The state
adds `read_documents` (files a finished read read), `spend.budget_usd` with the setting's default and `own_budget`,
`can.opus` (Opus, Run anyway and reads that land at once: admins and direct people), and on each job `model`,
`cost_usd` (so far), `recent_steps` (the last 8), `over` (run, deal or total), `retry_of`, `review`; `news` rows add
`auto` (it landed by itself, D71), `model` and `plan_ids`. `/api/meta/`'s `ai` adds `tabs` ({tab: [readers]}),
`send_order` and `default_model`. Built in slice 24: GET `deals/{id}/ai/chats/` → `{chats: [{id, number, title
("Chat N" when unnamed), named, tab, created_at, last_used_at, last_used_by, messages}], open (the chat this person
last wrote in), window: 30}`; PATCH `ai/chats/{id}/` `{title}` → `{id, title, named}`; GET `ai/chats/{id}/messages/
?before=` → `{chat, messages: [{id, role, text, author, created_at, job_id, turn: {id, status, land, wait_reason,
resolution, over, error, model, cost_usd, summary, items, findings, board, landed {summary, plan_ids, areas, items,
auto, undone}, retry_of}}], more}` (50 a page, oldest first); POST `deals/{id}/ai/messages/` `{text (≤ 8,000),
chat_id?, document_ids? (≤ 3, none that list members), tab?, board?, viewer?, model?, budget_override?}` → 201
`{chat_id, message, job, queue_position}` (409 without a key, for Opus or Run anyway by someone neither admin nor
direct; 400 for bad ids, text, tab or page state); PATCH `deals/{id}/ai/` `{locked?, budget_usd?}` → the state plus
`activity_ids` (anyone locks; only an admin changes the budget, 403 otherwise, OQ34). A turn's changes use the same
`apply/` (`select`: item ids), `undo/`, `discard/` and `retry/` (Run anyway, Try again) doors as a read. Built in
slice 22: POST `deals/{id}/ai/recheck/` `{refs? | plan_ids? | document_ids?, model?}` (✦ Ask Claude to re-check, D40,
D93) → 201 the `recheck` job (target the owner, `quotes`; `params.refs` the values it checks), 200 the same one going;
409 without a key, with nothing flagged there ("Nothing there is flagged for review…") or past 400 values; 400 for ids
or refs not the deal's. Its change set (`kind: recheck`) always waits for a person and uses the same `apply/` (`select`:
item ids, one item per value), `undo/` and `discard/` doors. The state's `waiting` and `news` rows add `kind`, `news`
lists used re-checks too, and the state adds `flags: {open, suggest}` (the deal's open warnings, from the owners'
`registry.flag_counts`, and the 20 past which the strip offers "✦ Re-check N flags", E80).

| Method | Path | Auth | Request and response |
|---|---|---|---|
| GET / PATCH | `deals/{id}/ai/` | user; `budget_usd`: admin (D100, OQ34) | The light state: jobs, waiting change-set ids and counts, news, lock, spend and permissions, with no side effects. PATCH `{locked?, budget_usd?}` |
| GET | `deals/{id}/ai/chats/` | user | The deal's chats |
| PATCH | `ai/chats/{id}/` | user | Rename |
| GET | `ai/chats/{id}/messages/` | user | `?before=` pages back |
| POST | `deals/{id}/ai/messages/` | user | `{chat_id?, text, document_ids?, tab, viewer?, board?, model?, budget_override?}` → `201 {chat_id, message, job, queue_position}` |
| POST | `deals/{id}/ai/reads/`, `…/recheck/`, `…/locate/`, `…/rank/` | user | The button doors: read files (D39), re-check values (D93), find each value in its file (E59), rank plans (D96) → `201` job. `rank/` (slice 37, served by quotes: it reads intake's guidance and the line's plans) takes `{line, plan_ids?, model?}` → `201` the `rank` job (`200` the same rank going); 409 with the sentence without Claude, without guidance ("Add client guidance first…"), on a locked table, for Opus by a producer or with no quoted plan; 400 a bad line or ids |
| GET | `ai/jobs/{id}/` | user | One job and its change set, with an ETag |
| POST | `deals/{id}/ai/sends/` | user | `{document_ids, model?, budget_override?, tab?}` → `201 {jobs, not_read}`: the files just attached, one read per reader in the send order (D16, D17; built in slice 20); the intake reader reads only what is sent from the Intake tab (`tab: 'intake'`; slice 51) |
| POST | `ai/jobs/{id}/cancel/`, `…/apply/`, `…/discard/`, `…/undo/`, `…/retry/` | user | `apply/ {select?, picks?}` → `{job, landed}`; `undo/ {force?}` → `{job, undone}`, 409 with `can_force` when something changed since (built in slice 19); `retry/ {model?, force?, budget_override?}` → `201` the new read (built in slice 20) |

Payloads come from `ai/selectors.py`; `useAiState` is the only poller (O.4). Client guidance is written through intake
(§7.6), not here (O.6 #16). Attach SBC and "As quoted" are quotes' doors (§7.8). Full list: Part D, D.6.

### 7.6 Intake — `intake/`

Built: slices 11, 39 and 40 (the GET, the answers PATCH, coverage and the intent doors; the checklist, the BOR and
Mark as marketed). Slice 40's GET adds `contacts` (the client's, each with its `issues`), `primary_id`,
`contacts_ok`, `bor {name, signed_at, signed_by, by_name, files, on_file}`, `compliance [{kind, label, documents}]`,
`checklist {tier, tier_label, enrolled, estimate, headcount_source, geo, items, required, done, missing, all_clear}`,
`ready {state, label, gaps, contacts_ok, bor_on_file, census_ok, checklist_clear}` and `marketed {at, by, by_name} |
null`. The GET answers `{answers, sources, hidden, needed, status, issues, readiness, notes, coverage, intent}`;
`answers.target_effective_date` is read from `Deal.effective_date`, its one home (B1).

| Method | Path | Auth | Request | Response |
|---|---|---|---|---|
| GET | `deals/{id}/intake/` | user | — | intake payload; a deal with no row reads as empty (M.5 B34) |
| PATCH | `deals/{id}/intake/` | user | `{"answers": {key: raw value \| list \| null}, "expect"?: {key: value seen}, "relay"?: bool}` | `200 {answers (changed; null = cleared), sources (changed), hidden, needed, status, issues, readiness {needed, answered, pct}, notes {multi_state, census}, effective_date, activity_id}` · `400 {"answers": {key: "error"}}` — nothing saved if any key fails; unknown key → 400 · `409 {detail, keys}` when an `expect`ed answer changed since. `relay` saves with origin `relay` ("These came from the client"). Built in slice 39 |
| POST / DELETE | `deals/{id}/intake/sign/` | user | `{name}` | `200 {bor, ready, activity_id}` / `204`; `400 {name}` without a name; `409` on a lost deal. Built in slice 40 |
| POST / DELETE | `deals/{id}/intake/marketed/` | user | `{override?: bool}` | `200 {marketed, ready, skipped: [gap], activity_id}` · `409 {detail, keys, gaps}` while not ready and not overridden · `409` on a lost deal / DELETE (unmark) `200 {marketed: null, ready, activity_id}`. Built in slice 40 |
| GET / POST | `deals/{id}/coverage/` | user | `{line, carrier, funding, effective_date, renewal_date, in_force, rate_guarantee_through, notes, on_proposal, commission, commission_source}` and the renewal letter's facts (B14, J65) | list / `201 coverage row` |
| PATCH / DELETE | `coverage/{id}/` | user | same | row / `204` · `400 {"carrier": ["Edit carrier and funding on the current plans in the Advisor."]}` when the line has current plans (§6.5) |
| GET / POST | `deals/{id}/intake/sources/`, `deals/{id}/intake/marks/` | user | `?documents=&bucket=&page=` / `{action, ids or document_ids}` | the station's rows, counts and quality / the changed marks and the Activity id (E.6) |
| GET | `deals/{id}/intake/source/` | user | `?key=` (a question of the form, or `client_guidance`) | `{key, label, value, hint, what, source: {origin, doc, page, cell, line, loc, low, mark, confirmed} \| null}`: one answer's source, for ↗ and the station's intake view (`intake:<key>`; E18, E44); `400` for a key the form does not ask. Built in slice 65 |

Writes the later slices add. Their paths sit under `deals/{id}/intake/`, and the slice that builds each names it.

| Service | What it does | Items | Slice |
|---|---|---|---|
| `set_intent` | Per line: in force, Shop it / Keep as-is / Leave off, and on the proposal; bulk or single, all or nothing. The only writer of `requested_lines`, through `deals.services.set_lines`. `POST deals/{id}/intake/intent/` `{line \| lines, has_today?, this_year? (market, keep, off), shop?, remove?}` → `{intent, coverage, requested_lines, activity_id}`; `shop` is the Lines-to-quote chips' and the header picker's control (it never answers a line); `remove` takes one line | B16–B19, B32 | 11 |
| `confirm_intent`, `reopen_intent` | Confirm coverage and intent; reopen. `POST deals/{id}/intake/intent/confirm/` and `…/reopen/`, answered like the intent door; an unchanged confirmation writes nothing | B20 | 11 |
| `set_checklist_item` | One checklist item's controls (C25, O.6 #2): `PATCH deals/{id}/intake/checklist/` `{item, checked?, note?, requirement? ('' \| required \| waived), client_note?}` → `{item: {key, label, checked, by, by_name, at, requirement}, checklist, ready, activity_id}`; each half writes only when sent; the two derived items answer 400; an unchanged change writes nothing; Undo reverts it | B26, B27 | 40 (41: COBRA) |
| `mark_marketed`, `unmark_marketed` | Mark as marketed (`POST`/`DELETE deals/{id}/intake/marketed/`, above); a 409 lists the gaps until confirmed; the skipped items are recorded; Undo | B34 | 40 |
| rules | Per-question Auto, Required or Waived, from Review's board | B37, OQ17 | 57 |

`client_guidance` is an answer like any other, saved by the drawer's GuidanceBox through `PATCH deals/{id}/intake/`
(D98, O.6 #16). Questionnaire's `choice/` endpoint writes the form choice through intake's `set_form_choice` (§7.9).

The payload is one read with a fixed query count (B.6). It keeps v1.1's `answers`, `sources`, `hidden`, `issues`,
`coverage` (with `from_plans`), `bor` and `contacts`, and adds the client entries, the intent rows (B16), the
documents each line needs (B21), the checklist rows with the size tier and headcount from `intake.providers.headcount`
(B25–B27), and B33's state — Blocked, Ready to market or Sent to market — with its gaps. `requested_lines` is written
here, through `set_intent` (B17); `PATCH deals/{id}/` stops taking it in slice 11.

### 7.7 Census — `census/`

Built in slice 12: the census page (GET, with `derived: {fte, aged_65, as_of, hours_threshold}` and `imports`), the
imports door, the import GET / PATCH (also `reformat: false`, "Use the original file instead"), apply with
`?dry_run=1` and discard. The dry run answers `{added, changed, removed, kept, cells_changed, counts, masked_ssns}`,
people as `{id?, name, kind, columns | why | restored}`; a real apply `{stats, summary, import, activity_id}`. Opening
an import reads the file's samples, so it writes a `viewed` row. Built in slice 41: members (add, edit, remove),
clear, marks, missing, the template and the export; the page adds `members[].review`, `review {open, check,
unflagged}` and `cobra` (intake's tick, C25). Not built yet: `census/sources/`, the station's census rows, which wait
for the Documents station's census view.

| Method | Path | Auth | Request | Response |
|---|---|---|---|---|
| GET | `deals/{id}/census/` | user | `?page=1&page_size=100&show=all\|issues\|missing` | census page. A `q` here is ignored: a name never rides a URL (§3.8, E28; slice 47) |
| POST | `deals/{id}/census/search/` (slice 47) | user | `{q, page, page_size, show}` | the census page, its roster narrowed to the families with a first or last name holding `q`; writes nothing; a refusal never repeats the name |
| POST | `deals/{id}/census/members/` | user | `{kind, employee_id?, values?, relay?}` | `201 {member, summary, review, activity_id}`: an employee sorts last, a dependent under its employee (C7) |
| PATCH | `census/members/{id}/` | user | `{"values": {key: raw}, "expect"?: {key: value seen}, "relay"?: bool}` | `200 {member, changed, summary, review, activity_id}`: the changed member and its issues only (C6) · `400 {"values": …}` (an unknown key, or a masked SSN whose last four match nothing on file) · `409 {detail, keys}` when an `expect`ed value changed since |
| DELETE | `census/members/{id}/` | user | — | `204`: a soft removal, dependents too (C7, O.6 #13) |
| GET | `census/members/{id}/source/` | user | `?key=` (a census column) | `{member_id, key, label, value, hint, what, source: {origin, doc, page, cell, line, loc, low, mark, confirmed} \| null}`: one cell's source, for ↗ and the roster beside its file (`census:<member>:<key>`; E18, E43); the value as the roster shows it (SSNs masked), `what` the column's label, never the person (rule 10); `400` for an unknown column, `404` for a removed person. Built in slice 65 |
| POST | `deals/{id}/census/clear/` | user | `{confirm: true}` | `204` — soft-removes every member |
| POST | `deals/{id}/census/imports/` | user | `{document_id}` — a file just uploaded, or a client upload already on the deal | `201 import` (proposed mapping, and the pivot recipe when the file has one row per benefit, C13; a file applied before starts from its last choices) · `400 {"detail": "Could not find a header row in this file."}` |
| GET / PATCH | `census/imports/{id}/` | user | `{"sheet_name": "Census", "header_row": 3, "first_data_row": 7, "mapping": [{"column": 0, "field": "first_name"}]}` | import, with up to 3 sample values per column read from the file for this response only (§5.3.2). Changing the sheet or header row re-proposes the mapping. Slice 51: every import row adds `job_id`, `read` (a roster Claude read: no sheet, samples from its people, no column letters; a sheet, header row or first row sent answers 400), `people` and `assisted` (columns the mapping assist proposed; each such mapping entry has `assist: true`) |
| POST | `census/imports/{id}/apply/` | user | `?dry_run=1` | dry run `{added, changed, removed, kept, cells_changed}` (C17) · real `{stats, summary}` |
| POST | `census/imports/{id}/discard/` | user | — | `204` |
| GET | `deals/{id}/census/template/` | user | — | the census template, prefilled from the roster (§9.1, C38) |
| GET | `deals/{id}/census/export/` | user | — | full census workbook (§9.2); logged through `log_access` |
| GET / POST | `deals/{id}/census/sources/`, `deals/{id}/census/marks/` | user | as intake's | the station's rows / the changed marks (C8, E.6). Marks take `{action, refs?}` (`census:<member>:<key>`; none = every open warning) and answer `{action, changed, activity_id, cells [{ref, review}], review}`; sources are not built yet |
| GET | `deals/{id}/census/missing/` | user | — | `{refs, count}`: the roster's required blanks, whatever page is shown, for "Select all missing" (C8, C24; slice 41) |

Per-column Auto, Required or Waived (`CensusSettings.rules`; C27, OQ17) is written by census's `set_rules` from
Review's board (slice 57). The census format lens moved to rfp (`deals/{id}/rfp/formats/`; C31).

Census page:

```json
{
  "summary": {"employees": 152, "dependents": 38, "errors": 4, "warnings": 9,
              "required_total": 1540, "required_filled": 1531, "missing_required": 9, "readiness_pct": 99},
  "rollup": {"medical": {"EE": 61, "ES": 12, "EC": 9, "FAM": 21, "waived": 8, "blank": 2, "source": "census"}},
  "columns": ["ext_emp_id", "first_name", "…"],
  "page": {"number": 1, "pages": 2, "employees": 152},
  "members": [
    {"id": 901, "kind": "employee", "employee_id": null, "values": {"first_name": "Avery"}, "sources": {},
     "issues": {"ssn": [{"code": "ssn_format", "severity": "error", "message": "…"}]}, "missing": ["dob"]},
    {"id": 902, "kind": "dependent", "employee_id": 901, "values": {}, "sources": {}, "issues": {}, "missing": []}
  ]
}
```

Pages contain employees, each followed by its dependents; unlinked dependents come on the last page. `show=issues`
keeps employees where they or a dependent have an issue; `show=missing` keeps those with missing required cells;
`q` matches first or last name. Validation always runs over the whole census (duplicate SSNs need it); only the page
is returned. Census issues and missing cells are computed on read, never stored.
The counts other apps read are stored in `CensusFacts` (§6.6). Rollups, readiness and exports read approved values
only; pending client answers wait in `client` (O.3.1).

### 7.8 Quotes (Advisor) — `quotes/`

Built: v1.1's table — lines, the comparison, create, PATCH and DELETE (a hard delete; F.5 #36), renewal, copy (without
rates), sold, recommend, star, enrollment, order, packages, and the plan template and its import. The rows below are
the design; a path with no plan id sits under `deals/{id}/`.

| Path | What it does | Items | Slice |
|---|---|---|---|
| `plans/lines/` | GET: per-line counts in one grouped query | F.5 #37 | built; 7 |
| `plans/` | GET `?line=`: the comparison (below) · POST: create a plan | F.6 | built |
| `plans/{id}/` | PATCH only `carrier`, `name`, `plan_number`, `client_name`, `notes`, `bundling` (blank, `unbundled` or `included`; slice 35) and `values`, with `expect`; role, links and stars have their own doors | F71, J14, F78 | built; 7, 35 |
| `plans/{id}/renewal/` | POST: Create renewal | §5.4 | built |
| `plans/{id}/copy/` | POST `{name?}`: `copy_plan`, keeping the rates → the copy (201) | F81 | built; 8 |
| `plans/{id}/recommend/` | POST `{recommended}`, within `room()` | §5.4, OQ37 | built; 7 |
| `plans/{id}/sold/` | POST `{sold}` → `{plan, deal}`; refused on a lost deal; runs `sale_changed` (§5.1) | F123, H124 | built; 6, 7 |
| `plans/star/` | POST: stars, with the 16-column cap, the reason, the auto-link and the lock | F50, F51 | built; 7 |
| `plans/order/` | POST `{line, move}`, `{line, swap}` or `{line, reset}`; stop-loss included | F43–F47, OQ13 | built; 7 |
| `plans/enrollment/` | POST the line's whole typed set `{line, plans?: [{id, enrollment}], whole_line?, on?, census_names?: {plan id: [texts]}, keep?}`: a part left out stays; `plans` is the whole per-plan set (a plan left out loses its counts); `whole_line` `{}` or null clears the figure; `census_names` are a current plan's census texts matched by hand (a text given to one plan leaves the others); `keep` stamps counts typed before the latest import as typed now. Any change to typed figures stamps `typed_at`; an unchanged save writes nothing. → `{line_enrollment: {on, figure, typed_at} \| null, plans: [changed], activity_id}`; one Activity row, area `enrollment`, revertible. 400 naming the field (`line`, `plans`, `enrollment`, `on`, `census_names`) | F85, F88, F90, F91, F92 | built; 13 |
| `plans/packages/`, `packages/{id}/` | Member-built packages, each with its `package()` result | §5.5 | built (today `{id, name, plan_ids}`; the results come only in the comparison) |
| `plans/template/`, `plans/import/` | The plan template and its import (`?dry_run=1`), filed as `plan_template` | §9.3, E8 | built; 15 (kind `plan_template`; `other` today) |
| `plans/role/`, `plans/links/` | Role and links; a plan made current loses its star and links (its recommendation means "Keep this plan", OQ37) | F52, F53 | 7 |
| `plans/slot/` | `put_in_slot`, for Pages' picks | F48, J5–J13 | 7, 14 |
| `plans/shortlist/clear/` | Clear the stars on one line | F55 | 7 |
| `plans/move-line/`, `plans/delete/`, `plans/clear/` | Move to another line keeping the id, `{plan_ids, line}` → `{line, plans, activity_id}`; soft delete, `{plan_ids}`, and clear a line, `{line}`, each → `{removed, kept, note, plans, activity_id}` (Restore is Revert of `activity_id`). `plans/{id}/` takes no DELETE | F59–F61 | built; 8 |
| `plans/board-export/` | GET `?line=&plans=<ids in the order drawn>&columns=<keys>&orientation=rows\|cols`: the board as Excel, equal to the screen; every figure from the comparison payload; current plans ride along; unknown ids and keys dropped; written with XlsxWriter through `xlsx_safe`; printing `sl_lasers` writes a `downloaded` row | F93, J167 | built; 9 |
| `plans/find/` | GET: the finder's index, every line in one query: `{plans: [{id, line, current, carrier, texts, name, carrier_name}]}` (texts: name, plan number, carrier, network, plan type, codes; `carrier` is the key `deals.carriers.match` gives; `name` and `carrier_name` as typed, for pickers such as a bundle's quote to sell, slice 35). The browser's pure `finder` matches the words and folds the carrier aliases `/api/meta/` serves ("UHC"), so typing never waits on the server and "Also matches N on Dental" needs no second read | F14–F17, OQ14 | built; 10 |
| `saved-views/`, `saved-views/{id}/` | Saved board and stop-loss setups, Mine and Shared. GET `?view=&line=`: mine and the shared ones offered on that line; POST `{name, description, view, line, shared, config}` → 201; GET/PATCH/DELETE `{id}`: others' private views answer 404, Update and Delete are for the owner or an admin (403 with the sentence). The config goes through `board.clean_config` (an unknown key or value is a 400 naming it) | F28, F29 | built (quotes view); 10, 36 |
| `plans/sources/`, `plans/marks/` | The station's values and marks (F.6's `plans/review/`). GET `sources/?documents=1,2&bucket=&page=` (no `documents`: every value with a file) → `{rows: [{ref, plan_id, key, label, sub, value, bucket, where, doc, origin, low, loc, mark, confirmed (each with by_name), open, potential, dealt, hint, what}], page, pages, total, page_size: 200, counts: {bucket: {open, done}}, all: {open, done}, warnings: {open, check, unflagged}, quality: {high, low, missing}, headline: {label, tone}}`, worst first (`review_rules.review_bucket`), dealt values last in their bucket, then board order. POST `marks/` `{action: approve\|ignore\|check\|clear, refs: ["plan:41:rate_ee"] \| plan_ids \| document_ids}`: refs name exactly those values; plans and files take only their open warnings (for clear, their marks); nothing named takes the whole deal; → `{action, changed, activity_id, truncated, values: [{ref, plan_id, key, cell: {s?, m?, p?}, mark, confirmed, open, potential, dealt, bucket}], plans: [{id, flags, incomplete}]}` (no `values` past 2,000: refetch). One Activity row (`marked`, never merged) with each value's marks before and after under `mark.<key>`, never the value; Revert (Undo) restores the values still as it left them and is refused, naming them, when none is | E.6, F63–F67 | built; 17 |
| `plans/{id}/source/?key=` | One value's full source, for ↗: `{plan_id, key, label, value, hint, what, source: {origin, doc, page, cell, line, loc, low, mark, confirmed}}`; read only | F.6, E18 | built; 15 |
| `plans/as-quoted/?document=&line=` | "As quoted", from `QuoteLayout`. GET with no `document`: `{files: [{document, line, line_label, label, where, page_label, plans, rows, written_at}]}`, one per table on a file not removed, in upload order; with `?document=<id>[&line=]`: `{document, line, line_label, label, kind, where, page_label, written_at, job, columns: [{col, plan, head}], left_out, rows: [{label, keys, printed?}]}` — the plans still on the deal in printed order (a removed one is left out and counted), rows in printed order, `printed` one cell per column (blank for a PHI kind, even one filed so after the read). Live values come from the comparison. 400 a bad id or line; 404 no table | F42, E42 | built; 21 |
| `plans/{id}/sbc/` | Attach SBC: a staged read of design values. POST multipart `{file}` (filed on the deal as kind `sbc`, the plan's carrier and role, medical) or `{document_id}` (an SBC already there), `model?` → 201 the `read` job (target `sbc`, `params.plan`), 200 the same read going. 409 without a key, on a plan of another line, on a priced version or copy ("takes its design from the plan it was made from"); 400 no file, a file not the deal's or not an SBC, a bad id; 404 no plan | D38, D47 | built; 22 |
| `plans/pair/` | POST `{plan_ids: [first, second]}` prints the second as one column with the first; `{plan_ids: [id], split: true}` takes the pair holding it apart → `{plans, activity_id}` (a pair made again: `{plans: [], activity_id: null}`). 409 with the sentence: itself, another line, another carrier, another kind, a plan already paired ("split it first"), more than 8 pairs a line, a Split on a full line; 400 a bad or foreign id. One revertible Activity row (`plan.pair_of`) | J15, J161, F137, O.6 #4 | built; 33 |
| `plans/priced/`, `plans/{id}/priced/` | Priced versions: a dry-run preview, then the commit. POST `deals/{id}/plans/priced/` `{plan_ids, kind: concession\|bundle\|holiday, all?: {op, value}, each?: {rate key: {op, value} \| "keep"}, parts?: [{line, op, value, plan_id? \| carrier?}], conditional?, credit?: {annual} \| {months}, note?, name?, dry_run?}` → 201 (200 for a dry run) `{dry_run, drafts: [{original_id, name, label, derived, starred, changes: {key: value}, premium, change, part_of, credit, enrollment_used, enrollment_source}], plans: [the versions written], warning, activity_id}`; one version per plan named, all on one line, one `created` row. POST `plans/{id}/priced/` (✎) takes the same body on a version and re-prices it from its original (one revertible `updated` row; the same body again writes nothing). `op`: `pct_off`, `pct_up`, `flat_off`, `flat_up`, `set` (a bundle has no `set`). Malformed → 400 with the sentence; refusals → 409 (a sold plan, a concession or bundle on the in-force plan, a bundle on an `included` quote, a rate below zero, a dollar credit across several plans, two lines, a version's kind, an original gone). Remove a version with `plans/delete/` (Undo restores it). The board's words are `/api/meta/` `board.priced` | F76–F84 | built; 35 |
| `plans/stop-loss/`, `plans/stop-loss/workbook/` | Stop-loss analysis and its five-tab workbook. GET `plans/stop-loss/?without=<plan>:<laser position>,…` → `{line, basis {lives, months, source, words}, currents, current_id, columns [{id, carrier, name, role, current, starred, figures (rounded once in quotes' math; lasers by position: {n, amount, extra, included}), vs, scored, what_if, terms}], ranks {rank key: [option ids], lowest first, unscored last}, punchline, what_if, refusal}`; `without` is the laser what-if, never stored; a malformed pair is a 400. The workbook is served by proposals (the sheet writer lives there): 409 with the sentence on no stop-loss plan or two in-force contracts; writes nothing | F98–F107, J166 | built; 36 |

There is no merge endpoint: the reader's `combine` and Claude's `merge_plans` call the one merge service (O.6 #32).
Rank starts at `deals/{id}/ai/rank/` (§7.5); the page split is proposals' `deals/{id}/proposal/pages/` (§7.12).

The comparison is compact (F.6): cells carry flags (status, mark, origin, document index, and `p` on a potential
error that is not an open warning — a value its file does not print or pin down that nobody dealt with, E50, slice
23), documents are listed once, and a value's full source comes on ↗. The Documents station's Grid reads these same
cached comparisons, every line with plans, so a Grid opened from the Advisor draws at once (E36; slice 23). Each plan's `facts` are `incomplete` (a key field blank or to check; a missing
total is not incomplete, F22, the filter card names it instead, F140), `flags`, `compliance` and `numbers` (its
numeric values read once, strictly, for the board's sliders, caps and rules; F21; slice 10). Budget: 600 plans in ≤ 3 MB raw and ≤ 2.5 s (Q.7). Plans come in
`order.layout`'s order (F120).
Each plan carries `enrollment_used` and `enrollment_source` (a key of `/api/meta/` `enrollment.sources`); the line's
`enrollment` block is what the counts card, the census notice and the split read: `{keys, on, figure, offers_figure,
typed_at, stale, typed_plans, census: {figures, source, imported_at} | null, texts: [{text, counts, enrolled, plan_id,
how: name|number|hand|null}] | null, census_now: [plan ids], split: {lost, unlinked, figure} | null, medical}` (slice
13). Only the fields of the line's groups (§4.3) are
included. `base_ids` are the plan's comparison base (§5.5); `part_of` names the base when the plan carries only part
of its people (its change is then null); `member_packages` lists the packages the member built. `packages` lists the
packages of §5.5 in their order: a
per-carrier package appears only when it covers the same people as today; member-built packages always appear, with
their reason when they don't. The Proposal tab's preview and the workbook use the same `package()` results.

Full list: Part F, F.6, with D.6 for Attach SBC and O.3.5 for "As quoted".

### 7.9 Questionnaire — `questionnaire/`

Built in slices 42 and 43 (`check/`, `pdf/` and `blank/`), and 52 (`reads/`). The deal paths sit under
`deals/{id}/questionnaires/`; marks name answers `questionnaire:<form>:<slot>` (E103).

| Method | Path | What it does |
|---|---|---|
| GET | `meta/questionnaires/{form}/` | The form's spec, cached per version |
| GET | `deals/{id}/questionnaires/` | The deal's forms: armed, started, choice source, band notice, progress, signed |
| PATCH | `…/choice/` | `{item, choice}`; writes the checklist's form choice; `409` for a swap away from a signed form |
| GET | `…/{form}/` | Effective values, statuses, rows, progress, blanks and signatures; never writes |
| PATCH | `…/{form}/answers/` | `{answers, relay?}`; `409` when the form is locked |
| POST / DELETE | `…/{form}/rows/{block}/`, `…/{form}/rows/{block}/{row_id}/` | Add or remove a row |
| POST | `…/{form}/sign/`, `…/{form}/reopen/` | Sign `{who, name, authorized, sign_anyway}`; reopen `{reason}` |
| GET | `…/{form}/check/`, `…/{form}/pdf/?ack=`, `…/{form}/blank/` | The check `{problems, ack}`; the filled PDF, or the filed copy once signed (logged; a stale `ack` answers 409); the bundled blank |
| GET / POST | `…/sources/`, `…/marks/` | The station's rows and marks (E103) |
| GET | `deals/{id}/questionnaires/reads/{read_id}/` | A staged Claude read against the form as it stands: `{id, form, label, job, document, status, signed, entries: [{ref, kind answer\|row, label, new, old, page, low, sensitive, state fill\|replace\|conflict, tick, why, opens?, block?, block_label?, number?, target_number?, values?}], counts}`; a used, discarded or undone read lists no entries; 404 for another deal's. Use and Discard are the read job's (`ai/jobs/{id}/apply\|discard\|undo/`; `select` refs `"<form>:<field>"`, `"<form>:row:<block>:<n>"`, `"form:<form>"`); never writes (slice 52) |

Review's decisions go through review's endpoints, which call these services; the portal's questionnaire doors are
review's (§7.14). Full list: Part G, G.6.

### 7.10 Commission — `commission/`

Any deal user reads and edits rates and previews a split; only the all tier or the deal's owner saves a split (OQ70;
on the client page the client's owner); the Book's figures follow the viewer's tier (H.6). Built in slice 48: the deal
endpoints but `book/` and `disclosure.pdf` (built in slice 49 with the records, people and their exports, the tab's
`booking` block, and `GET commissions/clients/?q`, Add to book's client search, archived clients and clients with no
deal included), the client split with its own `POST
clients/{id}/commission/split/preview/` (percentages only: no revenue at the client level), parties (GET: a commission
tier, the own tier without the percentages; writes: the all tier) and settings (the all tier; the PATCH also takes the
agency's `default_commission`, H100). Split errors are keyed `rows.<i>.<field>`, `rows.primary` and `rows.split_total`.

| Method | Path | What it does |
|---|---|---|
| GET / PATCH | `deals/{id}/commission/` | The tab's payload / `{rates, year_number}` |
| POST | `deals/{id}/commission/split/preview/` | The rows plus the basis the GET returned → the preview |
| PUT | `deals/{id}/commission/split/` | Save the split (all tier or the deal's owner) |
| POST | `deals/{id}/commission/book/` | Booking (all tier; H25–H37, H120) |
| GET | `deals/{id}/commission/disclosure.pdf` | The CAA disclosure (all tier; H108) |
| GET / PUT | `clients/{id}/commission/split/` | The client split; PUT by the all tier or the client's owner (H106; on the client page from slice 68) |
| GET / POST | `commissions/records/` | The Book, filterable by `?client=` / Add to book (H58) |
| GET | `commissions/records/export/` | The Book export (H52) |
| GET / PATCH | `commissions/records/{id}/` | One record |
| PUT · POST | `commissions/records/{id}/shares/` · `…/{id}/rebook/` | Typed shares · rebook |
| GET | `commissions/people/`, `…/{id}/`, `…/export/` | By person (H68) |
| GET / POST · PATCH | `commissions/parties/` · `…/{id}/` | Producers and partners (H95–H98) |
| GET / PATCH | `commissions/settings/` | Settings (H100) |

Waiting with slice 50 while OQ6 is No: the client statement (`clients/{id}/commission/statement/`, its export and
disclosure; H103, H105), the records' `months/` and `dispute-packet/`, and the statements, receipts and gaps (H59–H93
except H68). v1.1's `PUT deals/{id}/commission/` with a split list totalling 100 gives way to Party and Row terms
(§5.6). Full list: Part H, H.6.

### 7.11 RFP — `rfp/`

Slice 44 builds `GET / PATCH deals/{id}/rfp/` (the page payload; the PATCH takes route, carriers and funding as
`{add, remove}`, other carriers, due date and notes, and answers `{changed, cleared, activity_id, request, carriers,
done}`) and `POST deals/{id}/rfp/done/` (`{done, activity_id}`); `checks_stamp`, `include`, `form` and the other rows
come with the packet, files and sends (slices 45–46). Slice 26 added no endpoint (proposals reads `asked_by_line`).
Slice 45 builds `include` on the PATCH (`{file key: true | false | null}` or `'reset'`; the answer adds `packet`), the
census files of the one key space (`files/census-warner|aetna|angle|angle-csv|uhc/`, no `ack` until slice 46's check;
400 an unknown key, 409 no census), their `look/` windows (`documents.sheets.window`'s shape plus `warnings`) and the
lens (`formats/`, `formats/{key}/?rows=1–200`).
Slice 46 builds the rest of the table below: `files/{key}/` for every key (`form`, `form-census-<variant>`, `cover`,
`questionnaire-<form>`, `disclosure-<form>`, `proposal` — the latest issued proposal, OQ68 — `doc-<id>`, `packet`,
`draft-<key>`) with `?ack=`; `checks/` → `{checks_stamp, cards: {key: {status, count}}, deal}`; `check/?file=` →
`{key, label, ok, problems, ack}`; `drafts/{key}/sent/ {sent}` → `{drafts, done, stage, activity_id}`. The page adds
`packet` (sections, rows, members, notices), `drafts` (rows, sent_count, total, sent_earlier) and `checks_stamp`.

| Method | Path | What it does |
|---|---|---|
| GET / PATCH | `deals/{id}/rfp/` | The page payload with its `checks_stamp` / settings, toggles and `include` (carriers and funding as `{add, remove}`) |
| POST | `deals/{id}/rfp/done/` | `{card, done}` → `{done}` |
| GET | `deals/{id}/rfp/checks/`, `…/check/?file=` | The pills and deal problems; one file's report and its digest |
| GET | `deals/{id}/rfp/files/{key}/?ack=` | Any file in the one key space, `packet` (zip) or `draft-<key>` (`.eml`); a stale `ack` answers 409 |
| GET | `deals/{id}/rfp/files/{key}/look/?sheet=&start=` | Windows on the real file |
| POST | `deals/{id}/rfp/drafts/{key}/sent/` | `{sent}`; the first send pins the route and moves the deal to Quoting; 409 on a lost deal |
| GET | `deals/{id}/rfp/formats/`, `…/formats/{key}/?rows=` | The census format lens (C31) |

Files go out through `file_response`, named like `<Client> - <Carrier> census.xlsx`; the zip and `.eml` stream in
chunks; census and PHI files write `downloaded` rows. No query parameter is named `format`. v1.1's `PUT` with a
`lines` list, `rfp/packet/` and `rfp/drafts/{key}/eml/` give way to the one key space (K16). Full list: Part K, K.6.

### 7.12 Proposal — `proposals/`

Built: `GET`, `PATCH deals/{id}/proposal/` and `POST …/proposal/marks/` (slice 25: the builder payload; `{path:
value}` → `{changed, cleared, activity_id}`; `{card, line?, done}` → `{card, line, stamp, activity_id}`); `GET
proposal/pages/` (slice 14; `?preset=key` gives the builder's Key rows). v1.1's PUT, selection and preview are gone.
Slice 26 adds to the builder payload `output` (with defaults), `experience`, `next_steps`, `summary` {on, picked,
standard, blocks: the live preview, each block {key, label, scope, line, available, reason, value_label, sub,
delta_label, delta_dir}, medicare}, `markets` {has_asks, auto, override, on, lines}, `ledger` (the Presentation pages,
J42) and `best_only` (why "The recommendation only" waits); an intent or coverage edit takes the Coverage & marketing
intent card's mark off (intake's `coverage_changed`, J46). Slice 29: `GET …/proposal/files/pdf/` (the client PDF, a
draft built on each request; like every download it writes only its `downloaded` row, §3.8), and the `ledger` reads
the firm's pages (`FirmPages`, `TeamMember`). Slice 31: `GET …/proposal/files/pptx/` (the client PowerPoint, the same
recorded pages replayed as slides; it too writes only its `downloaded` row). Slice 27: `GET …/proposal/files/xlsx/`
(the client spreadsheet, a draft built on each request, `<Client> - <year> Benefits Proposal-DRAFT.xlsx`; it carries no
member data, so it writes nothing at all, J97; `409 {detail}` when no line has a tab). Slice 28: `GET
…/proposal/preview/?file=workbook&tab=` (the Export viewer's Excel view, one tab a request: `{file, built_at, draft,
opens_on, tabs: [{title, counts, capped}], tab: {title, rows, cols, col_px, row_px, merges, freeze, zoom, gridlines,
styles, looks, cells: [[r, c, text, flags, extra]], dropdowns, images, checks, counts, print, cut}}`; `?file=deck` is
slice 30's; any other file answers 400; `409 {detail}` in the download's words; no-store; writes nothing, not even a
`downloaded` row), and the builder payload's `stamps {files, firm}` (`proposals/stamps.py`). The client PDF and
PowerPoint take the spreadsheet's name rule, `<Client> - <year> Benefits Proposal-DRAFT.pdf` / `.pptx` (J104). Slice 30:
`?file=deck` (one build behind the Export viewer's PowerPoint, PDF and Paper views: `{file, built_at, style, draft,
slides: [{n, title, kind: cover | table | page, line, continued, notes, chart, fit}], paper: {scale, sheet, as_is,
inner}, pdf}`, `pdf` the download's own bytes as base64, `fit` on a plan set's first slide the recorder's fit log plus
`{slides, money_slide, tall_rows}`; writes nothing) and `GET …/proposal/files/letter/` (the client PDF on US Letter,
`paint/paper.letter`; `<Client> - <year> Benefits Proposal-DRAFT Letter.pdf`; it writes only its `downloaded` row).
The "Not printing" chips read the builder payload's `ledger`, not the preview's. Slice 34: the firm-level routes
below, plus `GET proposal/cover-images/{id}/thumb/` (the ≤ 600 px thumbnail), `GET proposal/pictures/{key}/thumb/`
(a stock picture's tile) and `GET, POST, DELETE proposal/team/{id}/photo/` (multipart `photo`); `proposal/covers/`
takes `?picture=` only (Classic's orientation waits, J143) and pages the Presentation cover, then each upload; the
ledger's firm rows carry `fix: {drawer: 'firm'}`; `/api/meta/` proposal gains `pictures`, `templates` and `firm`.

| Method | Path | What it does |
|---|---|---|
| GET / PATCH | `deals/{id}/proposal/` | The builder payload / `{path: value}` changes, merged by path under a lock |
| POST | `deals/{id}/proposal/marks/` | `{card, line?, done}` |
| GET | `deals/{id}/proposal/pages/?line=&preset=` | The page split (`proposals.pages`, six a page), each column's facts and words, the rows of the Advisor's Columns tab `preset` (default Primary; client fields only) as formatted cells, `others` for the picker and where "＋ Add a plan" lands (slice 14) |
| GET | `deals/{id}/proposal/preview/?file=deck` or `?file=workbook&tab=` | The export viewer's payloads; `no-store`; writes nothing |
| GET | `deals/{id}/proposal/files/{pdf,pptx,xlsx,letter}/` | Draft files; writes nothing |
| POST | `deals/{id}/proposal/issue/` | `202 {version, state}` · `409 {blockers}` |
| GET | `deals/{id}/proposal/issues/`, `…/issues/{v}/{pdf,pptx,xlsx,letter}/`, `…/issues/{v}/packet/` | The issued versions and their states; the stored bytes; the Letter PDF made from the stored PDF; a zip |
| GET | `proposal/covers/?orientation&picture` | Firm-level cover tiles from thumbnails, with an ETag |
| GET, POST · DELETE | `proposal/cover-images/` · `…/{id}/` | Cover uploads |
| GET / PATCH | `proposal/firm-pages/` | About, figures and calendar |
| GET, POST · PATCH, DELETE | `proposal/team/` · `…/{id}/` | The team and photos |
| GET, POST · PATCH, DELETE | `proposal/templates/?kind=` · `…/{id}/` | Templates |

Plan writes (stars, slots, links, order, enrollment, sold, values) stay in quotes (§7.8); the internal spreadsheet is
quotes' plan template (J98).

**Issuing** (`issue(user, deal, include)`, J.6.4):
1. Under the Deal lock: check readiness and the 16-column cap (kept lines never block, B36); quotes stamps the option
   numbers; create `ProposalIssue(vN, building)`; queue an `issue` job holding the Facts.
2. The job builds the PDF, PowerPoint and workbook outside any lock.
3. A second transaction stores them as protected Documents of kind `proposal`, marks vN `issued`, moves the stage with
   `advance(deal, 'proposal')` and logs "Issued proposal vN". A failure marks vN `failed`, with Retry.

The issued file is never regenerated: downloading v1 after v2 exists returns v1's stored bytes.

Built (slice 32; `proposals/issues/`, `issue_views.py`): `POST …/proposal/issue/` → 202 the version (`{version, state,
error, created_at, created_by, issued_at, issued_by, job, files: [{key, label, document_id, name, size}], job_id}`; 200
with the version already building) · 409 `{detail, blockers}` (the builder's `ready` sentence, the 16-column sentence,
"No plans on this proposal yet…"); `GET …/issues/` → [version], newest first (also the builder payload's `issues`);
`POST …/issues/{v}/retry/` (a failed version, same number; 409 for an issued one); `GET …/issues/{v}/{pdf,pptx,xlsx}/`
(stored bytes), `…/letter/` (`paint.paper.letter` of the stored PDF), `…/packet/?include=pdf,pptx,xlsx` (the stored
files in one zip); each writes only its `downloaded` row ("the client PDF (v1)"). Step 1 records the numbers it stamps
in an Activity row of its own ("Stamped n option numbers for proposal vN"; quotes' stamp records none); the job reads
the deal when it runs (it does not carry the Facts, which hold dates and picture bytes) and asks the gate again;
step 3 records "Issued proposal vN" (or "Proposal vN could not be built"), never reverted. Issued files print no Draft
and "Version n" in the deck's footer; their names drop -DRAFT (J104).

Full list: Part J, J.6.6.

### 7.13 Review & requests — `review/` (staff)

Built in slice 53: `board/` (no separate `badges/`: the tab's counts ride its own payload, O.6 #3), `requests/` with
its dry run, `requests/{rid}/close/` and `PATCH links/{lid}/` for mark_sent, unsend, extend, revoke, restore and
new_pin. The rest with slices 54–59 and 64.
- `GET deals/{id}/review/board/` → `{deal_id, asks_closed, counts: {to_send, to_review, waiting, questions},
  readiness: {pct, state}, lanes: {waiting: [request]}, in_progress: [{link_id, request_id, name, last_saved_at}]}`;
  a request is `{id, created_at, created_by, message, asks: [words], sections, state, first_sent_at, answered_at,
  answered_by, closed_at, closed_by, close_reason, close_reason_label, expiring, soonest_days, recipients}`, a
  recipient `{link_id, contact_id, name, email, role, security, blank, path, sent, sent_at, opened, opened_at,
  last_opened_at, opens, submitted_at, last_saved_at, expires_at, ceiling_at, days_left, expired, revoked,
  revoked_at, revoked_by, covered, state, in_progress, can_extend, can_restore}`; `path` (`/portal/<token>`) only
  while the link can still open or be turned back on.
- `POST deals/{id}/review/requests/` `{people: [{contact_id} | {name, email?}], asks, message?, security?, expires_on?,
  blank?}` → 201 `{request, links: [{link_id, name, email, path, pin, security, expires_at}], activity_id}`, each PIN
  shown this once; `?dry_run=1` → `{floor: {level, because}, security, people, asks}` and writes nothing. 400 by
  field; 409 when `deals.rules.client_asks_open` refuses.
- `POST …/requests/{rid}/close/` `{reason}` → `{request, changed, activity_id}`; `PATCH links/{lid}/` `{action,
  copied?}` → `{link, request, changed, activity_id, pin?}`; refusals are 409 with a sentence.

| Method | Path | What it does |
|---|---|---|
| GET | `deals/{id}/review/badges/`, `…/board/?scope=` | Counts; lanes, Next and questions (L1, L2) |
| GET | `deals/{id}/review/queue/?surface=&form=&group=&phase=&link=&page=` | Client answers, 50 a page |
| GET | `deals/{id}/review/request/?pane=&page=`, `…/census-blanks/`, `…/overlay/?surface=`, `…/messages/?link=&kind=` | The request page by pane; blanks for edit mode; section marks; a message draft |
| GET, POST | `deals/{id}/review/stamp/`, `…/seen/`, `…/tray/`, `…/tray/remove/`, `…/tray/send/` | Polling, the last look, the tray and its send plan |
| POST, PATCH, DELETE | `deals/{id}/review/notes/`, `…/notes/{nid}/` | Note, reply, resolve, delete a draft |
| POST | `deals/{id}/review/approve/`, `…/reject/`, `…/enter/`, `…/uploads/{doc}/`, `…/preview/` | Decisions, through the owners' services; `preview/` writes nothing |
| POST | `deals/{id}/review/requests/[?dry_run=1]`, `…/requests/{rid}/form/[?dry_run=1]`, `…/requests/{rid}/people/`, `…/requests/{rid}/close/`, `…/links/update/` | The builder, the Ask card, people, close, Update links |
| PATCH · GET | `links/{lid}/` · `links/{lid}/preview/` | `{action}`: mark_sent, unsend, extend, revoke, restore, expiry, address, new_pin, security, blank, nudge · View as client |
| GET · POST | `deals/{id}/confidence/` · `deals/{id}/review/marks/` | The Overview's data-confidence read · `{document_id, action}` marks one file across every owner in one transaction (M.6; slice 64) |

v1.1's `deals/{id}/links/`, with one link holding the asks, and `review/values/approve|reject/` give way to requests
with one link per person (L.6). Full list: Part L, L.6.

### 7.14 Client portal — `portal/{token}/` (public)

Built in slice 54 (V2: intake, census and documents; `review/portal/`); questions, `seen/` and the questionnaire
doors join with slices 56–58. All portal endpoints: `AllowAny`, **no authentication classes**, throttled per token:
`portal_read` 300/h, `portal_write` 3,600/h, `portal_poll` 600/h, and `portal_pin` 10/h on top of the five-try lock.
The global anonymous rate never applies. Unknown token → `404 {"detail": "This link isn't valid."}`. Expired, revoked
or closed → `410`, carrying the agency's contact; writes on a lost or archived deal also answer `410`; `428` until the
PIN is given (L.6).

`GET portal/{t}/` returns the allowlisted payload and records the open. The other doors are `verify/`, `save/`,
`files/`, `submit/`, `people/`, `questions/`, `sign/`, `stamp/?since=` and `seen/`, and the files `census-template/`,
`questionnaires/{form}/blank/`, `questionnaires/{form}/spec/` and `logo/` (L.6).

- **Allowlisted payloads.** Each payload holds only the keys review's tests list, and nothing else may be added
  without updating this spec and those tests. No team notes, commission, intent, document ids, owner names, other
  deals' data or files from outside the request ever appear (L.6).
- **The census template on this token is always blank.** A prefilled roster (birth dates, addresses, salaries) behind
  a bearer link sent by ordinary email would hand the whole census to anyone holding the link.
- SSN is never asked and never shown (OQ16).
- A GET writes only the open stamp. A staff session sees the page, records no open and gets 403 on writes (L.6).
- Headers: `private, no-store`, `no-referrer`, `noindex`; only the questionnaire spec is `private, max-age`.
- **Second factor.** A phoned PIN, when `rules/policy.floor(asks)` requires it: a page that shows census people or
  questionnaire answers, and medical or claimant send-backs. Upload-only asks open with the link alone (OQ80). The
  verification token is a TimestampSigner token, 1 hour idle under an 8-hour ceiling, re-issued with each response;
  the portal's own axios instance sends it as `X-Link-Verification` (L.6).
- A link lasts 7 days, sliding on save, under a 30-day ceiling from creation (OQ81).
- Saves go through the owners' `save_client`; answers wait as `client` entries until staff approve them (O.3.4).
- Request logs and error reports drop `/api/portal/` paths (§11). Old `/b/` links show "This link has moved" (L136).

**Built (slice 54).** Refs name each answer as `rules.requests.carries` does (`intake:<key>`, `intake:block:<contacts|
coverage|lines>`, `census:<member id>:<column>`); what a link may write is exactly what `review/portal/asked.py` says
it asks now (blanks and gaps read stored values only). Every answer, refusals included, carries the three headers.
- `GET portal/{t}/` → `{agency {name, phone, email, color}, account_name, expires_at, days_left, submitted_at,
  first_submitted_at, can_write, staff, preview, form_stamp, message, colleagues, answered_elsewhere_at, intake,
  people, add_people, census_file, documents, checklist}` (`review/portal/payload.KEYS`; the nested keys are pinned by
  review's tests). `intake` = `{sections: [{key, label, fields: [{key, label, type, options, hint, help, needed, value,
  base, locked, we_read, by_colleague, shown, shown_when}]}], blocks: {contacts {value, base, by_colleague, roles},
  coverage {value, base, by_colleague, lines, funding}, lines {value, base, by_colleague, lines, note}, bor {signed,
  name, signed_at, on_file}}}`; a person `{id, title, kind, employee_id, added, fields: [{column, label, type, group,
  group_label, help, choices, required, value, base, by_colleague}]}`; `add_people` `{left, relationships}`;
  `census_file` `{detail, accept, received: [{name, at}]}`; a document `{slot, label, detail, accept, note, received}`;
  `checklist` `{items: [{key, kind, label, done, filled?, total?}], done, total}`. The client's GET records the open
  (one conditional UPDATE; a re-read within 30 minutes adds nothing; the first open writes "Client opened their
  link"). 428 `{detail, verification, kind: 'pin', locked, agency}`; 410 `{detail, agency}`; 404 `{detail}`.
- `POST verify/` `{pin}` → `{verified}` and the `X-Link-Verification` header, or 400 `{detail, tries_left, locked}`.
- `POST save/` `{answers: {ref: {value, base}}}` → `{saved: [ref], bases: {ref: base}, link: {expires_at, days_left},
  activity_id}`; 400 `{answers: {ref: sentence}}` (a ref the link does not ask, a refused value); 409 `{detail,
  conflicts: [{ref, theirs, base}]}`; all or nothing. `POST submit/` → the same plus `submitted_at`.
- `POST files/` multipart `{slot, file}` (`census_file`, or a document slot such as `invoice@medical`) → 201 `{slot,
  received, link}`; `POST people/` `{people: [{kind, first_name, last_name, employee_id?, relationship?, dob?}]}` → 201
  `{people: [person], add_people}`; `POST sign/` `{name}` → `{bor, link}`; `GET stamp/` → `{form_stamp, days_left}`;
  `GET census-template/` → the blank template; `GET portal/moved/` → `{agency}` (takes no token);
  `GET links/{lid}/preview/` (staff) → the page with `preview: true`, no open counted.

Full list: Part L, L.6.

### 7.15 Agenda and work queue — `agenda/`

Not built (slices 60, 61 and 68).

| Method | Path | Request and response |
|---|---|---|
| GET | `deals/{id}/agenda/` | `{today, next_step, waiting, journey, progress, rows}` |
| POST | `deals/{id}/agenda/marks/` | `{step_key, kind, until?, note?}` → `{step, next_step}`; `400` or `409` |
| DELETE | `deals/{id}/agenda/marks/{step_key}/` | `{step, next_step}` |
| POST | `deals/{id}/agenda/follow-ups/` | `{step_key, kind: call or email, body}` → `{step, note}` |
| POST | `deals/{id}/tasks/` | `{title, due, assigned_to?, note?, done?}` → `201` task row |
| PATCH | `tasks/{id}/` | any of `title`, `due`, `note`, `assigned_to`, `done`, `move_note` → task row |
| DELETE | `tasks/{id}/` | `204`, a soft delete; `403` unless the creator or an admin |
| GET | `deals/{id}/journey/` | `{journey, waiting, next_step: {key, label, tab, params}}`, with the sidebar's badges and meters; the shell's one read, from counts and EXISTS checks only (M.6, O.6 #3; slice 61) |
| GET | `work-queue/` | `?include=closed` → `{today, rows, owners, client_names}` (slice 61) |
| GET | `work-queue/stats/` | `{actions_week, sales_month}`, each `{total, change_pct, series}` (slice 61) |
| GET | `clients/{id}/agenda/` | `{today, counts, deals: [{deal, next_step, waiting, rows}]}`, from one `facts_for` (slice 68) |

Task and mark writes from the client page use the deal endpoints. `POST agenda/check/` waits with Plan my day (OQ8).
Full list: Part I, I.6.

### 7.16 Overview — `overview/`

Not built (slices 62 and 67).

| Method | Path | Auth | Response |
|---|---|---|---|
| GET | `deals/{id}/overview/` | user | M.6's payload: `identity`, `facts`, `archived`, `asks`, `tiles`, `get_to_market`, `quote_to_close`, `enrollment_check`, `outreach`, `commission`, `coverage_notes` (slice 62) |
| GET | `clients/{id}/overview/` | user | The client page's Overview: one batched `summary.facts(deal_ids)` per app, questionnaire's `summaries(deals)`, `commission.summary.card` and the intake and quotes facts, in a fixed number of queries (slice 67) |

Neither read writes anything or creates a row. The Overview's writes use their owners' endpoints: notes, contacts,
lost and reopen, intake facts, uploads, tray asks, AI starts, marks, archive and revert (M.6). v1.1's `next_action`
and `summaries` blocks go: the next step is agenda's (I42), and each app's `summary.facts(deal_ids)` replaces
`summary(deal)` (§5.10). Full list: Part M, M.6.

---

## 8. Screens (the old look)

Every screen is the old Vantage screen, rebuilt on 2V's data. Daniel's words: the old formatting "was perfect" (README,
Context; OQ10).

- **The look.** Slice 2 ports the old stylesheets whole, in the old order, with the old class names (`bb-*`, `bnf-*`,
  `gk-*`, `rr-*`, `xg-*`, `lg-*`); slice 4 moves the screens built in M1–M6 onto them (O.5, §3.9). Components use those
  classes; there are no CSS modules. A token the old sheets used without defining keeps what it rendered (OQ10). Each
  part's X.6 lists the classes its screens use.
- **The words.** Titles, subtitles, labels, empty texts and error texts are the old ones, unless an item says otherwise.
- **The content.** A screen holds its part's X.3 rows whose verdict is Keep, Simplify or New. Drop and Defer rows are
  not built. The subsections below name the rows and the slices that build them; they do not repeat the rows.
- **The proof.** The Look lane (Q.5) captures each screen state on the same golden deal in both apps, at 1440×900 (the
  workspace also at 1280 and 1920, the portal at 390×844), and compares pixels and computed style. Each difference is a
  match, within tolerance, intended or unexplained. An intended difference is listed with its item ID in
  `browser/look/accepted.json` and signed once by Daniel; an unexplained one fails the lane. On the old side,
  `browser/look/dropped.yaml` hides the UI of Drop and Defer rows.
- **Not built yet.** A tab whose slice is not built is left out of the sidebar, and its route opens the deal's default
  tab. The sidebar's badges and meters and the journey stepper arrive with slice 61 (§13.12, risk 5). The Look lane
  labels each gap "pending slice N".
- Names in examples are fictional.

### 8.1 Top bar and routes

The top bar is the old one (A6): a fixed 56 px navy bar (`navbar`) with the brand link (the agency's name), then
**Benefits** (the home page), **Commissions** (shown when the user's commission tier is not none, H44), **Admin**
(admins only, in the old menu's look; it opens Django admin at `/admin/`), the username, which opens Change password
(Django's page, `/accounts/password_change/`), and **Logout**. The old Calendar link waits with the Radar (I88); the
other old links belong to modules out of scope (A2, A22, A40).

| Route | Page | Top bar | Slice |
|---|---|---|---|
| `/login` | Sign in (§8.2) | no | built |
| `/` | Home: Prospects; `?view=book` Clients; `?view=queue` Work queue (§8.3) | yes | 4; Work queue 61 |
| `/archived` | Archived clients (§8.3) | yes | 38 |
| `/deals/new` | New deal (§8.3; the old `/benefits/cases/new`) | yes | 20 |
| `/deals/:dealId` | The deal's default tab: the Advisor until slice 62, then the Overview (O.4) | yes | built |
| `/deals/:dealId/:tab` | Deal page (§8.4). Tabs: `overview`, `agenda`, `review`, `intake`, `census`, `questionnaire`, `rfp`, `commission`, `advisor`, `proposal`, `documents`. An unknown or unbuilt tab opens the default tab | yes | per tab |
| `/deals/:dealId/documents/:docId/window` | The document pop-out window (E69–E71) | no | 65 |
| `/clients/:clientId/:tab` | Client page (§8.5). Tabs: `overview` (the default), `agenda`, `commissions`, `notes`; anything else opens `overview` | yes | 67–68 |
| `/commissions` | Commissions (§8.18); needs a commission tier | yes | 48–49 |
| `/portal/:token` | Client portal (§8.20) | no | 54 |
| `/preview/links/:linkId` | View as client, for staff (L78) | no | 54 |
| `/b/:token` | "This link has moved", for the old app's links (L136) | no | 54 |
| anything else | "Page not found" with a link to the home page | yes | built |

In-tab state lives in the query string (O.4): `?view=`, `?line=`, `?file=`, `?doc=&ref=&page=&back=&list=`, `?focus=`,
`?form=`, `?claude=1` and `?claude=read&docs=…`. Signed-out visitors to a staff page go to `/login`, then back to where
they were going.

### 8.2 Sign-in and account pages

- **Sign in:** username, password, **Sign in**; the server's message on failure; under the button, "Forgot your
  password? Ask an admin to reset it."
- **Change password** and every user or agency-settings screen are Django's own pages (§7.2); the SPA builds none of
  them. They are replaced by Microsoft 365 sign-in before real PHI (§3.8).
- The sign-in page takes the old look in slice 4 (A1, A5).
- **Sign in with Microsoft** (slice 47): when `auth/options/` names Microsoft 365, a full-width button above the
  form takes the browser to the firm's sign-in; a refusal comes back as `/login?signin=<code>` and shows the server's
  sentence in the error box. With passwords off, the button is all the card holds.

### 8.3 Home views

The home page is the old Benefits home (A7–A13, I70–I127), its views renamed for the client status (§5.1; OQ2). The
header keeps the eyebrow "Benefits", each view's title and subtitle, **＋ New deal** and the **Archived** link; the
Calendar button waits with the Radar (I88). The view pill (`bnf-viewtab`) keeps the old order:

| Old view (`?view=`) | View | What it lists | Slice |
|---|---|---|---|
| New clients (bare `/`, the landing view) | **Prospects**, the landing view (OQ95) | Clients whose status is Prospect, one row each: I86's table and cards (the Prospects count, Potential deal size, Client responses) and I78's filters; lost deals hidden unless asked for (I80). Title "Prospects"; subtitle "Every prospect once — from intake to the sale — with the one thing each needs next." Rows open the deal, at its next-step link from slice 61. A sale moves the row to Clients at once (I122 as changed by OQ101 c; OQ91) | 4 on `GET clients/`; 61 on the work feed |
| Clients (`book`) | **Clients** | New and Existing clients, in the old book's classes (A13), with chips All · New clients · Existing clients. Columns: Client (sub-line "New client · since <date>" or "Existing client"), Potential deal size, Owner, Next action (from slice 61), Deals, Archive. A "Clients" stat card. **＋ New client** opens the dialog with Status preset to Existing client. Empty: "No clients yet — a prospect becomes a client when a plan is marked sold, or with Convert to client." Rows open the deal until slice 67, then the client page | 4; Next action 61 |
| Work queue (`queue`) | **Work queue** | As before (I70–I85): each open deal's next step, hand tasks and nudges, with the old columns, filters, sorts and stat cards. Deal rows carry the client's status. Reminder rows wait for the Radar (I72) | 61 |

- Clients is searched on the server, 250 ms after typing stops; chips and sorting are query parameters; 25 rows per
  page; the URL keeps the search and filters so Back works.
- Stat cards show real numbers and real sparklines (A10, I82–I85, I124, I127; OQ94).
- Existing clients get no view of their own until renewals (OQ1, OQ2).
- **New deal page** (`/deals/new`, A14): the two old mode cards, "1 · Get to Market — New client — start the intake" and
  "2 · Quote to Close — I already have carrier quotes", then Group name *, Renewal date and Notes (the deal's first
  note). It creates a Prospect and its deal. Card 2 creates the deal first and opens the Advisor with Work with Claude
  (D43; slice 20). Until slice 20, **＋ New deal** opens the New client dialog with Status Prospect. **Built in slice
  20** (`pages/NewDealPage/`): ＋ New deal opens it; card 2 shows only with Claude set up (D26) and opens Work with
  Claude on the page (`QuoteDrop`): the first files dropped or attached make the deal (Prospect, no lines: the read's
  `add_lines` brings them, D56), are filed as carrier quotes and read at once, and the deal opens on
  `/deals/{id}/advisor?claude=1`; card 1's "Create deal & open intake ▸" opens Intake. Notes go to the deal's notes
  (slice 38's `deals/{id}/notes/`). The duplicate check ("Already here?") is the dialog's.
- **New client dialog** (2V's, on old classes from slice 4): Client name (required), Status (Prospect or Existing
  client, §5.1), Target effective date (optional), Lines to quote (multi-select, default Medical; from slice 11 written
  through Intake's intent service, B17), Owner (users, default me). While the name is typed, up to 5 existing clients
  containing it are listed ("Already here? Example Co. — open") to prevent duplicates. **Create** opens the new deal.
- **Archived** (`/archived`, A13, M105; slice 38): archived clients with their status and their deal's stage,
  **Restore**, and **Try again** when the list fails to load. Archiving starts on the Overview, on the client page and
  from the old row button (M6, M7, M103, I126).

### 8.4 Deal page

The deal page is the old deal workspace (A20–A26; `bb-workspace`): a 232 px sticky sidebar, then the header strip, the
journey stepper, the Claude strip and the open tab.

**Sidebar** (A20, A21, A23), top to bottom:
- "← Benefits"; the client's name; "Renews <effective date>"; the intake ready chip (Blocked / Ready to market /
  Sent to market; B33).
- The client block "<client> ↗", for New and Existing clients only, as the old block showed only for linked deals. It
  opens the client page from slice 67 (A20). The year strip waits with renewals.
- The nav (below).
- "Deal readiness" meters: Intake, Proposal and Census. Hand-off is dropped (A23).

**The nav** keeps the old order and groups exactly (A21; OQ9):

| Group label | Tabs, in order |
|---|---|
| (none) | Overview · Agenda |
| 1 · Get to Market | Review & requests · Intake · Census · Questionnaire · RFP · Commission |
| 2 · Quote to Close | Advisor · Proposal |
| Shared | Documents |

- Questionnaire shows only while the deal has a form that is armed or started (G7).
- The old Close-out, Benefit guide, Implementation and Data Hub items are not built (A22).
- Badges as before: plain counts, the three-tone Review badge, the violet ↩ where client answers wait, "?" for open
  client questions, and Commission's "1" while no primary producer is set (A21, L13, H9).
- The order is the old one, not the app chain's (§3.3). Quotes never wait for a questionnaire: typed summary tier
  counts carry the Advisor and Proposal with no intake, census or questionnaire (OQ9; F85–F92).

**Header strip** (old classes; new against the old app, M112):
- The client name (the client dialog until slice 67, then the client page) and the client's status (§5.1).
- The stage pill (`bb-stage-pill`, with a class for `proposal`, M15); "Lost" shows here on every tab. **Stage ▾** sets
  intake, quoting or proposal by hand (A30).
- The effective date (inline edit; intake's `target_effective_date` writes the same field, B1) and the owner (a select;
  `deals.services.set_owner`, one Activity row).
- **Lines**: removable chips and **+ Line**, written through Intake's intent service from slice 11 (B17, B32).
- The Activity drawer, with Revert (A34; slice 5).
- The Potential deal size and the Agent of record, typed inline; a blank agent shows its default (the owner, else the
  agency producer) in grey (M27, M29, OQ49; slice 38).
- Mark lost, its dialog and the lost banner stay here until slice 62 moves them to the Overview (M1, M2, M4, M112), and
  so do Archive… ⓘ, its inline confirmation and the archived banner with Restore (M6, M7, M103; slice 38). A lost deal
  refuses what `deals.rules.refuses` lists; internal edits still work (O.3.7).

**Journey stepper** (A24, M39, I120): Get to Market and Quote to Close; dots ✓, current, to do and –; a click opens the
step's tab; the current dot is the step that owns the next step; no step is ever "skipped" (M40). It reads agenda's
`journey/` (O.4).

**Around every tab:** the ✦ Work with Claude pill, drawer and strip (A25; §8.17); the review tray dock (L49; slice 56);
toasts; and one error boundary per tab, so a failing tab leaves the sidebar and the other tabs working (A26).

Only the open tab's code and data load, and switching tabs never reloads the header (O.4). The one exception is the
idle prefetch of the RFP, Intake and Census first pages (K3).

### 8.5 Client page

The client page answers OQ2: one page per client, with its own Overview and Agenda, built for prospects and new
clients. Existing-client work waits with renewals (OQ1). The page opens for every status, because every client has a
row from creation (§5.1). Slice 67 builds the route, the sidebar, Overview, Notes and the ways in; slice 68 builds
Agenda and Commissions.

- **Ways in** (slice 67): Clients rows; the deal header's client name; the deal sidebar's client block (clients only,
  A20); the Overview's client box (M21). The client dialog retires in slice 67; its fields move to the header card.
  `/commissions?client=` stays the Book's filter.
- **Layout:** the old client workspace (`bb-workspace`, `bb-sidebar bnf-cw-sidebar`), one section at a time.
- **Sidebar:** "← Clients" ("← Prospects" for a prospect); the name, "Owner <name>" or "No primary producer", and
  "Effective <date>"; chips for the status, Archived and the agenda rollup (N overdue / N due soon / on track); the nav
  Overview · *Upkeep:* Agenda (badge: the overdue count) · *Revenue:* Commissions (an amber 1 while no primary producer
  is set) · *Relationship:* Notes. Below it, the old "Plan year" block without the year strip: "<year> sections", the
  current deal's nav in the deal sidebar's order with its badges, each item opening `/deals/:id/:tab`; and "This year at
  a glance" with the deal's Intake, Census and Proposal meters (A23).

| Old tab | Verdict | This build |
|---|---|---|
| Overview | Simplify | The blocks below (slice 67) |
| Agenda | Simplify | One panel per deal (Up next, Waiting, Later, "All of this deal's tasks ▸"); Add a task on a deal (the deal pick shows only with two or more deals); Done; the `?focus=` flash (I103; slice 68). Reminders and client tasks wait (I104–I108) |
| Plan years | Defer | Existing-client work (OQ1) |
| Notifications | Defer | The Radar |
| Commissions | Simplify | The client split editor (H106) and the client's booked records, by tier (slice 68). The client statement waits for slice 50 (H103, H105; OQ6) |
| Notes | Keep | The standing brief (`Client.notes`, saved on blur) and the current deal's notepad (slice 67). Earlier years wait (M78) |
| Deals & history | Defer | Multi-year; the Overview's History card lists the deals |

**Overview blocks, in the old order** (M101):
1. **Title row:** **Convert to client** (prospects only, in Start renewal's old place) and **Archive client…** with its
   inline confirm and banner (M6, M7, M103).
2. **Header card:** avatar, name and the brief's first line. Chips: the status (New client in the old "First year" chip
   `bnf-cat-custom`, Existing client in the old "Renewal client" chip `bnf-cat-renewal`, Prospect in grey), "Client
   since <date>", "Effective <date> · in Nd", and the owner. The client box: "<year> deal ↗" with its stage pill and
   "Next: …", or "No deal in flight" and "Last sold …". Facts: Client name (editable); Status (a select that posts to
   the status door, §5.1); Primary producer (read-only, with "set ▸", H41); Main contact (a select that sets the
   primary, with email and phone); Employees (`facts.enrolled_headcount`, with its source); Funding
   (`facts.incumbent`); Legal name, FEIN, SIC and Situs, read-only, with "edit in intake ↗".
3. **Waiting banner** of the current deal (agenda's light read).
4. **Tiles:** Effective (days to or since), Agenda (overdue, soon or clear) and Expected revenue (by tier). Received
   waits for the ledger (OQ6).
5. **Deal card**, in the old Renewal card's look: stage, compact stepper, next step, "Intake x% · Census y% · Proposal
   z% · N plans quoted", "Open the deal →" and "Commission tab".
6. **Coverage in force:** for a client, the sold plans per line (premium a month from the Sold package, and
   commission); for a prospect, the current coverage with its in-force commission.
7. **Activity:** the shared Timeline over the client's deals, with the status rows.
8. **Side cards:** the commission snapshot (H106), Latest notes (three), and History, one row per deal with its
   artifact chips (G116).

- **Left out:** the Plan years, Notifications and Deals & history tabs, the year strip and year pages, the past-year
  band (A28, M102), the next-plan-year chip, Start renewal (H104), the upkeep card, reminders and client tasks
  (I104–I108) and "Year N with us" wait with renewals or the Radar; Received figures wait for the ledger. P&C, service
  owner, Inactive, External ref, unlinked deals and Link to client are dropped (M19, M23).
- **Built from the deal's parts:** the compact journey stepper, the Waiting banner, the Timeline with `activityLook`,
  the notes card, `FactRow`, the tiles, the Agenda sections and forms, the commission card, SplitEditor in client scope
  and the deal sidebar's nav, each exported by its tab folder's `index.js`. Page code lives in `pages/ClientPage/`.
  Reads: `GET clients/{id}/overview/`, `…/agenda/` and `…/activity/`, and the client split (§7.10); keys
  `['client', id, …]` with `staleTime: 0`. The reads write nothing, and the overview read runs a fixed number of
  queries.

### 8.6 Overview (`overview`)

Part M (M1–M112; M.6). Slices 62–64, on slice 38's deals additions; deals open here from slice 62. The blocks keep
the old order (M.6), except that the Waiting banner sits under the title (M33; OQ96):
- **Title row:** **Mark as lost…** with its inline row and banner, and **Archive client…** with its confirm and banner
  (M1–M7, M103). Export status report waits (M95–M100; OQ8).
- **Header:** avatar, name and legal name; chips for the deal type (`deals.rules.deal_type`, M14), stage, days open,
  Renews and owner (M13–M18). The client box: a link for New and Existing clients (the client page from slice 67); for
  a prospect, "Not on the client book yet" with **Convert to client** (M21, M23; §5.1). Click-to-edit facts write
  through their owners (M24–M30).
- **Tiles:** Intake complete, Plans quoted, Last contact, Expected revenue (M35–M38).
- **Card 1, Get to Market:** the readiness badge and requirement groups, with the intent, intake, census,
  questionnaire, documents and confirmation rows, their asks and overrides, the enrollment check and the typed-count
  notice (M42–M61, M67, M108–M111). **Card 2, Quote to Close** (M62, M65).
- **Feed:** the outreach strip, "Who we've asked" and the Timeline from Activity (M68–M71). **Notes:** five kinds, pin,
  edit and soft delete with Undo (M73–M77). **Side cards:** coverage notes and the commission card (M80, M81).
- **Data confidence** and Double-check with AI (M83–M93; slice 64).
- Not built: the carry banner, earlier deals and earlier notes wait with renewals (M22, M31, M32, M47, M78, M84); the
  status report waits (OQ8); P&C is dropped (M19).

### 8.7 Agenda (`agenda`)

Part I (I1–I69, I119–I121; I.6). Slice 60. The old tab: title "Agenda" and its subtitle (I2); five sections with
toggles and counts, Done collapsed (I4–I6); step rows with date, dot, words, chip, **Open ▸** and their buttons
(I10–I14); **Later** with its picks and note (I15–I18); **Done anyway** and **Undo** (I19–I22); hand tasks with add,
tick, move, edit and soft delete (I27–I34); nudge rows owned by Review & requests (I35–I40); `?focus=` scrolls to a row
and flashes it (I7). Steps come from the catalogue (I41–I66). Once quotes are in, intake steps stop leading, and
"Import the census" does not lead while typed counts price the Advisor (I44, I50; OQ90). Plan my day and the task bar
wait (I91–I102; OQ8).

### 8.8 Review & requests (`review`)

Part L (L1–L75, L111–L136; L.6). Slices 53–59. Pills Board · Request · Review with their counts (L1); the readiness
strip and the Next banner (L2–L4); the Missing, Waiting and To review lanes (L5–L10, L135); keyboard queues
(L15–L23); the request page with its who bar, ask rail, embedded form, comment margin and edit mode (L24–L48); the tray
(L49–L54); requests and links with the builder, the Ask card and the link settings card (L55–L75). The same Board,
Request and Review views serve Intake, Census and Questionnaire, scoped by `SectionHost`, with a section bar on each
(L14, L45). The tab's counts come in its own payload from slice 53 (O.6 #3).

### 8.9 Intake (`intake`)

Part B (B1–B44; B.6). Slices 11, 39 and 40. Pills Form · Board · Request · Review (B36).
- The form: four cards and 56 questions, badges, inline checks and the Enter/Tab flow (B1–B12; slice 39).
- Contacts and current coverage (B13, B14), with both coverage editors kept, writing through one service (OQ15).
- The coverage and marketing intent card (B16–B24; slice 11), the only writer of the deal's lines (B17).
- The marketing readiness checklist with COBRA (B25–B28), the BOR e-signature and compliance uploads (B29, B31), the
  ready badge and **Mark as marketed** (B33, B34; slice 40).
- Per-question Required and Waived (B37; OQ17). Renewal carry waits (B30, B44).

### 8.10 Census (`census`)

Part C (C1–C47; C.5). Slices 12 and 41. Pills Roster · Board · Request · Review.
- The roster grid on `src/grid/`: paged by employee, line chips, a frozen Person column, cell colours by status or
  mark, Excel keys with a 50-step undo, ＋ Add employee and dependents, marks and asks (C1–C8; slice 41).
- Banners and the empty roster's doors (C9, C10). **Built in slice 51:** "Scan the census with Claude ▸" leads the
  doors and the drawer opens by itself once on an empty roster (D41, C10; greyed with the PHI-gate sentence while the
  switch is off, absent without Claude); "A census file is waiting for review." over the roster for a read import
  (C9); "Not our template? Read it with Claude ▸" in the mapping dialog hands a spreadsheet to the mapping assist
  (D42, D109); `?import=<id>` opens that import's dialog (the drawer's hand-off, D29).
- Getting a file in: the import door and the old mapping dialog with its reformat banner, then a dry run listing who
  is added, changed, removed and kept (C12–C17; slice 12).
- Validation with one severity word, readiness and "Census OK" (C21–C24). The COBRA tick lives in intake (C25;
  O.6 #2).
- The carrier format lens is the RFP's (C31; K79–K89). The template and export are §9.1 and §9.2.
- SSN is optional, masked and never asked on the portal (OQ16).

### 8.11 Questionnaire (`questionnaire`)

Part G (G1–G136; G.6). Slices 42, 43, 52 and 58. Shown only while the deal has a form (G7). The three forms are
Florida Blue 51+, Warner large group and the SIIA disclosure (G1; OQ5).
- Pills Form · Board · Request · Review (G34); form chips with `?form=` (G35).
- The paper layout and the table layout (G36–G38); inputs, autosave and the Enter/Tab flow (G39–G41); "N% complete"
  (G42); the band notice "Group size now says …" with Keep or Switch (G133).
- The signature card, **Reopen the form** with a reason, and the filed signed copy (G49–G55, G135).
- The ⬇ menu and the check modal (G56, G65–G67); the files are §9.12.
- **Built in slice 52:** a filled form read by Claude (D113, G99–G102) waits in the Work with Claude drawer's card, never
  on the tab; once used, its answers show on the form as Claude's reads (origin `ai`, file and page, amber when Claude
  doubted them) and the Claude strip over the tab offers ↶ Undo this run.

### 8.12 RFP (`rfp`)

Part K (K1–K124; K.6). Slices 44–46; slice 26 builds only the app and `asked_by_line`. The old tab key was `carriers`;
the route is `/deals/:id/rfp` (K1). Slice 44 builds the shell, the census line and cards 1–3 (intake's coverage card
and checklist mounted with this page's marks; OQ60: Confirmed and Mark completed both), and the idle warm-up (K3).
Slice 45 builds card 4's carrier census rows (K34–K41) and the lens with its Export readiness cards (K79–K88; OQ63:
both), which the Census tab mounts around its roster ("Our census"; `?lens=<key>` is where "Check ▸" lands).
Slice 46 builds the rest of card 4 (K42–K56: Warner's forms with the census, questionnaires and "Not set up", the form
with its variant chips and the cover by route, the issued proposal, attachments, pills, Reset to recommended and the
zip), card 5 (K57–K68, K120: drafts, Copy, Open in Outlook, the Sent tick, Sent earlier, and intake's Mark as marketed
once a draft is sent, K33) and the check modal before every download, shared from `src/exportcheck/` (K69, K70).
- Title and subtitle, "✓ N of M completed", the census line, and five collapsible cards with **Mark completed**
  (K4–K12).
- Cards: 1 What we're shopping (K13–K16); 2 What we're requesting (K17–K30); 3 Marketing readiness checklist
  (K31–K33); 4 RFP packet (K34–K56); 5 Emails to send (K57–K68, K120, K121).
- The export check modal (K69–K78, K122) and the census format lens (K79–K89), which the census review view mounts.
- The files are §9.8–§9.11.

### 8.13 Commission (`commission`)

Part H (H1–H24, H35, H120, H121; H.6). Slices 48 and 49. Every deal user sees and edits the rates; ledger figures
follow the commission tier (H5, H102).
- The rates grid: line rows, the in-force column, an agreed rate per line (CompInput), and Expected/yr with its basis
  and source (H1–H9).
- Who gets what: the split editor with its live preview, scope and terms (H10–H24, H121).
- After the sale: the booked block, "Booked · view" and BookingSummaryModal (H23, H35), the "Out of date · Update" chip
  (H120) and the CAA disclosure download (H108; §9.15).
- The ledger waits (OQ6).

### 8.14 Advisor (`advisor`)

Part F (F1–F144; F.6), with Part J's builder, Pages and Export viewer and Part D's review card. Slices 7–10, 13, 14,
21, 25–31 and 34–37. It replaces 2V's simplified Advisor (F134; slice 9). View pills (F1): Quote comparison,
Stop-loss analysis (only with a stop-loss line, F2), Proposal builder and Export viewer; Unleashed waits (F4; OQ4).
The view and the line are kept per browser, and `?view=` and `?line=` win (F1, F5).

**Quote comparison** (needs 4, 5 and 7–10):
- Line tabs with counts and the "Off the proposal" chip (F5, F13); the title, the count line and its notes (F8–F11).
- The finder over name, plan number, carrier, network, type, codes and aliases ("UHC"; OQ14), with "Also matches N on
  Dental" (F14–F17).
- Filters: the budget select, "Monthly total ≤ $", intake's budget hints, "N have no price yet", sliders, caps, hides,
  carrier chips and Claude's rule chips (F18–F27, F139, F140); saved setups, Mine and Shared (F28; OQ7).
- Columns, sort and layouts: presets, header sort, ⇄ Transpose up to 60 plans, sizes per user, rows windowed above 150
  plans (F31–F36, F40, F41); ▦ Pages "What the client will see", with PlanPicker (F37–F39, F45–F48); "As quoted" for one
  scanned file (F42; need 3; slice 21). Built in slice 21 as a view pill, "As quoted", offered once a read has landed a
  printed table (not a layout of the board): one chip per scanned file and line, then the quote on the station's Grid
  (Documents' `AsQuotedBoard`, loaded lazily): the plans in the file's column order, one band "As printed on page N",
  mapped rows live and editable (✎ Edit, picks, A/I/C/U, F opens the value on Documents), the rows that fill no field
  greyed with their printed text.
- Stars within the 16-column cap, current plans, links and "Replacing:" (F50–F55); ticks and batch actions; delete,
  clear and move to another line (F57–F61). A renewal needs its own star to print once its line has stars (OQ11).
  Stop-loss plans take arrows and slot picks like every line (OQ13, answered yes; this reverses the old app's rule,
  F49 and J7).
- Cells with flags, marks and ↗ to the source (F62–F67, F141); ✎ Edit mode with Excel keys and Ctrl+Z (F68–F73).
- Priced versions: the composer for concessions, bundles, premium holidays and named copies (F76–F78, F80–F84;
  slice 35; OQ7). In ✎ Edit, ＋ on a plan opens a live draft under it (the source pink, a blue row of the changes, the
  violet draft priced by the server's dry run; transposed, columns), edited in the row or docked above the table (⌸,
  kept per browser); ✎ reopens a version, ✕ removes it. Chips: the family's glyph and label, "superseded" on the
  original, BUNDLED, "requires …" and "updated <date>". Bundle templates wait (F79).
- Enrollment: "＋ Add summary medical tiers", the counts card with the split, and the census notice "Priced from the
  census now · Keep my typed counts" (F85–F92; need 6; slice 13; OQ18–OQ21).
- ⤓ Export, Import from template, ＋ Add SBCs and ＋ Add quotes (F93–F96).

**Stop-loss analysis** (F98–F107, F29; slice 36): the basis with its source, the in-force cards, verdict cards ranked
lowest first, the option table, the laser what-if (never saved) and the five-tab workbook (§9.13). Built in slice 36
(`deal/advisor/stoploss/`, the old StopLossAnalysis.jsx's markup and words): the pill second, only with a stop-loss
line (F2); one basis for every column, the line's enrolled people (the in-force contract's lives, else the line's
typed figure, else the medical enrolled employees, else the census) named in words; ranks, deltas and the punchline
(lowest premium against lowest maximum annual liability, whatever the rank key) from the server; the four controls
saved as `SavedView(view='stop-loss')` on the old saved bar (F29); lasers by position on screen too (F104).

**Proposal builder** (J17–J68; slices 25, 26 and 34):
- Collapsible cards with completed marks (J18–J20); the toolbar with the checks list, the three file buttons and
  "Open proposal ▸" (J23, J24, J27, J28).
- Deal cards: cover, pictures, layout, package summary, spreadsheet options, page switches with their ledger, team,
  plan experience and the intent card (J32–J35, J38, J39, J41–J43, J45, J46).
- Line cards: the plans on the proposal with the EnrollmentStrip (J47, J48; kept, OQ18); the page tables (J49–J54);
  the recommendation and its words (J52, J55–J57); parts, the table note, card stats, rows and Markets checked
  (J58–J63).
- The executive summary, next steps and templates (J64–J68); the Firm pages drawer (J155; slice 34).
- Classic and the share link wait (J25, J26, J36, J37, J40; OQ8).

**Export viewer** (need 11; J105–J120; slices 28 and 30): chips Excel, PowerPoint, Paper and PDF; the deck viewer with
its rail, jump chips, fit report and notes; the Paper frame; the workbook screen with frozen panes, printed pages and
checks per tab; downloads and **Print…**. Previews build only while shown and write nothing (J107; O.3.6).
- **Built (slice 28):** the "Export viewer" pill, last (F3); `?file=` and the file kept per browser as the old
  `exportFile` (F136); the chips (J105: PowerPoint, Paper and PDF greyed "next" until slice 30's deck view); the
  toolbar with the Draft badge, "Built 2:05 PM · 13 tabs", ↻ Refresh and ⬇ Download spreadsheet (J112; the "Not
  printing" chips are the deck view's, as in the old app); the Excel view (J116–J118: Screen with frozen panes, zoom,
  run-on text, ####, read-only drop-downs, rows windowed past 160, cell select; Printed pages; the checks per tab with
  their cells, tab dots, Ctrl+PgUp/PgDn; capped tabs at 2,500 rows). Each preview is a React Query entry keyed on
  file, tab and the builder's `stamps` settled 900 ms (J107): `files` moves with the deal's latest recorded write and
  at midnight, never with a completed mark or a download; `firm` with the agency settings, firm pages and team. The
  key sits outside `['deal', id]`, so a deal write rebuilds it only through its stamp; staleTime Infinity, no retry,
  no refetch on focus or mount, the last copy kept while the next builds, enabled only while shown and nothing is
  saving. "Open proposal ▸" on the builder opens it (J27). The grid lives in `deal/proposal/export/` (one screen uses
  it), not `src/viewer/`.
- **Built (slice 30):** the deck view (J108–J111, J114, J115): PowerPoint, PDF and Paper page through one build's
  PDF, drawn with the one pdf.js build (`src/viewer/pdfjs.js`), so switching files never builds again and keeps the
  page. It opens on the first Medical plan set and keeps the slide picked by title and position across rebuilds (J108,
  J109); ←→, ↑↓, PgUp/PgDn, Home/End; rail thumbnails; Jump chips with fit dots; the fit report above a plan set
  (J110: fits, notes moved on, runs on, the smallest type, rates apart from the benefits, rows over two lines); the
  PowerPoint's speaker notes (J111); a chart slide says PowerPoint draws it as a native chart (J.5 B22); "Not printing"
  from the builder's ledger, each opening the builder (J112). Paper sets each page on its Letter sheet with "Prints on
  US Letter landscape at 75%… This table's 9 pt type prints at 6.8 pt." (J114). Downloads: ⬇ Download PowerPoint,
  ⬇ Download PDF, ⬇ Download Letter PDF and **Print…**, whose window opens on the click and falls back to a download
  with a toast when pop-ups are blocked (J115, `export/printPdf.js`). Work with Claude is sent the viewer's state with
  each message (file, slide or tab, the fits; `deal/shared/viewerBridge.js`) and proposals' context provider puts it
  in words, building nothing (J120). "See the slides ▸" on the builder's Plans card opens the PowerPoint on that
  line's first plan set (J58, `?view=export&file=powerpoint`).

### 8.15 Proposal (`proposal`)

Part J (J70–J104; J.6.8). Slice 32; 2V's selection and preview retire in slice 25. The tab is the Advisor's board in
presented mode plus the packet card, composed by the route, so neither folder imports the other (J.3.6):
- Title "Plan comparison" with the refresh chip (J70); the legend and mark colours (J71); the Claude lock switch (J72);
  ✎ Edit and the grid's undo (J73–J75); "★ Shortlist (n) / Show all N plans" (J76).
- Import plan template, ＋ Add plan, ＋ Add quotes and ＋ Add SBCs, and Re-read quotes (J77–J80); line tabs, the
  enrollment-source notes and the bulk review bar (J81, J83, J84).
- Chips, ◀ ▶ and the ⋯ menu: Mark as sold with BookingSummaryModal, roles and renewals, Attach SBC…, Move to line… and
  Remove column (J87–J93); cost rows (J94). Several sold plans per line are allowed (OQ12).
- **The packet card** (J96–J104): the checks list; draft downloads that write nothing; the internal spreadsheet, which
  is the plan template export (J98; §9.3); **Issue to client (v N)**, run as an `issue` job that stores the PDF,
  PowerPoint and workbook as protected documents and offers the Letter PDF (J102, J103); the issued list with its states
  and Retry.
- Florida Blue 5182 and 5183 print as one column from slice 33 (J15; OQ42).
- Built (slice 32): `pages/DealPage/ProposalRoute.jsx` composes `deal/proposal`'s tab (title, `packet/PacketCard`,
  `IssuedList`, `ChecksList`) with `deal/advisor`'s `PresentedBoard` (the board's own transposed table, hooks and menu
  in Proposal order, every row of the line, the shortlist = what the proposal presents until Show all, no
  "Replacing:" in the heads). The packet card starts closed, as the old one; its ticks and open state are kept per
  browser (`vantage.bnf.proposalPacket`). BookingSummaryModal waits for commission's booking (H; slice 48 on).
- **Gap: 2V's ＋ Plan and ＋ Package dialogs.** v1.1's ＋ Plan dialog (with its "option or bought together" question)
  and ＋ Package dialog have no old twin; F134 gives them to this tab, and Part J has no row for them. Until §16 decides,
  they stay as built, on old classes, and the Look lane lists them as intended differences.

### 8.16 Documents (`documents`)

Part E (E1–E104; E.6) with D121–D133. Slices 15, 16, 17, 21, 23 and 65; until slice 15, 2V's Documents v1 stays, on old
classes.
- File tabs in upload order with bucket tags, and "All proposals (N)" (E1–E3); drop anywhere to "File as" (E4–E6); the
  File panel for label, kind, role, carrier and lines (E10–E14).
- **Remove** archives a file, and "Show removed files (N)" restores it (E15, E16; OQ23). Issued proposals and signed
  questionnaires are protected and cannot be removed (O.3.7).
- Viewers by shape: PDF with pages, zoom and the value boxed; image; sheet with the "As in Excel" look; and "can't be
  previewed here" (E21–E33).
- The Scanned data panel beside the file, as a List or a Grid, with the quality headline (E34–E47); "As in the file"
  for a scanned quote (E42; slice 21).
- Reviewing values: the file strip and bulk bar, the A, I, C, U and F keys, picks and Undo (E48–E58, D121–D126;
  slice 17); **Check this file** (E59; slice 16).
- Find with aliases, Review mode and Edit (E60–E68; slice 23). Built: ▦ Grid beside ☰ List (kept per browser; the
  List alone sits beside the file, the Grid takes the width below it), the station grid on `src/grid/` over the
  Advisor's cached comparisons (E36–E41: the scope files' plans in the Advisor's order, fields in group bands, frozen
  panes, the Proposal's sizes, columns windowed above 40 plans), "⚠ Potential errors" and "Only rows with potential
  errors" (E50), Excel picks with the pick bar, its keys and Undo (E51–E55, D123); Find over the Grid or the List with
  the finder's word rule and carrier nicknames ("UHC", OQ14), "N of M", Enter, Only matches, Esc (E60–E64, D127);
  Review mode, where a click or an arrow finds the value in its file and E or a double-click edits it, and ✎ Edit with
  Excel's keys, each value through the plan PATCH with `expect`, Ctrl+Z and Done ✓ (E65–E67, D125). F or a followed
  value moves only the viewer, to the value's own file; `?list=` keeps the panel on its file(s) and the file bar offers
  "← Back to" (D129, E31). E68 ("These came from the client") has no plan-value surface: the old app offered it on
  census and intake only, which join the station in slice 65.
- The pop-out window (E69–E71; slice 65; OQ99). Change history from Activity, with Revert (E73, E74).
- Census files open beside the roster (E43; OQ97) and intake files beside their answers (E44), from slice 65.
- **Built in slice 65 (OQ97–OQ99 defaults):** a census file's Scanned data is the Census tab's whole Roster
  (`deal/census/RosterBeside`, Roster's `beside`: no COBRA tick, import door, ⟲ Re-map or counts), under the file as
  the Grid is, and a cell's ↗ rings it in the workbook; an intake file's is the whole form card by card
  (`IntakeFileView`): "N of M questions read from this file", the rest muted, "Other file", intake's badges, a row
  read from a file opens there, then Contacts and Current coverage read-only; a questionnaire file points to the
  Questionnaire tab (E45). The station's ↗ asks census and intake for their values (`census:<member>:<key>`,
  `intake:<key>`; §7.6, §7.7). ⧉ New window (E69) opens `/deals/:dealId/documents/:docId/window` (no top bar), linked
  per browser tab by a BroadcastChannel (`viewer/docWindowLink.js`): the client's name, the deal's year and the file,
  the status pill, the file buttons, and the value F opened, boxed; A, I, C, U and F pressed there act on the tab's
  selection (never E); the tab shows "… is open in its own window" with Show the window and Bring it back here. The
  deal layout says which client is on screen (E71: 2 s beat, 6.5 s silence), so the window covers itself with
  "You're no longer working on <client>" when the tab leaves and clears when it comes back. A "Check this file" that
  lands refreshes the List too.
- How values, marks and the locator work: §10.7.

### 8.17 Work with Claude drawer and strip

Part D (D1–D45, D134; D.6). Slices 18–20, 24 and 66. Shown only when a key is set (D26); how reads land is §10.
- **The pill:** the navy ✦ Work with Claude pill, bottom-right on Overview, Intake, Census, Questionnaire, Advisor,
  Proposal and Documents (D1, M106). `?claude=1` opens the drawer; a drawer opened with the button stays open across
  tabs (D3).
- **The drawer:** a right panel with no scrim, min(560 px, 94 vw), 880 px while a review shows, so the table stays
  usable (D4). It holds:
  - the reading picker and the lock switch (D5); the client guidance box and ⚖ Rank plans (D6);
  - chats, with New and Rename (D7); the spend lines (D8); the model picker (D9);
  - file chips and the File room (D13, D14); the composer and the microphone (D19, D20; slice 66);
  - the running card with Stop (D21, D22); Undo, Try again and Check again (D23); the over-budget card (D24);
  - the staged review card and the proposed-changes list (D28, D31).
- **The strip** over Intake, Census, Questionnaire, Advisor and Proposal (A25): progress with Stop, "✓ N values
  changed", and news with Review ▸, the rank and "✦ Re-check N flags" (D34). Changed columns flash after a landing
  (D35).
- **Doors on other tabs:** ＋ Add quotes, ＋ Add SBCs, Attach SBC…, Re-read, Ask Claude to re-check, "Not our template?
  Read it with Claude ▸" and Intake's ✦ (D37–D40, D42, D134); the quote-first door (D43); `?claude=read&docs=…` opens
  the quote reader on named files (I53). **Built in slice 51:** Intake's "✦ Work with Claude" in its head (D134, the
  old words and title); "Not our template? Read it with Claude ▸" in the census mapping dialog (D42: this build reads
  it as the census's own hand-off, a spreadsheet the usual mapping could not place, to the mapping assist; the plan
  template's import keeps its dry run); a census read's card ("A census file is waiting for review … Review it on the
  Census tab ▸", Discard; `deal/claude/CensusReadCard`) and an intake read's body (`IntakeReview`, the old IntakeDiff's
  Field · New scan · Current table with ticks, then coverage and contacts); the drawer's words follow the reader
  (into the census or Intake; those reads always wait, meta `ai.targets[].waits`). **Built in slice 22:** "＋ Add SBCs" beside "＋ Add quotes" (opens the drawer
  on SBCs, F95); "Attach SBC…" in a medical plan's ⋯ menu on the Advisor's board (not on a priced version or a copy;
  the file uploads and its read waits, the drawer opening on it, D38); the Re-read panel offers SBCs too, each file
  read by its reader (E76); "✦ Ask Claude to re-check" on the review strips (the Advisor's, the station's strip and
  List, F66, E77) and "✦ Re-check N flags ▸" on the Claude strip past 20 open warnings (E80); the re-check's card
  (`deal/claude/RecheckCard`, the old flag re-check's words) in the drawer and under its file on Documents.
- **Built in slice 52:** a filled form's read waits as its own card (`deal/claude/QuestionnaireReadCard`, the old
  IntakeDiff's Question · New scan · Current table with ticks and ↗ to the page, then each row and where it goes — "Group
  Medical Conditions 2 → a new row", "Current plan 1 → row 1 of the form" — then "Left alone" with why), read from
  the questionnaire's `reads/` door; "Use this scan ▸" / "Apply N selected ▸", Discard, and "Open on the Questionnaire
  tab ▸" (G108's words); a signed form turns Use off and says to reopen it. On the Questionnaire tab the "Reading"
  picker names the deal's forms ("Florida Blue 51+", "SIIA disclosure"; G102), defaulting to the form on screen; the
  questionnaire reader reads member pages (no "left out" chip) and its ↶ Undo this run asks in its own words.
- Claude Unleashed, lessons and saved readers wait (D2, D10, D30, D33; OQ4).
- **Built in slice 20** (`src/deal/claude/`): `WorkWithClaude` (the strip, the pill and the drawer, mounted once in the
  deal shell under the header; the shell's section is `bnf-claude-section`, where landed plans flash, and the workspace
  wears `bnf-wwc-room` on the pill's tabs), `door.js` (the one door: a tab opens the drawer on a kind or hands it the
  files dropped on it), `ClaudeDrawer` (D4; Escape closes unless a dialog is over it) with the head's "Reading" picker
  (D5: the tab's readers' kinds from meta `ai.tabs`, stamped on attached files, for everyone), `ModelBar` (D9's one
  picker, labelled "Claude", Opus 5.5 only for admins and direct people; "Deal $y of $25"; "Last read: <model> · $x",
  D8), `FileChips` (D13: kind and role selects, pages and left-out pages, "scanned"; "📥 Read N files into the table"),
  `FileRoom` (D14: on Documents and Overview the "File as" list, then every file with ticks), `useAttach` (D16, D17: a
  drop or 📎 uploads under the kind and sends at once; a drop is never refused, the read queues), `RunningCard` (D21,
  D22, D27), `OverBudget` (D24), `ClaudeStrip` (D34), `flashPlans` (D35, F112), `AddQuotesButton` (F96, D37: the
  Advisor's board head and its empty states) and `QuoteDrop` (the quote-first door's drawer, D43). Documents' drop zone
  and "＋ Add files" hand their files to the drawer when Claude is set up (else the tab files them itself). Not built
  here: chats and the composer (D7, D19, D25; slice 24), the lock switch and guidance box (D5's lock, D6; slice 24),
  the mic (D20; slice 66), ＋ Add SBCs and Attach SBC… (slice 22), Check again (D93; slice 22).
- **Built in slice 66** (`src/voice/`; D20 simplified): the mic beside the composer's Send dictates through Chrome's
  on-device speech recognition only (`processLocally`, the old D-065 rule): the voice never leaves the computer, nothing
  is recorded or uploaded, and the words wait in the composer, like typed ones, until Send. `localSpeech.js` is the
  only file that names the browser's speech API; `MicButton` shows only in desktop Chrome on a secure page whose model
  is available or downloadable (asked when the drawer opens), and the first click on a computer without the speech
  pack starts its one-time download ("Downloading Chrome's speech model…", then "Voice is ready…"), with no setup,
  progress or help cards. Listening shows "Listening… click to stop" and the phrase being heard in grey; each finished
  phrase joins the words after a space; a blocked microphone or silence says so in the old words; a fatal error hides
  the mic for the session. Send (or Enter) stops the mic first, and Escape stops it before it closes the drawer (D4).

### 8.18 Commissions page (`/commissions`)

Part H (H42–H58, H68, H95–H102). Slices 48 and 49. Open to users with a commission tier; the title reads
"Commissions", or "My commissions" for the own tier (H42, H102). Tiles: Expected, House, Pool, Next 12 months and
Booked records (H45); the unconfirmed-defaults banner (H47); tabs by `?tab=` (H48):
- **Book** (H49–H57; slice 49): filters, group by client, the old columns, the export (§9.15) and the record drawer with
  facts, splits, notes and history. **Add to book** books a client from outside the app, with Status default Existing
  client (H58; §5.1).
- **By person** (H68; slice 49).
- **Producers & partners** (H95–H98) and **Settings** (H100, H101; slice 48).
- The Received YTD and Open gaps tiles and the Gaps, Statements and Documents tabs wait with the ledger (H45,
  H59–H93; OQ6), and so does the client statement (H103, H105). The Book split waits (H69).

### 8.19 Admin pages

- **Django admin** (`/admin/`) holds users and their Profile flags (`claude_direct`, `commissions_access`; A3, H101);
  agency settings (the logo, re-encoded on save, brand colour, contact, `producer_name`, `producer_npn` and
  `rfp_return_email`; J155, OQ41, OQ65); carrier notes for Claude (D119); and a read-only list of client links
  (L134). The firm pages, team and cover images left Django admin with slice 34 (J155). An admin cannot deactivate or demote themselves there
  (a `ModelAdmin` check).
- **In the app:** the Firm pages drawer, open to every user (J155; slice 34), and the Producers & partners and Settings
  tabs of `/commissions` (H95–H101; slice 48).
- Not built: the old Manage Users page, the roles matrix and the Review & request settings page (A2, A5, L74; OQ83).

### 8.20 Client portal (`/portal/:token`)

Part L (L76–L110, L136; L.6). Slices 54, 58 and 59.
- The old portal page, outside the app shell: no navbar and no help bubble (L76); the agency's name, logo and colour;
  usable on a phone (the Look lane runs it at 390×844).
- **The gate:** an unknown link answers 404; an expired, revoked or closed one answers 410 with the agency's contact;
  a PIN is asked with 428 and a six-digit box (L77; OQ80).
- **Inside:** the top bar "Secure link · expires in N days" (L80); the to-do rail (L81); the shared request card (L82);
  intake with company details, contacts, coverage, lines and the BOR e-signature (L83–L86); employee details and added
  people (L88, L90); questionnaires (L91; slice 58); document slots and the census file with its blank template (L93,
  L94); autosave with conflicts (L95–L97); Submit, follow-ups and the receipt (L98–L100; the receipt in slice 59);
  threads and "This is right" (L101, L102); the expired page (L107).
- SSN is never asked (OQ16). Commission and coverage intent are never shown (L108).
- Staff use View as client at `/preview/links/:linkId`; their writes there answer 403 (L78). Old `/b/` links show
  "This link has moved" (L136).
- **Built (slice 54):** `frontend/src/portal/` (PortalPage, PortalGate, PortalShell, PortalForm, TodoRail,
  IntakeSection, blocks/, PeopleSection, CellInput, AddPersonForm, FileSlots, SubmitBar, Unavailable, MovedPage,
  PreviewPage, `portalApi` with its own axios instance, `useAutosave`, `usePortalWrites`, `usePortalStamp`,
  `portalModel`), on the old classes; walked at 390×844 (`--need s54`). View as client is on the request card.

### 8.21 The grid

`src/grid/` is ported from the old grid hooks, not bought (O.3.5). It serves the Advisor, Proposal, Documents and
Census grids and knows nothing about plans or people.
- **Selection:** click, drag, Shift and Ctrl picks; a header picks a column and a label a row; arrows, Ctrl+A, Esc and
  edge scroll (E51).
- **Keys:** F2 or typing edits; Enter and Shift+Enter move down and up; Tab and Shift+Tab move right and left; arrows,
  Home and End move; Delete and Backspace clear; Esc cancels; an unchanged value writes nothing, and a blur does not
  save (F69).
- **Undo:** Ctrl+Z and ↶ Undo, 50 steps per cell in the current ✎ Edit session. Undo writes the earlier value with
  `expect`, and is refused if the cell changed since (F70, J74; O.6 #33). Activity's Revert stays in the log.
- **Saving:** commits go through a per-cell write queue — one request in flight per cell, the latest value wins, results
  apply in order. A failed commit shows the server's message on the cell and restores the last saved value.
- **Layout:** frozen panes; Excel-style sizes kept per user, with ↺ Reset sizes; a three-line clip with the full value
  on hover; windowed rows and columns (E39, F35, F36, F40). The old grid, freeze and grid-size sheets give the look.

### 8.22 Loading, empty and error states

- First load of a tab: the old load panel with its words ("Loading N quoted plans…", "Loading the agenda…") and **Try
  again**. Refetches keep the data on screen with the old "Refreshing…" chip (`bnf-load-panel*`, `bnf-refresh-chip*`;
  F6, K2, I3).
- Every list has the old empty state that offers the next action (E47, F7, I5, I125).
- A failed request shows an inline error with **Try again**. Save errors appear where the value was typed. A `401`
  returns to sign-in. A `403` from a missing CSRF header fetches `auth/csrf/` once and retries.
- Successful saves are quiet (a tick); actions that create, delete or generate show a toast.
- Error toasts carry the server's message (M10).

---

## 9. Generated files (the old formats)

Every file the app makes is the old app's file, ported: the client files in the old Presentation format (need 12;
Part J), and the working files as the old app wrote them (Parts C, F, G, H and K). Rules for every file:
- **Names** come from `safe_filename`: characters outside `[A-Za-z0-9 ._-]` are removed, and no name carries a person
  or other PHI (§3.8). Client proposal files are `<Client> - <year> Benefits Proposal[-DRAFT].<ext>` (J104); carrier
  census files are `<Client> - <Carrier> census.xlsx` (K.6); other names are given below.
- **Downloads** go through `deals.downloads.file_response`, with an explicit content-type map; zips and `.eml` files
  stream in chunks (K.6). A file that carries PHI writes one `downloaded` Activity row that names the document or the
  file, never a person (`log_access`, O.3.2; Q.8). Building or previewing a file writes nothing else (Q.3 #2).
- **Spreadsheet text** goes through `documents/xlsx_safe.py`: XlsxWriter's string-to-formula, URL and number
  conversions are off, text is written with `write_string`, and links are written one by one (D114, J153). CSV text
  that starts like a formula gets a leading apostrophe (K107).
- **Client files** print only `client: True` fields (§4.3) and only approved values (L.6; OQ85). They never print
  anything on J.4's list: non-client fields, `sl_lasers`, commission figures, birth dates, status sentences,
  `star_reason`, `client_guidance`, internal notes, sources, document names and review marks (N.3 #10; H125). Canaries
  prove it (Q.8).
- **The old writers are pinned:** reportlab 4.2.5, python-pptx 1.0.2 and XlsxWriter 3.3.0, each in the slice that adds
  it, so the Fidelity lane compares our code, not library versions (O.3.6).
- **Proof.** Each file is compared with the old app's file for the same golden deal (the Fidelity lane, Q.5), and its
  figures equal the signed keys (Q.4).
- **Retired or not built:** v1.1's internal comparison workbook (the plan template export replaces it, J98); Classic
  files (J143; OQ8); the status report (M95–M100; OQ8); the benefit guide and contribution model (J99, J168); the
  commission dispute packet and gap exports (H63, H66; OQ6).

### 9.1 Blank census template (`census/template.py`)

- Sheet **Census**: row 1 holds the labels of the deal's census columns (§4.4) in order: every column, minus the lines
  the group is not quoting, plus the columns made Required on this deal (C38; OQ17). Header style: bold white on navy
  `#173a63`, wrapped, row height 28; column widths 12–28 by label length; freeze panes at `A2`.
- Staff downloads (`deals/{id}/census/template/`) are prefilled when the deal already has people: rows 2+, each
  employee followed by its dependents. A prefilled copy writes a `downloaded` row. **The client portal's copy is always
  blank** (L.6); the old masked, prefilled portal copy is not ported (C35, C38).
- Sheet **How to fill this in**, second: the group's name, the old notes (one row per person, keep the header row,
  blanks are fine, dates, tiers, extra columns are fine) and the columns needed to quote (C38).
- Because every label is an exact header synonym (§4.8), a filled template re-imports at full confidence.
- Slice 41.

### 9.2 Census export (`census/template.py`)

Staff-only workbook: sheet **Census** with a first column **Type** (Employee / Dependent), then all 45 columns, then
**Issues** (the person's messages joined with "; "). Unmasked. Same header styling as §9.1. Every download writes a
`downloaded` Activity row (§3.8).
The row is written by `log_access` (O.3.2). Slice 41.

### 9.3 Plan template (`quotes/template.py`)

One sheet per line, named by the line's label:

| Row | Column A | Column B | Columns C… (one per plan) |
|---|---|---|---|
| 1 | `<Client> — <Line> plans` | | |
| 2 | Fill one column per plan. Don't change columns A–B. | | |
| 4 | Plan ID | `id` | existing plan id, blank for a new plan |
| 5 | Role | `role` | current / renewal / alternate |
| 6 | Carrier | `carrier` | |
| 7 | Plan name | `name` | |
| 8 | Plan number | `plan_number` | |
| 9 | Renews / replaces plan IDs | `link` | a renewal: the id of the current plan it renews; an alternate: the ids of the current plans it replaces, separated by commas; or blank |
| 11+ | field label | field key | one row per field of the line (§4.3 order) |

Existing plans are exported in Advisor order, followed by 3 empty plan columns. Column B is grey; columns A–B are
frozen.

**Import rules** (all-or-nothing; a dry run reports the same result without writing):
- Each sheet name must be a line label or key; otherwise the error `Sheet "<name>" isn't a line of coverage`.
- Every key in column B must be `id`, `role`, `carrier`, `name`, `plan_number`, `link` or a field of that line;
  otherwise `<Sheet>!B<row>: unknown field "<key>"`.
- A plan column with no Plan ID, carrier or name is skipped.
- With a Plan ID: it must be a plan of this deal on this line (`… isn't a plan on this deal's <line> line`) → update.
  Without: create; role, carrier and name are required.
- Values are cleaned as every plan write is (§5, Plans); a refused value becomes `<Sheet>!<cell>: <message>`.
- A **blank cell leaves the existing value unchanged** (clear values in the app).
- A **cell equal to the stored value** (after cleaning) changes nothing — not the value, not its source (§3.7). So
  re-importing an exported template changes exactly the edited cells, and never turns an unconfirmed AI value into an
  "import". The dry run reports `{create, update, cells_changed, errors}`.
- The `link` cell must name current plans on the line and obey the role rules of §5 (Plans): one
  for a renewal, any number for an alternate.
- The uploaded file is stored as a document of kind `plan_template`, label "Plan template import" (E8; slice 15,
  kind `other` today); changed values get sources `{origin: import, doc, cell}`.
- **The internal spreadsheet.** The same export is the Proposal's internal spreadsheet (J98): every plan and every
  field, `client: False` ones and `sl_lasers` included. So it is staff-only, never attached to anything a client
  receives, and every download writes a `downloaded` row (slice 5, `log_access`; nothing today). It round-trips
  through the import.
- Its literal-text guard moves into `documents/xlsx_safe.py`, the one helper every spreadsheet uses (D114).

### 9.4 Client spreadsheet (`proposals/workbook/`)

The old Presentation workbook (J145–J154; slice 27): the baseline output, since "everything starts and ends with that
Excel document" (Stephanie, 2026-11-05). `workbook/model.py` is a pure model of values, formulas with their stored
results, formats, merges, widths, drop-downs, print setup and images; `write.py` writes it with XlsxWriter through
`xlsx_safe`; the Export viewer shows the same model, one tab at a time (J116; O.3.6).

**Written with XlsxWriter, every formula with its stored result.** A library that stores a formula without its result
(openpyxl does) leaves every total empty in any viewer that does not calculate — phone mail previews, Outlook's preview
pane, and Excel's Protected View until "Enable Editing", which is how an emailed attachment opens. XlsxWriter's
`write_formula(cell, formula, format, value)` stores the app's number as the result, so every viewer shows the app's
totals whether it calculates or not.

- **Formulas:** the old templates, verbatim (`workbook/formulas.py`): per-tier guards, the stated-premium fallback,
  text read as missing, counts through SUM. Only IF, OR, AND, SUM, ROUND, INDEX, MATCH, IFERROR, MIN, MAX and HYPERLINK
  are used; there is no SUMPRODUCT, so a what-if count on an unrated tier falls back to the stated premium or blank
  (J147; J.5 B33). Every stored result comes from quotes' math and `package()` (O.3.7).
- **Tabs, in order** (J145–J151):

| Tab | Holds | Items |
|---|---|---|
| Cover | Banner, logo, title, introduction, "Prepared by" (`deals.rules.agent_name`, OQ41), the summary snapshot, each line's recommendation words, "Figures as of this download" | J145, J57 |
| Markets Checked | Who was asked and who quoted, when the builder shows it | J146, J63 |
| One per tier-rated line | Up to 16 plans: title band, SOLD and RECOMMENDED markers, design rows, counts and rates, live totals, changes and packages with one current plan, credit and net; freeze at B7; a page break before each carrier | J147 |
| Dynamic `<Line>` Compare | 5, 10 or 16 drop-down slots, the base-plan box, status words with fills, % against the current plan and the renewal, contribution modes; 9 pt, zoom 110; the file opens here | J148 |
| The quote list, `<Line>` Composite Rates, `<Line>` All Plans | Every quoted plan the client may see, one drop-down away; plan cards; an AutoFilter list without unread, hidden-carrier and unrated plans | J149, J150 |
| Other lines; in force | One column per plan for life, disability, PEPM and stop-loss lines; stated facts for a line kept as is | J151 |
| Disclaimers | The old wording, one constant, until Stephanie's review (OQ40) | J151 |

- A line with more plans than its rates tab holds keeps them all on its Compare, Composite Rates and All Plans tabs, so
  the file never refuses for size (J3). A carrier hidden on Markets checked also leaves Compare and All Plans, labelled
  on the Markets card (J154; OQ39).
- **Print:** breaks by width and before each carrier, as before; Compare prints 5 slots a page (J.6.11).
- **Settings:** the agency as author, recalculation on open, zoom 130 or 110 (J152).
- **Draft** shows in page headers and footers only, never on the Cover tab (J102; OQ35). Option numbers are the
  per-line "Option n", stamped at Issue (J159; OQ36). A Florida Blue pair prints as one column from slice 33 (J15;
  OQ42).
- The team's settled points (current plans beside their renewals; benefits, rates and totals on one page; no mental
  health row; the minimum value and Part D rows) are checked against the old rows in slice 27; any gap goes to
  Stephanie's review (OQ40).
- **Correctness requirement**, for every plan and every printed package: the stored result of each formula, the result
  of evaluating the written formulas on the written cell values, and a LibreOffice recalculation of the file all equal
  the app's figure exactly (§12.6).
- **Built (slice 27):** `workbook/facts.py` reads the deal once through an allow-list (client fields only, quotes'
  results, the layout Pages and Issue share); `layout.py` names the tabs; `tabs/` draws Cover, Markets Checked, the
  rates tabs (`rates.py`, `rates_cost.py`), the generic and in-force tabs, Dynamic Compare, Composite Rates, All Plans
  (`bank.py`, `bank_map.py`, `compare*.py`, `slots.py`, `composite.py`, `all_plans.py`) and Disclaimers on the pure
  model (`model.py`, `cells.py`, `styles.py`, `grammar.py`, `formulas.py`, `print_plan.py`); `write.py` writes it.
  Every stored result is quotes' figure (`quotes/math/contribution.py` and `premium.annual` were added for the Compare
  tab's contribution and the year); a test-only evaluator (`proposals/tests/sheet_eval.py`) and the Recalc lane
  (`bash tools/parity/recalc.sh`: `pytest -m recalc` writes the files, `tools/parity/recalc.py` recalculates them in
  the parity tools image) hold every formula to it. Not printed yet: the cover banner (covers, slice 34), bundle
  caveats (priced bundles, slice 35); 2V has no read state, so no "unread" plan is left off All Plans.
- **Built (slice 28):** a model width is the width the file stores, as the old writer stored it and as `print_plan`
  plans with it: `write.py` sets each column in whole pixels (`int(width × 7 + 0.5)`; a stored 46 draws at 322 px),
  since XlsxWriter's `set_column` would add Excel's 5 px padding and every column would print wider than planned.
  The Export viewer (`proposals/viewer/`) shows the model one tab a request: the tab's look is `look(write(model))`,
  documents' look reader over the tab as the download's writer writes it; each value is the model's (a formula's
  stored result) drawn through its number format by `workbook/text.py` (the old `workbook_text`), with the format's
  colour, the conditional fills that hold now (`viewer/fills.py`) and Excel's alignment for numbers; the checks
  (`viewer/workbook_checks.py`: error, ####, cut off, tight) and the printed pages (`viewer/workbook_pages.py`, over
  the tab's print setup with `print_plan.PRINT_WIDTH`) are read from the model too. No formula is evaluated (J119).

### 9.5 Client PDF and PowerPoint: one layout (`proposals/story/`, `proposals/layout/`)

The old Presentation pages, 16:9 (960 × 540 pt), laid out once and drawn twice, so a figure, plan, caption or
disclaimer can never differ between the PDF and the PowerPoint (J122; slice 29).
- `story/` turns one client-shaped Facts, built from `deal_state()` in a fixed number of queries, into our own
  flowables. `layout/` fits them with reportlab's platypus through its public API only (`wrap`, `split`, `drawOn`), and
  a recorder logs every placed frame and the fit log (J122; J.6.3).
- **Pages,** in the old order (J123–J138, J165): cover; agenda and dividers; About and Team; coverage overview; "What
  we negotiated"; premium chart and dashboard; plan experience and Markets checked; renewal-set pages; "Your options";
  the exhibits; the cost-only line; "What employees pay"; recommendation pages (one panel, or a table when a current
  plan has several picks); incumbent pages; next steps, calendar, Thank you, bios and Important information. The
  renewal history page waits with renewals (J129).
- **Six plans a slide** at most, each current plan kept with its renewal and current plans always included (D-221;
  `pages.py`, the one splitter, J.6.3).
- **Chrome and fitting:** titles from 26 down to 16 pt, the rule, the footer stamp, the rates note, the firm and the
  page number (J139); table type from 12 down to 8 pt, rows of at most two lines, "(continued)" pages, long values moved
  to notes (J140).
- Firm pages print nothing until they are written (J125, J155; OQ41).
- **Built (slice 29):** `story/facts.py` (+ `line_facts.py`, `firm_read.py`) reads the client Facts; `story/sequence.py`
  orders the pages (`opening`, `firm`, `coverage`, `answer`, `glance`, `line_pages`, `exhibit`, `exhibit_rows`,
  `recommend`, `closing`); `layout/record.lay_out` runs the one pass into recorded pages {n, kind, title, continued,
  line, fit, notes, frames, chrome}, each frame plain JSON (`layout/items.py`); `story/build.deck(deal)` gives them
  with the pictures' bytes. The plan sets' rows are the client spreadsheet's house maps (`workbook/rows.py`,
  `workbook/design.py`, J133). Stock pictures are cropped once under `assets/images/stock_images/` (B12).
- **The old files' geometry** (the Fidelity fix-up after slice 28; §12.7): frames sit where old Vantage's reportlab put
  the same things, within the lane's 0.5 pt. A paragraph's first baseline is one size of its first line below its top
  (0.96 for the furniture's words) and every later line one leading under it; each kind keeps its old style's leading
  and space (a header row the page sizes leads at 1.25 ×, the overview's and dashboard's cells at the size + 2.5), and
  space before overlaps the space after, as reportlab's frame does. Tables keep reportlab's geometry
  (`layout/grid.py`): words centred between each cell's own padding, an empty cell one 12 pt line, a cell spanning rows
  sharing what it needs among them. The WE RECOMMEND panel is one table in both files, the plan in a cell spanning
  every row (J136); "Your options" keeps the table's 12 pt and runs on, as the old one did (J132).

### 9.6 PowerPoint (`proposals/paint/pptx/`)

`paint/pptx/` replays the recorded frames with python-pptx 1.0.2 (J141; slice 31): a slide master with the band, the
footer and the stamp; four layouts; title placeholders; native charts, only with two or more rows; speaker notes with
the producer's reasons; live slide numbers without "of M". Text is Arial, which has Helvetica's metrics, so PowerPoint
wraps where the layout did (J142). Each text box equals its recorded frame (J.6.10); a wrapping box or table cell gets
1 pt more room on the side its words never reach, for a renderer's rounding.
- **Built (slice 31):** `paint/pptx/deck.draw(pages, title, sources)` replays `story.build.deck(deal)`'s pages, no second
  layout pass. The master is the old app's, dressed in code from python-pptx's own template as old Vantage did (it
  shipped no .pptx): "Proposal content" (the master holds the content pages' shared chrome, lifted once; the title
  placeholder in the title zone, 26 pt bold in the brand's navy), "Proposal dark page" (the recorded dark ground and
  the mark), "Proposal photo page" (the ground alone) and "Proposal plain page"; the brand is the theme's accent 1.
  A content slide's title fills its placeholder (its own size only when the layout stepped it down); a whole page's
  title frame fills the placeholder at its recorded place. Runs are written unkerned (`kern="0"`), as the layout
  measured them. Tables are native ("No Style, No Grid"), the premium chart a native clustered column chart. One
  known difference from the PDF: PowerPoint and LibreOffice put a line's extra leading above its baseline, the PDF
  below it, so text whose leading is not 1.2× its size sits a few points off on the slide (13/19 body text ~3 pt
  lower, the cover's 44/48 name ~3 pt higher); tables, at 1.2×, agree. Old Vantage's PDF and deck differ the same
  way; the PDF keeps reportlab's placement, which the Fidelity lane holds it to (§9.5).

### 9.7 PDF, Paper and the Letter PDF (`proposals/paint/`)

- **PDF** (`paint/pdf.py`; slice 29): the same frames, drawn by reportlab 4.2.5 in Helvetica, with fonts, colours and
  letterhead from `deals/pdfkit.py` (J122, J142; O.3.6). There is no LibreOffice conversion.
- **Paper** (J114; slice 30): the Export viewer shows each 16:9 page on a US Letter sheet of its own orientation, scaled
  to fit inside half-inch margins and centred, as printing the PowerPoint or the PDF on Letter does. A slide prints at
  75%, so "9 pt prints at 6.8 pt", and the viewer says so before anyone prints. Stephanie prints from PowerPoint because
  a PDF's type comes out too small (2026-11-05).
- **Letter PDF** (`paint/paper.py`, pypdf): the same placement, as a file. A draft's is made from the draft PDF; an
  issue's is made from its stored PDF bytes, so it never differs from what was issued (J103, J115).
- **Built (slice 30):** `paint/paper.py`: `placement(w, h)` (a Letter page as it is; any other on a Letter sheet of
  its own orientation, scaled into the half-inch margin and centred: a slide at 75%), `summary(w, h)` → `{scale, sheet,
  as_is, inner}` for the Paper view, `letter(pdf_bytes)` (pypdf's `merge_transformed_page`; links move with their
  page). The draft's Letter PDF is `GET …/proposal/files/letter/`; Issue (slice 32) calls `letter` on the stored bytes.

### 9.8 Carrier census files (`rfp/formats/`, `rfp/xlsx/`)

Each carrier's own workbook, filled the way a careful person would fill it in Excel (K90–K98; slice 45).
- **Definitions** live in the data module `rfp/formats/definitions.py`, generated once from a migrated old database at
  its final state (migrations 0054, 0055 and 0066), diffed against the 2026-09-17 document and the live rows, and never
  retyped (K93). Each format holds its geometry, its columns `{header, hint, field or source, transform, value_map,
  required, employee_only, line, inherits}`, its group-information tab, `gaps` and `not_sent` (K.6). The bundled
  workbooks are hash-checked (Appendix A).
- **The four formats** (K93):

| Key | Carrier | Columns | Row cap | Delivered as | Notes |
|---|---|---|---|---|---|
| `warner_census` | Warner Pacific (the universal census) | B–X | 500 | xlsx | PAY MODE prints "Annual" whenever a salary is written. Columns S and X, both headed CLASSES (S under the BASIC LIFE banner, X under DISABILITY), both take `emp_class` (checked against the workbook in slice 45, OQ109) |
| `aetna_gateway` | Aetna | A–I | 485 | xlsx | The AFA UW / FI UW selector in J1 follows the funding asked; status words "Active, Cobra, St Con, Retiree"; gender required |
| `angle` | Angle Health | B–I | 213 (the pre-styled rows) | xlsx, plus a CSV that carries everyone | Angle's own workbook, filled in place; the example row is cleared; dates are real dates |
| `uhc` | UnitedHealthcare | A–X | 350 | xlsx | A group-information tab with 19 group facts; a middle initial in hidden column H; "Waive all products?" is gone (0066) |

- **Rows:** each employee followed by its dependents in family order, from the data row; members only, since the
  employee-only scope is dropped (K38). A roster past the cap stops there, with a truthful warning naming how many
  people did not fit, shown in the check (K97; OQ61).
- **Cells** (K92), in order:
  - `field` → the member's value; if blank and `inherits`, the employee's value.
  - `source`: `row:member_type` → relationship token; `row:enroll:<field>` → `ENROLL` when that amount is present;
    derived values: age at the effective date, county (typed, else the ZIP crosswalk) and `IN_AREA` for a
    contiguous-US ZIP.
  - `employee_only` → blank on dependent rows. `line` → blank unless the deal requests that line (K16).
  - `transform`: `tier` → token `EE/ES/EC/FAM/WAIVE` (§4.2); `gender` → `M/F`; `status` → `COBRA` if the text contains
    COBRA, `RETIREE` if it contains RETIRE, `STCON` if it contains "ST CON" or "CONTINU", else `ACTIVE`; `date` → a real
    date cell; `zip5` → 5 digits (4 digits get a leading zero, ZIP+4 is cut); `initial`. The other old sources and
    transforms (`case:`, `const:`, `date_mdy`, `upper`, the SSN and `tier_code` transforms) are dropped (K95).
  - **Relationship token:** employee rows → `employee`; dependents: text containing domestic, dp or civil union →
    `domestic_partner`; child, son, daughter, dependent, stepchild or ch → `child`; spouse, wife, husband, partner or
    sp → `spouse`; anything else → `child` with a warning.
  - `value_map` turns a token into the carrier's spelling; a token missing from the map writes blank.
- **Required and missing:** a `required` column left blank is a check problem with its count, and a blank tier is
  counted once per employee (K74). The same marks feed the Census tab's required cells for the formats the request
  sends, through `rfp.required_columns` (K124), so a blank is flagged before the file is filled. The columns we do not
  store are listed per format (`gaps`, `not_sent`; K88).
- **Writing** (`rfp/xlsx/`, the old `fill_xlsx`, ported unchanged; K90): only the sheet data, merges and dimension are
  rewritten; each cell keeps an explicit style (its own, else the nearest row's, the row's or the column's); text cells
  stay text; formulas are untouched; strings are inline; the recalculation flag is set only when a formula reads a
  written column; Aetna's thumbnail is dropped; zip entries are written as Excel writes them. A column whose header
  moved fails the build, and tests catch it (K71, K96).
- **CSV** (Angle): written from the filled rows as Excel's "CSV UTF-8" does (K91), named
  `<Client> - <Carrier> census.csv`.
- Only approved values print (OQ85). The files carry PHI, so downloads are logged (K113); a file that cannot be built
  answers 409 naming its label only (K55).

### 9.9 Warner quote request form and cover page (`rfp/forms/`, `rfp/cover.py`)

- **Quote request form** (K42, K46, K99–K101): Warner's own workbook in three versions (Simplified, the default for
  every size; Small group 2–50; Large group 51+), written as §9.8 writes. `rfp/forms/maps.py` holds `VARIANTS`, copied
  as is: every input cell is paired with the label beside it, and each label is checked before writing.
  - Filled: the group header facts (`quotes.facts.group_facts` and `rfp/printed.py`, K101), with the band's enrolled
    count (K17) and the SIC code as Nature of Business (OQ62); the broker block (`deals.rules.agent_name`); and the
    commission request (K106). Dates are written as dates, counts as numbers.
  - Simplified carries only the header and the commission box (K100).
  - The 2–50 and 51+ versions add the funding boxes (2–50 has no ASO box, so asking for ASO warns), the carrier ×
    column matrix where a box exists, the notes cell (wrap on) and Additional Carriers (K99).
  - The packet's copy carries only the census header; the "form + census" downloads carry the census inline, up to
    500 people (K42, K99).
- **Cover page** (direct route; K102): one page, Letter portrait, drawn with `deals/pdfkit.py`: the letterhead; the
  group and its size, with the band's enrolled count (K17); the coverage requested beside what is in force; the funding
  boxes; the broker (`deals.rules.agent_name`) and the return-to address (`rfp_return_email`, else the owner's email;
  OQ65); BOR on file; the commission by line; the notes; the date in agency time. It never names a carrier.
- Built in slice 46: `rfp/forms/maps.py` and `fill.py` (label guard, header, boxes, matrix, Notes with wrap,
  Additional Carriers, the census inside at Warner's geometry), `rfp/cover/` (the kit and the page; K.6 named
  `deals/pdfkit.py`, rfp is its only user so far). The ASO box the 2–50 form lacks is a check problem.

### 9.10 RFP packet (`rfp/packet.py`)

- `<Client> - RFP packet - <YYYY-MM-DD>.zip` holds exactly the ticked files (K34–K56):
  - the census files (§9.8): Warner's universal census when nothing is picked, the route is Warner, a picked carrier has
    no format of its own, or "Other carriers" is filled (K39; OQ64), plus each picked carrier's own format;
  - the Warner request form (Warner route) or the cover page (direct route);
  - the questionnaire PDFs and disclosures (K43; §9.12);
  - the attachments: renewal, claims, invoice, SBCs and paper questionnaires, by their default ticks (K49; OQ66, OQ69),
    under `Documents/` with their original names (a file carrying member data under documents' `<Client> - <Kind>`
    name, rule 10), duplicates suffixed ` (2)`;
  - off by default, the latest issued proposal (OQ68; J169).
- `README.txt`: the group, the date, the files, the lines and funding asked for and the notes, signed with the agency's
  name. It names no carrier and carries no warnings; what to fix is the check's job (D-143; K103).
- `Quote request summary.txt`, on the Warner route only: the request in words (K103).
- Nothing ticked answers 400. A member that cannot be built refuses the whole download with 409, naming its label only
  (K55); v1.1's "Could not include" list is gone.
- The zip streams in chunks and is logged when it carries a census or PHI documents (K.6).
- Built in slice 46 (`rfp/packet.py`, `rfp/members.py`): the cover that leads is the zip's first file.

### 9.11 Email drafts (`rfp/drafts.py`, `rfp/eml.py`)

- **Warner route:** one draft — To `FLQuoting@WarnerPacific.com`; Subject
  `Quote request: <group> | eff. <MM/DD/YYYY> | <short lines>`; attachments: the whole packet's files; extra text: the
  request summary.
- **Direct route:** one draft per picked carrier, plus one "Other carriers" draft when that field is filled. To is
  blank (the rep fills it in; OQ59). Subject `RFP: <group> | eff. <MM/DD/YYYY> | <short lines>`, listing only the lines
  that carrier quotes (K60). A direct draft never names another carrier.
- **Attachments** follow `audience.receives()` (K61): the paper questionnaire follows `takes` (G112); PHI files go only
  to carriers quoting the lines they cover, to medical carriers when a file has no lines, and never to "Other
  carriers" (OQ66); the universal census goes where §9.10 puts it (K39; OQ64); each carrier gets its own census format.
  A draft whose files pass about 20 MB is a check problem (K121).
- CC: the returns inbox, `AgencySettings.rfp_return_email`, else the deal owner's email (OQ65). Short lines: §4.1
  "Short", comma-separated.
- **Body** (lines are omitted when their value is empty):

```
Hi,

<opening> <docs line>
- <attachment name>
- <attachment name>

<extra text>

Quotes are due back by <Month D, YYYY>.

Please reply all so your quote reaches <CC address>.

Thank you,
<agent name: deals.rules.agent_name>
<agency name>
<agency phone>
```

  Opening — Warner: `Please see the attached quote request for <group>, effective <Month D, YYYY>.` with docs line
  `The documents to quote are attached:`. Direct: `Please see the attached RFP for <group>, effective <Month D, YYYY>.`
  with `The documents to quote are also attached:`.
- **`.eml` file:** an RFC 5322 message with header `X-Unsent: 1` (Outlook opens it as an unsent draft), To, CC, Subject
  and **no From** (Outlook sends from the account that opens it); `multipart/mixed` with a UTF-8 `text/plain` body and
  the attachments.
- Attachments are typed from an explicit map, and the message streams in chunks. A member that cannot be built answers
  409 naming its label only, never a member's value (K63).
- Built in slice 46 (`rfp/drafts.py`, `rfp/audience.py`, `rfp/eml.py`). Outlook itself was not used: the `.eml` is
  proven by reading it back (headers, `X-Unsent: 1`, no From, the attachments and their types).

### 9.12 Questionnaire PDFs (`questionnaire/pdf/`)

Part G (G56–G67, G135; G.6). Built in slice 43 (`questionnaire/pdf/`, `check/`, `rfp_rules.py`, `selectors/rfp.py`);
they join the RFP packet in slice 46, which reads `selectors.rfp.rfp_files`, `sent_with` and `changed_since`.
- **The ⬇ menu** (G56, G61): "Download PDF" (the filled form, or the filed signed copy once the officer has signed)
  and "Blank carrier PDF". "Carrier PDF (Acrobat)" is absent until the XFA copy is built (G58, deferred; OQ57).
- **Florida Blue 51+:** a stamped flat copy over the bundled blank, placed by `stamp_place.py` (pure) and drawn by
  `stamp_draw.py`: the CMYK repaint, Arimo 9.5 pt shrinking to 6 pt, the state's full name, the shared Q12 box, inline
  boxes, the cancer-area repaint, and "See attachment" with real row numbers; rows that do not fit print on an
  attachment page (G57; `attachment.py`).
- **Warner large group and the SIIA disclosure:** AcroForm fills (`acroform.py`): Warner's No box, the typed name at
  `/Sig`, dates and Warner's detail page; a blank missing a field fails loudly (G59).
- **Signing:** DRAFT until the officer signs, then "Electronically signed (typed name) · date" (G53, G57). The
  officer's signature files the filled PDF as a protected document of kind `questionnaire` or `stop_loss`; signed
  downloads and the RFP use that file, so a reopen never loses what was attested (G135). Typed names are the default
  (OQ54).
- **What prints:** stored, approved values only (G136; L.6; OQ85); hidden answers never print (G19).
- **The check** before a download: "Before you download: …" with Fix links and "Download anyway ⬇"; a stale `ack`
  answers 409 (G64–G66); "Check the form ▸" shows the PDF beside the problems (G67).
- Names `<slug>-<export_slug>.pdf` come from the server and the browser keeps them (G62). Downloads are logged, since
  `questionnaire` and `stop_loss` are PHI kinds (G63).
- A start-up check compares each bundled blank's SHA-256 with its layout, so a reissued form fails loudly (G125); the
  Florida Blue field data is a generated module (G124).

### 9.13 Stop-loss analysis workbook (`proposals/workbook/stop_loss_build.py`)

The old five-tab workbook, Stephanie's analysis generated (J166, F106; slice 36): In-Force Snapshot, Option Comparison,
Binding Notes, Glossary and FIE Rates, with live formulas whose results come from `quotes/math/stop_loss.py`.
- It is the client document for self-funded and level-funded deals (OQ43). It refuses a line with two or more current
  contracts (F106).
- Binding Notes read the SIIA disclosure's state through `quotes.providers.disclosure_state` (G117; O.6 #47).
- **Lasers (OQ104's default):** laser liability prints as amounts; the laser rows (`sl_lasers`, with
  claimant ids or initials) never print, unlike the old sheet.
- Written through `xlsx_safe`; checked by the Recalc and Fidelity lanes on GD5 (Q.4).
- Built in slice 36 in the proposals app, where the sheet model and writer live (quotes cannot import to its right),
  from quotes' client-safe read (`quotes/selectors/stop_loss_file.py`); served at quotes' path
  `plans/stop-loss/workbook/`. The old geometry, formulas, words and look; laser rows named "Laser 1", "Laser 2",
  one claimant per row across options; a number linked from the snapshot reads `=IF(ref="","",ref)`; the grammar
  gained N and COUNT, and COUNTIF's ">0" became a sum of IF(N(…)>0,1,0). The file keeps the old name
  (`<client-slug>-stop-loss-analysis.xlsx`) and writes no `downloaded` row (no claimant prints, as J97).

### 9.14 Advisor board export (`quotes/board_export.py`)

"⤓ Export" writes the board as it stands: the line, the plans and the columns on screen, through the plan template's
exporter (F93, J167; slice 9). It is staff-only and equals the screen. Like the plan template, a download that prints
`sl_lasers` writes a `downloaded` row.

### 9.15 Commission files (`commission/exports.py`, `commission/disclosure.py`)

- **Book export** (H52; slice 49): a Book sheet with the old 16 columns and a Totals sheet, with the Book's filters and
  the viewer's tier (`visible_shares`), through `xlsx_safe`.
- **By person export** (H68; slice 49): a pivot plus a sheet per person; the own tier sees only its own row.
- **CAA comp disclosure** (H108; slice 49): a PDF per plan year for medical, dental and vision, for the all tier only,
  from "Comp disclosure ⤓" on the Commission tab's booked block, with the old tooltip "send it only inside the close-out
  packet". The back office sends it (OQ76). Built in slice 49 per deal (`deals/{id}/commission/disclosure.pdf`, from its
  live medical, dental and vision records), drawn with reportlab in `commission/disclosure_pdf.py` (the old template's
  words, the agency's name from `AgencySettings`): there is no `deals/pdfkit.py`, and commission sits left of the PDF
  kits in `rfp` and `proposals`. The per-plan-year disclosure waits with the client statement (H103, H105; OQ6).
- No client file carries commission (H125).

---

## 10. AI and Work with Claude

Claude reads carrier quotes, SBCs and client files into values that keep their page or cell, and works over the deal
from the Work with Claude drawer (needs 1–3). Part D is the design and Part E the review station; O.3.3 and O.3.5 win
where they differ. AI speeds up data entry and checking; people decide what reaches the client. Without a key, every
AI door hides and the manual flow is unchanged (D26). Slices 16–24 build it; 37, 51, 52, 59 and 66 add to it.

### 10.1 Principles

- **Who lands what** (D71; O.3.3; OQ4). A quote read started by an admin or a `claude_direct` person lands at once, with
  Undo, unless the table is locked, the deal is lost, the read is partial, the file is an SBC or the read removes a
  plan; then it waits. Everyone else's reads wait as a staged change set. Intake, census and questionnaire reads always
  wait in their owner's review, and SBC reads always wait (OQ33). Reads started from the Documents' ↻ Re-read… panel
  always wait too (E75: "nothing on the deal changes until you use it"). **Built in slice 20:** `ai/land.py` decides
  (pure); the `read` kind's land hook (`ai.services.landing.on_finish`) lands the read as proposed through the reader's
  `apply`, exactly as "Use this scan ▸" would, inside the transaction that ends the job (`ai/running.py`), so a job the
  reaper took meanwhile takes its landing back; a landing the owner refuses waits with the refusal's sentence. The
  landed job is `land: auto`, `resolution: applied`, with `landed.auto`, and ↶ Undo this run works as for a person's.
- **A person applies every re-check**, and Claude never confirms its own value (D-119; OQ28). A value needs review when
  Claude doubted it or the locator could not find it: `review_rules.open_warning`, the old meaning (OQ28, answered
  2026-11-11: "only the values claude doubted need approval, but even unapproved values shouldn't stop the user from
  continuing. just give a little flag saying X number of things should be reviewed"). Nothing waits on a review: the
  Advisor's flags chip, its review strip and the station's strip say "N AI values to review", and that is all.
- **The person loading a document says what it is** (document role: current plans, renewal, alternates). The reader
  uses that role; it never decides by itself that a plan is current.
- **Every value keeps its place.** A landed value gets `origin: ai` with its document, page or cell, the printed line,
  the locator's result and any doubt (O.3.1). A person typing over it keeps the link to the file (E66, F141).
- **Reads never move plans.** New plans append in the quote's reading order, and the read stores the quote's printed
  layout (D62, F138; need 3).
- **Writes go through the owners.** `ai` holds jobs and change sets and never writes plans, answers or people. Each
  owner applies a change set through its services, in one transaction with one Activity row (D72; O.3.2).
- **Every run has a cost cap, and every deal a budget** (§10.3).
- **Member data** follows §10.8.
- Tests never reach the network (§12).

### 10.2 The `ai` app and the worker

`ai` sits after `documents` and imports only accounts, deals and documents (O.1; D.6). Owners register into it from
`AppConfig.ready()`.
- **Models** (O.2): `DealAi` (the table lock, the deal's budget and the next chat number; created on the first write),
  `Chat` (number, title, tab, last used by and at), `ChatMessage` (role, text, author, job), `CarrierNote` (carrier,
  text; Django admin, D119) and `Job`. Client guidance is intake's `client_guidance` answer, not a `DealAi` field
  (O.6 #16).
- **Jobs** (O.3.3, with D.6's fields):
  - kinds `read`, `turn`, `recheck`, `rank`, `locate` and `issue`; a `target` names the reader (quotes, sbc, intake,
    census, questionnaire);
  - lanes `work` (read, recheck, rank), `chat` (turn) and `system` (locate, issue), so a locate or an Issue never waits
    behind a long read; a partial unique constraint allows one running job per deal and lane;
  - `steps` hold at most 50 short lines, never file text or names; `result` holds the change set; `created_by` is null
    for a portal upload;
  - firm-level jobs with no deal (statement reads) wait with the ledger (OQ6).
- **Registry** (O.3.3): readers `{target, kinds, prompt, schema, build_changes, must_review, apply, undo, discard,
  can_access, on_client_upload}` from quotes, intake, census and questionnaire; the job kinds `rank` (quotes) and
  `issue` (proposals); context providers from quotes, intake, census (counts only), questionnaire, proposals and
  review; strict chat tools (§10.6); locate hooks from quotes, intake and questionnaire.
- **Worker** (`manage.py run_worker`, its own Compose service `worker`, same image; D105; slice 16):
  - it claims the oldest queued job whose deal and lane are free, with `select_for_update(skip_locked=True)`; oldest is
    first started, by id, never `created_at` (a clock that steps back under load would put a later job first);
  - it beats on stream events and between calls, never on a timer; each call has a read timeout and a wall-clock cap;
  - Stop aborts the stream and keeps the finished ranges;
  - a reaper takes jobs silent for 10 minutes, re-checking the heartbeat in its update;
  - tests run jobs inline with a fake client (`ai/testing.py`).
- **The browser** polls one endpoint, `GET deals/{id}/ai/`, through `useAiState`: every 2 s, slowing to 10 s while jobs
  run. A finished job refetches the areas it landed in and flashes its plans (O.4; D35). The state GET writes nothing.
  The endpoints are D.6's (§7).
- **Built in slice 16:** the models, the registry, `services.jobs` (start, which returns the same job already queued or
  running instead of a second; cancel), the worker (`claim`, `reap`, the loop) and its Compose service, the `locate`
  job, `check_sources`, the four endpoints of §7.5 and `src/api/ai.js` (`useAiState`, `useStartLocate`,
  `useStopJob`). `useAiState` polls only while a job is queued or running: 2 s for its first 20 s, then a second
  slower every 10 s, to 10 s (`api/aiPolling.js`); a job started in the page lands even if it finished between polls.
  Beats come from the work (each page read, each file), written at most once a second; Stop and the reaper are seen at
  the next beat.

### 10.3 The Claude client, models and budgets

- **`ai/client.py`** is the only module that imports `anthropic` (D.6).
  - Messages API only: no beta features, no Files API, no token counting; files go base64 in each request (OQ29).
  - `extract()` makes one streamed structured-output call (`output_config.format`, 128k `max_tokens`). `converse()`
    runs one streamed round with strict tools and `tool_choice: auto`. There are no forced tool calls (O.3.3), which
    retires v1.1's `call_tool`.
  - Thinking is adaptive, and effort is set per kind from settings (chat low; reads and checks high until the trial).
    Prompts, schemas and tools are byte-identical across deals, so they cache; a turn adds a second cache breakpoint
    after its files.
  - Errors: `AccountError` (the run stops), `OverLimit`, `Truncated` (the range halves) and `Refused` (one retry on the
    other of Sonnet 5.5 and Opus 5.5; server-side fallbacks are a beta, so none). Cost is recorded per call from the
    model that answered, priced by `ai/pricing.py`.
- **Models** (D9, D91; OQ31): one picker. Opus 5.5 is for admins and direct people, and scanned PDFs read on it when
  allowed. Reads never run on Haiku 5.5, which serves chat and edits only. The golden-deal trial sets the default
  model, read effort and caps (OQ31; the Eval lane's first run is in slice 18, Q.6).
- **Budgets** (`ai/budget.py`; D53, D99, D100):
  - an estimate from pages and numbers before a run, without an API call;
  - a run cap (`AI_READ_LIMIT_USD`, 3) and a deal budget (`AI_DEAL_BUDGET_USD`, 25), both on real usage; past the cap
    a run keeps what it finished and waits;
  - admins and direct people may **Run anyway** (D24); only admins change a deal's budget (OQ34);
  - deal spend is one sum over `Job.cost_usd` (D8).
- **Built in slice 18:** `ai/client.py` (`request`, `check`, the live transport with read timeout and wall-clock cap,
  `install` for the fake; errors `NoKey`, `AccountError`, `CallFailed`, `Truncated`, `Refused`; `OverLimit` is
  `ai/budget.py`'s), `ai/pricing.py`, `ai/budget.py` (the estimate, the run cap, the deal budget and the total cap over
  the `Call` ledger, §3.5), `ai/calls.py` (each call reserved, sent, settled — Stop included). The one deviation: there
  is no single `extract()` call site in a job, because up to four ranges stream at once in threads that only talk to
  Claude while the job's own thread reserves, settles and beats (`calls.Runner`); `calls.extract` is the one-thread
  form the Eval lane uses. A refusal retries once on the other of Sonnet 5.5 and Opus 5.5 only for admins and direct
  people (D91). Every call's real usage and cost is recorded per call; `manage.py ai_spend` adds them up. Since slice
  24 a call that was sent but ended without its usage (Stop or cancel mid-stream, an error after sending) is charged
  conservatively, never at $0: what the stream reported before it ended, else its input as estimated before sending,
  else its whole reservation (`calls.charged_usage`); a call still queued at Stop costs nothing. A chat turn is
  checked against the deal's budget before its first call (`budget.check_turn`) and stops calling at the run cap.

### 10.4 Readers

Every reader runs through `ai/reading.py` (D.6). Files go in upload order (by id, never the clock: a later file wins,
D57), up to four page ranges at once: screen →
ranges (`ranges.py`) → an estimate that stops at the cap → content (PDF ranges with a page map, sheets as A1 grids,
images) → `extract`, halving on `Truncated` → locate → merge → `build_changes` → checks → an Opus step-up on a hard
finding, when allowed → landing (§10.5).

| Reader | What it does | Items | Slice |
|---|---|---|---|
| Quotes and renewals | Plans with carrier, name, number, codes, roles and links, and rows in printed order; matches existing plans and never duplicates a current plan; renewal packets; which plan a quote replaces, unticked when unsure; printed tier counts proposed unticked, never a plan's enrollment (OQ30); the printed layout, `QuoteLayout` | D46–D67, D115–D117, F138, F143 | 18, 19, 21 |
| SBC | Flags design values that differ from the plan's; never a new plan, except an unticked design-only plan when nothing matches; always reviewed (OQ33) | D38, D47 | 22 |
| Re-check | One check mode for flags and the Overview's double-check: agree, fix or not found; a person applies it | D93, E77, M92, M93 | 22, 64 |
| Rank | Stars 5–8 plans with reasons, within `room()`, from the client guidance; refused without guidance; curated lines skipped | D96, D97, F111 | 37 |
| Census mapping assist | Proposes targets for the mapping dialog from column shapes (below) | D109 | 51 |
| Census roster | A PDF roster becomes a staged `CensusImport` for the Census tab | D110, C19 | 51 |
| Intake prefill | Company documents become intake answers, staged in Intake's review | D112, B40 | 51 |
| Questionnaire | A filled form, staged slot by slot; never a signed form | D113, G99–G102 | 52 |
| Client uploads | A client's census and intake files are read and staged; paper questionnaires are only filed (OQ89) | D44, L111 | 59 |

- **SBC values:** like a quote read, only plan-design fields are kept; any rate it returns is dropped.
- **Census mapping assist**: when the offline mapping (C14) leaves columns unmapped or low,
  sends only the headers and each column's value **shapes** — never values: "9 digits", "a date", "2 letters",
  "a number", "text" — which is all a mapping needs. Names, SSNs and birth dates never reach the model. It proposes
  targets for the mapping dialog to show.
- The census, intake and questionnaire readers register only behind the PHI gate (§10.8). Reading commission
  statements waits with the ledger (H82–H91; OQ6).
- **Built in slice 51** (C11, C19, D29, D41, D42, D109, D110, D112, D134, B39, B40):
  - **The PHI-gate switch** (`AI_PHI_READERS`, slice 47): the census and intake readers and intake's chat tool register
    only while it is on; the read door then answers 400 with `ai.services.jobs.PHI_OFF` ("Claude reads census, intake
    and questionnaire files only once the PHI gate is passed …"), a send leaves their files filed, and `/api/meta/`'s
    `ai` says `phi_readers` / `phi_off` so the Census tab's door shows greyed with the reason.
  - **The census reader** (`census/reader/`, target `census`, kind `census`, always waits): a spreadsheet never goes to
    Claude (the Reader's new `local` hook): the importer reads it, the offline mapper proposes its columns (starting
    from a person's own choices when the same file already waits) and the mapping assist (`census/reader/assist.py`)
    proposes the columns left unmapped or under 0.85 from the headers and each column's counted shapes ("9 digits with
    dashes or spaces (98 of 100)", "a date", "2 letters", "a word", "text, 2 words", "an amount"); one call, 16k
    `max_tokens`, recorded in the ledger against the job; it may use only census columns no other column holds, never
    replaces a confident one, and every proposal is at most 0.80 (Check in the dialog, `assist: true`). PDF pages and
    pictures are read whole by Claude (the member-data screen never leaves a roster's pages out): every person in
    printed order, `dependent`, the `employee` a dependent is printed under, and `values [{key, value, page,
    unsure}]`; `merge.py` keeps a person read twice once (SSN, else name and birth date, same role, same file) and
    puts each dependent under its printed employee, else the employee above (C19; old `census_people`, except that a
    dependent with no employee stays a dependent, `dep_orphan`). `changes.py` stages the import (`services.reads`) and
    the job's change set is only a pointer: one item `{op: census_import, import, read, people, employees,
    dependents, columns, assisted}` with counts-only findings (D29, D.6). The Census tab reviews it (§8.10); its Apply
    also uses the read (`ai.services.landing.owner_applied`) and its Discard discards it (`owner_discarded`), and the
    read's own "Use this scan" / Discard go through the import (`reader_apply`, `reader_discard`). ↶ Undo this run is
    refused for a census import (key-only rows: import the file wanted again), and its landed strip shows no Undo
    (`landed.undo: false`). Activity (area census, actor Claude): "Claude read a census file: 6 people (3 dependents)"
    or "Mapped a census file: 9 of 10 columns, 3 proposed by Claude from the column shapes".
  - **The intake reader** (`intake/reader/`, target `intake`, kinds `other`, `invoice`, `plan_doc`, `form_5500`;
    always waits; a send reaches it only from the Intake tab, `ai.kinds.OWN_TAB_ONLY`, the old app's rule): answers,
    coverage in force and contacts (the old `record_intake`); the first reading of an answer wins and a different
    later one flags it. Its change set lists `answer` items (cleaned by the form's one cleaner; equal answers not
    listed, D60; an answer typed, relayed, the client's or approved arrives unticked and says why, D61/B39; one Claude
    was unsure of arrives unticked), `coverage` items (a line the deal lacks, or an existing line's blanks; carrier
    and funding left out where current plans own them) and `contact` items (new by email, else name). "Use this
    scan" (`intake/services/read_apply.py`): contacts through deals' contact service, then the answers (origin `ai`
    with file, page or cell, `read_value` and `low`; the effective date through its door) and coverage lines in one
    intake row (action `read`); ↶ Undo this run reverts that row through intake's reverter and removes the contacts it
    added unless edited since. The change set is emptied once used (the Reader's `empties`, D74).
  - **Intake in a chat (B39):** `propose_intake_changes` (answers with `dictated`, coverage lines) and the `<intake>`
    context on the Intake tab (answers, needed blanks, coverage in force, the form's own checks); a dictated value lands
    as the producer's typed edit, any other as Claude's (`ai`, flagged to check), an answer a person stands behind is
    never written over unless the producer said it; they land through intake's turn owner as Claude's own row, with
    ↶ Undo this run. Contacts stay with the reader (a contact's rows keep keys only, so a chat's Undo could not take
    one back). The tool is sent without `strict` (past the API's grammar limit, slice 37: adding it as a strict tool
    made the API refuse every turn), so its whole input is checked in code before anything is staged: an unknown
    field, a part that is not a list of objects, an object's own extra fields, a missing key, an unknown line or
    funding are refused in a sentence Claude can act on.
- **Built in slice 52** (D113, G99–G102, G106, G107, G109): **the questionnaire reader** (`questionnaire/reader/`,
  target `questionnaire`, kinds `questionnaire` and `stop_loss`; always waits; behind the PHI-gate switch with its chat
  context). A file's kind decides the form it fills: the deal's medical form (the one the checklist arms, else the one
  most recently worked on) or its stop-loss disclosure (`reader/which.py`, `forms.FILE_KIND`). The `local` hook refuses
  before any call when the deal has no form for the file or the form is signed (G99: "… is signed, so Claude reads
  nothing into it"), and lets Claude see the pages whole (a filled form is member data by design, like a roster). One
  cached prompt carries the three forms' questions (key, label, type, the options or where the dependent pickers' are
  listed, the condition tables in the pickers' own labels) and one small schema for every form: `answers [{key, value,
  page, unsure}]` and `rows [{block, page, values [{key, value, unsure}]}]`, the keys enums of every form's fields (one
  property per field would not fit the grammar); the per-call note names the deal's form for the file, never the file.
  `merge.py` (the old `_merge_qform`): files in upload order, the first reading of an answer wins and a different later
  one is doubted, rows appended up to the section's maximum (more are counted), each answer's own page when it is in
  its range. `clean.py` puts what was read through the form's own `clean_batch` (a picker's answer matched to its
  option: case and punctuation aside, a printed name to its code, a SIC code to its digits; the SIC pair filled);
  what the form will not take is counted, never named. `changes.py` stages it as a `StagedRead` per form (§6.8;
  Activity "Claude read a filled Florida Blue 51+: 24 answers, 3 rows, waiting for review", counts only) and the change
  set only points at it: `items [{id: 'form:<key>', op: questionnaire_read, read, form, label, tick, signed, answers,
  rows, conflicts}]`; a read that finds nothing fails ("No questionnaire answers could be read from this file."), one
  that matches the form waits for no one (D60), and a form signed while Claude read is staged saying so.
  `reader/review.py` works the entries out against the form as it stands, on every look and again at Use: an answer
  may fill a blank, replace the live prefill or an unconfirmed read; one a person stands behind (typed, relayed, the
  client's waiting or approved, confirmed prefill, approved) is a listed conflict and never written; one Claude
  doubted arrives unticked. A row updates the rows an earlier read of the same file left untouched (G100), else fills
  the Advisor's started plan row that shares a value, else an empty row, else adds one; the answer that opens a section
  (Q16 for the conditions) comes with its rows. "Use this scan ▸" / "Apply N selected ▸" (`services/reads.py`, Deal →
  job → the form's row; a signed form refuses, 409) lands values as `ai` with file, page, `read_value` and `low`, rows
  the read adds as its own (`origin ai`, `doc`), one before/after Activity row and one keys-only row for sensitive
  answers (rule 4), neither revertible from Change history: ↶ Undo this run (`services/read_undo.py`) puts every
  answer back from the staged read's `landed` (refused after a later edit, `can_force`; refused on a signed form) and
  takes off the rows it added unless written into since. The `<questionnaire>` chat context (G106) gives each form's
  progress, signature and answers with where they came from, sensitive slots only as answered or blank. G107: the job
  log says "Finding the form each file fills", "Reading pages 1–3" and "Read Florida Blue 51+: 25 answers, 5 rows, ready
  for review". G109: `manage.py questionnaire_sample` (dev) stamps a synthetic filled Florida Blue 51+ onto the bundled
  blank with its key, and `--score` counts a waiting read against it.
- **Built in slice 18:** `ai/reading.py` (the job), `ai/read_files.py` (files in upload order, `FileIn`, the plan per
  file), `ai/ranges.py` (header-only pages always out, screened pages out only with the switch, a range under a quarter
  of `max_tokens`, halving), `ai/content.py`, `ai/codes.py` (F143's parser, left of quotes), and the quote reader in
  `quotes/reader/`: `prompt.py` (one cached prompt built from the field list; the per-call note says what the file was
  filed as, never its name), `schema.py` (row-major: `lines[{line, columns[{col, carrier, plan_name, plan_number, codes,
  side: current|renewal|quote, renews_col, replaces, unsure}], rows[{label, key|'', cells[{col, value, page, cell,
  unsure}]}], counts[{col|-1, tier, count, page}]}]`), `merge.py` (D57: one plan across ranges and files by codes,
  number halves or carrier and name; a later file wins, with a finding), `match.py` (D59: by `read_ref`, plan-number
  half, strong code, then the one plan of that carrier and name; same line and role; never a priced version),
  `rules.py` (D58, D61: house formats, the line's fields, who wins, doubt, E93's member-data scrub of the printed
  label), `changes.py` and `counts.py` (the change set: reading order, D117's current-plan rule, renewals' links,
  D115's replaces, OQ30's counts, D56's lines, `kept`), `locating.py` (E79: every value found in its file before
  review). The read door is `POST deals/{id}/ai/reads/` (D39). Not built here: `read_checks` beyond the findings the
  rules make (D88, slice 24), the Opus step-up on a hard finding (D76; built in slice 20: `reading.steps_up` and
  `step_up`, the whole read again on Opus 5.5 for an admin or a direct person, its read replacing the first, the cost
  cap counting both), carrier notes (D119, slice 24). **Built in slice 24:** `quotes/read_checks.py` (D88, the old
  `plan_checks.verify` over a change set) runs in `build_changes`: hard findings — a tier rate printed nowhere in its
  file (unless it has image pages), a new plan with no rates on a tier-rated line, two plans of one line and role
  sharing a code, a current plan left without its renewal on a line with renewals — step the read up (D76 is live);
  soft ones (values not found, tier order, printed counts × rates against the printed premium) are listed. Each read's
  per-call note carries its file's carrier note (`ai/carrier_notes.py`).
- **Built in slice 22:** the SBC reader (`quotes/reader/sbc.py`, `sbc_prompt.py`; the old phase 10e rules): the quote
  reader's row-major answer, read with the SBC prompt (one plan's design, never a rate, the coverage examples skipped);
  values outside the medical design fields are dropped in code (rates, contributions, level-funded and stop-loss, said
  in a finding). Its plan goes to the plan "Attach SBC…" named (`params.plan`), else to the plans of the first tier
  that names them — plan-number half, strong code, carrier and name — over every role but never a priced version or a
  copy; a current plan and its renewal named alike both take it; several unrelated plans, or none, make an unticked
  design-only plan (an alternate). The SBC beats a quote: a value a quote read put on the plan that the SBC prints
  differently is replaced and flagged (`low` names both figures; listed as the change set's `conflicts`, the card's
  "Where the SBC and the quote disagree"), typed, imported and approved values are left alone (D61), and a quote read
  leaves a value read from one of the deal's SBCs alone (`rules.decide`'s `sbc_docs`, with a finding). The reader is
  `must_review` (OQ33), its change set lands through `read_apply` (no printed table) and ↶ Undo this run. The re-check
  (`ai/recheck.py`, `recheck_prompt.py`; the old `flag_check` and `scan_audit.audit_claims`): the owner's checker
  (`registry.checkers`; quotes' `recheck.py`) names the open warnings with a file, Claude reads each file only on the
  pages its claims name (a value with no page rides a PDF of at most 30 pages, else it is listed as not checked), 40
  claims a call, and the best verdict across calls wins; formatting is no difference. The change set has one item per
  value: `confirm` (Claude agrees, ticked) and `set_values` (a fix, the page's value cleaned as typed; unticked when
  Claude was unsure; frozen on a sold plan), and `unverified` (not found, still flagged). A person applies it
  (`quotes/services/recheck_apply.py`): fixes land as a read's values (`read_plans.Landing`, area `quote_read`, action
  `recheck`), approvals through `mark_values(..., via='recheck')` as the person who pressed Apply (E77); ↶ Undo this run
  reverts both. `quotes/split.py` (D116): two plans of one carrier, line and side are halves of one plan when their
  numbers differ only in a last digit one apart (05182 / 05183) or one prices employees only and the other the
  dependent tiers; a read's fresh halves stay two plans (a finding says so); a deal's one "A / B" plan takes both
  halves of a read (each tier's rate from the half that prints it; a disagreement keeps the employee-only half's, said).
  Not built: the reader's `combine` op (O.6 #32) — fresh halves are never combined (D-219), and two plans that are one
  are joined by Claude's `merge_plans` or by hand.

### 10.5 Landing, review and Undo

- **The change set** (`Job.result`) has one shape for every target and both review cards: items with an op, a tick
  and their values (old and new, page or cell, locator state, doubt), plus findings, failed parts and left-out pages
  (D.6, with `line` on each value, O.3.3). Census, intake and questionnaire jobs hold only a pointer, emptied after
  apply (D74).
- **Review cards** (D28, D31): "Review this scan", the field-group diff with its chips, the renews and replaces selects,
  then **Use this scan ▸**, **Apply N selected ▸** or **Discard**. Stale and unsure values arrive unticked. Typed,
  imported, client and confirmed values are "Left alone" (D61), and an unchanged value writes nothing (D60).
- **Applying** (`quotes/read_apply.py`; D72): one transaction that locks the deal and the line's plans, numbers new
  plans in reading order, writes `QuoteLayout` and records one Activity row with before and after. The first landed
  quote read moves the deal to Quoting (D75; N.1).
- **Undo this run** (D73) reverts the job's Activity row. It checks each value against the stored "after"; when
  something changed since, it says so and offers **Undo anyway**. A plan the run created stays when someone starred,
  recommended, sold, packaged, linked or typed into it. A census import is undone through its `CensusImport`.
- **Try again** with the next model, and **Check again** (D76). **Built in slice 20:** `ai.services.retry` (`POST
  ai/jobs/{id}/retry/`): the same files on the next model up the ladder the person may use (Sonnet 5.5 → Opus 5.5 for
  admins and direct people; the same model for others), undoing a used read first and discarding a waiting one; the
  landed strip offers "↻ Try again with Opus 5.5", a failed read "↻ Try again", and an over-budget read "Run anyway"
  (D24) through the same door. Check again is slice 22's re-check.
- **Built in slice 19:** `quotes/services/read_apply.py` (D72), `read_plans.py` (the plans and values) and
  `quotes/reader/choice.py` (what the person chose): **Use this scan ▸** sends nothing and lands the read as proposed
  (ticked items and values; never a printed count, an unsure link or a "Which current plan?" item); once a tick
  changes, the same button reads **Apply N selected ▸** and sends `select` (item ids, `"<item>:<key>"` for a value
  that arrived unticked, `"<item>:replaces"`) and `picks` (`{item: plan id | "new" | "alternate"}`, D117). One
  transaction locks the Deal, the job, then the lines' plans. **Deviation from D72's "one Activity row":** a landing
  writes one row per owner, all in that transaction — the plans and values (area `quote_read`, action `read`, a
  `plan.read_ref` key on each plan the read made), the ticked printed counts through `set_enrollment` (area
  `enrollment`, D67: they become typed counts) and lines added through Intake's `set_intent` (D56) — and the job keeps
  their ids (`result.landed.activity_ids`), so Undo reverts them together, newest first. A value lands only while it is
  still what the person saw; a plan or current plan the deal gained since is not made again. The deal advances to
  Quoting when anything landed (D75); a read that matches the deal writes nothing (D60), and its printed counts are not
  proposed again once held. **Undo this run** (`quotes/revert_read.py`, D73) puts back the values with the source
  entries they replaced (kept in `landed.sources`), takes off the plans the read made unless someone starred,
  recommended, sold, packaged, linked, typed into or otherwise changed them since (they stay, named), and refuses with
  `can_force` when a value or another owner's row changed since; **Undo anyway** leaves those and puts back the rest.
  The state's `news` lists reads used in the last 15 minutes (`{type: 'landed', job_id, documents, summary, skipped,
  activity_id, at}`) for the "✓ Used Claude's read — … ↶ Undo this run" strip. Documents gains ↻ Re-read… and the old
  Re-read panel (E75, every kind the quote reader reads, E76), the staged banner in Scanned data (E78) and ↗ on staged
  values (E78's pin). Applying on a lost deal is a person's internal edit and passes (O.3.7; the old app refused it).
- **Built in slice 21:** the landing also keeps the file's printed tables (`QuoteLayout`, D66; §6.7), in the
  `quote_read` row, and the PDFs' printed page numbers (E94, `Document.page_labels`); a read that changes only the
  table records "Used Claude's read: the file's printed table" and does not move the stage. Undo puts the table back.
- **Built in slice 18:** every read waits (`land: staged`); the staged card shows on Documents under the file it read
  (`deal/claude/ReadReviews` with `ReviewCard`, the quote body `deal/advisor/claude/QuoteReview`, `PlanDiff`,
  `ChangeList`): Discard works (D74); "Use this scan ▸" and "Apply N selected ▸" show, disabled, until slice 19's
  `read_apply`.
- **Review never gates** (OQ28): a landed value Claude doubted, or one the locator cannot find, is counted and
  coloured until a person approves or ignores it; Issue, the exports, the Advisor's edits and every other door go ahead
  with values still to review.

### 10.6 Work with Claude: chats and tools

- **Turns** (D77–D92; slice 24) run in the chat lane, so a question never waits behind a read. A turn sees the last 30
  messages, each app's context (never stored; the census as counts only), at most 3 attached files and the plan table
  capped at 120k characters, and runs up to 8 streamed rounds (D78, D79, D82, D83).
- **Tools** are strict and validated in code (D81; O.3.3): `read_documents`, `read_document`, `propose_changes`,
  `check_values`, `rank_plans`, `set_board`, `merge_plans`, `clear_line`, `pair_plans`, `add_lines`,
  `update_client_guidance`, `set_table_note` and `set_rows`.
  - Every write stages through `propose_changes` and lands by the rule of §10.1, with Undo. Dictated values get
    `origin: typed` (D85). Removing a sold or recommended plan is refused (D86).
  - `set_board` sets the board's filters and picks and writes nothing (D80).
- **Client guidance** (D98, F111): intake's `client_guidance` answer, at most 4,000 characters, written by the drawer
  through intake. Rank reads it; no client file prints it (J.4).
- **Carrier notes** (D119): an admin's note per carrier, added to each call outside the cache, in place of lessons.
- **Deferred:** Claude Unleashed (D101, F4), lessons (D102) and saved readers (D103), per OQ4; census and questionnaire
  turn tools (D111, G103); earlier-year chats (D11).
- **Built in slice 24:** `ai/turn.py` (the `turn` kind: history, context, files, up to 8 rounds, the reply as the
  chat's next message), `history.py`, `turn_prompt.py` (the cached system prompt; the context: `<deal>`,
  `<documents>`, each provider, `<carrier-notes>`, whether changes land), `turn_files.py` (≤ 3 attached files whole,
  ≤ 100 pages; `read_document`), `turn_state.py` (the change set), `tools.py` (strict specs in a fixed order; inputs
  parsed from text too), `services/chats.py`, `services/turns.py` (the land hook, apply, Undo through each owner's
  reverter, Run anyway and Try again), `services/deal_ai.py` (lock, budget, their reverter), `carrier_notes.py`.
  Owners register: quotes `set_board`, `propose_changes` (set_values, remove_plan), `clear_line`, the `<plans>` and
  `<board>` context (each plan's monthly total from the Advisor's own figures, F114) and the turn owner
  (`quotes/turn/`); intake `update_client_guidance` and `<guidance>` (`intake/turn.py`). The browser applies a turn's
  board patch through `deal/shared/boardBridge.js` (F108): the Advisor's `useBoardBridge` sets the line and the
  config in the URL, and Claude's pick (F25) shows as its chip. Not built here: `read_documents`, `check_values`,
  `rank_plans`, `merge_plans`, `pair_plans`, `add_lines`, `set_table_note`, `set_rows` (slices 22, 37 and the
  builder's; slice 22 built `merge_plans` — the one merge service, F142, refusing the two halves of one plan, D-219 —
  and `check_values`, which starts ✦ Ask Claude to re-check in a job of its own that waits for the producer); creating a plan from a chat (Claude adds plans by reading their file). **Decision (slice 24):** a turn's
  changes land at once for an admin or a direct person (§2's `claude_direct`: "chat changes land at once, with Undo"),
  removals included — the person asked for them, and sold or recommended plans are refused when proposed (D86) —
  unless the table is locked or the deal lost; everyone else's wait in the chat for "Apply N selected ▸"
  (`land.decide_turn`). §10.1's "a read that removes a plan waits" stays a rule for reads.
- **Built in slice 37:** ⚖ Rank plans (D6, D36, D96, D97, F111, OQ44) and the tools `pair_plans`, `rank_plans`,
  `set_table_note` and `set_rows` (J160, J161, D120). quotes registers the `rank` job kind (`quotes/rank/`): the door
  `deals/{id}/ai/rank/` and Claude's `rank_plans` start one job per line (Rank needs a line, F111) that asks Claude
  once — intake's guidance block, the quoted plans of the line (only those a filtered board shows) as compact JSON
  with the Advisor's own monthly totals, and how many fit — for 5–8 picks with a reason each (structured output); its
  landing, in the job's ending transaction, writes them through the star rule (`quotes.services.rank.rank`: the ★'s
  auto-link, within `room()`, a pick already starred for the same reason left as it is) as one Claude row with ↶ Undo
  this run on the strip (D36: the rank's news). A locked table refuses the door and fails a landing. A quote read that
  lands (by itself or used) queues a rank, on commit, for each line it added quotes to, when the deal has guidance and
  nobody has starred, sold or recommended on that line (D96's curated lines). `pair_plans` (quotes) stages a pair or a
  split through the pair service (§5.4); proposals registers `set_table_note` and `set_rows` (`proposals/turn.py`,
  through `set_config(by_claude=True)`, Claude's own Activity row) and the `<proposal>` context (each line's note and
  rows; on the Proposal tab the rows a line can print). Each lands like every turn item, with ↶ Undo this run.
  **The API's grammar limit:** the API compiles every strict tool of a request into one grammar and refuses one too
  large ("reduce the number of strict tools"); slice 24's seven tools are at that edge (`set_board`'s thirteen optional
  fields the most of it), so `ai/tools.py` sends only those seven (`STRICT`) with `strict: true` and every later tool
  without it — each is validated again in code, as D81 asks of every tool.

### 10.7 The Documents review station

Part E (E.6); the screens are §8.16.
- **Each owner serves its own values.** Every value owner serves `GET …/sources/?documents=&bucket=&page=` (rows,
  bucket counts and quality, 200 a page) and `POST …/marks/`; `documents` has no registry (O.3.1; E.6). The station's
  grid reads the Advisor's own comparison, so arriving from the Advisor is instant (E36).
- **One set of pure rules,** `documents/review_rules.py`: `apply_mark`, `is_approved`, `open_warning`,
  `potential_error`, `shows_approval`, `review_bucket`, `origin_bucket` and `quality_headline` (O.3.1). Owners' statuses
  and stored `flags` call `open_warning`, so the Advisor, the station and the Overview agree. A changed value drops its
  mark and confirmation (`values.apply`).
- **Marks** (E85–E88): approve, ignore, needs checking and clear, by ids, plans, documents or scope; rows locked by id;
  one Activity row that never merges and holds marks, never values; Undo reverts it once. Review's `mark_document` marks
  one file across every owner in one transaction (O.6 #30; slice 64).
- **The locator** (`documents/locate/`; E81–E84) is pure and reads visible cells only. Its states are found, derived,
  weak, absent and "check by eye". It runs inside every read and in **Check this file**, a `locate` job in the system
  lane (E59; slice 16). A scanned page is never "not in the file"; browser OCR only draws (E25; slice 65; OQ98).
  Built in slice 65: a PDF page with no text layer, opened for a value on its page (page 1 when none was recorded),
  is drawn again about 2,000 px wide and read by tesseract.js in a worker in the browser (`viewer/pdfOcr.js`, files
  from our own origin, one read per page kept); the same matcher (`pdfFind`) boxes the value in what it read
  (`viewer/ocrWords.js`) and the toolbar says "✓ Located on the scanned image" (`data-find="ocr"`, never `found`). An
  image is read once the same way. Nothing is written: the locator's answer stays "check by eye" (NOCHECK
  `no_text`), so the List and the file bar say so beside the box. GD4 carries P1's scanned SBC to show it
  (`golden/scanned_sbc.py`).
  Built in slice 16 (`fold`, `query`, `pdf_text` with form answers, `pdf_index`, `sheet_cells`, `sheet_index`), the
  old rules ported, with one change: in a sheet the cell where the plan's words (column) and the field's words (row)
  cross wins, so one figure printed under two plans opens each plan's own cell (the old scored row or column alone).
  Quotes' hooks (`quotes/locate_hooks.py`) check every live plan value whose source names the file, as it stands: a
  value typed over a read one keeps its file (E66), so it is checked too, and one typed to something the file does
  not print is "not in the file" (GD1's negotiated copy). "Check this file" sits in the file's controls row with the
  old strip's progress and Stop until slice 17's List takes it; the file bar says "Not in the file" or "Check by eye"
  for the value a ↗ opened.
- **"As in the file"** shows a scanned quote's columns and printed rows from `QuoteLayout` (E42, F42; O.3.5). Built in
  slice 21: "▤ As in the file" beside ☰ List and ▦ Grid (kept per browser) on a proposal file a landed read gave a
  table; it sits beside the file as the List does, on the station's Grid with its Find, filters, Review and ✎ Edit, a
  chip per line when the file prints several.
- This replaces v1.1's "Values from this document" panel and its `confirmed_by/at`.
- **Built in slice 17:** `documents/review_rules.py` (`apply_mark`, `is_approved`, `is_dealt`, `open_warning`,
  `potential_error`, `shows_approval`, `review_bucket`, `origin_bucket`, `quality_headline`, `warning_counts`; the
  eight buckets served on `/api/meta/` as `review_buckets`); `Plan.flags` stamped on every write and checked by
  `manage.py rebuild_facts` (registered in `deals.stored_counts`); quotes' `plans/sources/` and `plans/marks/`
  (§7.8). The station's Scanned data panel shows the List (the Grid is slice 23's) with the quality headline, the file
  strip, the bucket chips, the bulk bar (which takes "Check this file"), the A, I, C, U and F keys, ↶ Undo and the
  Change history card over Activity; the Advisor shows the flags chip with its menu and the review strip. Which values need review follows OQ28: a typed or imported
  value the locator cannot find is no open warning (the old app located only what was read; only Claude's values need
  approval), but it is a potential error and the List puts it under "Not in the file". This also supersedes E.4's
  "'Not in the file' stays out of those counts": for Claude's values it is counted, as §10.1 says.

### 10.8 Member data, PHI and the BAA

- **The BAA** (2026-11-06; D.1; OQ29): only the Foobalabs key; the Messages API only, with no beta features. OQ29
  answered (2026-11-12): live data is allowed in this version (the BAA prerequisites are met), so the PHI-gate
  paperwork is done; tests, seeds and the Eval corpus stay synthetic, and no build step opens a real client's file.
- **PHI readers** (census, intake and questionnaire) register only while the PHI-gate setting is on (O.3.3).
- **Files are read whole,** as the old app reads them since D-225 (old commit 891f1b3; O.6 #45; OQ22).
  `documents/screening.py` still runs at upload and stores `Document.screen`. `ranges.py` always leaves out pages that
  carry only the running header and footer, and leaves out pages the screen flags only while `AI_MEMBER_DATA_SCREEN`
  is on (off by default).
- **Kept:** the SSN scrub; census context as counts only (D78); the mapping assist's shapes only (D109); a
  questionnaire's sensitive slots reported only as answered or blank (G106); no printed text in `QuoteLayout` for PHI
  kinds (O.3.5); no `line` on census or questionnaire values (E93). Lasers are left out of reads and typed by a person
  (D118).
- **Never** in Activity, Job steps, errors or results, chat messages or logs: census values, medical answers,
  `sl_lasers` or file names (D.4). The canaries prove it (Q.8).
- **Settings** (§3.5): `ANTHROPIC_API_KEY`, `AI_MODEL`, `AI_READ_LIMIT_USD`, `AI_DEAL_BUDGET_USD`, `AI_EFFORT_*`,
  `AI_MEMBER_DATA_SCREEN` and the PHI-gate switch. **Tests:** Q.6 (recorded reads, the synthetic corpus, request-side
  checks and the Eval lane).

---

## 11. Deployment

### 11.1 Stages

Two stages, gated by data, not by phase:

- **Staging, slice 69** (STG-1; v1.1's M2 was never built): the same build on Cloud Run and Cloud SQL, with the
  worker. It can come up any time after slice 16, so Stephanie signs in to the real thing early, and must be up before
  slice 47 and Milestone 1, whose Gates B and C run on staging (V.2). It runs the production settings
  (`ENVIRONMENT=production`, §3.5). Until the PHI gate it holds synthetic data and plan data only: the golden deals
  and their synthetic files (§12.6), plan data typed by hand, and uploads of kind `plan_template` or `proposal`.
  Claude reads only synthetic files until the key is confirmed under the BAA (OQ29).
- **Production with real member data — the PHI gate (slice 47):** BAAs with every service that stores or processes PHI
  (Google Cloud; Anthropic before Claude reads real documents, OQ29); sign-in through the firm's Microsoft 365
  accounts (MFA and offboarding live there); the controls of §3.8 in place; Daniel signs the checklist in §11.4. Real
  member data enters only after that: first Gate C's census at Milestone 2 (V.2), then the firm's own work from
  cutover (OQ100).

Everything below applies to both stages; earlier slices MUST stay compatible with it.

### 11.2 Google Cloud

- **Target:** Google Cloud Run. One container image for the web service: a Node build stage produces the SPA; the
  Python stage serves it through Django (WhiteNoise) on the same origin as the API, so the session cookie needs no
  cross-site settings (§3.8). `/api/*`, `/admin/*` and `/accounts/*` go to Django views; every other path returns the
  SPA's `index.html`. WhiteNoise also serves the files under `/static/`: the pdf.js modules, whose `.mjs` files must
  be typed as JavaScript (slice 15), and the tesseract.js files for scanned pages (slice 65; E.6). LibreOffice and
  poppler stay out of this image; they live in the tools image of the parity and Recalc lanes (§12.7).
- **Database:** Cloud SQL for PostgreSQL (version pinned explicitly), private connectivity, TLS verified. Slice 69's
  design (not connected): PostgreSQL 15, private IP only, reached by Direct VPC egress, `DB_SSLMODE=verify-ca` against
  the instance's server CA mounted from Secret Manager; `CLOUD_SQL_INSTANCE` keeps the socket path available (§3.5).
- **Files:** Cloud Storage via `django-storages`, private bucket. Downloads keep streaming through the authenticated
  endpoints; no public URLs. All code MUST use Django's storage API only (no direct filesystem paths), so local
  `MEDIA_ROOT` and Cloud Storage are interchangeable. Slice 69: `GS_BUCKET_NAME` switches it; the bucket is uniform,
  public access prevented, versioned; the storage's `url()` never makes a signed or public link (`backend/storage.py`).
- **Secrets:** Secret Manager (pinned versions). **Images:** Artifact Registry,
  `<region>-docker.pkg.dev/<project>/vantage/app:<full commit SHA>`, with a clean-up policy.
- **Migrations:** a Cloud Run Job runs `migrate` before traffic shifts (slice 69: `start.sh migrate`, which runs
  `check --deploy` first). Service and job definitions, the commands that create and connect the project (none run
  yet), the release script, the release gate and the local rehearsal live in `deploy/` (deploy/README.md).
- **Worker** (from slice 16): a separate Cloud Run worker pool, or a service with CPU always allocated and at least
  one instance, running `manage.py run_worker` from the same image (O.3.3). It runs every job lane, not only Claude's:
  reads, chats, re-checks and Rank, and also `locate` and `issue`, which builds the proposal files (slice 32). It runs
  whether or not an API key is set. Claims skip locked rows, so a second instance is safe. Slice 69 defines it as a
  service (`start.sh worker`: internal ingress, CPU always allocated, one instance), which answers Cloud Run's start-up
  probe on `$PORT` from an empty folder; a worker pool runs the same image and arguments.
- **Request and response size:** Cloud Run refuses request bodies over 32 MiB, so uploads stop at 30 MB (§3.8, OQ24).
  It also refuses a response over 32 MiB that is not streamed, so the RFP packet zip and the `.eml` drafts stream in
  chunks (K.6). Staging confirms the streaming with a large synthetic packet when slice 46 ships.
- **Logs:** request logs (Cloud Run's and gunicorn's) and error reports must exclude `/api/portal/`, `/portal/` and
  `/b/` paths (tokens are in the URL; O.4, L.6). No PHI reaches any log (§3.8); the canary scan in §11.4 checks it.
  Slice 69: the app's and gunicorn's logs drop them (§3.5), and a Cloud Logging exclusion on the `_Default` sink keeps
  Cloud Run's request logs for them, matched on the URL or the Referer, out of storage.
- Regional, contractual (BAA) and cost decisions follow the existing deployment decision record kept with the earlier
  system (Appendix C). Slice 69 follows it: region `us-east1`, budget alerts and never a spend cap, backups and
  point-in-time recovery set explicitly; Cloud SQL stays on PostgreSQL 15 to match §3.1 (that record chose 17).

### 11.3 Release gate

- **Every release:** the lanes Q.2 runs at each release are green: Fast, Front and Lint, plus Recalc from slice 27,
  and Fidelity and Look from their slices until the old app is switched off (§12.1, §12.7). `manage.py check --deploy`
  is clean, and `/api/health/` reports the new commit with zero pending migrations. WhiteNoise serves `.mjs` as
  JavaScript, and a sandboxed PDF opens in the Documents station in Chrome and Edge (E.6).
- **At each milestone** the release gate is part of Gate A (V.2), run on a fresh database with the production image:
  every lane green; Fidelity on the parity profiles of GD1, GD2, GD3 and GD5, and on GD6 for the secondary outputs;
  every MVP screen labelled in Look; Eval at its thresholds with the chosen default model; at Milestone 2, also the
  staging canary scan (§11.4). Gates B and C then run on staging (§1.5).

### 11.4 The PHI gate (slice 47)

Real member data enters only after Daniel signs this checklist (V.2's exit criteria). Slice 47 builds what the
checklist needs. It is done when staff sign in on staging with their firm accounts and the checklist is signed.

1. **BAAs** with every service that stores or processes PHI: Google Cloud, and Anthropic (the BAA of 2026-11-06 covers
   the Messages API without beta features).
2. **The Claude key:** Anthropic has confirmed in writing that tools, inline files, effort and caching are covered
   (OQ29). Until then Claude reads only synthetic files.
3. **Sign-in** goes through the firm's Microsoft 365 accounts, so MFA and offboarding live there. The sign-in lifetime
   is settled (§3.5, OQ107).
4. **The access-log check:** every download or view of a PHI file writes one `downloaded` or `viewed` row with the
   document id, never its name (§3.8).
5. **The staging canary scan:** after a scripted walk with the canary census, a log query over every log of the
   deployment finds no canary (§12.9).
6. **The controls of §3.8:** PHI never reaches logs, Activity, Job steps, error text, file names or URLs; client files
   print only `client: True` fields and nothing on J.4's never list; the token paths stay out of the logs (§11.2).
7. **The PHI-gate setting** `AI_PHI_READERS` is turned on last (§3.5). Only then do the census, intake and
   questionnaire readers register (O.3.3). The member-data screen follows OQ22.

The client portal comes after the gate (slice 54). It opens to clients only with its second factor (OQ80) and its
logging (OQ86) in place.

**Built in slice 47** (Google Cloud and Microsoft 365 not connected): the checklist itself, with each item's check,
status and the order of the last switches, is `deploy/phi-gate.md`; Daniel signs it there. Item 3 is
`accounts/oidc.py`, `firm.py` and `signin_views.py` with deploy checks E006–E008 (§3.5); item 4 is
`backend/tests/test_phi_access.py` in the Fast lane; item 5 is `deploy/canary_walk.py` and `deploy/canary_scan.py`
(`deploy/canary_scan.sh` on the dev stack); item 6 adds `manage.py scrub_key_only_values`, which rewrites Activity rows
written before `sl_lasers` became key-only (commit c543269) and runs before real data; item 7 is the
`ai.registry` gate on `AI_PHI_READERS`. Items 1 and 2 are confirmed by Daniel's answer to OQ29 (2026-11-12). The
first local scan found the census roster's search sending a name in its URL; the search now posts it
(`POST deals/{id}/census/search/`, §7.7), the page's GET ignores a `q`, and the local scan is clean. What stays open
needs staging or Daniel.

---

## 12. Testing

The earlier system's problem was not too few tests; it was that no test said "this is right". Here correctness is
shown by **golden deals** whose answer keys the benefits team has checked (§12.6) and by table-driven tests of the
pure rules in §5. Everything else is regression.

The port adds a second proof (Q.1). Screens and client files are right when they match the old app on the same
synthetic deal; every other difference is listed with the item that causes it and signed by Daniel (§12.7). Part Q
holds the details. Verification says when a slice is done (V.1) and how the MVP is accepted (V.2, §1.5).

### 12.1 Tools and layout

- pytest + pytest-django, `DJANGO_SETTINGS_MODULE=backend.settings_test`,
  `addopts = --reuse-db -q -p no:cacheprovider` (no cache folder inside the synced repository). After editing an
  existing migration, run once with `--create-db`. Today `pytest.ini` registers only `recalc` and deselects nothing.
  Slice 7 registers `perf` and adds `-m "not recalc and not perf"` to `addopts`, so both stay out of the Fast lane (a
  `-m perf` or `-m recalc` on the command line overrides it); recalc tests also skip when LibreOffice is missing.
- Tests live in `<app>/tests/test_<topic>.py`; a test's name carries the item it proves (`test_F45_pick_replaces_slot`,
  V.1 #2). Shared fixtures in the root `conftest.py`: `user`, `admin_user`, `api` (a signed-in DRF `APIClient` with
  session auth; the permission matrix checks CSRF on every write, Q.3 #3), `admin_api`, `anon_api` (built), a fixture
  for each actor of the permission matrix and the helpers of the Q.3 contracts (slice 5), and factory functions:
  `make_client`, `make_deal` (built), and one per model as its app arrives (`make_plan`, `make_document`, `make_member`,
  …).
- Factories create only the rows a test needs. No demo seeders inside tests: golden deals come only from
  root-`conftest.py` fixtures, built once per test module under `django_db_blocker` (§12.6). App tests never import
  `golden`, and tests that write use factory deals. **All data is synthetic.**
- Code that depends on the date reads it through `deals/clock.py` (`today()` in `AGENCY_TIME_ZONE`, `now()`); tests
  patch that one module. Date rules hold at 21:00 Eastern (Q.3 #7).
- Nothing leaves the machine. A socket guard (slice 3) lets tests open only the database socket, `settings_test.py`
  blanks the API key, and jobs run inline with the fake Claude client (§12.8). Test media go to a temporary folder, and
  lane outputs (images, reports, recalculated files) go outside the OneDrive-synced repository (Q.2).
- Workbook tests read the generated file back and check that it equals the sheet model (values, stored results,
  formats, merges), that every stored result equals the app's figure, and that a test-only evaluator, which
  understands only the closed function list §9.4 allows, agrees (J.6.10). The **LibreOffice recalculation check**
  (§12.6) is marked `recalc`, runs outside the Fast lane (`pytest -m recalc`) with LibreOffice from the tools image
  (§12.7), and is skipped when LibreOffice is not installed.
- Vitest covers the frontend's pure modules (§12.5). The parity and walk harnesses live in `tools/parity/` and
  `browser/` (§12.7).

**Lanes** (Q.2). Every slice runs Fast, Front and Lint; Q.9 names the extra lanes each slice runs. The last column
gives the slice each lane arrives in.

| Lane | What it proves | Command | When | Budget | From slice |
|---|---|---|---|---|---|
| Fast | rules, services, endpoints, the Q.3 contracts, golden keys, recorded AI reads, canaries, query scaling | `docker compose exec backend pytest` (one app: `pytest quotes`) | every change | ≤60 s in all; ≤10 s per app | built |
| Front | Vitest on pure modules, ESLint, build | `npm test`, `npm run lint`, `npm run build` | frontend changes | Vitest ≤10 s | built; Vitest in 6 |
| Lint | ruff, `makemigrations --check`, the import-linter chain, stylelint, the CSS port proof | `ruff check .`, `lint-imports`, `npx stylelint`, `node frontend/scripts/port-proof.mjs` (host) | every change | ≤30 s | built; stylelint and the port proof in 2, `lint-imports` in 6 |
| Recalc | a LibreOffice recalculation equals the keys | `pytest -m recalc` (LibreOffice from the tools image) | workbook slices; each release | ≤3 min | 27 |
| Fidelity | old and new files compared (Q.5) | `python tools/parity/files.py --deals all`, in the tools image | painter slices; each release | ≤10 min | 28 (the workbook from 27) |
| Look | old and new screens compared, by pixels and computed style (Q.5) | `npm --prefix browser run look -- --screens <key>` | UI slices; each release | ≤15 min | 3 |
| Walk | each need and each "done when", scripted in Chrome | `npm --prefix browser run walk -- --need <n>` | UI slices; nightly | ≤10 min | 3 |
| Perf | time and size budgets on GD-Big (Q.7) | `pytest -m perf` | slices that touch hot reads; weekly | ≤5 min | 7 |
| Eval | live reads of the synthetic corpus, scored against keys (Q.6) | `manage.py reader_eval --set all` | model, prompt, schema or merge changes; monthly | ≤30 min, about $20 | 18 |

### 12.2 Speed budget

The whole suite runs in **under 60 seconds** and any single app in **under 10 seconds** (the `recalc` and `perf` tests
are excluded). A slow test is fixed before new features land. Lint stays within 30 seconds and Vitest within 10; the
other lanes' budgets are in §12.1. When the serial Fast run passes 45 seconds, pytest-xdist is added, and the 10
seconds per app still holds (V.4 #5).

**Built (slice 39, 2026-11-12).** The serial run reached 77 s, so pytest-xdist 3.8.0 joined: the whole suite runs
`docker compose exec backend pytest -n 8 --dist loadfile` (about 45 s with other lanes testing beside it; `loadfile`
keeps a module's golden fixtures on one worker). One app still runs serially, because each worker's start costs about
8 s on the Windows bind mount (a serial start about 4 s). `pytest quotes` (345 tests) is about 20 s, over its 10 s
budget: its test count, not slow tests, sets it. §3.4's advice to move the repository out of the OneDrive-synced
folder is the first remedy; splitting the quotes suite by marker is the second.

**The app's own budgets** (Q.7). In the Fast lane, every list or summary read runs the same number of queries at two
sizes (Q.3 #4). In the Perf lane, Q.7's time and size budgets hold on GD-Big: for example, the Advisor's comparison
of 600 plans stays within 3 MB and 2.5 s (the old app sent 3.78 MB).

### 12.3 Tests that MUST exist

1. **The contracts every app passes** (Q.3). Shared helpers live in the root `conftest.py`, and each app adds a small
   table. They cover the write path (one Activity row with before and after; the same call again changes nothing;
   Revert works once and is refused after a later write), GETs that write nothing (a sweep of Django's URL registry),
   the permission matrix (every endpoint × actor; a write without the CSRF header answers 403), query scaling,
   quote-first (GD3 at checkpoints A and B), canaries (§12.9), the clock, concurrency, and stored counts equal to a
   rebuild.
2. **Rules.** Every pure rule in §5 has a table-driven test covering each row, and one service test shows that the
   screens and files call that function, not a copy (Q.1). Always included: every worked example in §5.5, including
   the package examples, and §5.6's commission example (3,805).
3. **Per slice.** Q.9, with the rows §13.2 adds or amends (slices 4, 6, 7, 9, 14, 36, 38, 49, 61, 62 and 67–69), names
   what each slice's tests pin, the golden deals they use and the extra lanes (for example the client lifecycle in slice
   6 and the client page in slices 67–68). Each part's X.6 lists the tests of its items.
4. **Golden keys,** checked three ways (§12.6).

A test that pins a default names its open question, so an answer finds its tests (V.3 #8). Where Daniel has answered,
the test follows the answer: for example, a stop-loss quote moves with the arrows and takes a slot pick (OQ13), and a
sale makes a prospect a New client (OQ2).

The baseline's tests (M0–M6) stay green, and the tests v1.1 §12.3 required stay MUST: health's 200 and 503 shapes;
deploy checks only when `ENVIRONMENT=production`; gzip for JSON only; `/api/meta/` serves every vocabulary; login
success, a wrong password and an inactive user; logout ends the session; `me` answers 401 when signed out; and the
write-path, deals, documents, quotes and proposals tests. A slice that rewrites one of these areas keeps its test, and
a slice that retires a baseline rule rewrites that rule's tests in the same change: slice 7 rewrites the carrier-sort
test in `proposals/tests/test_proposal.py` (Q.3 #10).

### 12.4 Tests we never write

Tests that read source code, templates, CSS or documentation (lint scripts may: the chain contract, stylelint, the CSS
port proof; Q.1); tests that pin counts of anything (tests, rules, files, queries: a scaling test compares two sizes
and never pins a number; Q.3 #4); parity tests between generated files inside the suite (Fidelity, Look and Walk
compare 2V with the old app as acceptance lanes, §12.7); pixel comparisons inside the suite (J.6.12, ruling 16);
snapshot tests of whole payloads (assert the keys and values that matter); tests that reach the network (AI reads are
replayed, §12.8); endpoint-shape tests for an endpoint a golden-deal test already passes through; tests of behaviour
Django owns (password hashing, admin pages, session expiry mechanics).

`deals/tests/test_platform.py` breaks this rule today: it pins 27 lines and 96 fields. It is rewritten to check
membership (Q.3 #10).

### 12.5 Frontend checks

`npm run lint` (ESLint with the react-hooks rules) and `npm run build` must pass.

- **Vitest** (`npm test`, from slice 6) covers pure modules only, for example the grid keys, the undo stack,
  `pageRows`, the finder and `findText` (O.4, Q.9), within 10 seconds.
- **stylelint** (Lint lane, from slice 2) refuses unknown custom properties, so an undefined colour token cannot come
  back (OQ10).
- **Clicking through.** Behaviour is verified by clicking through each slice's "done when" (§13) on a golden deal,
  beside the old app on the same deal from slice 3. It is scripted in the Walk lane when the slice advances one of the
  twelve needs (V.1 #10). Walk scripts find elements by role and visible text, because the old walkthrough anchors are
  not ported (A40).
- **Gate C is Stephanie's walk,** at both milestones (V.2): one real deal built beside her own spreadsheet and the old
  app, with plan data and typed counts at Milestone 1 and a census only after the PHI gate (§11.4).

### 12.6 Golden deals

- `manage.py seed_golden` builds the golden deals **through the services** (never raw SQL), from one JSON spec per
  deal, with synthetic data only. The same command seeds the development database and staging, so there is always a
  realistic deal to click through. It is idempotent: re-running replaces the golden deals.
- From slice 3 the seed lives in the `golden` app, last in the chain (§3.3). The app takes over `proposals/golden.py`,
  `golden_data.py` and the answer keys; only the seed command and the root `conftest.py` import it.
- Each new slice extends the golden deals rather than adding new fixtures.
- From slice 6 each spec names its client's status, Prospect unless stated (§5.1, OQ2). A sale made through the
  services turns the client into a New client: GD1-sold, GD3's checkpoint-A sale (from slice 49) and GD6 at
  Milestone 2.

The deals (§13.4 lists what each holds and what each slice adds; Q.4 lists what each key pins):

| Deal | What it proves | Seeded in slice |
|---|---|---|
| GD1 Golden Manufacturing | The Advisor and the client files on a three-plan medical line with dental and vision; its variant GD1-sold (slice 49) books two sold plans | built |
| GD2 Golden Small Shop | A one-plan small group: one-page outputs, PEPM commission, the small-group band | built |
| GD3 Quote-first | Pricing from typed counts with no intake answers and no census (checkpoint A), then the census taking over (B) | 13 |
| GD4 Census by plan name | The census import, matching, and pricing each current plan from its own members | 12 |
| GD5 Stop-loss | The stop-loss analysis and its workbook | 36 |
| GD6 Get to Market | Intake to sale: readiness, census, questionnaire, RFP, the portal and booking | 38–59 |
| GD-Big | Scale, in tests only: 600 plans, 2,000 members, 5,000 Activity rows and more | 7 |

- **Answer keys.** A key is worked out in a spreadsheet or by hand, never taken from the app's own output. It carries
  `checked_by`, `checked_on` and `method`, and changes only with Stephanie's agreement. GD1's and GD2's keys, built in
  M3–M6 but never signed, are signed before slice 7; each later key is signed before the slice that prices its deal.
- One test builds each golden deal, generates its workbook, and compares it with the key **three ways**: the app's
  numbers; the stored results in the file; and (`-m recalc`) a LibreOffice headless recalculation of the file (the file
  comparisons from slice 27; today `proposals/tests/test_golden.py` checks the app's numbers and the preview). Run the
  `recalc` tests before every release. They also run on every workbook slice (Q.2). The PDF and PowerPoint, read back as
  text, print each key figure in its plan's row (Q.4).
- **Rate bases without a golden deal** (OQ103, a proposal for Daniel). Stephanie signs one worked example for each of
  `volume_1000`, `weekly_10` and `payroll_100` before slice 27, which prints them. Slice 7 pins provisional examples in
  the math tests, and they change only when her signed ones differ.
- **The old app as an answer key, once per deal:** before the slice that prices a deal, the old app runs the deal's
  parity profile (§12.7), and its figures are compared with the key. A disagreement is fixed in whichever app is wrong
  (Q.4). Stephanie's marked-up review of the old app's Excel (OQ40) is wanted before slice 27.

### 12.7 Parity with the old app

Screens and client files are right when they match the old app on the same synthetic deal (Q.1). Q.5 has the
tolerances and the list of screens.

- **The harness (slice 3).** `tools/parity/` runs the old app (Django 4.2) read-only, at the commit the port follows
  (891f1b3, §13.3), as its own Compose project: its own database and media, an internal network, a dummy AI key and
  synthetic data only. One tools image (LibreOffice, poppler and the Python readers) recalculates, rasterizes and
  reads back both apps' files. 2V pins the old writers (reportlab 4.2.5, python-pptx 1.0.2, XlsxWriter 3.3.0) in the
  slices that add them, so Fidelity compares our code, not library versions.
- **Parity profiles.** Each golden spec has one. It leaves out what the old app cannot express, such as census by plan
  name (C41), and maps the client status onto the old app's client records (§13.4). 2V loads it with `seed_golden`;
  the old app loads it with `tools/parity/old_loader.py` through `manage.py shell`. Slice 3 builds the loader for GD1
  and GD2, and each slice that seeds a deal extends it.
- **Fidelity (files).** The old app's proposal downloads (workbook, PDF, deck and Paper), carrier files, questionnaire
  PDFs and stop-loss workbook are compared with 2V's, with dates, stamps, ids and authors masked on both sides.
  Built (slice 28): `python tools/parity/files.py --deals all` runs on the host: it fetches both apps' client
  spreadsheet, PDF and PowerPoint for each golden deal over their own APIs (standard library only; Paper joins with
  slice 30), then compares them in the parity tools image (`--compare`, no network) and judges each difference against
  `tools/parity/intended.yaml`, exiting 1 while any is unexplained; `report.md` and `differences.json` go to
  `%LOCALAPPDATA%/2vantage-fidelity/<time>/`. Each golden deal must be at its parity profile's checkpoint in both apps
  (GD3 at A): a walk that moves one makes its comparison meaningless until `seed_golden` runs again.
- **Look (screens).** `browser/` drives the installed Chrome through `playwright-core`, captures about 70 screen
  states in both apps, and compares them by pixels, class order and computed style. A harness-only sheet, generated
  from `browser/look/dropped.yaml` (one entry per Drop or Defer row with visible UI), hides on the old screens what
  the plan drops.
- **Walk.** Scripts in `browser/` walk each need and each "done when" in Chrome (§12.5).
- **Judging.** Each difference is a match, within tolerance, intended, or unexplained. An intended difference is
  listed with its item in `tools/parity/intended.yaml` or `browser/look/accepted.json`. Daniel signs each label once,
  and a changed image is judged again. An unexplained difference fails the lane. Answers that reverse the old app are
  intended differences, for example stop-loss arrows and slot picks (OQ13, labelled in GD5's profile).
- These are acceptance lanes, not suite tests (§12.4). They end when the old app is switched off at cutover (OQ100),
  and the last approved images seed the optional `-m look` job (J.6.11).

### 12.8 AI reader tests

Q.6 has the details and the Eval thresholds.

- **In the suite nothing calls out.** `ai/testing.py` replays recorded responses keyed by reader, file hash and page
  range, and an unknown key fails with "record it". Recorded reads carry their model, date and schema version; the
  recorder refuses files outside the corpus manifest.
- **The corpus is synthetic:** each file comes with its perfect response and named faults, and the corpus includes a
  two-current-plan renewal with printed per-plan counts and a Florida Blue pair.
- **Request-side checks** on the fake client's log: the Messages API only, with no beta headers; structured output;
  flagged pages left out only with the screen switch on (OQ22); column shapes only from the mapping assist, and counts
  only as census context (§3.8).
- **Eval** (opt-in, from slice 18): `manage.py reader_eval --set all` reads the corpus live. `ai/eval/` invents
  carriers, plans and rates, so every key is known by construction. It keeps a tuning set and a held-out set, reports
  counts only, and exits 1 under any of Q.6's thresholds. It runs when a model, prompt, schema or merge rule changes,
  and monthly, for about $20 a run. The first run informs OQ31; the golden-deal trial that sets the default model,
  read effort and caps runs once the key is confirmed under the BAA (OQ29).

### 12.9 PHI and client-safety canaries

Q.8 has the full lists.

- **PHI canaries.** Unique strings go into every PHI field of GD4, GD6 and the portal flow. None may appear in
  Activity (`changes` included), Job steps, errors, chat messages, logs, error bodies, URLs, `Content-Disposition`
  names, non-PHI payloads, or AI requests sent before the gate. The tests take the PHI kinds from
  `documents/kinds.py`.
- **Access logging.** Every PHI download or view writes one `downloaded` or `viewed` row with the document id, and
  leaves "Last updated" alone.
- **Client-safety canaries** go into `star_reason`, `client_guidance`, internal notes, document names, review marks,
  lasers, commission figures and birth dates. Every client file is read back in full, and none may appear (H125, J.4).
- **The staging canary scan** (slice 47, and Gate A at Milestone 2): after a scripted walk with the canary census on
  staging, a log query finds no canary (§11.4). Built: `deploy/canary_walk.py` (each run makes its own canaries,
  `deploy/canaries.py`) and `deploy/canary_scan.py` over `gcloud logging read` on staging, or `deploy/canary_scan.sh`
  over the dev stack's logs.

---

## 13. Build order

Build in Needs order. Each **slice** is reviewed and committed by the project owner before the next starts (changes are
left uncommitted for review). A slice is done when its tests and checks pass and its "done when" holds in the browser.

This section is Part P of docs/porting (`P-build-order.md`) with Daniel's answers of 2026-11-11 applied: 69 slices in
six phases (slice 50 waits under OQ6, so 68 are built), closed by two milestones. Where this section and Part P differ,
this section wins; 13.2 lists every difference.

### 13.1 How slices work

- A slice is one app or one shared framework, rarely two. It builds only in Part O's apps and folders (§3.2) and imports
  only to the left (§3.3).
- Daniel reviews and commits each slice before the next one is reviewed. A slice may be built ahead on its own branch
  (13.12), but review stays one slice at a time.
- **Needs** lists the slices that must be committed first. Slices 4 (after 6) and 47 (after 69) are the only ones built
  out of number order. **Done when** is walked in the browser on a golden deal, after the slice's tests and lints pass
  (V.1). **Answer first** names the open questions whose answers change the slice; "answered" marks those Daniel has
  settled. Every other question keeps its §16 default, built in one place, so a later answer is cheap.
- Item ranges (for example F43–F48) cover only the Keep, Simplify and New rows of the porting parts. A part's X.3 rows
  and X.6 design are the slice's detailed specification. CL items are the client lifecycle and client page, which no
  part lists (13.11).
- Sizes are relative (S, M, L, XL); an XL slice is reviewed in two sittings, backend first.
- Each slice's tests are in Q.9, with the rows 13.2 adds, on top of the Q.3 contracts and the Fast, Front and Lint lanes
  (§12). V.1 lists everything a slice must show before it is done.
- Slices 1–66 keep Part P's numbers. Slices 67–69 are new: they are numbered after 66 so that every slice number in
  docs/porting stays valid, and each sits in the table of the phase where it is built.

### 13.2 What the answers, and the check against v1.1, change in Part P

The Slices column names the slices whose Part P row changes; §16 gives every slice an answer touches.

| Cause | What changes from Part P | Slices |
|---|---|---|
| OQ2: prospects and new clients are built; existing clients wait | Slice 6 adds the client lifecycle, Prospect → New client → Existing client (§5.1), grows from M to L and needs slice 3 for the golden specs' statuses; `opened_as` and `deal_type` move to it from slice 38. Slice 7's `set_sold` calls `sale_changed`. Slice 4 needs 6 and builds the Prospects and Clients views. A sale moves its client from Prospects to Clients at once, which changes I122 and OQ91's default (slice 61; OQ101 c). Two new slices build the client page with its own Overview and Agenda: 67 CLI-1 and 68 CLI-2. Milestone 2 follows slice 68. The items, and the porting rows they change, are in 13.11 | 4, 6, 7, 38, 48, 49, 61–63, 67, 68 |
| OQ6: No, the default | Slice 50 is not built and keeps its number. H59–H93 except H68, with H103, H105 and H123, become Defer; OQ78 and OQ79 wait with them. Milestone 2 does not wait for slice 50 | 50 |
| OQ7: "use your best judgement" | Kept: the priced-version composer (F76–F78, F80–F84), the Advisor's saved setups, Mine and Shared (F28), stop-loss settings (F29) and proposal templates (J68). Deferred: census filter sets (F30, and C27's saved filter setups) and, as before, bundle templates (F79) | 10, 34–36, 57 |
| OQ9: accepted, with the sidebar in the old order | (a)–(d) stand. The deal sidebar keeps old Vantage's order and groups exactly (A21); the chain orders imports, never screens. A tab not yet built is left out. A missing questionnaire never holds up quotes: typed summary tier counts carry the Advisor and Proposal (F85–F92) | 4 |
| OQ13: yes | Stop-loss plans take arrows, slot picks and reset like every line. F49 becomes Drop, and O.6 #26 loses its stop-loss case. **This reverses the old app**, which kept stop-loss in the order added | 7, 9, 14, 36 |
| Check against v1.1, proposed (OQ105): staging had no slice, though V.2 runs Gates B and C on staging | New slice 69 STG-1 builds §11's staging after slice 16. Slice 47 needs it, and Milestone 1 follows it | 69, 47 |
| Check against v1.1, proposed (OQ103): three rate bases had no signed example | Stephanie signs one worked example for each of volume_1000, weekly_10 and payroll_100 before slice 27, which prints them, as v1.1's R2.4 asked; slice 7 pins provisional examples. This is a new gate on Stephanie, beyond V.4's | 7, 27 |
| Check against v1.1 (OQ104, OQ106) | Client files print laser liability as amounts and list lasers by position, never `sl_lasers` (slices 27, 36). Contacts keep seven roles; B13's eighth, `partner_agent`, is dropped (H13, M81; slices 38, 40) | 27, 36, 38, 40 |
| v1.1 §16's open rows, numbered (OQ107, OQ109) | Slice 47 waits on the sign-in lifetime (OQ107); slice 45 checks whether `emp_class` fills Warner's columns S and X (OQ109) | 45, 47 |

Every other answer confirms its default (OQ1, OQ3, OQ5, OQ10, OQ14, OQ15, OQ17, OQ18, OQ20), so Part P stands there.
OQ4, OQ8, OQ11, OQ12, OQ16, OQ19 and OQ21 were left blank; their defaults are built until Daniel answers (§16).

**Tests Q.9 gains.** Q.9 has no rows for slices 67–69, and its rows 4, 6, 7, 9, 14, 36, 38, 49, 61 and 62 predate the
answers. These rows complete it ("added" joins Q.9's row):

| Slice | Tests must pin | Golden | Extra lanes |
|---|---|---|---|
| 4 (added) | a Vitest pins the sidebar's order and groups | GD1, GD2 | — |
| 6 (added) | a sale converts a prospect once, in the sale's transaction, with one Activity row; un-selling undoes only a sale's conversion, un-selling one of two sold plans changes nothing, and a hand conversion survives an un-sell; existing clients ignore sales; Back to prospect answers 409 while a plan is sold, Convert answers 409 on a lost deal, and New client → Existing client answers 409; create refuses `new_client`, and PATCH refuses `relationship`; the comma filter; `opened_as` follows the status, then freezes at the sale; over random runs of sells, un-sells and moves, a client with a sold plan is never a Prospect; the migration's mapping; a sale's row refuses Revert, and a hand row reverts | GD1, GD2 | — |
| 7 (added) | a stop-loss quote moves with the arrows and takes a slot pick; each rate basis equals its worked example (OQ103) | GD1 | — |
| 9 (added) | the up, down, left and right arrows move a stop-loss plan like any line's | GD1 | Look |
| 14 (added) | a stop-loss column takes a slot pick, with the slot's star and link | GD1 | — |
| 36 (added) | GD5's parity profile labels the stop-loss arrows an intended difference (OQ13) | GD5 | Look |
| 38 (amended) | drop "`deal_type` frozen", which moved to slice 6 (CL8) | GD1, GD6 | — |
| 49 (added) | GD1-sold's client is a New client; un-selling both its plans voids both records and returns the client to Prospect; H58's outside client is created as an Existing client | GD1-sold | — |
| 61 (added) | Prospects lists only Prospect clients and Clients only New and Existing ones; a sale moves the row at once (I122 as changed) | GD2, GD-Big | — |
| 62 (added) | a prospect's client box offers Convert to client, refused on a lost deal; a client's box links to its client (the dialog until 67) | GD2, GD1-sold | Look |
| 67 | the client payload for a prospect, a New client and a client with no deal; its GETs write nothing; the same queries at any size | GD1-sold, GD3, GD6, GD-Big | Look, Perf |
| 68 | the client agenda equals its deals' agendas; commission figures follow the viewer's tier | GD1-sold | Look |
| 69 | the release gate passes with staging's settings | GD1 | — |

**v1.1's releases are retired.** M0, M1 and M3–M6 are the baseline (13.3). M2 (staging), never built, becomes slice 69
(OQ105); M7 and M8 become slices 27 and 32; M9 becomes Gate C at Milestone 1. R2.2 and R2.3 become slices 16–22, and
R2.4 becomes the signed rate-basis examples (OQ103). R2.1, copying a plan design from an earlier deal, has no old-app
item and is not in this build unless Daniel asks (OQ110); carrying last year's plans waits with renewals (OQ1). Release
3 becomes Phase 4 (slices 38–47, with R3.9 in slice 47), and its acceptance becomes GD6's walk at Milestone 2. Release 4
becomes Phase 5 (slices 48–68).

### 13.3 Before slice 1

- **Commit the baseline.** Every 2Vantage app is untracked today, so no slice's change could be read on its own. Daniel
  commits M0–M6 first.
- **The baseline is not the design.** M0–M6 was built to v1.1. Where it differs from this spec, the slice that owns the
  area retires the difference; nothing is a rule because it is built, and no slice copies a baseline pattern this spec
  retires. For example: the flip to an existing client at a sale, `PATCH clients/{id}/` taking `relationship`, and
  `set_sold` locking the Plan before the Deal (slice 6); the per-role order, membership list and carrier sort, quotes'
  writes in `marks.py` and `template.apply`, ids read with a bare `int()` (a 500) and refusals answered 400 instead of
  409 (7; 25 for proposals); Activity without before and after, `updated_at` moving on an unchanged write, and
  `last_activity_at` counting downloads (5); golden inside `proposals` (3); hard deletes of plans (8), documents, which
  any user may delete (15), and clients and notes (38); `Plan.enrollment_on` (13); `option_label`, and a GET that
  creates `ProposalConfig` (25); CSS modules and `tokens.css` (4). The parts list the rest with evidence: E.5 #27–42,
  F.5 #27–38, J.5 B27–B36 and M.5 B33–B36; Q.3 #10 names two tests that pin counts.
- **Fix the old commit the port follows: 891f1b3.** Two old-repo commits landed on 2026-11-11 while this plan was
  written. 7385bb3 committed the need-9 code (`plan_slots.py`, `plan_slot_tests.py`, `PlanPicker.jsx`,
  `ProposalPages.jsx`, `keyRows.js`) and D-224, so J.5 B20's rescue step is void and slice 14 ports from that commit.
  891f1b3 added D-225, which turned the member-data screen off for every Claude read (OQ22). Later old-repo decisions
  are listed for Daniel before the slice that ports their area.
- **Scope and conventions.** Daniel answers OQ1–OQ9, or accepts their defaults. He answered in decisions.md on
  2026-11-11 (§16); OQ4 and OQ8 were left blank, so their defaults are built.
- **Before slice 6:** OQ101, prospect to client, or its default. **Before slice 7:** Stephanie signs GD1's and GD2's
  keys (V.4 #2). **Before slice 27:** she signs the three rate-basis examples (OQ103; 13.4).

### 13.4 Golden deals

`seed_golden` lives in the `golden` app from slice 3 and builds every deal through services, with synthetic data only,
from one JSON spec per deal. Slices extend these deals; no slice adds a private fixture. Each spec has a parity profile
for the old app (Q.5). From slice 6 each spec also names its client's status, Prospect unless stated (§5.1). The old app
had no Prospect / New client status: a parity profile maps a Prospect to a deal not on the client book, a New client to
a deal linked to a client of type New, and an Existing client to one of type Existing. Stephanie signs a key before the
slice that prices its deal: GD1's and GD2's keys before slice 7, and the worked examples for the volume_1000, weekly_10
and payroll_100 bases before slice 27 (OQ103). Q.4 lists what each key pins.
- **GD1 Golden Manufacturing** (built): three current medical plans with renewals; alternates from two carriers; a
  consolidation; plans bought together; two picks for one plan; dental and vision. Slice 15 adds a synthetic quote PDF,
  workbook and SBC; slice 33 a Florida Blue pair; slice 49 a variant, GD1-sold, with two sold medical plans (OQ12),
  whose client is a New client (built: `golden/variants/gd1-sold.json`, GD1 under the client "Golden Manufacturing
  Sold (synthetic)" with Medical agreed at 5 % and CG1N and U2 sold, so Cigna and UnitedHealthcare book one record each,
  OQ75; its key `golden/keys/gd1-sold.json`, unsigned; the root fixtures `gd1_sold` (module) and `sell_gd1` (a test's
  own copy); `seed_golden` builds it with the rest, and `seed_golden GD1-sold` alone).
- **GD2 Golden Small Shop** (built): a one-plan small group.
- **GD3 Quote-first** (slice 13): no intake answers and no census. Medical starts with typed whole-line tier counts and
  ten alternates; a PEPM line prices from typed lives (F92) and an accident quote borrows medical's counts (OQ19). Its
  spec also holds what arrives later, which the seed leaves out: the packet's two current plans with their printed
  counts (`arrivals`, `links_after_split`) and the checkpoint-B census; `golden/quote_first.py` moves a test's copy
  through the checkpoints (the root conftest's `quote_first`), and the Walk lane's need 6 walks them on screen. From
  slice 18 it carries unread synthetic files: a renewal packet that brings two current plans with renewals and printed
  per-plan counts (built: `renewal_packet` in the spec, `golden/renewal_packet.py`, attached by the seed as kind
  renewal; the root fixtures `gd3_packet` and `gd3_packet_answer` give its perfect read), an alternate quote and an SBC
  (not yet built). Its script has two checkpoints:
  - **A**: typed counts only; the packet lands and the counts are split; from slice 42 the Florida Blue 51+ form is
    started (52 enrolled); from slice 49 a sale is booked, which makes its client a New client.
  - **B**: a 48-person census arrives, its elections naming both current plans, so the census takes over (F91), the band
    notice shows (G133) and the booking reads "Out of date" (H120).
- **GD4 Census by plan name** (slice 12): about 150 people with dependents and waivers; elections naming three current
  plans, one alias and an unmatched variant; a copy on Warner's template.
- **GD5 Stop-loss** (slice 36): level-funded medical with stop-loss and TPA quotes and lasers; the SIIA disclosure from
  slice 43. Built: medical LF-C (typed 30/6/5/7, 48 employees), its renewal and a Cigna level-funded quote; the
  Stop-Loss line's in-force Symetra contract, its renewal and three options (one unscored), every analysis figure in
  `golden/keys/gd5.json` (unsigned); the old app's own figures equal it (`old_loader` prints them).
- **GD6 Get to Market** (slices 38–59): full intake, contacts, coverage with in-force commission, BOR, a 60-person
  census, Florida Blue 51+ signed, the Warner route, and a client link answered and approved. At Milestone 2 its plan is
  sold and booked, and its client becomes a New client with its own client page.
- **GD-Big** (tests only): 600 plans, 2,000 members, 200 links, 200 notes, 100 documents and 5,000 Activity rows.

### 13.5 Phase 0 — Ground

The spec, the look, the golden deals and the old-app harness.

| # | Slice | Needs | Builds | Done when | Answer first |
|---|---|---|---|---|---|
| 1 | PLAN · M | 13.3 | plan.md v2.0 rewritten from Parts A–Q and Daniel's answers: scope (§1.4), with the client lifecycle and client page (OQ2), chain (§3.3), models, API, screens in the old look, the old file formats (§9), AI with the chat (§10), Part P as §13, a shorter §15, and every open question in §16 with its default and slice. CLAUDE.md: the chain, the conventions OQ9 changes, the worker and Vitest commands, under 80 lines. No code | Daniel agrees with §1.4, §13, §15 and §16; the suite passes | OQ1–OQ9: answered 2026-11-11; OQ4 and OQ8 left blank, so their defaults are built |
| 2 | LOOK-1 · L | 1 | O.5's port: the class sweep, the cut into ≤300-line files and one manifest, the token pins, the two button fixes, Plex fonts, stylelint and the port-proof script | The port proof shows each sheet's files equal the old sheet minus the listed edits; every M1–M6 flow still works | answered: OQ10 |
| 3 | PAR-1 · L | 2 | The `golden` app (seed, specs with parity profiles, keys with signature fields, root-conftest fixtures; moved from proposals); the root conftest's socket guard. `tools/parity/`: the old app as its own Compose project, the tools image (LibreOffice, poppler), `old_loader.py` for GD1 and GD2. `browser/` with the Look lane and the generated hide list | GD1 and GD2 load into both apps from one spec, and the Look lane captures the old app's GD1 screens | — |
| 4 | LOOK-2 · L | 3, 6 | AppShell (A6). DealShell with path tabs and an error boundary per tab (A20, A21, A26); its sidebar keeps the old order and groups (OQ9), pinned by a Vitest, and leaves out tabs not yet built; its client block waits for slice 67. The home header with the Prospects and Clients views (A7, A9, A13; CL10–CL12), the New client dialog with Status (Prospect or Existing client), deal header with a `proposal` stage pill and the client's status, Activity drawer and Documents v1. 2V's simplified Advisor and Proposal move onto old classes until slices 9 and 25 replace them. Every `*.module.css` and 2V's tokens go | The sign-in page, top bar and GD1's built screens pass Look with labelled differences only; every M1–M6 flow still works; the sidebar lists A21's tabs in the old order and groups, and Look labels each missing tab "pending slice N"; GD1 and GD2 list under Prospects; Clients shows its empty words; a client created as Existing client lists under Clients · Existing clients | OQ95, OQ101 (c) |

### 13.6 Phase 1 — The Advisor without Claude

| # | Slice | Needs | Builds | Done when | Answer first |
|---|---|---|---|---|---|
| 5 | FND-1 · M | 1 | O.3.2's Activity, the revert endpoint and reverter registry, quotes' first reverter, Revert in the drawer (A34), `log_access`; O.3.1's source entry and `values.apply` (A31–A33); the Q.3 contract helpers in the root conftest (write path, GET sweep, permission matrix) | On GD1, Revert restores a plan value; a second Revert says it was already undone; after a later edit, Revert is refused; a hand edit over a read value keeps ↗ | — |
| 6 | FND-2 · L | 3, 5 | `advance` reloads and locks; `deals/rules.py` (`refuses`, with `convert`; `agent_name` as owner, then agency producer; `deal_type` over `Deal.opened_as`, moved from slice 38); `deals/carriers.py` (F14, K105); `AgencySettings.producer_name/npn`; `accounts.Profile` (A3, A4); the import-linter chain contract; Vitest. The client lifecycle (§5.1; CL1–CL9): `deals/lifecycle.py`; `set_status` behind `POST clients/{id}/status/`, asking `deals.providers.client_has_sold`, which quotes fills; `sale_changed`, which quotes' `set_sold` calls inside the sale's transaction in place of 2V's flip to existing; `client_since` and `converted_by_sale`; `opened_as` following the status until the sale; the comma filter; the migration from new and existing; each golden spec's status. On 2V's current screens: Status in the New client and client dialogs, with refused moves greyed and their sentence as the tooltip, and the status badge in the deal header | A lost GD1 refuses each `refuses` action with its sentence; the chain contract fails on an import to the right; marking a GD2 plan sold makes Golden Small Shop a New client with one Activity row, and un-selling makes it a Prospect again; after Convert to client, an un-sell leaves it a client; Back to prospect while a plan is sold is refused with its sentence | OQ101; OQ108 (generating `deals/carriers.py`) |
| 7 | ADV-1 · L | 3, 6 | quotes: O.2's Plan fields; `presented` and `room` (F119, J2, J3); `order.layout` (F120, J4) with no stop-loss case, so stop-loss takes arrows, slot picks and reset like every line (OQ13); `slots`, `closeness`, `facts` (F121, F122). Services: stars with the cap, reason and auto-link (F50, F51); clearing the shortlist per line (F55); roles and links (F52, F53); move, swap, reset, `put_in_slot` (F43–F48); recommend within `room()`; `set_sold` refusing lost deals (F123) and calling `sale_changed` (slice 6). PATCH limited (F71). `quotes/math/` with `round_decimal`, reading `deals.lines.ENROLLMENT_KEYS` and `TIER_CODES`, pinned by worked examples for the volume_1000, weekly_10 and payroll_100 bases, provisional until Stephanie signs them (§5.5, OQ103); the `perf` marker and the `addopts` that keeps it and `recalc` out of the Fast lane (§12.1); both signals; `deal_state` in one grouped query. 2V's per-role order, membership list and carrier sort retire (F.5 #27–32) | On GD1 a 17th star is refused with a sentence; a starred quote made current loses its star and links; a rate edit moves nothing; GD1 matches its signed key, and each rate basis its worked example | OQ11, OQ12, OQ103; answered: OQ13 |
| 8 | ADV-2 · M | 7 | Soft delete and restore (F60); clear line (F61); `move_line` in place (F59); `copy_plan` with rates (F81); the one merge service (F142). A sold plan cannot be deleted | Deleting a current plan turns its renewal into an alternate, and Revert restores both; a plan moved to dental keeps its id; a copy keeps its rates | OQ110 (only if yes) |
| 9 | ADV-3 · L | 4, 8 | `src/grid/`. AdvisorTab with pills and line tabs (F1, F2, F5–F11); presets and sort (F31–F33, F36, F40, F41); ⇄ Transpose (F34, F35); chips (F62); edit mode (F68–F73); ticks and batch star (F57, F58); delete, clear and move on screen (F59–F61); the board exporter (F93, J98, J167); ▲▼ and ◀▶ on every line, stop-loss included (OQ13) | GD1's board passes Look; Transpose keeps the header frozen and refuses above 60 plans; Excel keys and Ctrl+Z work; the export matches the screen | — |
| 10 | ADV-4 · M | 9 | Finder over name, plan number, carrier, network, type, codes and aliases, with "Also matches N on Dental" (F14–F17); budget select and "Monthly total ≤ $" (F18, F19); "N have no price yet" (F140); sliders, caps, hides and Claude's rule chips (F20–F27); saved board setups, Mine and Shared (F28; kept, OQ7) | On GD1 "UHC" finds UnitedHealthcare plans on every line; "Monthly total ≤ $45,000" hides the dearer plans and names those with no total | answered: OQ7, OQ14 |
| 11 | INT-1 · M | 9 | intake: B.6's models, `form.py`, the one cleaner, `CurrentCoverage` (B14); `set_intent` as the only writer of `requested_lines`, with confirm and reopen (B16–B21, B23, B24, B32); `intake.providers` with defaults; `deals/comp.py`. quotes fills `quote_lines` and adds `facts.incumbent` (F144) and the "Off the proposal" chip (F13). The coverage card | On GD1, Shop it and Keep as-is show per line; a change after Confirm shows "Changed since confirmed"; the Advisor flags the kept line | answered: OQ15 |
| 12 | CEN-1 · L | 11 | census: `fields.py`, `Member`, `CensusImport`, `CensusSettings`, `CensusFacts`. Read, reshape, map, apply and match with a dry run (C12–C17, C14's offline mapper only); validation (C21–C24); rollups by line and by plan name (C39–C46); fills `census_state`; the import door and MappingDialog (C15). Seeds GD4 | GD4's file imports through the mapping dialog; a re-import first lists who is added, changed, removed and kept; the Warner-template copy imports; tier counts equal a hand count | OQ16; answered: OQ17 |
| 13 | ADV-5 · M | 9, 12 | `LineEnrollment`; `enrollment_for` (O.6 #24); source words (F86); the counts card with the split, and CensusNotice (F85, F88, F91); F87, F89, F90, F92, F98; `facts.enrolled_headcount` and `enrollment_check`; quotes fills `headcount`. Seeds GD3 | On GD3 every medical plan prices from typed counts; a second current plan names the plans that lost their price and opens the split; a census import re-prices them with "Priced from the census now · Keep my typed counts"; counts typed after the import win again | OQ19, OQ21; answered: OQ18, OQ20 |
| 14 | ADV-6 · L | 13 | proposals: `pages.py` (the one splitter) and `GET proposal/pages/?line=`, with formatted cells and `others`. `deal/proposal/pages/` (PagesView, PlanPicker, PlanLinkPicker), ported from old commit 7385bb3 and mounted by the Advisor (F37–F39, F45, F46, F48, J5–J13); stop-loss columns take slot picks like any line (OQ13) | On GD1, clicking a column name and picking a plan puts it in that slot with the slot's star and link; "Replacing:" groups a quote under its plans; "Several…" makes a consolidation | — |

### 13.7 Phase 2 — Documents, Work with Claude and staging

| # | Slice | Needs | Builds | Done when | Answer first |
|---|---|---|---|---|---|
| 15 | DOC-1 · L | 4, 5 | documents: kinds and buckets; O.2's fields, `protected` included; upload checks (30 MB cap, magic bytes, page count); archive and restore, refusing protected files; `screen` at upload (D52); downloads and views logged through `log_access` (E99); the content-type map in `deals/downloads.py` (K63); deep links (E1–E8, E10–E18, E20–E24, E26–E32, E93–E99). `src/viewer/` without OCR; `sheets.py` and `look()`; `xlsx_safe.py` (D114). Synthetic files on GD1 | A value's ↗ opens the PDF page with the value boxed, or the cell in its Excel look; Remove archives a file, and "Show removed files" restores it | OQ22–OQ27 |
| 16 | DOC-2 · L | 15 | The ai core: `Job`, `DealAi`, the worker service, the reaper, the state endpoint and `useAiState` (A36, D105). `documents/locate/`, the `locate` job and quotes' hooks; "Check this file" (E59, E81–E84, D95) | "Check this file" runs with progress and Stop and survives `docker compose restart backend`; each ↗ then opens where the value was found, or says "not in the file" | — |
| 17 | DOC-3 · L | 9, 16 | `review_rules.py`; `Plan.flags`; quotes' `sources/` and `marks/`. The List view, file strip, bulk bar, keys and Undo (E34, E35, E47, E48, E52–E58, E85–E89, E92, D121, D122, D124, D126). The Advisor's flags chip and review strip (F63, F65, F67). Change history from Activity (E73, E74) | The strip reads "N AI values to review"; A, I and F mark values, and Undo restores them; the Advisor's amber agrees with the station | OQ28 |
| 18 | AI-1 · L | 13, 16 | `ai/client.py` (Messages API only); pricing, budgets and limits (D53, D99); `reading.py` and `ranges.py` (D46, D48–D51, D54–D62, D64, D65); quotes' reader modules, reading order (F138), codes (F143); the one read door (D39); the staged review card (D28, D31); the fake client, the corpus and the Eval lane | On GD3 a read of the renewal packet shows the staged card: two current plans and their renewals in printed order, with their per-plan counts unticked; nothing is written | OQ29, OQ30 |
| 19 | AI-2 · L | 18 | `read_apply` with Undo (D72–D75); counts landing (D67); D115, D117; the Re-read panel and staged banner (E75, E78, E79) | "Use this scan" lands GD3's packet and moves the deal to Quoting; accepting the counts prices both current plans; Undo removes the plans; an unchanged re-read writes nothing | — |
| 20 | AI-3 · L | 19 | The drawer and pill (D1, D3–D5, D8, D9); the File room and attach from anywhere (D13, D14, D16, D17); running and over-budget cards, strip and flash (D21–D24, D27, D34, D35, F112); landing by person (D71); Try again (D76); "＋ Add quotes" (F96, D37); the quote-first door (A14, D43) | From "I already have carrier quotes", dropped files create the deal and are read; an admin's read lands with Undo, a producer's waits for review; Stop keeps finished parts | OQ31 |
| 21 | AI-4 · M | 20 | `QuoteLayout` written at landing (D66, E94); the Advisor's "As quoted" (F42) and the Documents view (E42) | "As quoted" shows GD3's packet in the file's column order with its printed rows; unmapped rows are greyed, with their printed text | OQ32 |
| 22 | AI-5 · L | 17, 20 | SBC reads: design values only, never a new plan (D15, D38, D47). Re-checks applied by a person (D40, D93, E76, E77, E80, F66). `split.py` (D116; halves stay two plans); the merge tool (F142) | "Attach SBC…" stages design values; a value the SBC disagrees with is flagged; re-check approvals apply only when a person applies them | OQ33 |
| 23 | DOC-4 · M | 9, 17 | The station grid on `src/grid/` (E36–E41, E50, E51, D123); Find with aliases (E60–E64, D127); Review mode and edits (E65–E68, D125, D129) | In Review mode a click jumps the file to its value; Ctrl+F walks every match | — |
| 24 | AI-6 · L | 10, 11, 20 | Chats (D7, D19, D25); agent turns that stage plan changes (D77–D86, D88, D90–D92); `set_board` (D80, F108–F110, F114) and `clear_line`; GuidanceBox writing through intake (D6, D98); budget and lock (D100, D104, F113); carrier notes (D119) | "Show PPOs under $40,000 a month" sets the board; a direct person's "delete the duplicate Aetna plan" changes the table, with Undo | OQ34 |
| 69 | STG-1 · M | 16 | §11's staging: the production image on Cloud Run as the web service and a worker service (`run_worker`), Cloud SQL, a private Cloud Storage bucket through django-storages, Secret Manager, Artifact Registry, the migrations job and the release gate; `seed_golden` on staging. Synthetic data only until the PHI gate (47) | Stephanie signs in on staging and opens GD1 in the old look; "Check this file" runs in the staging worker; a synthetic upload lands in the private bucket and downloads through the app; the release gate passes (`check --deploy` clean, `/api/health/` naming the commit with no pending migrations) | OQ105 |

### 13.8 Phase 3 — The Proposal

The Proposal, its three files and the Florida Blue fold.

| # | Slice | Needs | Builds | Done when | Answer first |
|---|---|---|---|---|---|
| 25 | PRO-1 · XL | 11, 14 | `ProposalConfig` reshaped; `set_config` merged by path under a lock; card marks (J18–J20); `ready` and `checks`. quotes' `option_number`, `labels.numbers`, `stamp_option_numbers` and `client_name` (J14, J159). The builder shell and line cards (J16, J17, J23, J27–J31, J47–J62), with the EnrollmentStrip (J48; kept, OQ18). 2V's selection and preview retire | On GD1 two picks for one current plan each show their own change; a kept line needs no pick; predicted option numbers match Pages | OQ35–OQ37 |
| 26 | PRO-2 · L | 25 | Output and page switches with their ledger (J38, J39, J41, J42); plan experience (J45); the coverage card (J46); summary and renewal blocks (J64–J66); next steps (J67). Markets checked (J63), through a new `rfp` app holding only `RfpRequest` and `asked_by_line()` | Every card saves and marks itself done; Markets checked lists the quoting carriers, with "no RFP sent" | OQ38 |
| 27 | PRO-3 · L | 15, 25 | The workbook: the sheet model with the old formulas, the tabs (J145–J154), the writer through `xlsx_safe` (XlsxWriter 3.3.0); downloads (J24, J97, J104); the Recalc lane; every rate basis, checked against Stephanie's signed examples (OQ103) | The file opens in Excel with the old look; totals match GD1's key three ways | OQ39–OQ41, OQ103 |
| 28 | PRO-4 · L | 27 | The Export viewer in the Advisor (F3, F136, J105, J107, J112) with the workbook view (J116–J118); the Fidelity lane | The Excel chip pages through every tab as the file shows it; previews write nothing; Fidelity shows no unexplained difference | — |
| 29 | PRO-5 · XL | 26 | `story/`, `layout/` and `paint/pdf.py` (J122–J140 except J129; J142, J165; reportlab 4.2.5); the `FirmPages` and `TeamMember` models and stock covers, edited in Django admin until slice 34 | GD1's Client PDF has the old Presentation pages, type floors and "(continued)" pages | — |
| 30 | PRO-6 · M | 28, 29 | The deck view, slide rail, fit report, notes, Paper, downloads and Print… (J108–J111, J114, J115, J120) | The PowerPoint and PDF chips page through the slides; Paper shows the Letter frame; Print… opens the print dialog | — |
| 31 | PRO-7 · L | 29 | `paint/pptx/`, replaying the recorded frames (J141; python-pptx 1.0.2) | The .pptx opens with the old master, native charts and notes, slide for slide like the PDF | — |
| 32 | PRO-8 · L | 16, 30, 31 | The Proposal tab: the board in presented mode (J70–J94); the packet card (J96–J101); Issue as an `issue` job with stored, protected files (J102, J103) | Issue makes v1 with three stored files and moves the deal to Proposal; v2 leaves v1's bytes unchanged; an uncovered shopped line is refused with its sentence | — |
| 33 | PRO-9 · M | 32 | The D-219 fold: `Plan.pair_of`, `room()` counting a pair once, "⧉ One column with… · Split" on Pages (J15, F137), the fold in the three files, the `split_plan` check. Adds the pair to GD1 | On GD1, 5182 and 5183 print as one column on Pages and in the PDF, PowerPoint and workbook, and its total equals the pair's package; Split restores two | OQ42 |
| 34 | PRO-10 · M | 29 | `CoverImage` uploads, pictures, team, the firm-pages drawer and templates (J32–J35, J43, J68, J155); `documents/images.py` | An uploaded cover and a team member print on the PDF and the PowerPoint | answered: OQ7 |
| 35 | ADV-7 · M | 9 | Priced versions (F76–F78, F80–F84), kept (OQ7); bundle templates (F79) stay deferred | "5% off" previews its total, and commits a copy behind its original that prices the same people | answered: OQ7 |
| 36 | ADV-8 · L | 13, 27 | Stop-loss analysis (F98–F107) with saved settings (F29; kept, OQ7) and its five-tab workbook (J166), whose Binding Notes read `disclosure_state` (G117). Seeds GD5, whose parity profile labels the stop-loss arrows an intended difference (OQ13) | The verdict cards rank lowest first; the basis names its source; the laser what-if is never saved | OQ43, OQ104; answered: OQ7 |
| 37 | AI-7 · M | 24, 33 | Rank through the star rule (D36, D96, D97, F111); the tools `set_table_note`, `set_rows` (J160, D120) and `pair_plans` (J161) | With guidance written, Rank stars 5–8 plans with reasons within `room()`, and without it says "Add client guidance first"; asked, Claude pairs two halves and writes a table note, each with Undo | OQ44 |

**→ Milestone 1 (13.13).**

### 13.9 Phase 4 — Get to Market

Intake, census, the questionnaire and the RFP, up to the PHI gate.

| # | Slice | Needs | Builds | Done when | Answer first |
|---|---|---|---|---|---|
| 38 | FND-3 · M | 6, 25 | M's O1: `Contact` and `contacts.primary`; `Note` (A37); client archive and the Archived page, showing each client's status (A13, A18); `deal_size`, `agent_of_record` (first in `agent_name`), `set_owner`; `rules.client_asks_open`, `is_past`; the builder's RENEWAL chip (J22), read from `deal_type` (slice 6). Client DELETE answers 405; `mark_lost` answers 409 on a lost deal | Archiving a client hides it everywhere, and Restore brings it back; deleting a pinned note can be undone; a deal opened for an Existing client shows RENEWAL | OQ45–OQ49, OQ106 |
| 39 | INT-2 · L | 11 | The intake form (B1–B11, B36); budget hints on the Advisor (F139) | On GD6 all four cards fill by keyboard; a bad FEIN shows its message; "Client target $X/mo · Apply" appears on the Advisor | OQ50, OQ51 |
| 40 | INT-3 · L | 38, 39 | Contacts, the checklist with COBRA, BOR, readiness and Mark as marketed (B13, B25–B31, B33–B35) | GD6 reaches "Ready to market"; Mark as marketed records the skipped items and can be undone | OQ52, OQ53, OQ106 |
| 41 | CEN-2 · L | 12, 17 | The roster grid on `src/grid/` (C1–C10, C38); COBRA through intake (C25) | Flagged errors are fixed with Excel keys; the blank template re-imports cleanly | — |
| 42 | QST-1 · XL | 13, 40 | G's Q1 and Q2 (G1–G55, G124, G125, G133, G134, G136); `quotes.facts.group_facts`; questionnaire marks (E103); fills `questionnaire_items` | On GD6 Florida Blue 51+ is chosen by the band, with one plans row per current plan; the officer's signature locks the form | OQ54–OQ56 |
| 43 | QST-2 · L | 15, 42 | G's Q3 (G56, G57, G59, G61–G67, G110–G113); the signed copy filed as a protected Document (G135); fills `disclosure_state` (G117) | Stamped values sit inside their boxes; the signed copy is filed and refuses Remove; a stale check is refused; GD5's Binding Notes read "SIIA disclosure signed" | OQ57, OQ58 |
| 44 | RFP-1 · L | 26, 40 | K1–K33; the commission text from `AgencySettings.default_commission` | The band comes from the one headcount; the cross-check names the intake, census and Advisor counts; carrier picks save | OQ59, OQ60 |
| 45 | RFP-2 · XL | 41, 44 | K34–K42, K79–K98, K105–K108, K124; rfp fills `carrier_required`; whether `emp_class` fills Warner's columns S and X, checked against the workbook (OQ109) | The Warner, Aetna, Angle and UHC files open in Excel with each carrier's own formatting | OQ61–OQ64, OQ109 |
| 46 | RFP-3 · L | 43, 45 | K43–K78, K99–K104, K109–K123 | A draft `.eml` opens in Outlook; the first Sent tick moves the deal to Quoting; Markets checked lists who was asked | OQ65–OQ69 |
| 47 | PHI · M | 46, 69 | §11's PHI gate (v1.1's R3.9): Microsoft 365 sign-in; the access-log check; the key confirmed under the BAA; the staging canary scan | Staff sign in on staging with firm accounts; the §11 checklist is signed | OQ29, OQ107; OQ105 (needs 69) |

### 13.10 Phase 5 — The rest

Commissions, the readers for client files, review and the portal, Agenda, Overview and the client page.

| # | Slice | Needs | Builds | Done when | Answer first |
|---|---|---|---|---|---|
| 48 | COM-1 · L | 11, 38 | H1–H24, H95–H102, H106 (its endpoint and the client-scope SplitEditor; the client page mounts them in slice 68), H113, H116, H121; rfp's request text switches to `requested_rates` | A 60/40 split previews and saves | OQ70, OQ71 |
| 49 | COM-2 · XL | 32, 48 | H25–H58, H68, H108–H112, H114, H115, H120, H124, H125; GD1-sold. Booking reads `opened_as`; H58's outside client gets a Status, Existing client by default | Mark as sold opens BookingSummaryModal; un-selling voids the record; GD1-sold books both plans, and its client is a New client; un-selling both plans voids the records and returns the client to Prospect | OQ72–OQ77, OQ101 |
| 50 | COM-3 · XL, not built (OQ6 is No) | 16, 49 | Waits, and keeps its number. If OQ6 changes: H59–H93 (H68 is built in 49), H103, H105 and H123, with the client statement on the client page's Commissions tab; firm statements on a nullable `Document.deal` | A statement is entered or read, posted, and reconciled against the records | answered: OQ6 (No); OQ78 and OQ79 wait with it |
| 51 | AI-8 · L | 40, 41, 47 | D29, D41, D42, D109, D110, D112, D134, B39, B40, C11, C19; `CensusImport.job` | A synthetic PDF roster becomes a staged census import, handed to the Census tab; the mapper sends column shapes only | — |
| 52 | QST-3 · M | 43, 51 | G's Q6 (D113, G99–G102, G106–G109) | A synthetic filled form is staged, and never applied to a signed form | — |
| 53 | REV-1 · L | 40, 41 | L's V1: models, rules, link services, a minimal New link, the Waiting lane, `summary.facts` and the tab's own counts (L1, L2, L28) | A link is created, copied and revoked; the Waiting lane and the pills count it | OQ80–OQ83 |
| 54 | REV-2 · XL | 47, 53 | V2: the portal for intake, census and documents (B43, C35); "This link has moved" for old `/b/` links (L136) | A client fills answers and uploads files on a phone-sized screen | OQ84–OQ86 |
| 55 | REV-3 · L | 46, 54 | V3: queues, approvals, section bars, the rfp export-check provider (B38, C28, C32, C34) | An approved answer is stored with origin `client` | — |
| 56 | REV-4 · L | 55 | V4: the tray with its count and destination (L49), notes, threads, request page (B12) | Asks gathered in the tray go out on one link | OQ87 |
| 57 | REV-5 · L | 56 | V5: builder, Ask card, settings card, People & links, edit mode, comment margin (B37, C27 without its saved filter setups, C30); the contact partition (C29) only if OQ88 keeps it. Census filter sets (F30) wait (OQ7) | The Ask card changes an open link | OQ88; answered: OQ7 |
| 58 | REV-6 · L | 43, 57 | V6: questionnaires in review and on the portal (G68–G81, G83–G90, G92–G98) | The client answers the form and signs as the officer | — |
| 59 | REV-7 · M | 51, 58 | V7: reads started by client uploads, then the receipt (D44, D45, L125, L135) | A client's census file becomes a staged import that staff apply | OQ89 |
| 60 | AGD-1 · L | 38, 49, 59 | I's AG1: steps (the commission step included), marks, tasks and the deal's Agenda tab | GD3's next step reads "Add the census, or type enrollment in the Advisor"; Later holds a step until its day | OQ90–OQ93 |
| 61 | AGD-2 · L | 60 | I's AG2, with A9–A12, A23 and A24: the `journey/` read for the shell (badges and meters); the Work queue, Prospects (the old New clients view, I86) on the work feed with each row's `client_status`, and stats; Clients gains Next action; a sale moves its client from Prospects to Clients at once (I122 as changed by OQ101 c; OQ91) | The shell shows the stepper and badges; the dashboard's numbers are real; selling GD2's plan moves it from Prospects to Clients, showing its commission step | OQ91, OQ94, OQ95, OQ101 |
| 62 | OVW-1 · L | 49, 61 | M's O2: the Overview shell, header, banners, tiles and stepper, with the renewal-offer chip (M20); the client box (M21, M23): for a client, a link (to the client dialog until slice 67), and for a prospect, "Not on the client book yet" with Convert to client; deals open on the Overview. M.6's deal-type test reads "…while its client becomes a New client" | The block order matches the old Overview | OQ96, OQ101 |
| 63 | OVW-2 · L | 58, 62 | M's O3 and O4: Card 1, Card 2, feed, notes, side cards. Timeline and NotesCard take deal ids or a deal, so the client page can mount them | Every Card 1 control writes through its owning app | — |
| 64 | OVW-3 · M | 22, 63 | M's O5: review's `confidence` and `mark_document`; the re-check panel | Confirm all for one document can be undone | — |
| 65 | DOC-5 · M | 39, 41 | E43–E45, D130; the pop-out window (E69–E71, D128); browser OCR for scanned pages (E25) | The census file opens beside its roster; a scanned SBC page highlights its values; the pop-out follows the keys | OQ97–OQ99 |
| 66 | AI-9 · S | 20 | Voice input (D20) | The microphone dictates into the composer | — |
| 67 | CLI-1 · L | 63 | The client page (§8; CL13–CL23, CL26): the route `/clients/:clientId/:tab` and the sidebar with its Plan year block (CL13, CL14); `overview.client_payload` behind `GET clients/{id}/overview/`; `client_feed` behind `GET clients/{id}/activity/`; the Overview tab (CL15–CL22) with G116's artifact chips; the Notes tab (CL23); the ways in switch to the page, and the client dialog retires (CL26); E71's presence | GD1-sold opens on its client page in the old ClientWorkspace look (Look, with the deferred parts labelled); GD2's page offers Convert to client, which makes it a New client with an Activity row; on GD6, History's chips open the deal's Intake, Census and Questionnaire; the overview read's query count does not grow on GD-Big | OQ101 |
| 68 | CLI-2 · M | 67 | `agenda.client_agenda` behind `GET clients/{id}/agenda/`; the Agenda tab (CL24) with the nav badge and the rollup chip; the Commissions tab (CL25), mounting H106's client split and the client's booked records by tier | A task added on GD1-sold's client Agenda shows on the deal's Agenda and in the Work queue, and Later holds it; a 60/40 client split saves; an own-tier producer sees only their own share | — |

**→ Milestone 2 (13.13).**

### 13.11 Client lifecycle and client page items

OQ2's answer adds work that no porting part lists. Its items follow the parts' verdicts and are numbered CL1–CL28; §5.1
has the status rules and §8.5 the client page. A client's status is a client fact, stored on `deals.Client`; the deal
type (New business or Renewal, M14) is a different thing.

| # | Item | Verdict | Slice |
|---|---|---|---|
| CL1 | Status Prospect, New client or Existing client on `Client.relationship`, with `client_since` and `converted_by_sale` | New | 6 |
| CL2 | A sale makes a prospect a New client (replaces the flip to existing) | New | 6 |
| CL3 | Un-selling the last sold plan returns a sale-made New client to Prospect | New | 6 |
| CL4 | Convert to client by hand (the old "Link to client"), refused on a lost deal | New | 6; the Overview's client box 62; the client page 67 |
| CL5 | Back to prospect by hand, refused while a plan is sold | New | 6 |
| CL6 | A client is created as a Prospect or an Existing client; it becomes a New client only through CL2 or CL4 | Simplify (was Type New / Existing) | 6 |
| CL7 | New client → Existing client when the first plan year ends or the first renewal starts | Defer (OQ1) | — (refused with a sentence) |
| CL8 | `opened_as` follows the status until the deal's sale; `deal_type` is Renewal only for an Existing client | Simplify (M14, H30) | 6 (from 38) |
| CL9 | Status in client rows, the client detail, the deal header and `/api/meta/`; a comma filter | Simplify | 6 |
| CL10 | Home pills Prospects · Clients · Work queue (the old "New clients" relabelled) | Simplify (A9, I87) | 4; Work queue 61 |
| CL11 | Prospects view: I86, filtered by status | Simplify | 4 on `clients/`; 61 on the work feed |
| CL12 | Clients view: the old book's look, New and Existing clients, chips | Simplify (A13) | 4; Next action 61 |
| CL13 | Client page shell: route, sidebar, grouped nav, badges, rollup chip | Keep | 67 |
| CL14 | Sidebar "Plan year" block: the current deal's sections, linking to the deal page, with its Intake, Census and Proposal meters | Simplify | 67 |
| CL15 | Overview title row: Convert to client and Archive client… | Keep / New | 67 |
| CL16 | Header card: status, client since, effective date, owner, the client box and the facts | Simplify | 67 |
| CL17 | Waiting banner from the current deal | Keep | 67 |
| CL18 | Tiles: Effective, Agenda, Expected revenue | Simplify | 67 |
| CL19 | Deal card, in the old Renewal card's look | Simplify | 67 |
| CL20 | Coverage in force: the sold plans, or a prospect's current coverage | Simplify | 67 |
| CL21 | Activity across the client's deals, with the status rows | Keep | 67 |
| CL22 | Side cards: commission snapshot, latest notes, History with artifact chips | Keep | 67 |
| CL23 | Notes tab: the standing brief and the deal's notepad | Keep | 67 |
| CL24 | Agenda tab: per-deal panels, Add a task on a deal, Done, `?focus=` | Simplify (I103) | 68 |
| CL25 | Commissions tab: the client split and booked records, by tier | Simplify | 68 |
| CL26 | Ways in from the deal: the sidebar's client block (clients only), the Overview's client box, the header's client name | Keep / Simplify (A20, M21, M23) | 62, 67 |
| CL27 | Plan years, Notifications and Deals & history tabs; the year strip and year pages; the next-plan-year chip; Start renewal; the upkeep card; Received figures | Defer (OQ1, OQ6) | — |
| CL28 | Unlinked deals and Link to client on the client page; service owner, P&C, Inactive, External ref | Drop | — |

**Porting rows OQ2 changes** (plan.md wins over the parts here):
- **New verdicts.** I103 Defer → Simplify (CL24). I109 splits: the client nav badge is Keep, the agenda preview Simplify
  (CL19), link-client becomes Convert to client (CL4), and the Notifications links stay Defer. M101 Defer → Simplify
  (CL13–CL22). M23 Drop → Simplify: a prospect's client box offers Convert to client (slice 62). M21 Simplify → Keep: it
  opens the client page from slice 67. M19 Defer → Drop: P&C is not in 2Vantage. A9, A13, I86 and I87 Keep → Simplify:
  the first view is Prospects, Clients lists New and Existing clients, and the Archived page shows status. I122 keeps
  Simplify but changes behaviour: a sold deal no longer stays on the first view until its effective date, because the
  sale moves its client from Prospects to Clients at once (OQ101 c; OQ91's default changes with it).
- **New wording or home, same verdict.** A20: the client block shows for clients only and opens the client page (67);
  its year strip stays Defer. M14 and H30: `opened_as` follows the status until the sale, and nothing flips at the sale;
  M.6's test reads "a won prospect stays New business while its client becomes a New client". I123: agenda reads
  `deal_type` (O.6 #25), never `Client.relationship`. H58: its outside client gets a status, Existing client by default.
  H103 and H105 belong on the client page's Commissions tab when slice 50 returns. H106 ships in slice 48 and is mounted
  in 67–68. H41 sits on the header card. G116, and E71's client-page half, are built in slice 67, G116 through
  `summary.facts`, so O.6 #43's wait for OQ2 ends.
- **Still Defer:** A15, A28, I9, I72, I88, I104–I108, M22, M78, M102 and H104.
- **Questions this answers:** A-Q2, H-Q10 and the client-page part of M-Q2.

### 13.12 Parallel work and risks

**Parallel work.** Review stays one slice at a time. A slice may be built ahead on its own branch (a git worktree) and
rebased when its Needs are committed. After a rebase, the branch deletes its unmerged migrations and makes them again,
so migration numbers never clash.
- After slice 1: the look and parity (2–3) beside slice 5; slice 6 follows 3 and 5, and slice 4 follows 6.
- After 4 and 6: the Advisor lane (7–10) and documents (15–16).
- After 9: intake and census (11–12), then the Documents and Claude lane (17–24) beside the Advisor lane (13, 14).
  Joins: 17 needs 9; 18 needs 13; 24 needs 10 and 11.
- Staging (69, OQ105) any time after 16; it must be in before Milestone 1, and before 47.
- Phase 3: the workbook (27–28) beside the PDF (29), then 30, 31 and 34; 35 and 36 whenever their Needs are in; FND-3
  (38) once 25 is in.
- Phase 4: 38 beside 41; the questionnaire after 40; rfp joins both.
- Phase 5: commission (48–49), the readers (51–52) and review (53–59) in parallel; slice 50 waits (OQ6). Agenda and
  Overview come last, because they read every app; the client page (67–68) follows 63 and runs beside 65–66.

**Risks to this order.**
1. Real carrier files wait for OQ29. Slices 18–24 are built on synthetic files; the golden-deal trial (OQ31) runs once
   the key is confirmed.
2. Slices 27–31 port the largest old files, about 2,000 lines each.
3. Agenda (60) relies on the stored counts of slices 12 and 17.
4. The cascade breaks if a sheet is imported out of order: one manifest, the port proof, stylelint and the Look lane
   guard it.
5. Until slice 61 the shell has no stepper or sidebar badges; Milestone 1's Look labels mark them "pending slice 61".
   The Review tab has its own counts from slice 53. Until slice 67 the client dialog stands in for the client page, and
   Clients rows open the deal.
6. The old app keeps changing: two commits landed while this plan was written. 13.3 pins the commit the port follows.
7. The old loader is real work, because the old app stores one row per value. Each golden deal adds its part in the
   slice that seeds it.
8. The client status has one owner and two callers: deals' services change it, and quotes' `set_sold` calls
   `sale_changed` inside the sale's transaction (slice 6); quotes also fills `deals.providers.client_has_sold`. Slice 7
   rewrites `set_sold`; slice 6's lifecycle tests, with the invariant that a client with a sold plan is never a
   Prospect, guard the call.

### 13.13 Milestones

**Milestone 1 — the Advisor and the Proposal (after slices 37 and 69; 69 under OQ105).**
- Gates A and B (V.2) on slices 1–37 and 69: GD3, then GD1, walked on staging once as an admin and once as a producer,
  need by need.
- Priced versions, stop-loss (with its arrows, OQ13), Rank, the pair fold, the builder cards and templates work. The
  600-plan budget and `-m recalc` pass.
- Not yet built: contacts and notes (38), intake budget hints (39), the questionnaire, the asked carriers on Markets
  checked (46), booking on a sale (49), the portal, the stepper (61) and the client page (67–68). The client status
  works from slice 6.
- Then Gate C, Stephanie's walk (the old M9), on plan data and typed counts.

**Milestone 2 — the full MVP (after slice 68).**
- GD6 works end to end: intake reaches Ready; the census is imported and fixed; the questionnaire is signed; the packet
  and drafts are sent (Quoting); a client answers on the portal and staff approve; quotes are read with Claude; the
  Advisor; the Proposal is issued; the plan is sold and booked; the client is listed under Clients as a New client, and
  its client page shows the sale.
- Agenda, Overview and the client page are right at every step. The quote-first deal is never shown as "skipped".
- Gates A, B and C run again, because slices 38–68 change shared code (headcount, booking, journey, client status). The
  PHI gate is passed, so Gate C may use a census. The MVP is accepted on V.2's exit criteria.
- The speed budgets and `-m recalc` pass. No file is over 300 lines except data modules, and no test reads source. The
  class-usage sweep removes unused CSS.
- Left out unless Daniel says otherwise: the ledger (50; OQ6), renewals and the existing-client features (plan years,
  reminders, notifications, renewal history, year pages; OQ1, OQ2), census filter sets and bundle templates (OQ7), the
  status report, Unleashed, the share link, Plan my day and Classic (OQ4, OQ8).
- Cutover follows OQ100.

---

## 14. Working agreement and CLAUDE.md

### 14.1 The working agreement

Daniel owns the product and reviews every change; whoever builds (a person or Claude Code) works to this agreement.
CLAUDE.md (14.2) is its short form.

- **Precedence.** plan.md v2.0 is the normative core and the build order; the docs/porting parts are the detailed
  specifications (their X.3 inventory rows and X.6 designs); where they disagree, plan.md wins, then Part O, then the
  module part; the old v1.1 text is superseded wherever the porting parts say otherwise.
- **One slice at a time.** Build only what the current slice (§13) names, with every open question at its §16 default.
  Daniel reviews and commits each slice before the next is reviewed; changes are left uncommitted for him. Work ahead
  follows 13.12.
- **A port, not a redesign.** The port follows old commit 891f1b3 (13.3); a later old-repo decision is listed for Daniel
  before the slice that ports its area. The old repository is read-only, and nothing under `aBenefitsMeetings/` is ever
  opened (Appendix A). Screens and client files match the old app on the same golden deal. Each intended difference is
  labelled with its item ID (Q.5), and Daniel judges each label once.
- **Done means V.1.** The slice's Needs are committed and the old commit it ports from is named; each item it builds has
  behavioural tests named with its ID; the golden deals are extended, and a key changes only with Stephanie's agreement;
  Fast, Front and Lint are green within budget; the Q.3 contracts cover every new service and endpoint; the canaries,
  Recalc, Fidelity, Look and Eval run where the slice touches PHI, a painter, a screen or a reader; and the "done when"
  is walked on a golden deal. The summary for Daniel lists the files changed, the item IDs built, the needs advanced,
  the intended differences added, the lanes run with their results, what to check and what is next.
- **Open questions.** docs/porting/decisions.md is the open-question register, not a decision log. Each question there
  has a default, built until Daniel answers, and names the slice its answer changes; Daniel answers in that file. A new
  question, such as OQ101, takes the next number in that file and in §16. An answer is written, with its date, into the
  plan.md section it governs, and its §16 row is marked answered, no later than the slice it changes. Apart from that
  register there is no decision log, no generated map or digest, and no document whose line counts are tested.
- **The spec changes with the code.** When a rule in this spec changes, update the spec section in the same change.
  CLAUDE.md and 14.2 change together.

**After a slice ships, its §4 table points at the code.** §4's tables become Python constants; keeping both in sync by
hand would double every change. When the last slice that implements or changes a §4 table is committed, replace the
table in this file with one line naming the module, and change the module from then on. §4.1, §4.3 and §4.6's stages,
funding, document kinds and roles are built already (`deals/lines.py`, `deals/stages.py`, `quotes/fields.py`,
`documents/kinds.py`); §4.1 becomes a pointer after slice 13 and §4.3 after slice 36, because those slices still change
them (§4).

**Don't transcribe data by hand.** §4 and the porting parts list a great deal of business data. Generate each data
module by a one-off script from the old module that the part or Appendix C names, reading its literals with `ast` rather
than importing it, then diff the result against the §4 table or the part once and resolve every difference. A generated
module stays a data module: reviewable, and exempt from the 300-line rule (K93, G124).

### 14.2 CLAUDE.md

Slice 1 rewrites `CLAUDE.md` with this content (keep it under 80 lines; it is loaded into every Claude Code session):

```markdown
# 2Vantage — benefits workflow for prospects and new clients (Django 5.2 + DRF · React 19 + Vite · Postgres 15)

plan.md is the spec (scope §1.4, chain §3.3, build order §13, decisions §16). docs/porting/ holds the detailed parts:
A–M per module (X.3 verdicts, X.6 designs), N data flow, O architecture, Q testing; where they disagree, plan.md wins,
then Part O, then the module part. Build only what the current slice (§13) names; an open question gets its §16
default, and a new one takes the next OQ number in docs/porting/decisions.md and §16. Port from old commit 891f1b3.

## Commands ("slice N": that slice adds the command; lanes, budgets and when to run each: Part Q, Q.2)
docker compose up --build -d                    # frontend :4001, backend :8004, postgres :5436
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py seed_golden   # golden deals to click through (golden app from slice 3)
docker compose restart worker                   # job worker: manage.py run_worker, its own service (slice 16)
docker compose exec backend pytest [<app>]      # Fast lane: one app ≤10 s, everything ≤60 s
docker compose exec backend ruff check .        # then, from slice 6: docker compose exec backend lint-imports
docker compose exec backend python manage.py makemigrations --check --dry-run
docker compose exec frontend npm run lint && docker compose exec frontend npm run build
docker compose exec frontend npm test           # Vitest, pure modules only (slice 6)
docker compose exec frontend npx stylelint "src/**/*.css"; node frontend/scripts/port-proof.mjs   # CSS (slice 2)
docker compose exec backend pytest -m perf   # Perf (slice 7); Eval, opt-in: manage.py reader_eval --set all (slice 18)
Look and Walk (slice 3): npm --prefix browser run look -- --screens <key>; npm --prefix browser run walk -- --need <n>
Parity (slice 3): tools/parity/ runs old Vantage (../Vantage, read-only) as its own Compose project, with a tools image
for Recalc (pytest -m recalc, slice 27) and Fidelity (python tools/parity/files.py --deals all, slice 28).

## Map (Part O; OQ9 a; one Django app per tab; frontend folder per tab in frontend/src/deal/<tab>/)
accounts → deals → documents → ai → intake → census → quotes → questionnaire
         → commission → rfp → proposals → review → agenda → overview → golden
An app imports only from apps to its left (lint-imports); a fact read by an app lives in that app or one to its left. To
reach right, a left app owns a seam (provider slot, registry or on-commit signal) that the right app fills in
AppConfig.ready() (O.1); backend/ is the composition root. ai holds jobs, the worker, chats and the Claude client, never
business data. golden is seed-only: only seed_golden and the root conftest.py import it. Built so far: accounts, deals,
documents, ai, intake, census, quotes, questionnaire, commission, rfp, proposals, review, golden. The chain orders
imports, not screens: the deal sidebar keeps old Vantage's order and groups (A21, OQ9): Overview, Agenda · 1 Get to
Market: Review & requests, Intake, Census, Questionnaire (if the deal has a form), RFP, Commission · 2 Quote to Close:
Advisor, Proposal · Shared: Documents. Quotes never wait for intake, census or a questionnaire: typed summary tier
counts carry the Advisor and Proposal. Tab folders take the app's name except advisor/ (quotes) and proposal/
(proposals); from slice 4 a tab folder's index.js exports only what others mount. Other pages live in pages/ (home;
Archived, slice 38; Commissions, 48; client page, 67).

## Rules
1. Vocabularies are Python constants (deals/lines.py, deals/stages.py, documents/kinds.py, quotes/fields.py; from their
   slices deals/carriers.py, intake/form.py, census/fields.py), served by /api/meta/; never in JS or migrations.
2. Values live in JSON on their row with a parallel `sources` dict, written only by deals/values.apply(); an unchanged
   value writes nothing, not even its source or Activity. Status is computed on read, except the client status (rule 6)
   and stored counts (OQ9 c, slice 12: CensusFacts, `flags`), rewritten in one transaction, checked by rebuild_facts.
3. Every write goes through its app's services.py (a services/ package in a large app, OQ9 d), locks what it changes
   (select_for_update or one JSONB merge; across rows the Deal first, then owners in chain order, each by id) and
   returns only what changed. GETs write nothing but downloaded and viewed rows. Deal-tab queries use staleTime 0.
4. Every write is recorded in Activity with before and after per key (slice 5; keys only for census rows, sensitive
   questionnaire slots and lasers). Each writing app registers its reverter; Revert runs once and refuses after a later
   write to the key, and on sold plans, signed forms, issued proposals, a sale's client-status row and key-only rows.
5. Money math and all rounding live only in quotes/math/ (today math.py: round_money, float sums; slice 7 brings Decimal
   and round_decimal, half up like Excel, OQ9 b); commission rounds through it; the browser does no money math. Packages
   come only from package(); enrollment from enrollment_for; headcount from facts.enrolled_headcount (slice 13).
6. Client status (Prospect → New client → Existing client; slice 6) is on deals.Client; only deals' services change it.
7. The old look (slice 2 on): old Vantage's stylesheets, cut into ≤300-line files under src/styles/<old sheet>/ and
   imported once, in the old order, by one manifest in main.jsx (the port proof checks them). Every component, new ones
   too, uses the old class names (bb-*, bnf-*, gk-*, rr-*). No CSS modules (2V's go in slice 4), no per-route sheets.
8. No file over 300 lines, except data modules (vocabularies, tables). Split by responsibility, never by line count.
9. Sign-in is Django's session; every write sends X-CSRFToken. Every user sees every deal (OQ3). Users, their Profile
   flags (claude_direct, commissions_access; slice 6) and agency settings live in Django admin.
10. PHI (census people, medical answers, lasers, files carrying them): never in logs, Activity, Job steps, error text,
   file names or URLs; downloads and views are logged. Claude reads files whole; reads skip pages the upload screen
   flagged only while AI_MEMBER_DATA_SCREEN is on (OQ22). Test data is synthetic; real data waits for slice 47. Client
   files print only what `client: True` and J.4 allow. Never open Vantage/aBenefitsMeetings/ or any real client's file.
11. Portal views (review/portal/, slice 54): AllowAny, no authentication classes, allowlisted payloads, 404 bad token,
   410 expired; a GET writes only the open stamp; staff sessions get 403 on writes; client answers wait for approval.
12. Tests are behavioural (services, endpoints, pure functions, files read back), named with the item ID (test_F45_…),
   and pass the Q.3 contracts. No test reads source, CSS or docs (lint scripts may); no pinned counts; no network.
   Golden deals come from root-conftest fixtures (slice 3); a key changes only with Stephanie's agreement.
Until the slice that owns each, M0–M6 breaks some of these rules (plan.md §6 and §13.3 list them): never copy them.

## How a change is made (verification.md, V.1)
1. Read this file, the plan.md section and the docs/porting part for the area (its X.3 rows and X.6 design).
2. Change one app (its backend and frontend folders) or one shared framework. If another app must change, say why.
3. Run that app's tests, Vitest and the linters, plus the lanes the slice's Q.9 row names (Look, Fidelity, Walk…).
4. Click through the "done when" at http://localhost:4001 on a golden deal, beside old Vantage on the same deal (from
   slice 3); label each intended difference with its item ID (Q.5) and fix any other. Write outputs outside the repo.
5. Run the full suite once. When a rule changes, update its plan.md section in the same change.
6. Leave the change uncommitted for Daniel. Summarize: files changed, item IDs built, needs advanced, intended
   differences added, lanes run with their results, what to check, what is next.
```

---

## 15. Deliberate non-goals and deferrals

Everything Parts A–M mark Keep, Simplify or New is built, slice by slice (§13), except what §16's answers and the
rulings in §4.6, §13.2 and §13.11 change.
This section lists the rest: what is not rebuilt, and why (§15.1), and what waits, and for what (§15.2). Each part's
Drop and Defer rows give the detail.

### 15.1 Not rebuilt

These existed in the earlier system and are **not** to be rebuilt. Most made the old system slower to change; the rest
are not part of the benefits product.

**Machinery, replaced.**

| Do not build | Why |
|---|---|
| Version history with snapshots, diffs, restore, edit sessions and locks (A34, A35) | ~600 KB snapshots and a lock protocol on every write. The Activity log answers "who changed what, when", with before and after values and Revert (§3.7, O.3.2); a write locks only the rows it changes. (An issued proposal is a set of stored, protected files per issue — a record of what the client was sent, §7.12 and J103 — not version history.) |
| One database row per value (entity–attribute–value) | 60,000+ rows per large census, hand-written SQL counts and parity tests. Use JSON on the row (§3.7) |
| Field definitions in the database, seeded by migrations | Froze the field lists; every new field needed two migrations |
| Coverage-intent hashes | "Confirmed" compares the stored decisions with today's instead (B20) |
| Confirmation, review-mark, "located" and layer-stamp columns on every value | Replaced by one `sources` entry per value |
| An in-app test runner, walkthroughs or guided tours (A40) | Tests run from the terminal; tours wove test hooks into product code |
| A decision log, document line budgets, generated maps or digests, tests that read source | The main cause of 20-minute to 2-hour changes. `docs/porting/decisions.md` is the open-question register (§16), not a decision log |

**Out of the product.** Other products, or work after the sale; §1.4 lists them under "Outside this build". Each
would come back only as a porting part of its own.

| Do not build | Why |
|---|---|
| The Ask Claude help bubble, usage analytics and the dev harness (A40); demo buttons and demo seeds (A8, J162); the reports module | Not product features. `seed_golden` builds the golden deals (§12.6), and Work with Claude is built (§10) |
| The role matrix (A2) | The new app is benefits-only: admins and producers, plus two Profile flags (§1.2) |
| Data hub connectors (A22, M66) | Stubs that never connected. The firm pages they held go to Django admin and the Firm pages drawer (J155) |
| P&C, with its referral records and client badge; joint ventures, workflow boards and the form builder (H34, H119, M19) | Other products. Referral agents stay, as split rows (H12) |
| Implementation and close-out, benefit guides and the contribution model (A22, J99, J168; OQ26) | Work after the sale, outside the 13 modules in scope (README) |

v1.1 listed more here. These came back with the porting plan and are built: the Work with Claude chat and its agent
turns (OQ4), carrier questionnaires as in-app forms (OQ5), per-deal Required and Waived overrides and checklist
attestations (OQ17; B26–B28, B37, C27), the paper view and previews (J105–J118), priced versions, plan copies, merges,
slot picks, saved board setups and proposal templates (OQ7, need 9; F28, F76–F78, F80–F84, F142, J68), the Work queue
and Agenda tasks (Part I), and the client page (OQ2).

### 15.2 Deferred

Not in this build. §1.4's Deferred table lists the items of each; this table says why each waits and what brings it
back. Each item keeps its Defer verdict, and its old styles stay out of the port until it returns, at their old place in
the manifest (O.5). The client page is no longer deferred: slices 67–68 build it for prospects and new clients (OQ2).

| Deferred | Why it waits | What brings it back |
|---|---|---|
| Renewals | OQ1: "deferred for now" | Daniel's answer to OQ1. A renewal slice adds one orchestrator that calls each app's `carry_from(prior, new)` in its own savepoint (A16) |
| Existing-client work, with the Radar and its reminders (renewal reminders included) | OQ2: existing clients are not built yet | Renewals: a New client becomes an Existing client after year 1 (CL7), and the Radar returns with it |
| The commission ledger | OQ6: "No" | Slice 50 (COM-3), which keeps its number; OQ78 and OQ79 are answered first |
| Pay paperwork | Outside the deal workflow; payouts were never built, and W9 files need their own storage rules (H99, H107) | OQ77: after the MVP |
| Claude Unleashed, lessons and saved readers | OQ4's default | OQ4. Meanwhile Claude's row and note tools (J160) and admin carrier notes (D119) stand in |
| Claude's chat tools for the census and questionnaires | Roster writes go through the Census review until the PHI gate (D111), and they are not among Daniel's needs (G103) | Daniel asking, after the PHI gate (slice 47) |
| Classic, the `/p/` share link, the status report, Plan my day | OQ8's default | OQ8. The share link would live in review, on its `ClientLink` (J156) |
| Census filter sets and bundle templates | OQ7, our judgement | Daniel asking. Census filter sets would reuse `quotes.SavedView` (F30) |
| The Acrobat original of the Florida Blue form | OQ57's default: underwriting takes the stamped copy | Florida Blue asking for its original (G58) |

Smaller deferrals keep their reasons in their part's X.3, for example range copy and paste (F75) and antivirus on
uploads (E104, which waits for the PHI gate). v1.1's R2.1, copying a plan design from an earlier deal, is not in this
build: no porting part lists it, and OQ110 asks Daniel whether to add it (§13.2).

---

## 16. Decisions

Every open question has a row here. Each row gives the default, which is built until Daniel answers, and the slice the
answer changes. Each default is isolated, so a change is cheap. Rows sit under the first slice their answer changes, in
the order of `docs/porting/decisions.md`, whose tags name the source questions in Parts A–M. Daniel answered there on
2026-11-11; his words are quoted in the Decision column. A blank answer keeps its default: OQ4, OQ8, OQ11, OQ12, OQ16,
OQ19 and OQ21 are *Open (blank)*, and §1.4's scope is built on OQ4's and OQ8's defaults. Every answer is also written
into the section it governs, with its date.

Questions the team answered earlier, in the old system's meetings or by Daniel, are written into the sections they
govern, with the date and speaker: recommendations, consolidation and plans bought together (§5.4–§5.5), age-banded
quotes (§5.5), the stop-loss and TPA rows (§4.3), gender, hours and SSN-to-quote (§4.4) and the size-band threshold
(§5.7).

Slice numbers are §13's: slices 67 (CLI-1) and 68 (CLI-2) are new and come from OQ2, and slice 69 (STG-1) builds
staging (OQ105). Ten questions are new. OQ101 comes from OQ2's answer. OQ102–OQ106 and OQ110 come from checking v1.1
against the porting plan: the "+ Plan" prompt and "+ Package" dialog, the rate-basis examples, lasers on client files,
staging, contact roles and copying a plan design. OQ107–OQ109 are v1.1 §16's open rows #1, #2 and #11, numbered.
Add them to decisions.md when this version is agreed, and update OQ91's and OQ95's defaults there (OQ101 c).

**Status.**
- *Answered*: built as Daniel answered. This is the same as the default unless the row says otherwise: *changes
  default* (the answer differs from the default), *our judgement* (Daniel asked us to decide; OQ7), *adds* (the answer
  adds a rule the question did not ask about; OQ9).
- *Open*: the default is built. *(blank)*: Daniel left it unanswered. *(Stephanie)* and *(developer)* name who answers
  when it is not Daniel. *Default changed by OQ101 (c)* or *reworded by OQ101 (c)*: decisions.md's default or wording
  no longer fits the client status, so this row's is built. *Waits with 50*: asked again only if slice 50 returns
  (OQ6).

| # | Question | Decision | Status | Slice |
|---|---|---|---|---|
| **Before slice 1: scope and conventions** | | | | |
| OQ1 | Renewals: carry last year's data; past years, revalidation, renewal history, earlier-year chats, reminders? | "deferred for now." Deferred, with existing-client work (OQ2; §15.2) | Answered | 1 |
| OQ2 | Rebuild the client page, with a client-level Overview and Agenda? | "overview yes, agenda yes, rebuild client page yes but in reality we have prospects new clients and then clients after year 1. first they start off as prospects and we need to be able to transfer them over to new clients and then existing clients. prospects and clients needs to be built out but existing clients does not need to be." Applied: a client lifecycle, **Prospect → New client → Existing client** (CL1–CL28). Prospects and new clients are built now: the status and its moves in slice 6, the Prospects and Clients home views in slice 4, and the client page in slices 67–68, with Overview, Agenda, Commissions (the client split and its booked records) and Notes tabs. Existing-client work (plan years, renewals, reminders, Notifications, Deals & history, the move to Existing client) waits with renewals (OQ1), and the client statement with the ledger (OQ6). This replaces v1.1's "the client becomes existing when a deal sells". Open part: OQ101 | Answered, changes default | 1; 4, 6, 7, 38, 48–49, 61–63, 67–68 |
| OQ3 | Does every producer keep access to every deal? | "yes." (A43) | Answered | 1 |
| OQ4 | Work with Claude: keep the chat, with quote reads by admins and direct people landing at once with Undo? Defer Claude Unleashed (D-195, D-224) and use Claude's row and note tools (J160) meanwhile? Defer lessons and saved readers in favour of admin carrier notes? | Open. Default: yes to all | Open (blank) | 1; 19–20, 24, 37 |
| OQ5 | Is the questionnaire in scope, with all three forms (Florida Blue 51+, Warner large group, SIIA disclosure)? | "yes." | Answered | 1; 42–43, 52, 58 |
| OQ6 | Are the commission ledger's statements, reconciliation, gaps and statement reading in the first build? | "No." Rates, splits, booking and the Book are built (slices 48–49). Slice 50 waits, and OQ78–OQ79 wait with it | Answered | 1; 50 out |
| OQ7 | Keep what v1.1 §15 called non-goals: the priced-version composer, saved setups and proposal templates? | "im not sure what all of this is use your best judgement." Kept: the priced-version composer (one plan at several premiums; F76–F78, F80–F84), the Advisor's saved setups Mine and Shared (F28), stop-loss settings (F29) and proposal templates (J68). Deferred: census filter sets (F30) and bundle templates (F79) | Answered, our judgement; changes the default for F30 | 10, 34–36, 57 |
| OQ8 | Are Classic, the `/p/` share link, the status report or Plan my day needed? | Open. Default: all deferred; the Work queue stays | Open (blank) | 1; 61 |
| OQ9 | Four conventions: (a) the chain (questionnaire after quotes, agenda after review, rfp before proposals, a seed-only `golden` app); (b) `quotes/math/`, with commission rounding only through `round_decimal`; (c) `CensusFacts` and row `flags` stored and checked against a rebuild; (d) `services/` packages in large apps | "the order on the side navbar should be the same as the existing vantage repository but not having a questionnaire should not hinder us from loading in quotes that is why we have the editing summary tiers functionality." Applied: (a)–(d) accepted. The deal sidebar keeps old Vantage's order and groups exactly (A21): Overview, Agenda; 1 · Get to Market: Review & requests, Intake, Census, Questionnaire (only when the deal has a form), RFP, Commission; 2 · Quote to Close: Advisor, Proposal; Shared: Documents. A tab not yet built is left out until its slice, and the Look lane labels it "pending slice N" (slice 4). The chain orders imports only, never screens. Quotes sit left of questionnaire, so a missing questionnaire never stops quotes loading. Typed summary tier counts (F85–F92) carry the Advisor and Proposal with no intake, census or questionnaire | Answered; adds the sidebar-order rule | 1; 3–7, 12, 17 |
| **Slice 2: LOOK-1** | | | | |
| OQ10 | Undefined colour tokens (`--muted`, `--accent` and others): keep what rendered, or use the intended colours? | "keep what rendered." | Answered | 2 |
| **Slice 6: FND-2** | | | | |
| OQ101 | Prospect to client. (a) A prospect becomes a New client automatically when a plan on its deal is marked sold, or by hand with Convert to client; un-selling undoes only a conversion the sale made; Back to prospect is refused while a plan is sold. (b) New client → Existing client waits with renewals (when the first plan year ends or the first renewal starts); until then a client is Existing only when created as one, for a group the firm already serves, or set by hand while nothing is sold. (c) The old "New clients" view is labelled "Prospects"; won clients list under Clients, with chips New clients and Existing clients | Open. Default: yes to all three (CL1–CL12) | Open | 6; 4, 49, 61, 62, 67 |
| OQ108 | Do the old constants modules import on their own, so §4's data modules can be generated? (v1.1 §16 #2) | Open. Default: parse their literals with `ast`. Mostly moot from slice 3, when the old app runs in its own Compose project (Q.5) | Open (developer) | 6; each data module's slice |
| **Slice 7: ADV-1** | | | | |
| OQ11 | Once a line has stars, must its renewal have its own star to print? | Open. Default: yes, the old rule | Open (blank) | 7 |
| OQ12 | May a line have several sold plans? (The old app un-sold the other.) | Open. Default: allowed | Open (blank) | 7 |
| OQ13 | May stop-loss plans be reordered with the arrows and slot picks? | "yes." Stop-loss follows the one order rule (`order.layout`) and takes arrows, slot picks and reset like every line. **This reverses the old app**, which kept stop-loss in the order added (F49) and refused arrows and picks (J7) | Answered, changes default | 7; 9, 14, 36 |
| OQ103 | The rate bases with no golden deal (`volume_1000`, `weekly_10`, `payroll_100`) need one worked example each, as v1.1's R2.4 asked. May Stephanie sign them before slice 27, which prints them, while slice 7 pins provisional examples? This adds a gate on Stephanie beyond V.4's GD1 and GD2 keys | Open. Default: yes. Slice 27 found no signed examples (decisions.md says "answered by Stephanie", but no example is filed): the workbook's tests print §5.5's and slice 7's provisional examples for every basis until hers are filed | Open (Stephanie) | 7; 27 |
| **Slice 8: ADV-2** | | | | |
| OQ110 | Copy a plan design from an earlier deal (v1.1's R2.1)? No porting part lists it | Open. Default: not in this build; carrying last year's plans waits with renewals (OQ1) | Open | 8 (only if yes) |
| **Slice 10: ADV-4** | | | | |
| OQ14 | Should "UHC" find UnitedHealthcare in the finder and in Find on Documents? | "yes." | Answered | 10; 23 |
| **Slice 11: INT-1** | | | | |
| OQ15 | Keep both the coverage subcards and the intent card, or merge them? | "yes", read as accepting the default: keep both, through one service | Answered | 11 |
| **Slice 12: CEN-1** | | | | |
| OQ16 | Is SSN optional and never asked on the portal, or required as in the old app? | Open. Default: optional, masked, never asked on the portal | Open (blank) | 12 |
| OQ17 | Keep the per-deal Required and Waived overrides for each intake question and census column? | "keep." v1.1 §15 had dropped them | Answered | 12 |
| **Slice 13: ADV-5** | | | | |
| OQ18 | Do counts typed before the latest census import give way to it, with "Keep my typed counts" (F91), or do typed counts always win (H7)? Keep the builder's EnrollmentStrip? | "yes keep the strip.", read as accepting the default: F91, and the strip stays (J48) | Answered | 13; 25 |
| OQ19 | Do typed medical counts also price worksite tier-rated lines ("Borrowed from medical"), but not dental and vision? | Open. Default: yes | Open (blank) | 13 |
| OQ20 | When a second current plan arrives, should unlinked quotes keep pricing from the whole typed line figure until it is split? | "no; they ask what they replace." | Answered | 13 |
| OQ21 | The band's headcount: the Advisor's medical enrollment, then intake's enrolled count, then an estimate (the old app put intake first), with a warning naming all three? | Open. Default: yes | Open (blank) | 13 |
| **Slice 15: DOC-1** | | | | |
| OQ22 | Member-data screen for Claude reads: follow D-225, or always screen (D52)? | Open. Default: follow D-225. The screen runs at upload, and reads leave flagged pages out only while `AI_MEMBER_DATA_SCREEN` is on | Open | 15 |
| OQ23 | Should Remove archive a file (restorable, values stay linked)? Is a true purge ever needed? | Open. Default: archive, plus an admin-only purge | Open | 15 |
| OQ24 | Do files over 30 MB arrive? | Open. Default: a 30 MB cap | Open | 15 |
| OQ25 | Should the sheet viewer show hidden rows and columns greyed? | Open. Default: yes | Open | 15 |
| OQ26 | Do the wrap, POP and sold-paperwork file types wait for close-out and implementation? | Open. Default: yes | Open | 15 |
| OQ27 | Are invoices PHI, given that list bills name members? | Open. Default: no | Open | 15 |
| **Slice 17: DOC-3** | | | | |
| OQ28 | What needs approval: values Claude doubted or the locator missed (the old app), or every value Claude read? Does Claude never confirm its own value (D-119)? | "only the values claude doubted need approval, but even unapproved values shouldn't stop the user from continuing. just give a little flag saying X number of things should be reviewed" (2026-11-11). Applied: the old meaning, one rule (`review_rules.open_warning`): a value Claude read and doubted, or that the locator could not find in its file, until a person approves or ignores it, plus anything a person flagged ⚑; a typed value the file does not print is not one (§3.7, §10.7). Nothing is blocked by unreviewed values; the Advisor and the station show "N AI values to review". A person always applies; Claude never confirms its own value (D-119) | Answered | 17 |
| **Slice 18: AI-1** | | | | |
| OQ29 | The BAA and the key: only the Foobalabs key, and real files only after Anthropic confirms coverage in writing? | "live data is allowed in this version" (2026-11-12): the BAA prerequisites are met. Applied in slice 18: only `settings.ANTHROPIC_API_KEY`, the Messages API with no beta features; tests, seeds and the Eval corpus stay synthetic and no build step opens a real client's file (§10.8). Slice 47 records the key as confirmed under the BAA, with this answer as its source (`deploy/phi-gate.md` items 1–2) | Answered | 18; 47 |
| OQ30 | With no census, should Claude propose a quote's printed tier counts, unticked: as the line's figure, or per current plan when printed per plan? | Open. Default: yes. Built in slice 18 (`quotes/reader/counts.py`): per current plan when printed per plan, else as the line's figure, always unticked; with a census on the line they are not proposed and a finding says so | Open (default built) | 18 |
| **Slice 20: AI-3** | | | | |
| OQ31 | Should the golden-deal trial set the default model, read effort and cost caps, with Opus 5.5 kept to admins and direct people? (v1.1 §16 #7) | Open. Default: yes. Built in slice 20 on the default: Opus 5.5 is offered and stepped up to only for admins and direct people (D91); until the trial, §3.5's settings stand (Sonnet 5.5, effort high for reads, $3 a run, $25 a deal) | Open (default built) | 20 |
| **Slice 21: AI-4** | | | | |
| OQ32 | Need 3: show "As quoted" in the Advisor, on Documents, or both? Should printed rows that match no field reach the client files? | Open. Default: both screens; client files keep the quote's plan order but the house rows. Built in slice 21 on the default: the Advisor's "As quoted" view and Documents' "▤ As in the file"; printed rows that fill no field stay in `QuoteLayout` only and never reach values or client files | Open (default built) | 21 |
| **Slice 22: AI-5** | | | | |
| OQ33 | Should SBC reads wait for review even for direct people? | Open. Default: yes (D71). Built in slice 22 on the default: the SBC reader is `must_review`, so every SBC read waits for a person's "Use this scan ▸", an admin's and a direct person's too | Open (default built) | 22 |
| **Slice 24: AI-6** | | | | |
| OQ34 | Should only admins change a deal's AI budget? | Open. Default: yes. Built in slice 24: `PATCH deals/{id}/ai/` `{budget_usd}` answers 403 for anyone but an admin; admins set it with ✎ Budget in the drawer's head bar (D100) | Open (default built) | 24 |
| **Slice 69: STG-1 (after slice 16)** | | | | |
| OQ105 | v1.1's M2, staging, was never built and Part P has no slice for it, though V.2 runs Gates B and C on staging. Add slice 69 STG-1 after slice 16, with slice 47 and Milestone 1 waiting on it? | Open. Default: yes (§11.1, §13.2) | Open | 69; 47, M1 |
| **Slice 25: PRO-1** | | | | |
| OQ35 | Do files not yet issued carry Draft, are option numbers stamped only at Issue, and does an issue store all three files? | Open. Default: yes | Open | 25 |
| OQ36 | Keep the old per-line "Option n" (renewals numbered; current plans and priced versions not) instead of C/R/P labels? | Open. Default: yes | Open | 25 |
| OQ37 | Recommending a current plan: keep Daniel's 2026-11-10 rule, or allow it as the old app did? | "allow it as the old app did." Applied: a current plan may be recommended; it means "Keep this plan", covers itself, uses no extra column in `room()`, shows no change and prints "Keep this plan"; a plan turned current keeps its recommendation (§5.4, as old 891f1b3). Kept lines still need no pick | Answered, changes default | 7; 25 |
| OQ102 | v1.1's "+ Plan" prompt (is a second alternate for the same current plan an option, or bought together?) and its member-built "+ Package" dialog have no porting row; F134 leaves them to the Proposal section | Open. Default: keep both as 2V built them; slice 25 places them (F134) | Open | 25 |
| **Slice 26: PRO-2** | | | | |
| OQ38 | Show the carrier's renewal offer ($/yr, % change) in the renewal blocks (J65) and on the Overview chip (M20)? | Open. Default: yes. Slice 26 built the blocks with the default; they refuse ("No renewal letter's figures on this deal") until the letter's four facts are stored on intake's CurrentCoverage, which no slice has added yet | Open | 26; 62 |
| **Slice 27: PRO-3** | | | | |
| OQ39 | Does a carrier hidden on Markets checked also leave Compare and All Plans, labelled on screen? | Open. Default: yes. Built in slice 27: its unpresented quotes leave All Plans and the drop-downs, counted in an All Plans note; the Markets card says so | Open | 27 |
| OQ40 | Stephanie's Excel review: her marked-up rows and colours, the disclaimer wording, and whether plan notes, telehealth and Rx mail order print (v1.1 §16 #3–#5) | Open. Default: the old formats. Built in slice 27 as the old app printed them: the old rows (telehealth, mail order and the worksite Notes rows print), colours and the old disclaimer paragraphs | Open (Stephanie) | 27 |
| OQ41 | Firm pages: logo, colour and contact in Django admin; About, figures, calendar and team in an in-app drawer; "Prepared by" from the agent-name rule? | Open. Default: yes. Slice 27's Cover prints the agency's logo, name, phone and email from Django admin, with `deals.rules.agent_name` on the contact line; slice 34 built the Firm pages drawer (About, figures, calendar, team with photos) and took them out of Django admin | Open | 27; 29, 34 |
| OQ104 | Lasers on client files: print laser liability as amounts and list lasers by position, never the claimant ids or initials in `sl_lasers`, which the old stop-loss sheet printed? | Open. Default: yes (§3.8, §4.3, §9.13). Built in slice 36 with the default: the workbook and the board name lasers by position; Activity keeps a laser's key only (`deals.activity.key_only_values`) | Open | 27; 36 |
| **Slice 33: PRO-9** | | | | |
| OQ42 | Florida Blue 5182 and 5183 under D-219: should the in-network single deductible print "EE $2,500 / PP $5,000" or "$2,500"? | Open. Default: both figures (built in slice 33: `proposals.pair_fold`) | Open | 33 |
| **Slice 36: ADV-8** | | | | |
| OQ43 | Is the stop-loss workbook still the client document for self-funded deals? | Open. Default: kept. Built in slice 36 with the default (client fields only, §9.13) | Open | 36 |
| **Slice 37: AI-7** | | | | |
| OQ44 | Should Rank clear hand-picked stars outside the filter? | Open. Default: no (F.5 #11). Built in slice 37 with the default: Rank on a filtered board replaces only the stars among the plans the board shows; every star outside the filter stays. Rank on a whole line replaces the line's stars, hand-picked ones too, as the old Rank did (`quotes/rank/rules.py`) | Open | 37 |
| **Slice 38: FND-3** | | | | |
| OQ45 | Does anyone act as agent of record without a login? Is the owner always the primary producer? | Open. Default: an "Agent of record" field that falls back to the owner, then the agency producer; saving a split's primary sets the owner | Open | 38; 48 |
| OQ46 | Does Archive hide the client and its one deal, even a sold one, with links that stay readable but refuse writes? | Open. Default: yes | Open | 38 |
| OQ47 | Client deletion: never (405), or admin-only when the client has no sale and no ledger row? | Open. Default: never; archive instead | Open | 38 |
| OQ48 | Is the lost reason optional (the old screen) or required (v1.1 §5.1)? | Open. Default: optional | Open | 38 |
| OQ49 | A typed "Potential deal size" in the header? | Open. Default: yes | Open | 38 |
| OQ106 | Contact roles: keep the old app's eight, or seven without `partner_agent`, whose split partner is marked on the commission split instead (H13, M81)? B13 keeps eight | Open. Default: seven (§4.6) | Open | 38; 40 |
| **Slice 39: INT-2** | | | | |
| OQ50 | Do error-level checks (bad FEIN, eligible above total) block "Ready to market"? | Open. Default: no; they warn | Open | 39 |
| OQ51 | Is the Monthly Budget Target the medical premium or all lines? | Open. Default: a hint with Apply, never prefilled (F139) | Open | 39 |
| **Slice 40: INT-3** | | | | |
| OQ52 | Does Mark as marketed move the deal to Quoting, and does the last Sent tick set "Sent to market"? | Open. Default: no and no; the Emails card offers the button | Open | 40 |
| OQ53 | Size band at exactly 50: does enrolled or ATNE decide, and how would a hand override work? (v1.1 §16 #9) | Open. Default: 51 or more enrolled is large; the form choice is the only override | Open (Stephanie) | 40 |
| **Slice 42: QST-1** | | | | |
| OQ54 | Will carriers accept typed signatures, including staff signing for the officer with written authorization? | Open. Default: typed names plus the paper-copy route | Open | 42 |
| OQ55 | Who may reopen a signed form? | Open. Default: any user, with a reason | Open | 42 |
| OQ56 | Should Florida Blue's Q15 premiums prefill from the Advisor, and monthly or annual? Is Warner's "Double" the EE+Spouse rate? | Open. Default: staff type Q15 | Open | 42 |
| **Slice 43: QST-2** | | | | |
| OQ57 | Does underwriting accept the stamped flat copy, or only the Acrobat original (G58)? | Open. Default: stamped | Open | 43 |
| OQ58 | Is the SIIA disclosure opt-in, or on by default for level-funded and self-funded groups? | Open. Default: opt-in | Open | 43 |
| **Slice 44: RFP-1** | | | | |
| OQ59 | The full carrier list with each rep. Should Aflac, Kaiser, the Blues or UMR join the 25? (v1.1 §16 #10) | Open. Default: the 25 on Warner's forms | Open (Stephanie) | 44 |
| OQ60 | Card 1: keep both "Confirmed" and "Mark completed"? | Open. Default: both | Open | 44 |
| **Slice 45: RFP-2** | | | | |
| OQ61 | When a roster passes a template's rows (Warner 500, Aetna 485, UHC 350, Angle 213): split, keep writing, or stop? | Open. Default: stop with a truthful warning | Open | 45 |
| OQ62 | Should Warner's Nature of Business cell print the SIC code, or a new intake description? | Open. Default: the SIC code | Open | 45 |
| OQ63 | Readiness cards and lens chips: keep both, or merge them (X-163)? | Open. Default: both | Open | 45 |
| OQ64 | Does the universal census leave the packet when every picked carrier has its own format and "Other carriers" is empty (reversing D-063 #6)? | Open. Default: yes | Open | 45 |
| OQ109 | Does `emp_class` fill both Warner columns S and X? (v1.1 §16 #11) | Yes: in `warner_census.xlsx` S3 "CLASSES" sits under the BASIC LIFE banner (R2:S2) and X3 "CLASSES" under DISABILITY (U2:X2), both hinted "If multiple classes please list"; one census class per employee fills both, ungated by line, as the old final state did | Answered (developer, slice 45) | 45 |
| **Slice 46: RFP-3** | | | | |
| OQ65 | Which address is the returns inbox? | Open. Default: the deal owner's email until one is set | Open | 46 |
| OQ66 | Do PHI documents go only to carriers quoting their lines, to medical carriers when a document has no lines, and never to "Other carriers"? | Open. Default: yes | Open | 46 |
| OQ67 | Benefit Central, or email only? Can Mark's cover sample be supplied? Are more funding boxes needed than fully insured, level-funded and ASO? | Open. Default: email drafts and the built cover | Open | 46 |
| OQ68 | The RFP page stops offering five files (reversing D-063 #5). Agreed? Do carriers ever get the proposal? | Open. Default: agreed; an off-by-default card attaches the latest issued proposal | Open | 46 |
| OQ69 | Are SBCs with no role sent by default? | Open. Default: listed, unticked, "Role not set" | Open | 46 |
| **Slice 47: PHI** | | | | |
| OQ107 | Sign-in lifetime (§3.5; v1.1 §16 #1) | Open. Default: 12 hours (`SESSION_COOKIE_AGE`, built; a Microsoft 365 sign-in gets the same Django session, slice 47). Daniel's signature on `deploy/phi-gate.md` item 3 settles it | Open | 47 |
| **Slice 48: COM-1** | | | | |
| OQ70 | Who saves a split? | Open. Default: all-tier users and the deal's owner | Open | 48 |
| OQ71 | Is a partner's flat or PEPM amount per deal or per line? Is a referral % taken from the producer pool or from gross? | Open. Default: per deal; the pool, with gross selectable per row | Open | 48 |
| **Slice 49: COM-2** | | | | |
| OQ72 | Which year applies to clients served before the app? | Open. Default: earlier records, then a typed "year with us", else "year unknown" | Open | 49 |
| OQ73 | Do producers see only their own share on the Book? | Open. Default: yes; admins see everything | Open | 49 |
| OQ74 | Pre-sale basis: Renewal, then Current, then the starred plan as an estimate? | Open. Default: yes; after the sale only Sold counts | Open | 49 |
| OQ75 | Two carriers on one line: one commission record per carrier? | Open. Default: yes | Open | 49 |
| OQ76 | Who sends the CAA disclosure while close-out is out of scope? | Open. Default: the back office, by email | Open | 49 |
| OQ77 | Do comp agreements, producer profiles, payouts and the Book split return after the MVP? | Open. Default: yes | Open | 49 |
| **Slice 50: COM-3 (deferred, because OQ6 is No)** | | | | |
| OQ78 | Ledger start: import the book of business or the old app's records, or add by hand? (v1.1 §16 #15) | Waits with slice 50. Default when it returns: "Add to book" by hand, with a one-off import on request | Open (waits with 50) | 50 |
| OQ79 | Received YTD: by the date the money arrived, or by the month it pays for? | Waits with slice 50. Default: the arrival date | Open (waits with 50) | 50 |
| **Slice 53: REV-1** | | | | |
| OQ80 | Second factor: a phoned PIN only when a page shows census people or questionnaire answers, and for medical or claimant send-backs; or a PIN on every link? (v1.1 §16 #13) | Open. Default: the narrowed rule | Open | 53 |
| OQ81 | Link life: seven days, sliding on save, under a 30-day ceiling; or a fixed 14 days? | Open. Default: the old sliding rule | Open | 53 |
| OQ82 | Are links still copied, or should the app send email (codes, nudges, reply notices, tasks)? | Open. Default: links are copied | Open | 53 |
| OQ83 | Admin switches: per-form switches, raised security floors, editable follow-up days? | Open. Default: fixed rules and code constants | Open | 53 |
| **Slice 54: REV-2** | | | | |
| OQ84 | Do the client's contacts, coverage and lines wait for staff approval, or land directly as before? | Open. Default: wait | Open | 54 |
| OQ85 | Never print unapproved answers on carrier files or questionnaire PDFs? | Open. Default: never | Open | 54 |
| OQ86 | Before real PHI, must every portal open, save and submit be logged with IP and browser? | Open. Default: link stamps and Activity rows; IP only on the BOR signature | Open | 54 |
| **Slice 56: REV-4** | | | | |
| OQ87 | Does a new custom ask ("＋ Add request") wait in the tray rather than reach the portal at once? | Open. Default: yes | Open | 56 |
| **Slice 57: REV-5** | | | | |
| OQ88 | Keep census sends by contact (census columns assigned to contacts, one link each)? | Open. Default: drop it (L67). If kept, `CensusSettings.rules` stores the contacts and slice 57 sends the links | Open | 57 |
| **Slice 59: REV-7** | | | | |
| OQ89 | After the PHI gate, are clients' census and intake files read automatically (staged)? Is a paper questionnaire read before signing? | Open. Default: census and intake files are read and staged; paper questionnaires are only filed | Open | 59 |
| **Slice 60: AGD-1** | | | | |
| OQ90 | Once quotes are in, do the intake, questionnaire and RFP steps stop leading, and do typed counts stop "Import the census" leading? | Open. Default: yes, which fits OQ9's answer | Open | 60 |
| OQ91 | A sold deal shows the commission step and stays on New clients until its effective date. What ends a deal for you? | decisions.md's default: as stated. Built instead: the sold deal shows its commission step, or "Sold", and the sale moves its client from Prospects to Clients at once, where its row shows that step (I122 as changed; §13.11) | Open; default changed by OQ101 (c) | 60; 61 |
| OQ92 | Do Later and Done anyway apply to everyone? | Open. Default: yes | Open | 60 |
| OQ93 | May the creator or an admin delete a hand-added task (restorable)? | Open. Default: yes | Open | 60 |
| **Slice 61: AGD-2** | | | | |
| OQ94 | New meanings: progress counts the milestones that apply; "Actions completed" adds ticked tasks; sparklines show real figures; sales compare the same days of last month | Open. Default: accept | Open | 61 |
| OQ95 | Landing page: New clients first, with the client list under the Clients pill? | Open. Default: yes, with the old New clients view labelled Prospects (OQ101 c). Prospects lists clients whose status is Prospect, with I86's rows and cards; Clients lists new and existing clients, with chips | Open; reworded by OQ101 (c) | 61; 4 |
| **Slice 62: OVW-1** | | | | |
| OQ96 | Move "Waiting on" above the facts (X-84)? | Open. Default: move it; everything else keeps the old order | Open | 62 |
| **Slice 65: DOC-5** | | | | |
| OQ97 | Census on Documents: the full roster beside the file, or only the review list? | Open. Default: the roster | Open | 65 |
| OQ98 | Browser OCR for scanned pages (E25): may it wait? | Open. Default: built here | Open | 65 |
| OQ99 | The pop-out window (E69–E71, D128): may it wait? | Open. Default: built here | Open | 65 |
| **Milestone 2: cutover** | | | | |
| OQ100 | Close open requests in the old app first, or keep it read-only until they lapse? Old `/b/` links say "This link has moved" | Open. Default: no data moves (v1.1 §16 #15); Daniel sets the timing | Open | M2 |
| **Answered from v1.1 §16** | | | | |
| v1.1 #6, #12, #14 | Plans per printed Excel page; contacts at client level; the slide type floor | Answered by the porting plan: the old formats (Compare prints 5 a page; an 8 pt table floor; J.6) and client-level contacts (B13) | Answered | 27, 29, 38 |

v1.1 §16's other rows are now: #1 → OQ107; #2 → OQ108; #3–#5 → OQ40; #7 → OQ31; #8 → OQ16; #9 → OQ53; #10 → OQ59; #11 →
OQ109; #13 → OQ80; #15 → OQ78 and OQ100.

The approach's own decisions (verification.md, V.4) were approved with the porting plan: the seed-only `golden` app (OQ9
a); Stephanie's signatures on GD1's and GD2's keys before slice 7, and on each later key before the slice that prices
its deal (§13.4; v2.0 adds the rate-basis examples, OQ103); about $20 a month for Eval runs; one Look judgement per
label; pytest-xdist once the serial Fast run passes 45 s; and the old app run read-only beside 2Vantage, with a tools
image, until cutover.

---

## Appendix A — Assets supplied with this spec

Binary files, stylesheets and data that cannot be written into a document. They come from the earlier system's
repository (`Vantage/`) at commit 891f1b3, the commit the port follows (§13.3); copy them into 2Vantage when the slice
that needs them starts. **Never copy client files or anything from `Vantage/aBenefitsMeetings/`.**

| Asset | Source in `Vantage/` | Destination in 2Vantage | Used by |
|---|---|---|---|
| Stylesheets | `frontend/src/App.css` and the in-scope sheets in `frontend/src/styles/`, in the old `main.jsx` order: navbar, benefits, benefits-coverage, benefits-overview, benefits-journey, benefits-radar (agenda rows, `bnf-cat-chip`, `bnf-cal-*` and `bnf-cw-*` only), benefits-workqueue, benefits-tasks, benefits-questionnaire, benefits-census-review, benefits-grid, benefits-freeze, benefits-grid-sizes, benefits-history, benefits-export, commissions, reviewrequest, assistant (`hlp-mic*` only) and linkguard (`lg-*` only): about 19,300 lines. Plus the rules kept screens borrow from left-out sheets | `frontend/src/styles/<old file>/NN-topic.css`, cut at each sheet's own section comments into files of at most 300 lines, imported once, in order, by one manifest | §3.9, §8; slice 2 (O.5) |
| Fonts | IBM Plex Sans 400–700 and IBM Plex Mono 400–600, from the Google Fonts link in `frontend/index.html` | The same link in `frontend/index.html` | The screens; slice 2 (A.6) |
| Firm logo and marks | `assets/images/logos/`: `agency-logo.png` (the default while AgencySettings has no logo), `logo-on-dark.png`, `logo-on-light.png`, `mark.png`, `mark-ghost.png` (the Presentation format's covers and page chrome) | `assets/images/logos/` | §9.4, §9.6–§9.7; slices 27 and 29 (J123, J139, J145) |
| Stock pictures | `assets/images/stock_images/` (seven photographs, about 21 MB), with their labels and crop focus in `benefits/pipeline/stock_images.py` (`LIBRARY`) | `assets/images/stock_images/`, cropped once to the sizes the pages use (J.5 B12); keys and labels in `proposals/catalog.py` | §9.6–§9.7; slices 29 and 34 (J35) |
| Questionnaire blanks | `benefits/questionnaires/sources/`: `fl_blue_51_blank_v9.pdf` (the flat blank that is stamped), `fl_blue_51_uw_v9.pdf` and `fl_blue_51_uw_v9.template.xml` (the Acrobat-only XFA original and its template), `wp_lg_rev121225.pdf` (Warner large group), `stop_loss_siia.pdf` (SIIA disclosure), `Arimo.ttf` and `Arimo-OFL.txt` (the stamp font and its licence) | `assets/questionnaires/` | §9; slices 42–43 (G57, G125). The XFA original serves only the generator (G124) and, later, G58 |
| Questionnaire form specs | `benefits/questionnaires/fl_blue_51.py`, `fl_blue_51_data.py` (generated from the XFA template by `xfa_extract.py`), `fl_blue_51_layout.py`, `wp_lg.py`, `stop_loss_siia.py` | `questionnaire/forms/` (data modules; the generator becomes a dev command) | §4; slices 42–43 (G1, G124, G125) |
| Carrier census workbooks | `benefits/templates_xlsx/warner_census.xlsx`, `aetna_gateway_census.xlsx`, `angle_census.xlsx`, `uhc_census.xlsx` | `assets/carrier_templates/` | §9.8; slice 45 |
| Carrier census column definitions | The `CarrierTemplate` rows of a migrated old database: `benefits/migrations/0054_real_carrier_templates.py` (`TEMPLATES`) as amended by `0055_census_export_fidelity.py` (Warner's 500-row cap, PAY MODE "Annual"), `0061_uhc_waive_all.py`, `0065_census_columns_to_carriers.py` and `0066_uhc_stop_at_x.py` (UHC stops at column X; "Waive all" goes) | `rfp/formats/definitions.py` (plain data, generated once and diffed against `PlanningDocs/Benefits/carrier-census-templates_20260917.md`) | §9.8; slice 45 (K.6) |
| ZIP → county crosswalk | `benefits/data/zip_county.csv.gz` and its `README.md` (source and licence) | `assets/zip_county.csv.gz` | §9.8 `derive:county`; slice 45 |
| Warner quote request forms | `benefits/templates_xlsx/warner_qrf_simplified.xlsx`, `warner_qrf_small_group.xlsx`, `warner_qrf_large_group.xlsx` | `assets/forms/` | §9.9; slice 46 |
| Quote request form cell maps | the cell / label constants in `benefits/pipeline/quote_request_form.py` | `rfp/forms/maps.py` (`VARIANTS`) | §9.9; slice 46 (K99) |

The seven bundled workbooks (the four census files and the three Warner forms) are copied byte for byte and checked
against the SHA-256s in `benefits/templates_xlsx/README.md` (K.6). `warner_census.xlsx` is already cut from the
small-group form, so `recut_warner_census.py` stays behind.

Client files need no font files: the PDF prints in Helvetica and the PowerPoint in Arial (J142), and the cover designs
are drawn by code (`benefits/pipeline/proposal_covers.py`, J32). `benefits/guide/fonts/` (Roboto, Bebas Neue) stays
behind with the deferred Unleashed themes and benefit guide.

The parity lanes run the old repository itself, read-only, in its own Compose project from slice 3 (Q.5). Nothing in it
is changed.

---

## Appendix B — Background: why 2Vantage exists

The earlier system (`Vantage/`) grew to 18 Django apps, ~350,000 lines of Python and ~170,000 lines of frontend code,
with 257 routes in the benefits app alone and 8,370 tests that took 10–16 minutes per run. A small change took 20
minutes to 2 hours, mostly in the work around the change: full test runs that were usually red, a decision log and
generated digests to keep in sync, tests that read source code, files of 3,000+ lines, and a data model that stored
every
value as its own row. On 2026-10-29 the benefits team reset its priorities — proposals first, data before AI, a manual
fallback for everything, Excel as the baseline output — and on 2026-11-10 the project owner chose to rebuild the
benefits
workflow from scratch. This specification keeps the earlier system's business knowledge (field lists, rules, carrier
formats, premium math) and leaves its machinery behind (§15).

**Version 1.1** (2026-11-10) applies a review of version 1.0 that found it the right content at the wrong size and in
the wrong order. Version 1.0 built the whole new-business workflow in tab order — intake and census before the Advisor
and the proposal — so the first file a user could open arrived at slice 22 of 38, although nothing typed into intake or
imported into the census reaches a number in the workbook. Version 1.1 builds the proposal path first (Release 1,
§13), with no member-level data. It also corrects the model (a sale, a recommendation and a package are sets of plans,
and a
package's change against today is shown only when it covers the same people), the write path (concurrent saves,
unchanged values), and the client
documents (the firm's recommendation, a stored copy and a version of what the client was sent, stable option labels,
no laser rows on a client page), and moves sign-in onto Django's own sessions and admin.

**Version 2.0** (2026-11-11) is a production port, not a redesign. That day Daniel chose to port the old Vantage
benefits product: every important function kept, the screens and client files as they were (their formatting "was
perfect"), and code that is small, readable and tested. A deep review read the old code file by file in thirteen module
parts (A–M of `docs/porting/`). Parts D–M each had a reader, a completeness critic, an analyst, an adversarial
challenger and a finaliser; Parts A–C, read first, had a lighter review. The parts list 1,446 items, each with a verdict
and a home: 873 Keep, 285 Simplify, 123 Drop, 109 Defer and 56 New. Parts N–Q then set one data flow, one architecture
with 47 resolved conflicts, a build order of 66 slices and a testing approach. Daniel answered fourteen of the first
twenty-one questions the same day (§16); his answer on the client page added the client lifecycle and slices 67–68, and
checking v1.1 against the plan added staging as slice 69.

The review found that the old app mostly worked: what made it slow to change was its machinery, which this version still
leaves behind (§15). Version 2.0 therefore supersedes v1.1's redesign, scope and release plan wherever the porting parts
say otherwise. v1.1 had deliberately dropped things Daniel now wants (Work with Claude, the medical questionnaire, the
old client-file formats and the export viewer) and had redesigned the screens. 2Vantage's slices M0, M1 and M3–M6, built
under v1.1, are the baseline the build order starts from (§13.3); M2, staging, was never built and becomes slice 69. The
port follows the old repository at commit 891f1b3.

---

## Appendix C — Where each rule came from

For anyone who wants to check a rule against the earlier system's behaviour. Paths are in `Vantage/` at commit 891f1b3.
A hyphenated D-number (D-179) is a decision in the old `PlanningDocs/Benefits/decisions.md`; without the hyphen (D47) it
is a Part D item, and `docs/porting/decisions.md` holds the OQs. Paths under `aBenefitsMeetings/` are citations only:
they are never opened or copied (Appendix A).

**The porting plan.** Since v2.0 the detailed sources are in `docs/porting/`. Each part's X.1 table ("Files read") lists
every old file behind its items, one line each, with what it taught.

| Spec | Source |
|---|---|
| Items A1–M112, which every section cites | Their part's X.1 and X.3 tables: `docs/porting/A-foundation.md` to `M-overview.md` |
| §1.4 scope; Daniel's twelve needs | `docs/porting/README.md` (Context; traceability) |
| §3.3 chain; the apps, shared frameworks, frontend and stylesheet port; rulings between parts | Part O (O.1–O.5; O.6) |
| §3.9 and §8 look: tokens, classes and fonts | `frontend/src/App.css`, `frontend/src/styles/*.css`, `frontend/index.html` (A.6, O.5) |
| Client status and the client page (CL1–CL28, OQ2) | `benefits/pipeline/sale.py` (`mark_plan_sold`), `benefits/radar/reminders.py` (`get_or_create_client_for_case`); `frontend/src/components/benefits/shared/overview/ClientHeader.jsx` ("Link to client"); `frontend/src/components/benefits/radar/ClientsDashboard.jsx`, `ClientWorkspace.jsx`, `client/ClientHeaderCard.jsx`, `client/ClientOverviewTab.jsx` |
| §12 testing; §13 build order | Part Q and `docs/porting/verification.md`; Part P |
| §16 decisions | `docs/porting/decisions.md`, with Daniel's answers of 2026-11-11 |

**Rules this spec states itself.** v1.1's sources, re-sourced where the port changed the rule.

| Spec | Earlier source |
|---|---|
| §4.1 lines, field sets, rate bases | `benefits/lines.py` |
| §4.2 tiers and waiver words | `benefits/market/validation.py` (`TIER_ALIASES`, `WAIVE_WORDS`) |
| §4.3 plan fields, §4.4 census columns | `benefits/registry.py` |
| §4.5 intake questions and help | `benefits/market/intake.py` (`INTAKE_FIELD_SEED`, `FIELD_HELP`) |
| §4.7 carriers (`deals/carriers.py`, `rfp/carriers.py`) | `benefits/market/rfp_carriers.py` (the 25 carriers, `COLUMN_LINES`, the three-tier matcher); `benefits/implementation/carrier_change.py` (`norm_carrier`) |
| §4.8 header synonyms | `benefits/market/census_reader.py` (`HEADER_SYNONYMS`) |
| §5.1 stages | `benefits/stages.py` |
| §5.2 intake cleaning, conditions, validation, readiness | `benefits/market/intake_writes.py` (`clean_value`), `intake.py` (`condition_met`, `needs`, `contacts_ok`), `validation.py` (`validate_intake`) |
| §5.3 census import, validation, rollup, FTE, age | `benefits/market/census_reader.py`, `validation.py` (`validate_case`), `pipeline/plan_math.py` |
| §5.5 premium math | `benefits/pipeline/plan_math.py` (`round_money`, `tier_premium`, `group_premium`), `presentation_math.py` |
| §5.5 packages: a sum across a choice means nothing; totals compare the same people as today | `PlanningDocs/Benefits/decisions.md` D-179 ("a sum across a choice means nothing"; `presentation_model.renewal_set`) |
| §4.3 fields that never print for clients (`sl_lasers`) | `benefits/pipeline/composition.py` (`CLIENT_HIDDEN_ROWS`) |
| §4.3 stop-loss contract and cost rows print | `aBenefitsMeetings/2026-09-03meetingSummary.md` (Stephanie); `composition.py` (`CLIENT_SAFE_ROWS`) |
| §4.4 SSN, gender, hours | `aBenefitsMeetings/2026_09_22TranscriptBenefits.txt` (Stephanie, Rebecca); `2026_09_29meetingNotes_gemini.pdf`; `Wendy_WarnerPacific/email_2.txt`; `decisions.md` D-054 |
| §5.4 unit-rate decimals | `decisions.md` D-077 |
| §5.5 age-banded medical | `aBenefitsMeetings/benefits software meeting - 2026_10_27 10_02 EDT - Notes by Gemini.pdf` (Stephanie) |
| §5.5 what the team does with packages | `aBenefitsMeetings/2026_10_08meetingNotesGemini.pdf` (Stephanie, Rebecca); `2026_10_29meetingSummary.md` |
| §5.7 size band and override | `aBenefitsMeetings/2026_09_08Transcript.txt`; `2026_09_24geminiMeetingBenefits.pdf` (Stephanie); `decisions.md` D-068 |
| §5.6 commission | `benefits/market/validation.py` (`parse_comp`, `comp_label`), `serializers/overview.py` |
| §5.7 RFP rules and facts | `benefits/market/rfp.py` |
| §9.4 client workbook | `benefits/pipeline/presentation_workbook.py`, `presentation_bank.py`, `presentation_styles.py`, `workbook_values.py`, `workbook_text.py` (J.1). Earlier layout decisions: `PlanningDocs/Benefits/proposal-packages-and-outputs.md` §3.7; `aBenefitsMeetings/2026_10_29meetingSummary.md`; `aBenefitsMeetings/2026_11_05meetingSummary.md` (that meeting's decisions G1–G9, not Part G's items) |
| §9.4 disclaimer | `benefits/pipeline/disclaimers.py` (`STANDARD`, `DOCUMENT`; D-173) |
| §9.5–§9.7 deck and PDF, the old Presentation format | `benefits/pipeline/proposal_presentation.py` (the story), `proposal_furniture.py`, `proposal_covers.py`, `proposal_tokens.py` (type floors, 16:9 geometry), `proposal_deck.py` (the PowerPoint), `proposal_paper.py` (Paper); `proposal_pdf.py` (`_why_for`, "Prepared by") (J.1) |
| §9.8 carrier census fill | `benefits/pipeline/xlsx_fill.py`, `workbooks.py`, `plan_math.py` (`census_rows_for_template`); migrations 0054, 0055, 0061, 0065 and 0066 (K.1) |
| §9.9–§9.11 forms, packet, emails | `benefits/pipeline/quote_request_form.py`, `rfp_bundle.py`, `rfp_cover_pdf.py`, `rfp_email.py` |
| §10 AI and Work with Claude | `docscan/client.py`, `chunking.py`, `jobs.py`, `phi_screen.py`, `locate.py`; `benefits/ai/claude_readers.py`, `scan_chat.py`, `agent_turn.py`, `page_context.py`; `docs/CyberSecurity_PHI/claude-and-the-anthropic-baa.md` (D.1) |
| §11 deployment decisions | `PlanningDocs/Platform/production-deployment-plan.md` |
