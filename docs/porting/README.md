# 2Vantage: porting plan for the old Vantage benefits modules (deep code review → production rebuild)

> **Status: approved 2026-11-11; slice 1 done, for Daniel's review.** Slice 1 rewrote [`plan.md`](../../plan.md) (v2.0)
> and [`CLAUDE.md`](../../CLAUDE.md) from these parts and Daniel's answers to OQ1–OQ21. Where they disagree, plan.md wins,
> then [Part O](O-architecture.md), then the module part. The build order is plan.md §13, Part P with the answers
> applied (three new slices, 67–69); questions OQ101–OQ110, added by the rewrite, are in plan.md §16. The v1.1 spec and
> CLAUDE.md it replaced are kept in [superseded/](superseded/). These files are the approved plan of 2026-11-11,
> split by part without rewriting.

## Contents

| File | What it covers |
|---|---|
| [Decisions needed](decisions.md) | The 100 open questions, each with the default built until answered |
| [Part A — Platform foundation](A-foundation.md) | Sign-in, home, deal shell, stages, values and history, jobs, the look |
| [Part B — Intake](B-intake.md) | The 56 questions, contacts, coverage intent, the marketing checklist, BOR, marketed |
| [Part C — Census](C-census.md) | The roster, import and matching, validation, rollups that price plans |
| [Part D — AI readers and Work with Claude](D-ai-readers-and-work-with-claude.md) | The Work with Claude drawer, quote and SBC readers, jobs, budgets |
| [Part E — Documents review station](E-documents-review-station.md) | Files, the viewer, Find, review mode, checks against the source |
| [Part F — Advisor](F-advisor.md) | The quote comparison board and everything on it |
| [Part G — Medical questionnaire](G-medical-questionnaire.md) | Florida Blue 51+, Warner large group, the SIIA disclosure |
| [Part H — Commissions](H-commissions.md) | Rates, splits, booking, the book, statements and reconciliation |
| [Part I — Agenda](I-agenda.md) | Deal steps, tasks, marks, the work queue |
| [Part J — Proposal and export viewer](J-proposal-and-export-viewer.md) | The Proposal tab, the export viewer and the client files |
| [Part K — RFP](K-rfp.md) | Carriers, the packet, request forms, carrier census files, email drafts |
| [Part L — Review & requests, client portal](L-review-and-requests.md) | Review queues, requests and links, the client portal |
| [Part M — Overview](M-overview.md) | The deal Overview: header, banners, cards, feed, notes |
| [Part N — Cross-module data flow](N-cross-module-data-flow.md) | Every fact that crosses modules and who owns it |
| [Part O — Architecture of the new codebase](O-architecture.md) | The app chain, every app, shared frameworks, the stylesheet port, resolved conflicts |
| [Part P — Build order](P-build-order.md) | The 66 slices in six phases, with done-when and milestones |
| [Part Q — Testing approach](Q-testing.md) | Tests, golden deals, fidelity and visual-parity checks, performance budgets |
| [Verification](verification.md) | How each slice and the whole MVP are accepted; the top risks |

## Summary

**What this is.** A plan to port the old Vantage benefits product into 2Vantage as production code: every important function kept, the screens and client files as before, the code small, readable and tested. Nothing is built yet. Once Daniel approves it, slice 1 rewrites plan.md and CLAUDE.md from it.

**Approach.** Thirteen parts (A–M) read the old code file by file. Parts D–M each had a reader, a completeness critic, an analyst, an adversarial challenger and a finaliser; Parts A–C, read first, had a lighter review. Every function got a verdict and a home in the new code. A conflict audit compared the designs, and an adversarial critique of Parts N–Q was checked against the plan file, the old repo and 2V. Parts N–Q give one data flow (N), one architecture with 47 resolved conflicts (O), one build order of 66 slices (P) and one testing approach (Q).

**Scale.** Parts A–M list 1,446 items: A 43, B 44, C 47, D 134, E 104, F 144, G 136, H 125, I 127, J 170, K 124, L 136, M 112. By the first word of each X.3 verdict (C47 and M4 count as Keep):

