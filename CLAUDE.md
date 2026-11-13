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
docker compose exec backend pytest [<app>]      # Fast lane, one app (≤10 s); everything: pytest -n 8 --dist loadfile
docker compose exec backend ruff check . && docker compose exec backend lint-imports   # chain contract: .importlinter
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
documents, ai, intake, census, quotes, questionnaire, commission, rfp, proposals, review, agenda, golden. The chain
orders imports, not screens: the deal sidebar keeps old Vantage's order and groups (A21, OQ9): Overview, Agenda · 1 Get
to Market: Review & requests, Intake, Census, Questionnaire (if the deal has a form), RFP, Commission · 2 Quote to
Close: Advisor, Proposal · Shared: Documents. Quotes never wait for intake, census or a questionnaire: typed summary
tier counts carry the Advisor and Proposal. Tab folders take the app's name except advisor/ (quotes) and proposal/
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