| Keep | Simplify | Drop | Defer | New |
|---|---|---|---|---|
| 873 (60%) | 285 (20%) | 123 (9%) | 109 (8%) | 56 (4%) |

The old app mostly worked. What made it slow to change was its machinery (one row per value, version snapshots, edit sessions, tests that read source), and most drops are that machinery or demo code. Most defers wait for renewals (OQ1), the ledger (OQ6) or task mode (OQ8). Two Defer rows are built, because their condition is met by default: F137 (the Florida Blue fold) and M20 (the renewal-offer chip).

**The old repo moved during planning.** On 2026-11-11 it committed the need-9 code (7385bb3) and turned the member-data screen off for every Claude read (D-225, 891f1b3). The port follows 891f1b3.

**Key decisions.**
- **Chain:** `accounts → deals → documents → ai → intake → census → quotes → questionnaire → commission → rfp → proposals → review → agenda → overview`, plus a seed-only `golden` app. Imports point left; apps to the right are reached through providers, registries and on-commit signals.
- **Values and history:** JSON values with one source-entry shape. One Activity row with before and after values, and one revert path, replace version history.
- **The Advisor owns every plan rule:** one membership rule (`room` = 16 columns), one order, one enrollment precedence and one headcount. A quote-first deal with typed tier counts works on every screen and file, and the census takes over when it arrives (need 6). A line that gains a second current plan asks for its counts to be split instead of losing prices silently.
- **Need 3** gets a stored `quotes.QuoteLayout`, shown in the Advisor's "As quoted" view and on Documents.
- **Claude:** one job model with three lanes and a worker; one reading pipeline (Messages API only, structured outputs); files read whole, with one switch to bring the screen back. Quote reads by admins and direct people land at once, with Undo; the rest are staged.
- **Client files** port the old Presentation formats from one recorded layout and a pure sheet model with the old formulas. 5182 and 5183 print as one column (D-219). The export viewer writes nothing.
- **Look:** the old stylesheets copied in the old order with the old class names, plus the rules kept screens borrow from left-out sheets; undefined tokens pinned to what they rendered.
- **Proof:** behavioural tests; golden deals with keys Stephanie signs (GD1 and GD2 before slice 7); acceptance lanes against the old app, run read-only beside 2V.

**Build headline.** 66 slices in six phases, each reviewed and committed before the next.
- Phase 0 (1–4): the spec, the look, the golden deals and the old-app harness.
- Phase 1 (5–14): the Advisor without Claude.
- Phase 2 (15–24): Documents and Work with Claude.
- Phase 3 (25–37): the Proposal, its files and the Florida Blue fold. **Milestone 1** follows: Gates A and B on a quote-first deal and on GD1, then Stephanie's walk.
- Phase 4 (38–47): Get to Market, up to the PHI gate.
- Phase 5 (48–66): commissions, review and the portal, Agenda and Overview. **Milestone 2** is the full MVP, with every gate run again. Real member data waits for the PHI gate (slice 47).

**Decisions Daniel must make first.** Each has a default that is built if he does not answer.
1. Commit M0–M6 (P.1).
2. Scope (OQ1–OQ8): renewals, the client page and Claude Unleashed deferred; questionnaire in; the ledger waits; the chat with immediate landing; priced versions, saved setups and templates kept.
3. Conventions this plan changes (OQ9): rfp before proposals; a seed-only `golden` app; rounding only through `quotes/math/`, which commission also uses; two stored counts beside "status on read". Default: accept.
4. Look (OQ10): keep exactly what the old screens rendered.
5. Enrollment (OQ18–OQ21): the census beats counts typed before its import; worksite lines borrow medical counts; a second current plan asks for the split.
6. Need 3 (OQ32): both screens; client files keep the house rows.
7. Claude on real files (OQ22, OQ29): the Foobalabs key only, after Anthropic's written confirmation; files read whole (D-225).
8. Florida Blue (OQ42): your D-219 fold; only the deductible's print is asked.

**How to read this plan.** This summary, then the Context and Daniel's twelve needs with their traceability, then the decisions needed. Parts A–M are the module reviews: each has the files read (one line each), the old data model, every function with its verdict and new home, data flow, bugs, the new design and the module's own questions. Parts N–Q are the cross-module plan: data flow, architecture (which wins where a module part differs), build order and testing; Verification closes it.

## Context

Daniel wants a **production version** of the old Vantage benefits product: every important functionality kept, the
screens looking the same as before (their formatting "was perfect"), and code that is efficient, easy for a person to
read, tested and easy to test. The old repository works but was slow to change: about 145,000 lines of frontend code
and 27,000 of CSS, about 160,000 lines of backend (plus 100,000 of tests), on layers of machinery: values stored one
row per cell, version snapshots, edit sessions, a frozen field registry, and tests that read source files.

2Vantage so far (M0–M6, uncommitted) is a *redesigned* subset: sign-in, dashboard, deal header, a simplified Advisor,
Proposal selection and preview, Documents v1. Its spec, plan.md v1.1, deliberately dropped several things Daniel now
wants (Work with Claude, the medical questionnaire, commission statements, the export viewer's formats). **This plan
supersedes plan.md's scope**; plan.md is rewritten from it once approved.

**Modules in scope:** Advisor, Proposal (with the export viewer and every output format), Commissions, RFP, the medical
questionnaire, Census, Intake, Review & requests (with the client portal), Agenda, Overview, plus what they stand on:
Work with Claude and the AI readers, the Documents review station, and the platform foundation.

**The business workflow the build must serve:** intake → census → questionnaire → go to market (RFP) → quotes →
Advisor comparison → proposal → sold → commissions. Quotes often arrive **before** intake, census and questionnaire
are complete ("just a quick example of a quote"), so the Advisor and Proposal must work on a deal that has only typed
summary tier counts and no census, and pick up the census when it arrives.

### Daniel's stated Advisor and Proposal requirements (each must be traceable to a plan item below)

1. Scan in quotes with Work with Claude.
2. Read SBCs and carrier quotes with Work with Claude.
3. Recreate the exact order and rows of the scanned quote in the viewer.
4. Search plans by name.
5. Filter by budget, against the monthly total row.
6. Read enrollment from the census, and override it with quick summary medical tier counts when there is no census.
7. Star plans; set plans as current, more than one allowed.
8. Say which quote replaces which plan.
9. Click a plan and drop it into a chosen slot, to set the order easily (as in the client spreadsheet).
10. Transpose the table.
11. The export viewer: preview Excel, PowerPoint, paper and PDF.
12. Export the client spreadsheet, the PowerPoint, and the client PDF, all in the formats already built.

## Traceability: Daniel's twelve needs

| Owner need | Plan items that deliver it | Build slice |
|---|---|---|
| 1. Scan in quotes with Work with Claude | A14, D1, D3, D13, D14, D16, D17, D28, D39, D43, D46, D49–D51, D57–D62, D71–D75, E4, E5, E20, E75, E78, F95, F96, F112, F138, F143, I53, J79, J80, L125, M106 | **18 AI-1** (reader, read door), **19 AI-2** (landing, Undo), **20 AI-3** (drawer, quote-first door). Also 15–17; 59 (client uploads); 60 (the read-quotes step); 62 (drawer on the Overview) |
| 2. Read SBCs and carrier quotes with Work with Claude | D15, D38, D40, D47, D54, D57–D59, D93, D116, D117, E21–E29, E48–E59, E76, E77, E79, E81–E89, F63–F67, F141, F142, J86, J91, M83, M87–M89, M92, M93 | **15 DOC-1**, **16 DOC-2**, **17 DOC-3**, **22 AI-5**, **23 DOC-4**. Also 64 OVW-3. Scanned pages are checked by eye until 65 builds browser OCR (E25) |
| 3. Recreate the exact order and rows of the scanned quote | D66, D123, D133, E37, E42, E94, F42, F64, F138, J4, J62, J133, J149 | **21 AI-4**. The order is kept by 7 (`order.layout`) and 18 (reading order); the client files keep it in 27, 29 and 31 |
| 4. Search plans by name | F14–F17, F45, E60–E64, J9, D80 | **10 ADV-4**. Also 14 (picker search), 23 (Documents Find), 24 (Claude sets the board) |
| 5. Budget filter against the monthly total row | F18, F19, F41, F139, F140, D80 | **10 ADV-4**. Also 24 (Claude's rule), 39 (intake budget hints) |
| 6. Census enrollment, overridden by typed summary tier counts when there is no census | C39–C41, F85–F92, F98, D67, G5, G133, H6, H7, H120, I49–I51, J48, J83, K17, K19, K31, L4, L90, M42, M67, M110 | **12 CEN-1**, **13 ADV-5** (with the split when a second current plan arrives). Also 19 (read counts land), 25, 40, 42, 44, 49, 60, 62 |
| 7. Star plans; several current plans | F50, F51, F53, F55, F57, F58, F83, J1, J13, J76, J87, J90, D96, D97, E40, G30, G134, H26, M62 | **7 ADV-1**, **9 ADV-3**. Also 25, 37, 42, 49 |
| 8. Which quote replaces which plan | F37, F45, F52, F118, F120, D115, J12, J50, J136, J165 | **7 ADV-1**, **14 ADV-6**. Also 19, 25, 29 |
| 9. Click a plan into a chosen slot to set the order | F37, F38, F43–F46, F48, J5, J6, J8, J10, J11, J49, J88, E37 | **7 ADV-1** (`put_in_slot`), **14 ADV-6** (ported from old commit 7385bb3). Also 9, 25, 32 |
| 10. Transpose the table | F34, F35 | **9 ADV-3** |
| 11. Export viewer previewing Excel, PowerPoint, Paper and PDF | F3, F136, J105, J107–J112, J114–J118, J120, E22, E29, K82 | **28 PRO-4** (Excel view), **30 PRO-6** (PowerPoint, Paper and PDF views; the PowerPoint view shows the PDF's pages, J.5 B22) |
| 12. Client spreadsheet, PowerPoint and PDF in the formats already built | J15, J24, J97, J102–J104, J122–J142 except J129, J145–J154, J161, J165, F137, D114, H125, K64, K117 | **27 PRO-3**, **29 PRO-5**, **31 PRO-7**, **32 PRO-8**, **33 PRO-9** (5182 / 5183 as one column). Presentation format only: Classic (J36, J37, J113, J143) waits for OQ8. Carriers that were asked appear from 46 |

## How the review is done

Each module is read file by file in dependency order: models → rules and math → services → views and URLs → frontend
API → components → tests. Every file gets a one-line summary in that module's "Files read" table.

**Order of the reading:**
1. **Wave 1:** foundation, Intake, Census.
2. **Group A:** AI readers with Work with Claude, the Documents review station, Advisor, medical questionnaire,
   Commissions, Agenda. Each is given wave 1's findings.
3. **Group B:** Proposal with the export viewer, RFP, Review & requests with the portal, Overview. These depend on
   group A, and each is given group A's findings.

**How each group A and B module is reviewed:**
- a **deep reader**;
- a **completeness critic**, which sweeps the module's routes, components, models and tests for anything the reader
  missed, and checks its claims against the code;
- an **analyst**, who drafts the verdicts;
- an **adversarial challenger**, who argues against every Drop and against any complexity kept without need;
- a **finaliser**, who settles each verdict.

**Verdicts:** **Keep** = rebuild as it works now; **Simplify** = same user-visible behaviour, simpler build (says how);
**Drop** = not rebuilt (says why); **Defer** = later (says why); **New** = not in the old app but needed.
Each verdict also says where the functionality lives in the new codebase.

---
