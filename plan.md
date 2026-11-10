# 2Vantage — Developer Specification

**Version:** 1.0 draft for review · **Date:** 2026-11-10 · **Owner:** Daniel (project owner, approves every change)
**Audience:** a developer — or a Claude Code session — with **no knowledge** of the earlier system. Everything needed
to build 2Vantage from an empty repository is in this document plus the asset files listed in
[Appendix A](#appendix-a--assets-supplied-with-this-spec).

---

## How to use this document

- Read [§1 Product overview](#1-product-overview) and [§2 Insurance primer](#2-insurance-primer) first. They explain
  the business and its vocabulary; nothing later makes sense without them.
- [§3](#3-technical-foundation) fixes the stack, repository layout and conventions that every part follows.
- [§4](#4-reference-data) lists the vocabularies (lines of coverage, plan fields, census columns, intake questions,
  carriers). Implement them **exactly** as listed: they are business data, not suggestions.
- [§5](#5-business-rules) states every business rule (validation, premium math, readiness, stages). Each rule is
  testable as written.
- [§6](#6-data-model) to [§9](#9-generated-files) specify the data model, API, screens and generated files.
- [§13](#13-build-plan) is the order of work. Build one slice at a time; each slice has acceptance criteria.
- **MUST / MUST NOT / SHOULD / MAY** are used in their usual specification sense.
- Items marked **▲ To confirm** are best-current designs awaiting the benefits team's sign-off. Build them as
  written; they are isolated so a change is cheap.

### Contents

1. [Product overview](#1-product-overview)
2. [Insurance primer](#2-insurance-primer)
3. [Technical foundation](#3-technical-foundation)
4. [Reference data](#4-reference-data)
5. [Business rules](#5-business-rules)
6. [Data model](#6-data-model)
7. [API](#7-api)
8. [Screens](#8-screens)
9. [Generated files](#9-generated-files)
10. [AI document reading (Phase 9)](#10-ai-document-reading-phase-9)
11. [Deployment (Phase 10)](#11-deployment-phase-10)
12. [Testing](#12-testing)
13. [Build plan](#13-build-plan)
14. [Working agreement and CLAUDE.md](#14-working-agreement-and-claudemd)
15. [Deliberate non-goals](#15-deliberate-non-goals)
16. [Open questions](#16-open-questions)
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
3. sends that package to insurance companies (**carriers**) asking for prices (**RFP**, request for proposal);
4. receives price quotes back and lines them up side by side (**Advisor**, quote comparison);
5. presents the best options to the employer (**proposal** — an Excel workbook first, then PowerPoint and PDF);
6. records which plans the employer bought (**sold**) and the commission the agency expects.

2Vantage is the team's internal web application for steps 1–6, **for new clients** (employers the agency has
not served before). Renewals of existing clients come later and are out of scope for this version.

### 1.2 Users

| User | Who | What they do |
|---|---|---|
| Member | Account managers / producers on the benefits team (3–10 people) | Everything in the workflow |
| Admin | One or two senior members | Everything members do, plus manage user accounts and agency settings |
| Client contact | Someone at the employer (HR, owner) | No account. Opens a secure link to answer questions and upload files (Review & request) |

All signed-in users see all clients. There is no per-user data restriction.

### 1.3 The workflow on one page

```
Dashboard ──► New client ──► Deal workspace
                               │
   ┌───────────────────────────┼──────────────────────────────────────────────────────┐
   │ Overview   where the deal stands, what to do next, notes, activity                │
   │ Intake     company facts, contacts, current coverage, lines to quote, BOR         │
   │ Review &   send the client a link for missing answers/files; approve what returns │
   │  request                                                                          │
   │ Census     upload the employee list, fix errors, see enrollment by tier           │
   │ RFP        pick carriers, download carrier census files + forms, email drafts     │
   │ Commission commission rate per line, expected revenue, producer split            │
   │ Advisor    every plan (current / renewal / alternates) side by side, priced       │
   │ Proposal   choose plans to present → client Excel workbook → PowerPoint → PDF     │
   │ Documents  every file on the deal; (Phase 6) view it and check where values came  │
   └───────────────────────────────────────────────────────────────────────────────────┘
Stage:  Intake ──► Quoting ──► Proposal ──► Sold        (or Lost, with a reason)
```

### 1.4 Scope of version 1

**In scope:** sign-in and user admin; client dashboard with search; one deal per client; the nine tabs above;
generated files (census template, carrier census files, Warner quote request form, RFP packet zip, email drafts,
client proposal Excel, internal Excel, PowerPoint, PDF); a public client page for Review & request; AI document
reading as a later phase (§10); Google Cloud Run deployment as a later phase (§11).

**Out of scope:** renewals of existing clients, post-sale implementation tracking, benefit guides, commission
ledgers and statements, property & casualty insurance, carrier questionnaires as in-app forms, email sending
(the app drafts emails; people send them), and everything in [§15](#15-deliberate-non-goals).

### 1.5 What "done" looks like

A member can take a new client from nothing to a client-ready Excel proposal **by hand, with no AI**, in one
sitting: create the client, fill intake, import a census, enter current plans, renewals and alternates (typed or
imported from the Excel plan template), set enrollment counts, and download a proposal workbook whose totals match
the app to the dollar. Every later phase adds speed (RFP files, AI reading) without being required.

---

## 2. Insurance primer

Read this once. These terms appear everywhere.

| Term | Meaning |
|---|---|
| **Group** / employer / client | The company buying coverage for its employees |
| **Deal** | One client's purchase for one plan year. (The old system called it a "case"; 2Vantage says deal everywhere.) |
| **Plan year / effective date** | The date the new coverage starts, usually the 1st of a month |
| **Line of coverage** ("line") | A type of insurance: medical, dental, vision, life, disability, and ~20 smaller ones (§4.1) |
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
| **RFP** | Request for proposal — the package sent to carriers asking for quotes |
| **Quote** | A carrier's priced offer |
| **BOR** | Broker of record letter — the employer's signed authorization for this agency to represent it |
| **Funding** | *Fully insured* (fixed premium), *level-funded* (fixed monthly payment, employer funds claims with a stop-loss backstop) or *self-funded* (employer pays claims, buys **stop-loss** insurance against large claims) |
| **Small / large group** | Fewer than 51 / 51 or more enrolled employees. Changes which carriers and forms apply |
| **ATNE** | Average total number of employees in the prior year — decides small vs large group under insurance rules |
| **Commission** | What the carrier pays the agency: a percentage of premium, a flat amount, or PEPM |
| **Quote-blocking** | An intake answer carriers need before they will quote |
| **PHI** | Protected health information. In this app: anything identifying a census member (name, SSN, date of birth, address, salary). Strict handling rules apply (§3.8) |

---

## 3. Technical foundation

### 3.1 Stack

| Layer | Choice | Notes |
|---|---|---|
| Language | Python 3.12 | |
| Web framework | Django 5.2 (LTS) | |
| API | Django REST Framework 3.16 | Token authentication |
| Database | PostgreSQL 15 | JSONB for value dictionaries |
| Server | gunicorn 23 (production), `runserver` (local) | |
| Spreadsheets | openpyxl 3.1 | Generated workbooks. Carrier templates are filled by XML patching, never re-saved by openpyxl (§9.8) |
| PDF | reportlab 4.x; pypdf 5.x (page counts) | |
| PowerPoint | python-pptx 1.0 | |
| Images | Pillow | Logo re-encoding |
| AI (Phase 9) | anthropic SDK | One client wrapper (§10) |
| Frontend | React 19, React Router 7, Vite 6 | |
| Data fetching | TanStack Query 5, axios 1 | |
| PDF viewer (Phase 6) | pdfjs-dist 5 (legacy build); tesseract.js (optional OCR) | |
| Tests | pytest 8, pytest-django | §12 |
| Lint | ruff (Python), ESLint 9 with react-hooks (JS) | |
| Containers | Docker Compose (local) | Cloud Run later (§11) |

Pin exact versions in `requirements.txt` and `package-lock.json` when Phase 0 is built (`==` pins for Python).

### 3.2 Repository layout

```
2Vantage/
  plan.md  CLAUDE.md  README.md
  .gitignore  .dockerignore  .env.example
  docker-compose.yml  Dockerfile  start.sh  requirements.txt  manage.py
  pytest.ini  ruff.toml  conftest.py
  backend/        Django project package
                  settings.py  settings_test.py  urls.py  wsgi.py  asgi.py
                  health.py  checks.py  middleware.py  meta.py
  accounts/       sign-in, password, user admin
  deals/          Client, Deal, Contact, Note, Activity, AgencySettings; lines.py, stages.py
  documents/      Document; upload / download / viewer data
  intake/         form.py (questionnaire), Intake, CurrentCoverage
  census/         fields.py, Member, CensusImport, importer, validation, rollup, templates
  quotes/         fields.py, Plan, math.py, comparison, plan-template import/export
  commission/     Commission, math.py
  proposals/      ProposalConfig, workbook.py, deck.py, pdf.py, internal.py
  rfp/            carriers.py, RfpConfig, carrier census fill, quote request form, packet, email drafts
  review/         ClientLink, ClientValue, public portal views
  overview/       no models; composes every app's summary
  assets/         binary assets from Appendix A (carrier templates, ZIP crosswalk)
  frontend/
    Dockerfile.dev  Dockerfile  nginx.conf  vite.config.js  eslint.config.js  package.json  index.html
    src/
      main.jsx  App.jsx
      api/        client.js + one module per backend app (accounts.js, deals.js, intake.js, …)
      auth/       AuthProvider.jsx, LoginPage.jsx, RequireAuth.jsx, ResetPassword*.jsx
      ui/         shared components, each with Component.jsx + Component.module.css
      lib/        format.js, download.js, errors.js
      pages/      DashboardPage/, DealPage/, admin/, PortalPage/
      deal/       overview/ intake/ review/ census/ rfp/ commission/ advisor/ proposal/ documents/
      styles/     tokens.css, base.css
```

**Every backend app has the same shape:**

| File | Holds | Rule |
|---|---|---|
| `models.py` | Models | No business logic beyond trivial properties |
| `services.py` | Every write | Runs in a transaction, takes the acting user, appends one `Activity` row, returns what changed |
| `selectors.py` | Reads and response payloads | No writes |
| domain modules (`math.py`, `validation.py`, `rules.py`, …) | Pure functions | No database access; fully unit-tested |
| `views.py` | DRF `APIView`s | Thin: parse request → call a service or selector → respond |
| `urls.py`, `admin.py`, `tests/` | | |
| `summary.py` | `summary(deal) -> dict` | Read by `overview` only (§5.10) |

### 3.3 App dependency chain

```
accounts → deals → documents → intake → census → quotes → commission → proposals → rfp → review → overview
```

An app MAY import from apps to its left and MUST NOT import from apps to its right. Examples: `census` reads
`intake` (requested lines decide required columns); `quotes` reads `census` (enrollment prices plans);
`rfp` reads `intake`, `census`, `documents`, `commission`; `overview` reads everything and nothing reads it.
Migrations follow the same direction. From Phase 9 the `ai` app (§10) sits between `documents` and `intake`.

### 3.4 Local environment

| Service | URL / port | Image |
|---|---|---|
| frontend (Vite dev server) | http://localhost:4001 | `frontend/Dockerfile.dev` (Node 22) |
| backend (Django) | http://localhost:8004 (container 8000) | `Dockerfile` (Python 3.12-slim) |
| db (Postgres) | localhost:5436 (container 5432), database `vantage2` | `postgres:15` |

These ports deliberately differ from the older Vantage app (4000 / 8003 / 5435) and other local stacks
(5432–5434, 8000–8002, 3000–3001) so everything can run side by side.

**docker-compose.yml** (shape):

```yaml
services:
  db:
    image: postgres:15
    ports: ["5436:5432"]
    environment:
      POSTGRES_DB: ${DB_NAME:-vantage2}
      POSTGRES_USER: ${DB_USER:-vantage}
      POSTGRES_PASSWORD: ${DB_PASSWORD:-vantage-dev}
    volumes: [pgdata:/var/lib/postgresql/data]
    healthcheck: {test: ["CMD-SHELL", "pg_isready -U ${DB_USER:-vantage} -d ${DB_NAME:-vantage2}"], interval: 5s, retries: 10}
  backend:
    build: .
    ports: ["8004:8000"]
    volumes: [".:/app"]
    environment:
      ENVIRONMENT: local
      DJANGO_DEBUG: "True"
      DJANGO_SECRET_KEY: ${DJANGO_SECRET_KEY:-dev-only-not-secret}
      DB_NAME: ${DB_NAME:-vantage2}
      DB_USER: ${DB_USER:-vantage}
      DB_PASSWORD: ${DB_PASSWORD:-vantage-dev}
      DB_HOST: db
      DB_PORT: "5432"
      FRONTEND_URL: http://localhost:4001
    depends_on: {db: {condition: service_healthy}}
  frontend:
    build: {context: ./frontend, dockerfile: Dockerfile.dev}
    ports: ["4001:4001"]
    volumes: ["./frontend:/app", "/app/node_modules"]
    environment: {VITE_API_PROXY: "http://backend:8000"}
    depends_on: [backend]
volumes:
  pgdata:
```

**vite.config.js:** dev server on port 4001 (`strictPort: true`, `host: true`); **file watching by polling**
(`watch: {usePolling: true, interval: 300}`) because the repository lives in a synced folder whose change events do
not reach containers; proxy `/api` and `/admin` to `VITE_API_PROXY` (default `http://localhost:8004`).

**Dockerfile (backend):** `python:3.12-slim`; `PYTHONDONTWRITEBYTECODE=1`, `PYTHONUNBUFFERED=1`; a non-root user
`appuser` (uid 1000); install `requirements.txt`; `COPY --chown=appuser:appuser . .`; `EXPOSE 8000`;
`ENTRYPOINT ["/app/start.sh"]`. No compiler or Postgres client is needed (`psycopg2-binary` ships wheels).

**start.sh:** if `ENVIRONMENT=production`: `migrate --noinput`, `collectstatic --noinput`, then
`exec gunicorn backend.wsgi:application --bind :${PORT:-8000} --workers 2 --threads 4 --timeout 60 --access-logfile -`.
Otherwise: `migrate`, then `exec python manage.py runserver 0.0.0.0:8000`.

**.dockerignore:** `.git`, `.env*` (keep `.env.example`), `media/`, `staticfiles/`, `frontend/`, `**/__pycache__/`,
`**/*.pyc`, `*.md` (keep `README.md`), `.pytest_cache/`.

**.env.example** lists every variable in §3.5 with safe local defaults and no secrets.

**Everyday commands** (all from the repository root):

```bash
docker compose up --build -d
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py createsuperuser
docker compose exec backend pytest                     # whole suite (< 60 s)
docker compose exec backend pytest census              # one app (< 10 s)
docker compose exec backend ruff check .
docker compose exec backend python manage.py makemigrations --check --dry-run
docker compose exec frontend npm run lint
docker compose exec frontend npm run build
docker compose logs -f backend
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
| `FRONTEND_URL` | `http://localhost:4001` | Base for password-reset and client-portal links |
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL` | empty | SMTP; when `EMAIL_HOST_USER` is empty, mail prints to the console |
| `TOKEN_TTL_HOURS` | `0` | Sign-in token lifetime; 0 = no expiry (§16) |
| `GIT_SHA` | `unknown` | Build commit shown by `/api/health/` |
| `ANTHROPIC_API_KEY`, `AI_MODEL`, `AI_READ_LIMIT_USD` | empty | Phase 9 only |

Other fixed settings: `TIME_ZONE = 'UTC'`, `USE_TZ = True`; `MEDIA_ROOT = BASE_DIR / 'media'` (git-ignored);
default file storage is the local filesystem (Cloud Storage in Phase 10 is a settings change only);
`DEFAULT_AUTO_FIELD = BigAutoField`; Django admin mounted at `/admin/` for staff.

DRF settings: authentication `accounts.auth.ExpiringTokenAuthentication`; default permission `IsAuthenticated`;
throttles: anonymous 200/hour, user 5,000/hour, scope `login` 10/minute, scope `portal` 300/hour.

**`backend/settings_test.py`** imports settings and overrides: MD5 password hasher (fast), throttles off,
`ANTHROPIC_API_KEY = ''`, `MEDIA_ROOT` = a temporary directory, locmem email backend, `django.request` logging at
ERROR. `pytest.ini` points `DJANGO_SETTINGS_MODULE` at it.

**Logging:** one console handler at WARNING. Loggers `anthropic`, `httpx`, `httpcore` pinned at WARNING (their DEBUG
output contains document contents). App loggers at INFO (they still print only WARNING and above). Never configure
the `django` or `django.server` loggers. `disable_existing_loggers = False`.

**`backend/health.py`** — `GET /api/health/`, plain Django view (not DRF, no throttle), no auth, never cached:
runs `select 1`, counts unapplied migrations (cached once zero), returns
`{"ok": true, "database": "ok", "commit": "<GIT_SHA>", "migrations_pending": 0}` or
`503 {"ok": false, "database": "<ExceptionClassName>", "commit": "…"}`. It reveals nothing else.

**`backend/checks.py`** — Django system checks registered with `deploy=True`, active only when
`ENVIRONMENT == 'production'`: E001 DEBUG on; E002 default secret key; E003 console email backend; E004 the
`ANTHROPIC_LOG` environment variable set to `debug` or `info`. `manage.py check --deploy` must pass before a release.

**`backend/middleware.py`** — `JsonGZipMiddleware`: Django's `GZipMiddleware`, applied only when the response
`Content-Type` starts with `application/json`. File downloads are never compressed.

### 3.6 API conventions

- Everything lives under `/api/`. Requests and responses are JSON unless uploading or downloading a file.
- Authentication header: `Authorization: Token <key>`.
- Deal-owned collections nest under the deal (`/api/deals/{id}/census/`); single objects have flat URLs
  (`/api/plans/{id}/`). Trailing slashes everywhere.
- **Status codes:** 200 OK · 201 created · 204 deleted · 400 validation failed · 401 not signed in · 403 not allowed
  (non-admin on admin endpoints) · 404 not found · 409 conflict (e.g. writing to a lost deal) · 410 gone (expired or
  revoked client link) · 413 file too large.
- **Error bodies** use DRF's standard shapes: `{"field_name": ["message", …]}` for validation,
  `{"non_field_errors": ["…"]}` for whole-request problems, `{"detail": "…"}` otherwise. The frontend helper
  `lib/errors.js` turns any of these into display text.
- **Pagination** (lists that can grow): `?page=N`, 25 per page unless stated; response
  `{"count": n, "next": url|null, "previous": url|null, "results": [...]}`.
- **Formats:** dates `YYYY-MM-DD`; timestamps ISO 8601 UTC (`2026-11-10T15:04:05Z`). Stored field values are
  strings. Computed money is a JSON number: whole dollars for premiums and totals, two decimals for rates.
- **Writes return only what changed** — the updated object, or a small payload for the tab. Never a whole-deal
  payload.
- **Downloads** are `GET`s that stream a file with `Content-Disposition: attachment; filename="…"`. File names are
  built from the client name and the document type, with characters outside `[A-Za-z0-9 ._-]` removed. A
  download response is never compressed.
- No query parameter may be named `format` (DRF reserves it).
- **Lost deals:** every write to a lost deal returns `409 {"detail": "This deal is marked lost. Reopen it to make changes."}`
  except reopening it and adding notes. Reads always work.

### 3.7 Values and where they came from

Values entered about a deal live in JSON dictionaries on their row: `Intake.answers`, `Member.data`,
`Plan.values`. Each has a parallel `sources` dictionary with one entry per key that has a value:

```json
{
  "deductible_single": {
    "origin": "typed",          // typed | import | client | ai
    "by": 3,                    // user id (null for client)
    "at": "2026-11-20T15:04:40Z",
    "doc": 41,                  // document id, when the value was read from a file
    "page": 2,                  // PDF page, when known
    "cell": "Medical!D12",      // sheet cell, for spreadsheet imports
    "link": 7,                  // client link id, for origin=client
    "confirmed_by": 5,          // set when a person confirms an import/client/ai value
    "confirmed_at": "2026-11-21T09:12:00Z"
  }
}
```

Rules:
- Writing a value replaces its whole source entry. A confirmation therefore never outlives the value it confirmed.
- Clearing a value removes both the value and its source entry.
- **Status is computed, never stored:** `missing` (required and blank) · `blank` (optional and blank) ·
  `to_check` (origin `ai` and not confirmed) · `ok` (everything else).
- Values are stored as strings, normalized by the field's type on write (§5).

**Activity log.** Every service write appends one `Activity` row: who, when, which area, what action, and a
one-line summary such as "Edited 3 intake answers", "Imported census: 152 people (38 dependents)",
"Marked Aetna HMO 1500 sold". A summary MUST NOT contain census values or person names (§3.8).

### 3.8 Security and PHI

- **PHI in this app** is anything identifying a census member: names, SSNs, dates of birth, addresses, phone,
  email, salary. Rules:
  - never written to logs, error messages, `Activity` summaries, file names or URLs;
  - downloadable only through authenticated endpoints;
  - SSNs shown masked (`***-**-1234`) on the client portal;
  - never present in test fixtures or seed data — test data is synthetic.
- **Passwords** go through Django's password validators on every path that sets one.
- **Tokens** (DRF, 40 hex characters): one per user. Logging out deletes it. Changing or resetting a password
  deletes it and issues a new one. Deactivating a user deletes it. Optional expiry via `TOKEN_TTL_HOURS`.
- **Password reset** uses Django's `default_token_generator` and `urlsafe_base64` user ids (nothing secret is stored).
  The request endpoint always answers 200 so it never reveals which emails exist.
- **Client links** use `secrets.token_urlsafe(32)`, expire within 30 days at most, and can be revoked. A bad token
  answers 404, an expired or revoked one 410. Their payloads are explicit allowlists.
- **Uploads:** allowed extensions `.pdf .xlsx .xlsm .xls .csv .png .jpg .jpeg .docx .doc .txt .eml .msg`; maximum
  50 MB; stored under `media/deals/<deal_id>/`; never served by a public URL. Downloads set
  `X-Content-Type-Options: nosniff` and `Cache-Control: private, no-store`, with the content type chosen from the
  file extension, never from the upload.
- **Spreadsheet injection:** any text written into a generated CSV or XLSX that begins with `=`, `+`, `-`, `@`, a tab
  or a carriage return MUST be written as literal text (XLSX: a string cell with the quote prefix; CSV: prefix `'`).
  Formulas the code writes on purpose (proposal totals) are exempt.

### 3.9 Frontend conventions

- **Routing:** `BrowserRouter`; every page component is lazy-loaded (`React.lazy`), so each tab is its own bundle.
- **API client** (`src/api/client.js`): one axios instance with `baseURL: '/api'`. A request interceptor adds the
  token from `localStorage['token']`. A response interceptor, on 401 from any endpoint except `/auth/login/` and the
  portal, clears the token and sends the browser to `/login`.
- **Data fetching:** TanStack Query only — no hand-built caches. Query keys follow `['deal', dealId, '<area>', …]`.
  `/api/meta/` is fetched once (`staleTime: Infinity`). A mutation writes the returned object into the cache or
  invalidates **only its own area's** keys. The Overview refetches whenever it is opened.
- **Vocabulary** (lines, fields, questions, choices) always comes from `/api/meta/`. The frontend MUST NOT
  hard-code a backend list.
- **No business math in the frontend.** Premiums, totals, readiness and statuses are displayed as the server
  returns them.
- **Styling:** CSS Modules per component plus `styles/tokens.css` (colours, spacing, type scale, radii). Brand navy
  `#173a63`. No global class names outside `base.css` (resets, typography).
- **Shared UI kit** (`src/ui/`): Button, IconButton, Modal, ConfirmDialog, Field (label + input + help + error),
  FieldForm (renders a list of field definitions), Select, MultiSelect, DateInput, DataGrid (§8.16), Tabs, Badge,
  StatusDot, Toast (one provider), FileDrop, EmptyState, Spinner, ErrorBoundary.
- **Files stay under 300 lines.** Split a component before it grows past that.
- **Accessibility basics:** every input has a label; keyboard reachable; visible focus; colour is never the only
  signal (pair it with an icon or text).
- No walkthrough or tour code inside product components.

---

## 4. Reference data

These lists are business data. Implement them as Python constants in the module named in each heading. They are
served to the frontend by `GET /api/meta/` (§7.2) and are **never** stored in database tables or created by
migrations. Changing one is a one-line code change.

### 4.1 Lines of coverage — `deals/lines.py`

27 lines, in this display order. **Field set** chooses the plan fields (§4.3). **Rate basis** chooses the premium
formula (§5.5). **Priced from** says which census data the formula uses.

| Key | Label | Short | Field set | Rate basis | Priced from |
|---|---|---|---|---|---|
| `medical` | Medical | Med | medical | composite | `medical_tier` counts |
| `dental` | Dental | Den | dental | composite | `dental_tier` counts |
| `vision` | Vision | Vis | vision | composite | `vision_tier` counts |
| `basic_life_add` | Basic Life & AD&D | Life | life | volume_1000 | Σ `basic_life_amount` |
| `voluntary_life` | Voluntary Life | Vol Life | life | volume_1000 | Σ `vol_life_amount` |
| `std` | Short-Term Disability | STD | disability | weekly_10 | Σ `std_amount` |
| `ltd` | Long-Term Disability | LTD | disability | payroll_100 | Σ `annual_salary` |
| `voluntary_worksite` | Voluntary / Worksite | Worksite | generic | composite | `medical_tier` counts (proxy) |
| `hsa` | HSA | HSA | generic | pepm | employee count |
| `fsa` | FSA | FSA | generic | pepm | employee count |
| `hra` | HRA | HRA | generic | pepm | employee count |
| `eap` | EAP | EAP | generic | pepm | employee count |
| `telehealth` | Telehealth | Telehealth | generic | pepm | employee count |
| `voluntary_std` | Voluntary STD | Vol STD | disability | weekly_10 | Σ `std_amount` |
| `voluntary_ltd` | Voluntary LTD | Vol LTD | disability | payroll_100 | Σ `annual_salary` |
| `accident` | Accident | Accident | generic | composite | `medical_tier` counts (proxy) |
| `hospital` | Hospital Indemnity | Hospital | generic | composite | `medical_tier` counts (proxy) |
| `critical_illness` | Critical Illness | CI | generic | composite | `medical_tier` counts (proxy) |
| `legal` | Legal | Legal | generic | pepm | employee count |
| `identity_theft` | Identity Theft | ID Theft | generic | pepm | employee count |
| `gap` | Gap | Gap | generic | composite | `medical_tier` counts (proxy) |
| `dependent_care_fsa` | Dependent Care FSA | DCFSA | generic | pepm | employee count |
| `ichra` | ICHRA | ICHRA | generic | pepm | employee count |
| `pet` | Pet | Pet | generic | pepm | employee count |
| `individual_life` | Individual Life | Ind Life | life | volume_1000 | Σ `vol_life_amount` |
| `stop_loss` | Stop-Loss | Stop-Loss | stop_loss | stop_loss | enrolled employees (`medical_tier` counts) |
| `pbm` | PBM (Pharmacy) | PBM | generic | pepm | employee count |

"Proxy" means the line has no tier column of its own, so it borrows the medical tier counts and the UI labels the
counts "from medical (proxy)".

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

### 4.2 Coverage tiers — `census/fields.py`

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

95 fields. **Type** controls storage and display (§5.4). **Req.** marks fields whose blank value counts as missing.
The table order within each group is the display order.

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

"Universal" fields are `network`, `plan_type`, `plan_number` and `group_premium_monthly`.

| Group | Key | Label | Type | Req. | Lines |
|---|---|---|---|---|---|
| info — Plan info | `network` | Network | text | | all |
| | `plan_type` | Plan Type | text | | all |
| | `plan_number` | Plan Number | text | | all |
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
| | `unit_rate` | Unit Rate | rate | ✓ | life, disability, PEPM lines |
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

### 4.4 Census columns — `census/fields.py`

45 columns, in display order. **Required** codes: **A** every person · **E** employees only ·
**L:x** employees only, when line *x* is requested on the deal · **M** employees only, when medical is requested
**and** the deal has medical coverage in force today · blank = optional. Dependents are never required to fill
employment or enrollment columns (they inherit the employee's election).

| Group | Key | Label | Type | Required |
|---|---|---|---|---|
| Identity | `ext_emp_id` | Emp ID | text | |
| | `first_name` | First Name | text | A |
| | `middle_name` | Middle Name | text | |
| | `last_name` | Last Name | text | A |
| | `relationship` | Relationship | text | |
| | `subscriber_ssn` | Employee SSN | ssn | |
| Demographics | `dob` | Date of Birth | date | A |
| | `ssn` | SSN | ssn | A |
| | `gender` | Gender | text | |
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
| | `medical_tier` | Medical Tier | tier | E |
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

**Columns in scope for a deal** (shown in the grid and the blank template): Identity, Demographics, Employment and
Medical always; Dental, Vision, Life and Disability only when one of their lines is requested (Life: basic_life_add,
voluntary_life or individual_life; Disability: std, ltd, voluntary_std or voluntary_ltd).

**Accepted values** offered as choices (other spellings are still read by the rules in §5.3):

| Column | Choices |
|---|---|
| every tier column | EE, ES, EC, FAM, Waived |
| `gender` | M (Male), F (Female) |
| `relationship` (dependents) | Spouse, Child, Domestic Partner |
| `employment_status` | Full-time, Part-time, COBRA, Retiree |
| `state`, `work_state` | the 50 state codes plus DC |

### 4.5 Intake questionnaire — `intake/form.py`

**Sections:** `employer` Employer information · `eligibility` Eligibility & workforce · `goals` Goals & preferences ·
`compliance` Compliance & regulatory.

**Need:** **Q** quote-blocking (counts toward "ready to quote") · **C** counts when shown · blank = optional.
**Types:** text, number, money, percent, date, yesno, choice (one of the options), multi (several options).

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

**Blocks** (non-question parts of the intake page): **Contacts** (client-level; §6.2) · **Current coverage**
(§6.5) · **Lines to quote** (`Deal.requested_lines`) · **Authorizations & documents** (typed BOR signature plus
uploads of kind `bor`, `carrier_auth`, `invoice`, `renewal`, `claims`).

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

### 4.6 Other vocabularies

**Deal stages** (`deals/stages.py`): `intake` Intake · `quoting` Quoting · `proposal` Proposal · `sold` Sold ·
`lost` Lost. Order: intake → quoting → proposal → sold. `lost` is off the ladder.

**Contact roles:** `owner` Owner · `decision_maker` Decision Maker · `hr_admin` HR Admin · `benefit_admin` Benefit
Administrator · `payroll_contact` Payroll Contact · `billing` Billing · `prior_broker` Prior Broker.

**Funding (current coverage):** `fully_insured` Fully insured · `level_funded` Level-funded · `self_funded`
Self-funded · blank = unknown.

**Funding requested on an RFP:** `fully_insured` Fully insured · `level_funded` Level-funded · `aso` Self-funded (ASO).

**Document kinds** (`documents/kinds.py`): `quote` Carrier quote · `renewal` Renewal / rates · `sbc` SBC / plan
summary · `census` Census · `invoice` Current invoice · `bor` BOR / signed authorization · `carrier_auth` Carrier
authorization · `claims` Claims experience · `plan_doc` Plan document / SPD · `proposal` Proposal / presentation ·
`other` Other.

**Document roles** (only for kinds quote, renewal, sbc — "what is this document?"): `current` Current plans in
force · `renewal` Renewal of the current plans · `alternates` Alternate quotes · blank = not said.

**Commission types:** `pct` percentage of premium · `flat` flat dollars per year · `pepm` dollars per employee per month.

### 4.7 Carriers — `rfp/carriers.py`

25 carriers. **Census format** names a carrier-specific census file (§9.8); blank means the carrier accepts the
universal Warner census. **Small / Large** list the Warner form columns (§4.1) offered at each group size; "—"
means the carrier is not offered at that size.

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

**Warner Pacific quoting inbox:** `FLQuoting@WarnerPacific.com`.

**Matching a carrier name** (e.g. from a document or typed text) to a registry entry: lower-case, replace every
non-alphanumeric run with one space, trim; match against each carrier's normalized name and aliases; first exact
match wins; otherwise no match.

### 4.8 Census header synonyms — `census/importer.py`

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

Every rule here lives in a pure function (no database access) inside the named module and has unit tests (§12).

### 5.1 Deal stages — `deals/stages.py`

- Ladder: `intake → quoting → proposal → sold`. Automatic moves only go **forward**; a move to an earlier stage is
  ignored.

| Event | Moves the deal to |
|---|---|
| Deal created | `intake` |
| First RFP email draft marked sent (§5.8) | `quoting` |
| First client proposal file downloaded (workbook, deck or PDF) | `proposal` |
| A plan marked sold | `sold` (and the client's relationship becomes `existing`) |

- A member may also set the stage by hand to `intake`, `quoting` or `proposal` (forward or backward). `sold` is
  reached only by marking a plan sold. Un-selling the last sold plan on a deal returns it to `proposal`.
- **Lost:** "Mark lost" requires a reason (1–300 characters), records `lost_at` and `lost_from_stage`, and sets
  `lost`. "Reopen" restores `lost_from_stage` and clears the three lost fields. A lost deal refuses writes (§3.6).
  A sold deal cannot be marked lost (un-sell first).

### 5.2 Intake — `intake/form.py`, `intake/values.py`, `intake/validation.py`

**Cleaning a typed answer** (`clean_value(question, raw) → (value, error)`). Leading/trailing spaces are removed.
An empty answer is stored as "no answer" (the key is removed from `answers`).

| Type | Accepts | Stored as | Error text |
|---|---|---|---|
| text | anything | trimmed text | — |
| text, key `fein` | `NN-NNNNNNN` or 9 digits (spaces ignored) | `NN-NNNNNNN` | `FEIN takes XX-XXXXXXX, not "<raw>"` |
| number, money, percent | a number after removing `$`, `,` and `%` (regex `-?\d+(\.\d+)?`) | the number as text (`"1500"`, `"7.5"`) | `<Label> takes a number, not "<raw>"` |
| date | any common date (month-first when ambiguous) | `YYYY-MM-DD` | `<Label> takes a date, not "<raw>"` |
| yesno | yes, y, true, 1 / no, n, false, 0 (any case) | `Yes` / `No` | `<Label> takes Yes or No, not "<raw>"` |
| choice | one option, matched without case | the option as written in §4.5 | `<Label> takes one of: <options> — "<raw>" is not one of them` |
| multi | options separated by commas, semicolons, slashes or spaces | `"FL, GA"` (options as written, de-duplicated, in input order) | `<Label> takes <first 12 options>…; not: <bad parts>` |

**Shown-when conditions.** `{"field": key, "op": "gt"|"gte"|"eq"|"nonempty", "value": x}`: `eq` compares the stored
text exactly; `gt`/`gte` compare numbers (false if either side is not a number); `nonempty` is true for any answer.
A hidden question keeps its stored answer but is not shown and never counts toward readiness.

**Validation** (`validate_intake(deal) → {key: [issue]}`; issue = `{code, severity, message}`; severity `error` or
`warning`). Issues are advisory: they show beside the question and never block saving.

| Code | Severity | Rule | Message |
|---|---|---|---|
| `fein_format` | error | `fein` present and not `\d{2}-?\d{7}` | `FEIN "<v>" is not in XX-XXXXXXX format` |
| `counts_order` | error | `employee_count` > `total_employees` | `Eligible employees (<e>) exceeds total employees (<t>)` |
| `counts_sum` | warning | `enrolled_count` + `waiving_count` > `employee_count` (either present) | `Enrolled + waiving is more than the eligible count — check the numbers` |
| `state_format` | warning | `situs_state` not 2 letters; or any `states_operating` entry not 2 letters | `"<v>" is not a 2-letter state code` |
| `ale_suggest` | warning | `total_employees` ≥ 50 and `ale_status` blank | `<n> employees — likely an ACA Applicable Large Employer; please confirm` |
| `form_5500_contradiction` | error | max(`enrolled_count`, `enrolled_life_count`) ≥ 100 and `form_5500_required` = No | `<n> enrolled on at least one benefit line but Form 5500 is marked "No" — did you make a mistake, or is the group out of compliance? (100+ participants triggers a filing)` |
| `pcori_contradiction` | warning | `self_funded` = Yes and `pcori_filing` = No | `Self-funded groups owe a PCORI filing (IRS Form 720, due July 31) — please double-check this answer` |
| `hours_range` | warning | `hours_threshold` outside 1–40 | `Hours/week is usually between 1 and 40` |
| `child_age_range` | warning | `child_age_limit` outside 18–30 | `Dependent child age limit is usually 26 (allowed 18–30)` |
| `email_format` | error | a contact's email not `^[^@\s]+@[^@\s]+\.[^@\s]+$` (key `contact:<id>`) | `"<v>" is not a valid email address` |
| `renewal_past` | warning | a current-coverage row's renewal date before today (key `coverage:<id>`) | `Renewal date is in the past` |
| `renewal_far` | warning | a current-coverage row's renewal date more than 12 months away | `Renewal date is more than 12 months out` |

**Readiness.**
- *Needed questions* = every **Q** question, plus every **C** question that is currently shown.
- *Contacts OK* = at least one client contact with role `hr_admin` or `benefit_admin` that has both a name and an email.
- **Ready to quote** = every needed question answered **and** contacts OK **and** at least one requested line.
- **BOR on file** = `bor_signed_at` is set (typed signature) **or** a document of kind `bor` exists on the deal.
- Readiness % = round(answered needed ÷ needed × 100); 100 when nothing is needed.

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

#### 5.3.2 Importing a census file — `census/importer.py`

1. **Read the file.** `.csv`: decode UTF-8 (with or without BOM), else Latin-1. `.xlsx`/`.xlsm`: first worksheet,
   read-only, cached values (formulas never run). `.xls`: first sheet via xlrd. Every cell becomes text: dates
   `MM/DD/YYYY`, whole-number floats without `.0`, everything else trimmed text. Anything else → 400
   `"<name>" is not a spreadsheet or CSV census file.`
2. **Find the header row:** the first of the top 10 rows with at least 3 cells that are non-empty and not made only of
   `0-9 / . , $ -`. None → 400 `Could not find a header row in "<name>".` Drop trailing blank header cells. Data rows
   are the rows below; fully blank rows are dropped; each kept row remembers its sheet row number.
3. **Propose a mapping**, column by column, left to right. Each census key may be used by one column only (the first
   to claim it):
   - **Positional hint** (§4.8 bare effective dates) → confidence 0.70.
   - **Exact:** the normalized header equals the key with spaces, the column's label, or a synonym → 0.95.
   - **Fuzzy:** among unused keys (respecting the line-word guard), the synonym or key sharing the most words with the
     header, where the synonym has no more than one word beyond the overlap → 0.60.
   - No match → unmapped. Each mapping entry also carries up to 3 sample values from the column.
   - `low` = mapped and confidence < 0.85. Low entries are highlighted for review.
4. **Review.** The member sees every column, its samples and its proposed target, and may change a target or set it to
   "Ignore". Assigning one key to two columns → 400.
5. **Build people** from the rows under the confirmed mapping:
   - A row is an **employee** if its relationship is blank or one of the employee words (§4.8); otherwise a
     **dependent**.
   - An employee with no `ssn` but a `subscriber_ssn` gets `ssn` copied from it.
   - A dependent's employee is found by: the digits of its `subscriber_ssn` matching an employee's SSN (or that
     employee's `subscriber_ssn`), else its `ext_emp_id` matching an employee's, else the last employee above it.
     A dependent with no employee above it stays unlinked (a `dep_orphan` error shows).
   - Values are cleaned (§5.3.1). Sources: `origin: import`, the document id, and `cell` = sheet name + column letter +
     row number (e.g. `Census!D12`).
6. **Match to the existing roster** (empty for a new deal): an incoming person matches an existing member of the same
   kind by SSN digits, else by last name + first name + date of birth (case-insensitive). Matched: values present in
   the file overwrite; blanks in the file keep the existing value. Unmatched incoming: created. Existing members not
   matched: removed (with their dependents).
7. **Dry run first.** `apply?dry_run=1` returns `{create, update, remove, unchanged}` counts and writes nothing; the
   screen shows them and asks for confirmation when anything would be removed. The real apply runs in one transaction,
   marks the import `applied`, and logs `Imported census: <n> people (<d> dependents)`.

#### 5.3.3 Is a cell required? — `census/fields.py: is_required(key, member, deal)`
One function; nothing else decides this.
1. Dependent and the key is in Employment, Medical, Dental, Vision, Life or Disability, or is `zip` → **not required**.
2. Key marked **A** or **E** in §4.4 → **required**.
3. Key marked **L:x** → required when line *x* is in `deal.requested_lines`.
4. Key marked **M** (`medical_plan`) → required when `medical` is requested **and** the deal has a current-coverage row
   for medical with `in_force = true`.
5. Otherwise → not required.

#### 5.3.4 Validation — `census/validation.py: validate(members, deal) → {(member_id, key): [issue]}`

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

#### 5.3.6 Enrollment rollup — `census/rollup.py`
For each requested line with a composite basis (and always for medical): count employees by their value in the line's
tier column (§4.1; worksite-type lines use `medical_tier` and say "proxy"): `EE`, `ES`, `EC`, `FAM`, `waived`,
`blank`. Dependents are never counted. For volume lines: the sum of the volume column over employees (§4.1). For PEPM
lines: the employee count. For stop-loss: the medical EE+ES+EC+FAM total, else the employee count.

#### 5.3.7 Derived census facts
- **Full-time count (FTE):** employees whose `hours_per_week` ≥ the intake `hours_threshold` (default 30). Blank hours
  are not counted. Blank when the roster has no employees.
- **Age at effective date** (carrier exports): whole years from DOB to the deal's effective date (else the intake
  `target_effective_date`); blank if outside 0–120 or either date is missing.
- **In contiguous US:** a ZIP whose first three digits are **not** 006–009, 090–099, 340, 962–969 or 995–999.

### 5.4 Plans — `quotes/`

**Storing a plan value** (types from §4.3):

| Type | Accepts | Stored as | Refused with |
|---|---|---|---|
| text | anything | trimmed text | — |
| amount | anything | a number (`$`/`,` removed) when it is one, otherwise the carrier's text as typed | — |
| percent | anything | a number (`%` removed) when it is one, otherwise text | — |
| rate | a number (`$`, `,` removed), or N/A, NA, `-`, blank (= empty) | number text with up to 2 decimals | `<Label> takes a number, not "<raw>"` |
| number | a number, or blank | number text | `<Label> takes a number, not "<raw>"` |
| yesno | as intake (§5.2) | `Yes`/`No` | `<Label> takes Yes or No, not "<raw>"` |
| url | `http://…` or `https://…` | as typed | `<Label> takes a web address starting with http:// or https://` |

Display: amounts as currency (`$1,500`) when numeric, percent as `20%`, rates as `$512.34`.

**Roles and links.**
- `current` — in force today. Has no `renews` or `replaces` link.
- `renewal` — the current carrier's new rates for a current plan. `renews` MUST point to a current plan on the same
  deal and line. At most one renewal per current plan.
- `alternate` — a competing plan. `replaces` MAY point to a current plan on the same deal and line (many alternates may
  replace the same current plan).
- A plan's `line` never changes after creation.
- Changing a role clears links that no longer apply. Deleting a current plan turns its renewal into an alternate and
  clears every `replaces` link pointing at it.
- **"Create renewal"** on a current plan creates a `renewal` with the same carrier, name, plan number and every value
  except the rate and contribution groups (§4.3 `rates`, `contrib`, and `lf`), with their sources copied.
- **Starred** plans are the default selection for the proposal. Any number may be starred.
- **Sold:** at most one sold plan per line per deal (database constraint). Marking a plan sold un-sells the line's
  other sold plan in the same transaction, sets `sold_at`, moves the deal to `sold` and the client to `existing`.

**Plan value status:** `missing` when the field is required (§4.3) and blank; otherwise per §3.7.

### 5.5 Premium math — `quotes/math.py`

All money is computed in floating point and rounded **half away from zero** after first reading the value at 15
significant digits — exactly what Excel's `ROUND` does:

```python
def round_money(amount, places=0):
    if amount is None or not math.isfinite(amount): return None
    exact = Decimal(format(amount, '.15g')).quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
    return int(exact) if places == 0 else float(exact) + 0.0
```

**Which enrollment counts price a composite-rated plan** (`counts_for(plan)` → `(counts, source)` or a reason):

1. The plan's own typed counts, when `counts_on` is true and any count is above zero → source `typed`.
2. A **renewal**: its current plan's typed counts, when that plan's `counts_on` is true → `from current plan`.
3. An **alternate** with `replaces`: the replaced plan's typed counts, when on → `from replaced plan`.
4. If the line has **two or more current plans**, stop → no price, reason `per_plan_counts_needed`
   ("Enter enrollment for each current plan"). A line-wide census count would spread everyone across every plan.
5. The census rollup for the line (§5.3.6) → `census` (or `census (medical proxy)`).
6. Nothing → no price, reason `no_enrollment`.

**Monthly premium by rate basis** (`monthly_premium(plan, deal) → (dollars | None, reason)`):

| Basis | Formula | No price when |
|---|---|---|
| composite | round_money(Σ over tiers with count > 0 of rate × count) | counts sum to 0 (`no_enrollment`); an enrolled tier has no rate → use the quoted `group_premium_monthly` if present, else `missing_rate` |
| volume_1000 | round_money(volume ÷ 1,000 × unit_rate) | volume 0 (`no_enrollment`); no unit rate or no volume → quoted premium, else `missing_rate` / `no_volume` |
| weekly_10 | round_money(volume ÷ 10 × unit_rate) | as above |
| payroll_100 | round_money(annual salary total ÷ 12 ÷ 100 × unit_rate) | as above |
| pepm | round_money(unit_rate × employee count) | no employees (`no_enrollment`); no unit rate → quoted premium, else `missing_rate` |
| stop_loss | round_money((sl_spec_rate + sl_agg_rate + sl_other_load) × enrolled employees); blank agg/other count as 0 | no `sl_spec_rate` → quoted premium, else `missing_rate`; no enrolled employees → `no_enrollment` |

"Quoted premium" = the plan's `group_premium_monthly`, rounded. It is **never** used when nobody is enrolled — a price
with no enrollment is "no price", never $0.

**Derived figures:**
- Annual = monthly × 12 (blank when monthly is blank).
- **Comparison base** for a plan: a renewal → its current plan; an alternate with `replaces` → that plan; an
  alternate without `replaces` on a line with exactly one current plan → that plan; otherwise none.
- Change vs base: `delta` = annual − base annual; `pct` = round_money((annual − base) ÷ base × 100, 1); `pct` is blank
  when the base is 0 or blank.
- Renewals also report per-tier rate change: for each tier, `rate − current rate` and the percentage as above.
- Employee cost per tier = max(0, round_money(rate − contribution, 2)); blank if either is blank.
- **Packages** (per line): *Current* = all current plans; *Renewal* = all renewal plans; one *Alternate* package per
  carrier (its alternates). Package monthly = Σ of its plans' monthly premiums (each already rounded); blank if any plan
  has no price. Package change vs the Current package uses the same delta / pct rules. The renewal package's `pct` is
  the "average increase" shown on proposals.

**Worked examples** (each MUST be a unit test):

| Case | Inputs | Expected |
|---|---|---|
| Composite | rates EE 500.00, ES 1000.50, EC 900.25, FAM 1500.75; counts 10/3/2/5 | 5,000 + 3,001.50 + 1,800.50 + 7,503.75 = 17,305.75 → **17,306** |
| Half-up | 2642.5 | **2643** (Python's `round` gives 2642) |
| Half-up, cents | round_money(2.675, 2) | **2.68** |
| Missing enrolled rate, quoted premium 15,000 | rates EE only; counts EE 10, ES 2 | **15,000** (quoted) |
| Missing enrolled rate, no quoted premium | same, no `group_premium_monthly` | no price, `missing_rate` |
| No enrollment | counts all 0, quoted premium 9,000 | no price, `no_enrollment` |
| Volume per $1,000 | volume 1,250,000; unit 0.12 | **150** |
| Payroll per $100 | salaries 3,000,000; unit 0.45 | 3,000,000 ÷ 12 ÷ 100 × 0.45 = **1,125** |
| PEPM | unit 3.50; 42 employees | **147** |
| Stop-loss | spec 85.20, agg 12.10, other blank; 40 enrolled | (97.30) × 40 = **3,892** |
| Change | annual 120,000 vs base 100,000 | delta **20,000**, pct **20.0** |
| Two current plans, no typed counts | medical line, 2 current plans | no price, `per_plan_counts_needed` |

### 5.6 Commission — `commission/math.py`

- **Parsing** (`parse_comp(raw)`): a bare number or text (`5`, `"5%"`) means a percentage; a dict
  `{"type": "pct"|"flat"|"pepm", "value": …}` names its type. `$`, `%` and `,` are ignored. Errors: unknown type
  `Type must be percentage, flat, or PEPM`; not a number `Must be a number`; negative `Must not be negative`;
  percentage over 100 `Must be between 0 and 100`. Stored as `{"type": t, "value": "<number as %g>"}`.
- **Label:** pct `5%`; flat `$5,000/yr`; pepm `$32 PEPM` (cents shown only when not whole).
- **Effective rate per requested line:** the deal's rate for the line, else the agency default (§6.2
  `AgencySettings.default_commission`), else none.
- **Basis plan per line:** the sold plan, else the first starred plan in display order, else none.
- **Expected annual revenue:** pct → round(basis plan's annual premium × value ÷ 100); flat → round(value);
  pepm → round(value × employees enrolled in the line × 12). Blank when the needed figure is missing. Deal total = sum
  of the lines that have a figure.
- **Producer split:** a list of `{user_id | null, name, pct}`. When non-empty, percentages are 0–100 and must total
  exactly 100 (error `Splits must add up to 100%`). Names are required when there is no user.

### 5.7 RFP — `rfp/request.py`

- **Size band:** `large` when enrolled employees ≥ 51, else `small`. Enrolled = the intake `enrolled_count` if
  answered, else the census medical rollup total (EE+ES+EC+FAM).
- **Route:** `warner` (one request to Warner Pacific, who forwards it to the carriers) or `direct` (one email per
  carrier). Default `warner`.
- **Lines:** default = the deal's requested lines.
- **Funding requested:** default = the funding of the medical current-coverage row (`fully_insured`→fully insured,
  `level_funded`→level-funded, `self_funded`→`aso`); unknown → fully insured **and** level-funded.
- **Form** (Warner quote request form): default `simplified` for every group size; `small_group` (2–50) and
  `large_group` (51+) MAY be chosen; they add the carrier × line matrix, funding boxes and notes.
- **Carrier eligibility** (advice, never a block): a carrier is *eligible* when its Warner columns for the band (§4.7)
  cover at least one requested line; otherwise it shows the reason ("Not offered at 51+", "Doesn't quote dental").
- **Commission request text** (one cell on the form, one line in emails): the effective commission label for each RFP
  line (§5.6). If all lines share one label, print it (`5%`); otherwise group lines by label, larger groups first:
  `5% Med · 15% Den/Vis` (short labels from §4.1).
- **Group facts** used to fill forms, cover pages and emails:

| Fact | Source |
|---|---|
| `group.legal_name` | intake `legal_name`, else client name |
| `group.address_street`, `group.city_state_zip`, `group.zip` | intake `address_physical`, split at the first comma |
| `group.sic`, `group.fein` | intake |
| `group.total_employees`, `group.eligible`, `group.enrolled`, `group.waiving`, `group.atne` | intake counts |
| `group.fte` | census FTE count (§5.3.7) |
| `group.years_in_business`, `group.waiting_period`, `group.locations` | intake |
| `group.current_carrier`, `group.current_funding` | the medical current-coverage row |
| `group.contact_first`, `group.contact_last`, `group.contact_email` | the client's primary contact, else the first HR admin / benefit administrator |
| `deal.effective_date`, `deal.due_date` | deal; RFP due date |
| `broker.agent` | the deal owner's full name |
| `broker.agency`, `broker.email`, `broker.address`, `broker.city_state_zip` | agency settings |
| `broker.commission` | commission request text |
| `broker.is_bor` | BOR on file (§5.2) |
| `funding.fully_insured`, `funding.level_funded`, `funding.aso` | requested funding |

- **Sent:** each email draft (§9.11) can be marked sent or un-sent. The first time any draft is marked sent, the deal
  moves to `quoting`.

### 5.8 Review & request — `review/`

- A **link** belongs to one recipient (name and email) and asks for any mix of: specific intake questions (or "all
  needed questions still blank", resolved to explicit keys when the link is created), census (`missing` — each
  person's blank required cells; `upload` — a census file; `none`), and document kinds. An optional message (≤ 1,000
  characters) shows at the top of the client's page.
- **Expiry:** chosen at creation, 1–30 days (default 14). Extending adds days, never beyond 30 days from now.
  Revoking ends it at once; restoring re-opens it within its expiry.
- **Copying the link marks it sent** (the app never emails it).
- **Client answers** are stored as pending `ClientValue`s, cleaned by the same rules as staff edits (§5.2, §5.3.1).
  A newer save of the same question or cell replaces the pending one. A value the client didn't change (equal to the
  current value, or a masked SSN sent back unchanged) is ignored.
- **Client uploads** become documents with `source = client` and `review_state = ''` (to review).
- **Approving** writes the value to the deal (`Intake.answers` or `Member.data`) with `origin: client` and the link id,
  marks it `approved`, and logs `Approved <n> client answers`. **Rejecting** marks it `rejected`; nothing on the deal
  changes. Uploads are accepted or marked "wrong file".

### 5.9 Next action — `overview/next_action.py`

The first matching row wins:

| # | Condition | Action label | Tab |
|---|---|---|---|
| 1 | stage `lost` | Deal lost — <reason> | — |
| 2 | stage `sold` | Sold | — |
| 3 | not ready to quote (§5.2) | Finish intake (<n> needed) | intake |
| 4 | no census employees **and** no plan has typed counts | Add the census, or type enrollment in the Advisor | census |
| 5 | census has errors | Fix <n> census errors | census |
| 6 | no RFP draft marked sent **and** no renewal or alternate plans | Send the RFP | rfp |
| 7 | a requested composite line has no renewal or alternate plans | Enter quotes as they arrive | advisor |
| 8 | no starred plans | Shortlist plans for the proposal | advisor |
| 9 | no proposal file ever downloaded | Build the proposal | proposal |
| 10 | otherwise | Mark the plan the client chose as sold | advisor |

Pending client answers are shown beside the next action ("<n> client answers to review"), never instead of it.

### 5.10 Overview summaries
Each app's `summary.py` returns a small dictionary for the Overview (no other app reads it):

| App | Summary keys |
|---|---|
| intake | `ready_to_quote`, `needed`, `answered`, `missing` (labels), `contacts_ok`, `lines`, `bor_on_file`, `issues` (counts by severity) |
| census | the §5.3.5 summary plus the medical rollup |
| quotes | per requested line: counts of current / renewal / alternate / starred plans and the sold plan's name |
| commission | expected annual total and how many lines have a rate |
| proposals | when each file type was last generated |
| rfp | carriers picked, drafts sent / total |
| review | open links, pending answers, uploads to review |
| documents | file count by kind |

---

## 6. Data model

Django models, by app. Every model has an auto `id` (BigAutoField). "FK" = `ForeignKey`. `created_at` uses
`auto_now_add`, `updated_at` uses `auto_now`. JSON fields default to `{}` or `[]` as shown.

### 6.1 accounts
No custom models. Django's `User` (username, email, first/last name, password, `is_active`, `is_staff` = **admin**,
`is_superuser`). DRF's `authtoken.Token` (key, user, created). The token's `created` drives `TOKEN_TTL_HOURS`.

### 6.2 deals

**Client**

| Field | Type | Notes |
|---|---|---|
| `name` | Char(200), indexed | Employer name as the team refers to it |
| `relationship` | Char(10): `new`/`existing`, default `new` | Becomes `existing` when a deal sells |
| `owner` | FK User, null, SET_NULL | |
| `notes` | Text, blank | |
| `created_by` | FK User, PROTECT | |
| `created_at`, `updated_at` | DateTime | |

**Deal**

| Field | Type | Notes |
|---|---|---|
| `client` | FK Client, CASCADE, `related_name='deals'` | |
| `effective_date` | Date, null | Plan year start |
| `stage` | Char(10), default `intake` | §4.6 |
| `lost_reason` | Char(300), blank | |
| `lost_at` | DateTime, null | |
| `lost_from_stage` | Char(10), blank | |
| `requested_lines` | JSON list of line keys, default `[]` | Validated against §4.1 |
| `owner` | FK User, null, SET_NULL | |
| `created_by` | FK User, PROTECT | |
| `created_at`, `updated_at` | DateTime | |

Index `(client, effective_date)`. The one-to-one rows owned by later apps (`Intake`, `Commission`, `ProposalConfig`,
`RfpConfig`) are created by **their own app** on first access (`get_or_create`) — `deals` never imports them (§3.3).
When `Intake` is first created it pre-fills `legal_name` with the client name (`origin: typed`).

**Contact** — client-level

| Field | Type | Notes |
|---|---|---|
| `client` | FK Client, CASCADE, `related_name='contacts'` | |
| `role` | Char(20), default `hr_admin` | §4.6 |
| `name`, `title` | Char(200), blank | |
| `email` | Char(254), blank | Validated by `email_format` |
| `phone` | Char(50), blank | |
| `is_primary` | Bool, default false | Unique per client when true (partial unique constraint); setting one clears the others |
| `sort_order` | PositiveInt | |

**Note**

| Field | Type | Notes |
|---|---|---|
| `deal` | FK Deal, CASCADE, `related_name='notes'` | |
| `body` | Text | 1–5,000 characters |
| `kind` | Char(10): `note`/`call`/`email`/`meeting`, default `note` | |
| `pinned` | Bool | |
| `author` | FK User, null, SET_NULL | |
| `created_at`, `updated_at` | DateTime | Ordering: pinned first, newest first |

**Activity**

| Field | Type | Notes |
|---|---|---|
| `deal` | FK Deal, CASCADE, `related_name='activity'` | |
| `actor` | FK User, null, SET_NULL | Null for the client portal |
| `actor_label` | Char(200), blank | e.g. "Client via link to J. Smith" |
| `area` | Char(20) | `deal`, `intake`, `census`, `documents`, `quotes`, `commission`, `proposal`, `rfp`, `review` |
| `action` | Char(20) | `created`, `updated`, `deleted`, `imported`, `approved`, `rejected`, `sent`, `sold`, `lost`, `reopened`, `generated` |
| `summary` | Char(300) | No PHI (§3.8) |
| `created_at` | DateTime, default now | Index `(deal, -created_at)` |

**AgencySettings** — single row, `pk = 1`, read through `AgencySettings.get()`

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

### 6.3 documents

**Document**

| Field | Type | Notes |
|---|---|---|
| `deal` | FK Deal, CASCADE, `related_name='documents'` | |
| `file` | File, `upload_to` = `deals/<deal_id>/<uuid4>-<safe name>` | Bytes deleted when the row is deleted (`post_delete`) |
| `original_name` | Char(255) | |
| `size` | PositiveBigInt | bytes |
| `content_type` | Char(100) | from the extension |
| `page_count` | PositiveInt, null | PDFs only (pypdf) |
| `kind` | Char(20), default `other` | §4.6 |
| `role` | Char(12), blank | §4.6, only for quote / renewal / sbc |
| `carrier` | Char(200), blank | Who the document is from |
| `lines` | JSON list | Lines it covers; empty = not said |
| `label` | Char(200), blank | Display name; blank shows `original_name` |
| `source` | Char(10): `staff`/`client`, default `staff` | |
| `review_state` | Char(10): blank/`accepted`/`wrong` | Client uploads only |
| `uploaded_by` | FK User, null, SET_NULL | |
| `uploaded_at` | DateTime | Index `(deal, uploaded_at)` |

### 6.4 intake

**Intake** — one per deal

| Field | Type | Notes |
|---|---|---|
| `deal` | OneToOne Deal, CASCADE, primary key, `related_name='intake'` | |
| `answers` | JSON `{key: value}` | §5.2 |
| `sources` | JSON `{key: source}` | §3.7 |
| `bor_name` | Char(200), blank | Typed signature |
| `bor_signed_at` | DateTime, null | |
| `bor_signed_by` | FK User, null, SET_NULL | Who recorded it |
| `updated_at` | DateTime | |

**CurrentCoverage**

| Field | Type | Notes |
|---|---|---|
| `deal` | FK Deal, CASCADE, `related_name='coverage'` | |
| `line` | Char(20) | §4.1 |
| `carrier` | Char(200), blank | |
| `funding` | Char(20), blank | §4.6 |
| `effective_date`, `renewal_date`, `rate_guarantee_through` | Date, null | |
| `in_force` | Bool, default true | false = a gap the deal proposes to fill |
| `on_proposal` | Bool, default true | |
| `notes` | Char(300), blank | |
| `sort_order` | PositiveInt | |

### 6.5 census

**Member** — one row per person

| Field | Type | Notes |
|---|---|---|
| `deal` | FK Deal, CASCADE, `related_name='members'` | |
| `kind` | Char(10): `employee`/`dependent` | |
| `parent` | FK self, null, CASCADE, `related_name='dependents'` | Dependents only; deleting an employee deletes its dependents |
| `data` | JSON `{key: value}` | §4.4, §5.3.1 |
| `sources` | JSON `{key: source}` | |
| `sort_order` | PositiveInt | File order |
| `created_at`, `updated_at` | DateTime | Index `(deal, kind, sort_order)` |

**CensusImport**

| Field | Type | Notes |
|---|---|---|
| `deal` | FK Deal, CASCADE, `related_name='census_imports'` | |
| `document` | FK Document, null, SET_NULL | |
| `sheet_name` | Char(100), blank | |
| `header_row` | PositiveInt | 1-based |
| `headers` | JSON list | |
| `mapping` | JSON list `[{column, header, samples[], field, confidence, low}]` | `field` = census key or blank |
| `status` | Char(10): `proposed`/`applied`/`discarded` | |
| `stats` | JSON | `{rows, employees, dependents, created, updated, removed}` |
| `created_by` | FK User, null | |
| `created_at`, `applied_at` | DateTime (applied_at null) | |

### 6.6 quotes

**Plan**

| Field | Type | Notes |
|---|---|---|
| `deal` | FK Deal, CASCADE, `related_name='plans'` | |
| `line` | Char(20) | Immutable after creation |
| `role` | Char(10): `current`/`renewal`/`alternate` | |
| `carrier` | Char(200) | |
| `name` | Char(200) | |
| `plan_number` | Char(100), blank | |
| `renews` | FK self, null, SET_NULL, `related_name='renewal_set'` | Unique when not null (one renewal per current plan) |
| `replaces` | FK self, null, SET_NULL, `related_name='replaced_by'` | |
| `values` | JSON `{key: value}` | §4.3, §5.4 |
| `sources` | JSON `{key: source}` | |
| `tier_counts` | JSON `{EE, ES, EC, FAM}` integers ≥ 0 | |
| `counts_on` | Bool, default false | |
| `starred` | Bool, default false | |
| `sold` | Bool, default false | Unique per `(deal, line)` when true |
| `sold_at` | DateTime, null | |
| `source_document` | FK Document, null, SET_NULL | The file it was read from, if any |
| `notes` | Text, blank | Internal |
| `sort_order` | PositiveInt | Display order within its role |
| `created_at`, `updated_at` | DateTime | Index `(deal, line, role, sort_order)` |

### 6.7 commission

**Commission** — one per deal: `deal` (OneToOne, primary key), `rates` JSON `{line: {type, value}}`, `splits` JSON
list `[{user_id, name, pct}]`, `updated_by` FK User null, `updated_at`.

### 6.8 proposals

**ProposalConfig** — one per deal: `deal` (OneToOne, primary key), `title` Char(200) blank, `notes` Text blank,
`lines` JSON `{line: [plan ids in display order]}` (empty = use defaults, §8.12), `generated` JSON
`{"workbook"|"deck"|"pdf": timestamp}`, `updated_by`, `updated_at`.

### 6.9 rfp

**RfpConfig** — one per deal: `deal` (OneToOne, primary key), `route` Char(10) default `warner`, `carriers` JSON list,
`other_carriers` Char(300) blank, `lines` JSON list (empty = requested lines), `funding` JSON list (empty = default),
`form` Char(20) blank (= `simplified`), `due_date` Date null, `notes` Text blank, `documents` JSON list of document ids
to include, `sent` JSON `{draft key: timestamp}`, `updated_by`, `updated_at`.

### 6.10 review

**ClientLink**

| Field | Type | Notes |
|---|---|---|
| `deal` | FK Deal, CASCADE, `related_name='client_links'` | |
| `token` | Char(64), unique | `secrets.token_urlsafe(32)` |
| `recipient_name` | Char(200), blank | |
| `recipient_email` | Email, blank | |
| `message` | Text, blank, ≤ 1,000 characters | |
| `asks` | JSON `{"intake": [keys], "census": "none"|"missing"|"upload", "documents": [kinds]}` | |
| `expires_at` | DateTime | |
| `sent_at`, `opened_at`, `last_opened_at`, `submitted_at`, `revoked_at` | DateTime, null | |
| `open_count` | PositiveInt, default 0 | Page loads |
| `created_by` | FK User, null | |
| `created_at` | DateTime | |

`is_live` = not revoked and now < `expires_at`.

**ClientValue**

| Field | Type | Notes |
|---|---|---|
| `link` | FK ClientLink, CASCADE, `related_name='client_values'` | |
| `target` | Char(10): `intake`/`census` | |
| `key` | Char(100) | Question key or census column key |
| `member` | FK Member, null, CASCADE | Census only |
| `value` | Text | Already cleaned |
| `status` | Char(10): `pending`/`approved`/`rejected` | |
| `reviewed_by` | FK User, null | |
| `reviewed_at` | DateTime, null | |
| `created_at`, `updated_at` | DateTime | |

Constraint: unique `(link, target, key, member)` while `status = pending`, with `nulls_distinct=False`.

---

## 7. API

Conventions are in §3.6. Paths below omit the `/api` prefix. **Auth** column: *user* = any signed-in user,
*admin* = `is_staff`, *public* = no sign-in.

### 7.1 Platform

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `health/` | public | §3.5 |
| GET | `meta/` | user | Every vocabulary in §4 |

`GET meta/` response (shape):

```json
{
  "lines": [{"key": "medical", "label": "Medical", "short": "Med", "field_set": "medical",
             "rate_basis": "composite", "tier_field": "medical_tier", "proxy": false}],
  "tiers": [{"code": "EE", "label": "Employee only"}],
  "stages": [{"key": "intake", "label": "Intake"}],
  "contact_roles": [{"key": "hr_admin", "label": "HR Admin"}],
  "funding": [{"key": "fully_insured", "label": "Fully insured"}],
  "rfp_funding": [{"key": "aso", "label": "Self-funded (ASO)"}],
  "document_kinds": [{"key": "quote", "label": "Carrier quote"}],
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
                "lines": ["medical", "dental", "vision"]}]
  },
  "carriers": [{"key": "aetna", "name": "Aetna", "group": "medical", "census_format": "aetna_gateway"}]
}
```

### 7.2 Accounts — `auth/`

| Method | Path | Auth | Request | Response |
|---|---|---|---|---|
| POST | `auth/login/` | public (throttle 10/min) | `{username, password}` | `200 {token, user}` · `400 {"non_field_errors": ["Invalid username or password."]}` (also for inactive users) |
| POST | `auth/logout/` | user | — | `204` (token deleted) |
| GET | `auth/me/` | user | — | `200 user` |
| PATCH | `auth/me/` | user | `{first_name, last_name, email}` | `200 user` |
| POST | `auth/password/` | user | `{old_password, new_password}` | `200 {token}` (old token deleted, new one issued) · `400 {"old_password": ["Incorrect password."]}` or `{"new_password": [validator messages]}` |
| POST | `auth/password-reset/` | public | `{email}` | always `200 {"detail": "If that email belongs to an account, a reset link is on its way."}`; emails each active user with that address a link `FRONTEND_URL/reset-password/<uid>/<token>` |
| POST | `auth/password-reset/confirm/` | public | `{uid, token, new_password}` | `200 {"detail": "Password updated. Please sign in."}` (all tokens for the user deleted) · `400 {"token": ["This reset link is invalid or has expired."]}` |
| GET | `auth/users/` | admin | — | `200 [user + is_active, last_login]` |
| POST | `auth/users/` | admin | `{username, email, first_name, last_name, password, is_admin}` | `201 user` · `400` duplicate username/email or password rules |
| PATCH | `auth/users/{id}/` | admin | any of `{email, first_name, last_name, is_admin, is_active, password}` | `200 user` · `400 {"non_field_errors": ["You can't remove your own admin access or deactivate yourself."]}` |

`user` = `{id, username, first_name, last_name, full_name, email, is_admin}`. Deactivating a user deletes their token.

### 7.3 Clients and deals — `deals/`

| Method | Path | Auth | Request | Response |
|---|---|---|---|---|
| GET | `clients/` | user | `?q=&relationship=new\|existing&stage=&owner=me\|<id>&ordering=-updated\|name&page=` | paginated client rows |
| POST | `clients/` | user | `{name, relationship?, effective_date?, owner_id?}` | `201 {client, deal}` — creates the client and its first deal |
| GET | `clients/{id}/` | user | — | `{id, name, relationship, owner, notes, deals: [{id, effective_date, stage}], contacts: [...]}` |
| PATCH | `clients/{id}/` | user | `{name, relationship, owner_id, notes}` | client |
| DELETE | `clients/{id}/` | admin | — | `204` (deletes deals, documents and files) |
| GET / POST | `clients/{id}/contacts/` | user | `{role, name, title, email, phone, is_primary}` | list / `201 contact` |
| PATCH / DELETE | `contacts/{id}/` | user | same fields | contact / `204` |
| GET | `deals/{id}/` | user | — | deal header |
| PATCH | `deals/{id}/` | user | `{effective_date, stage, requested_lines, owner_id}` | deal header · `400 {"stage": ["Mark a plan sold or use Mark lost."]}` for `sold`/`lost` |
| POST | `deals/{id}/lost/` | user | `{reason}` | deal header · `400` blank reason · `409` if sold |
| POST | `deals/{id}/reopen/` | user | — | deal header |
| GET / POST | `deals/{id}/notes/` | user | `{body, kind, pinned}` | list (pinned first, newest first) / `201 note` |
| PATCH / DELETE | `notes/{id}/` | author or admin | same fields | note / `204` |
| GET | `deals/{id}/activity/` | user | `?page=` | paginated `[{id, at, actor, area, action, summary}]` |
| GET | `agency/` | user | — | settings + `has_logo` |
| PATCH | `agency/` | admin | any settings field except logo | settings |
| PUT / DELETE | `agency/logo/` | admin | multipart `file` (PNG/JPEG ≤ 2 MB) | settings / `204` |
| GET | `agency/logo/` | user | — | PNG |

**Client row** (dashboard):

```json
{"id": 12, "name": "Example Co.", "relationship": "new",
 "owner": {"id": 3, "name": "Dana Lee"},
 "deal": {"id": 31, "stage": "quoting", "effective_date": "2027-01-01"},
 "updated_at": "2026-11-20T15:04:05Z"}
```

`q` matches the client name case-insensitively anywhere in the name. `updated_at` is the later of the client's and its
current deal's. Default ordering newest first. The current deal is the open deal with the latest effective date
(version 1 has one deal per client).

**Deal header:** `{id, client: {id, name, relationship}, effective_date, stage, lost_reason, lost_at,
requested_lines, owner, created_at, updated_at}`.

### 7.4 Documents — `documents/`

| Method | Path | Auth | Request | Response |
|---|---|---|---|---|
| GET | `deals/{id}/documents/` | user | — | `[document]` newest first |
| POST | `deals/{id}/documents/` | user | multipart: `file` (required), `kind`, `role`, `carrier`, `lines` (JSON array), `label` | `201 document` · `400 {"file": ["That file type isn't accepted."]}` · `413 {"detail": "Files can be up to 50 MB."}` |
| PATCH | `documents/{id}/` | user | `{label, kind, role, carrier, lines}` | document |
| DELETE | `documents/{id}/` | user | — | `204` |
| GET | `documents/{id}/download/` | user | `?inline=1` to view in the browser | the file (§3.8 headers) |
| GET | `documents/{id}/sheet/` | user | `?sheet=<name>&start=0&rows=200` (Phase 6) | `{sheets: [names], sheet, start, total_rows, rows: [[cell text]]}` |

`document` = `{id, original_name, label, kind, role, carrier, lines, size, page_count, source, review_state,
uploaded_by: {id, name} | null, uploaded_at}`.

### 7.5 Intake — `intake/`

| Method | Path | Auth | Request | Response |
|---|---|---|---|---|
| GET | `deals/{id}/intake/` | user | — | intake payload |
| PATCH | `deals/{id}/intake/` | user | `{"answers": {key: raw value}}` | `200 {answers (changed), sources (changed), hidden, issues, readiness}` · `400 {"answers": {key: "error"}}` — nothing saved if any key fails; unknown key → 400 |
| POST / DELETE | `deals/{id}/intake/sign/` | user | `{name}` | `200 bor` / `204` |
| GET / POST | `deals/{id}/coverage/` | user | `{line, carrier, funding, effective_date, renewal_date, in_force, on_proposal, rate_guarantee_through, notes}` | list / `201 coverage row` |
| PATCH / DELETE | `coverage/{id}/` | user | same | row / `204` |

Intake payload:

```json
{
  "answers": {"legal_name": "Example Co. LLC", "fein": "12-3456789"},
  "sources": {"fein": {"origin": "typed", "by": 3, "at": "2026-11-20T15:04:40Z"}},
  "hidden": ["locations_list", "section_125_handler"],
  "issues": {"employee_count": [{"code": "counts_order", "severity": "error", "message": "…"}],
             "contact:7": [{"code": "email_format", "severity": "error", "message": "…"}]},
  "readiness": {"ready_to_quote": false, "needed": 9, "answered": 7, "pct": 78,
                "missing": [{"key": "sic_code", "label": "NAICS / SIC Code", "section": "employer"}],
                "contacts_ok": true, "lines": 3, "bor_on_file": false},
  "coverage": [{"id": 5, "line": "medical", "carrier": "Aetna", "funding": "fully_insured",
                "effective_date": "2026-01-01", "renewal_date": "2027-01-01", "in_force": true,
                "on_proposal": true, "rate_guarantee_through": null, "notes": ""}],
  "requested_lines": ["medical", "dental", "vision"],
  "bor": {"name": "", "signed_at": null, "signed_by": null},
  "contacts": [{"id": 7, "role": "hr_admin", "name": "Pat Doe", "title": "", "email": "pat@example.com",
                "phone": "", "is_primary": true}],
  "compliance_documents": {"bor": [], "carrier_auth": [], "invoice": [{"id": 41, "name": "Invoice.pdf"}],
                           "renewal": [], "claims": []}
}
```

### 7.6 Census — `census/`

| Method | Path | Auth | Request | Response |
|---|---|---|---|---|
| GET | `deals/{id}/census/` | user | `?page=1&page_size=100&show=all\|issues\|missing&q=` | census page |
| POST | `deals/{id}/census/members/` | user | `{kind, parent_id?, data}` | `201 {member, summary}` |
| PATCH | `census/members/{id}/` | user | `{"data": {key: raw}}` | `200 {member, summary, rollup}` |
| DELETE | `census/members/{id}/` | user | — | `204` (dependents too) |
| POST | `deals/{id}/census/clear/` | user | `{confirm: true}` | `204` — removes every member |
| POST | `deals/{id}/census/imports/` | user | `{document_id}` | `201 import` (proposed mapping) · `400 {"detail": "Could not find a header row in …"}` |
| GET / PATCH | `census/imports/{id}/` | user | `{"mapping": [{"column": 0, "field": "first_name"}]}` | import |
| POST | `census/imports/{id}/apply/` | user | `?dry_run=1` | dry run `{create, update, remove, unchanged}` · real `{stats, summary}` |
| POST | `census/imports/{id}/discard/` | user | — | `204` |
| GET | `deals/{id}/census/template/` | user | — | blank census template (§9.1) |
| GET | `deals/{id}/census/export/` | user | — | full census workbook (§9.2) |

Census page:

```json
{
  "summary": {"employees": 152, "dependents": 38, "errors": 4, "warnings": 9,
              "required_total": 1540, "required_filled": 1531, "missing_required": 9, "readiness_pct": 99},
  "rollup": {"medical": {"EE": 61, "ES": 12, "EC": 9, "FAM": 21, "waived": 8, "blank": 2, "source": "census"}},
  "columns": ["ext_emp_id", "first_name", "…"],
  "page": {"number": 1, "pages": 2, "employees": 152},
  "members": [
    {"id": 901, "kind": "employee", "parent_id": null, "data": {"first_name": "Avery"}, "sources": {},
     "issues": {"ssn": [{"code": "ssn_format", "severity": "error", "message": "…"}]}, "missing": ["dob"]},
    {"id": 902, "kind": "dependent", "parent_id": 901, "data": {}, "sources": {}, "issues": {}, "missing": []}
  ]
}
```

Pages contain employees, each followed by its dependents; unlinked dependents come on the last page. `show=issues`
keeps employees where they or a dependent have an issue; `show=missing` keeps those with missing required cells;
`q` matches first or last name. Validation always runs over the whole census (duplicate SSNs need it); only the page
is returned. Census issues and missing cells are computed on read, never stored.

### 7.7 Quotes (Advisor) — `quotes/`

| Method | Path | Auth | Request | Response |
|---|---|---|---|---|
| GET | `deals/{id}/plans/lines/` | user | — | `[{line, label, current, renewal, alternate, starred, sold_plan}]` |
| GET | `deals/{id}/plans/` | user | `?line=medical` | comparison |
| POST | `deals/{id}/plans/` | user | `{line, role, carrier, name, plan_number?, renews_id?, replaces_id?, values?}` | `201 plan` |
| PATCH | `plans/{id}/` | user | any of `{carrier, name, plan_number, role, renews_id, replaces_id, starred, notes, values: {key: raw}}` | `200 plan` · `400 {"values": {"rate_ee": "Rate — EE takes a number, not \"abc\""}}` |
| DELETE | `plans/{id}/` | user | — | `204` |
| POST | `plans/{id}/renewal/` | user | — | `201 plan` · `400` not current / already has a renewal |
| POST | `plans/{id}/sold/` | user | `{sold: true\|false}` | `200 {plan, deal}` |
| POST | `deals/{id}/plans/star/` | user | `{plan_ids, starred}` | `{updated}` |
| POST | `deals/{id}/plans/counts/` | user | `{"plans": [{"id": 5, "counts": {"EE": 10, "ES": 3, "EC": 2, "FAM": 5}, "on": true}]}` | `{plans}` |
| POST | `deals/{id}/plans/order/` | user | `{line, role, plan_ids}` | `204` |
| GET | `deals/{id}/plans/template/` | user | `?line=` (omit = every requested line) | plan template (§9.3) |
| POST | `deals/{id}/plans/import/` | user | multipart `file`; `?dry_run=1` | `{create, update, errors: [{sheet, cell, message}]}`; nothing written while `errors` is non-empty |

Comparison payload:

```json
{
  "line": "medical", "rate_basis": "composite",
  "groups": [{"key": "deduct", "label": "Deductibles & maximums", "fields": ["deductible_type", "deductible_single"]}],
  "plans": [
    {"id": 5, "role": "current", "carrier": "Aetna", "name": "Open Access HDHP 3300", "plan_number": "",
     "renews_id": null, "replaces_id": null, "starred": true, "sold": false, "sort_order": 0,
     "values": {"deductible_single": "3300"}, "sources": {}, "status": {"rate_es": "missing"},
     "tier_counts": {"EE": 10, "ES": 3, "EC": 2, "FAM": 5}, "counts_on": true,
     "counts": {"EE": 10, "ES": 3, "EC": 2, "FAM": 5}, "counts_source": "typed",
     "premium": {"monthly": 17306, "annual": 207672, "reason": null},
     "base_id": null, "change": null, "tier_rate_change": null,
     "employee_cost": {"EE": 120.0, "ES": null, "EC": null, "FAM": null}}
  ],
  "packages": [
    {"key": "current", "label": "Current", "plan_ids": [5, 6], "monthly": 30210, "annual": 362520, "change": null},
    {"key": "renewal", "label": "Renewal", "plan_ids": [9, 10], "monthly": 32750, "annual": 393000,
     "change": {"delta": 30480, "pct": 8.4}},
    {"key": "alt:cigna", "label": "Cigna", "plan_ids": [12, 13], "monthly": 29870, "annual": 358440,
     "change": {"delta": -4080, "pct": -1.1}}
  ],
  "warnings": [{"code": "per_plan_counts_needed", "message": "Enter enrollment for each current plan"}]
}
```

Plans are ordered current, renewal, alternate, then by `sort_order`. Only the fields of the line's groups (§4.3) are
included.

### 7.8 Commission — `commission/`

| Method | Path | Auth | Request | Response |
|---|---|---|---|---|
| GET | `deals/{id}/commission/` | user | — | commission payload |
| PUT | `deals/{id}/commission/` | user | `{"rates": {"medical": {"type": "pct", "value": "5"}, "dental": null}, "splits": [{"user_id": 3, "name": "Dana Lee", "pct": 60}]}` | commission payload · `400 {"rates": {"medical": "Must be between 0 and 100"}}` · `400 {"splits": ["Splits must add up to 100%"]}` |

Commission payload: `{rates, lines: [{line, label, comp, comp_label, source: "deal"|"agency"|null, basis_plan:
{id, name}|null, annual_premium, expected_annual, reason}], expected_total, splits, splits_total}`.

### 7.9 Proposal — `proposals/`

| Method | Path | Auth | Request | Response |
|---|---|---|---|---|
| GET | `deals/{id}/proposal/` | user | — | `{title, notes, lines: [{line, label, plan_ids, is_default, available: [{id, role, carrier, name, starred}]}], preview: {line: rows}, generated, warnings}` |
| PUT | `deals/{id}/proposal/` | user | `{title, notes, lines: {"medical": [5, 9, 12]}}` | as GET · `400` plan not on the deal / wrong line |
| GET | `deals/{id}/proposal/workbook/` | user | — | client Excel (§9.4); records `generated.workbook`; may advance stage |
| GET | `deals/{id}/proposal/deck/` | user | — | PowerPoint (§9.6) |
| GET | `deals/{id}/proposal/pdf/` | user | — | PDF (§9.7) |
| GET | `deals/{id}/proposal/internal/` | user | — | internal Excel (§9.5); never advances the stage |

`preview` contains, per presented line, the exact rows and cost block the workbook will print (§9.4), as JSON, so the
screen and the file can never disagree.

### 7.10 RFP — `rfp/`

| Method | Path | Auth | Request | Response |
|---|---|---|---|---|
| GET | `deals/{id}/rfp/` | user | — | RFP payload |
| PUT | `deals/{id}/rfp/` | user | `{route, carriers, other_carriers, lines, funding, form, due_date, notes, documents}` | RFP payload · `400` unknown carrier/line/funding/form or a document from another deal |
| GET | `deals/{id}/rfp/files/{key}/` | user | `key` = `census-<format>`, `census-angle-csv`, `qrf`, `cover` | the file |
| GET | `deals/{id}/rfp/packet/` | user | — | zip (§9.10) |
| GET | `deals/{id}/rfp/drafts/{key}/eml/` | user | — | `.eml` (§9.11) |
| POST | `deals/{id}/rfp/drafts/{key}/sent/` | user | `{sent: true\|false}` | `{drafts, deal}` |

RFP payload: `{config (with defaults filled in), band: {band, enrolled}, carriers: [{key, name, group, selected,
eligible, reason, census_format}], files: [{key, label, kind: "census"|"form"|"cover"|"document", ready, warnings}],
drafts: [{key, label, to, cc, subject, body, attachments, sent_at}], commission_request: {text, breakdown}, facts}`.

### 7.11 Review & request — `review/` (staff)

| Method | Path | Auth | Request | Response |
|---|---|---|---|---|
| GET | `deals/{id}/links/` | user | — | `[link]` |
| POST | `deals/{id}/links/` | user | `{recipient_name, recipient_email, message, asks: {intake: "needed" \| [keys], census: "none"\|"missing"\|"upload", documents: [kinds]}, expires_in_days}` | `201 link` · `400` nothing asked, unknown key/kind, days outside 1–30 |
| PATCH | `links/{id}/` | user | `{action: "mark_sent"\|"extend"\|"revoke"\|"restore", days?}` | link |
| GET | `deals/{id}/review/` | user | — | `{values: [{id, link: {id, recipient_name}, target, key, label, member: {id, name} \| null, current, proposed, created_at}], uploads: [document + link]}` |
| POST | `review/values/approve/` | user | `{ids}` | `{approved}` |
| POST | `review/values/reject/` | user | `{ids}` | `{rejected}` |
| POST | `review/uploads/{document_id}/` | user | `{review_state: "accepted"\|"wrong"}` | document |

`link` = `{id, recipient_name, recipient_email, message, asks, url, status, expires_at, sent_at, opened_at,
submitted_at, revoked_at, pending}` where `url` = `FRONTEND_URL/portal/<token>` and `status` is one of `draft` (not
copied yet), `sent`, `opened`, `submitted`, `expired`, `revoked`.

### 7.12 Client portal — `portal/` (public)

All portal endpoints: `AllowAny`, **no authentication classes**, throttle scope `portal`. Unknown token →
`404 {"detail": "This link isn't valid."}`. Expired or revoked → `410 {"detail": "This link has expired. Please contact
your broker for a new one."}`.

| Method | Path | Request | Response |
|---|---|---|---|
| GET | `portal/{token}/` | — | portal payload (allowlist below); records the open |
| GET | `portal/{token}/logo/` | — | agency logo PNG (404 if none) |
| POST | `portal/{token}/save/` | `{"intake": {key: value}, "census": [{"member_id": 12, "key": "dob", "value": "04/05/1980"}]}` | `200 {saved, errors: {intake: {key: msg}, census: {"12:dob": msg}}}` · `400 {"detail": "That question isn't part of this request."}` |
| POST | `portal/{token}/upload/` | multipart `kind`, `file` | `201 {name, kind, uploaded_at}` · `400` kind not asked |
| GET | `portal/{token}/census-template/` | — | the blank census template (§9.1) with SSNs masked; only when census is asked |
| POST | `portal/{token}/submit/` | — | `200 {submitted_at}` |

**Portal payload — the complete allowlist** (nothing else may be added without updating this spec):

```json
{
  "agency": {"name": "…", "phone": "…", "email": "…", "brand_color": "#173a63", "has_logo": true},
  "client_name": "Example Co.", "effective_date": "2027-01-01",
  "recipient_name": "Pat Doe", "message": "…", "expires_at": "…", "submitted_at": null,
  "intake": [{"key": "fein", "label": "FEIN", "type": "text", "options": [], "help": "…", "value": "12-3456789"}],
  "census": {"mode": "missing",
             "people": [{"member_id": 12, "kind": "employee", "name": "Avery Smith",
                         "fields": [{"key": "ssn", "label": "SSN", "type": "ssn", "options": [], "value": "***-**-6789"}]}]},
  "documents": [{"kind": "invoice", "label": "Current invoice", "uploaded": [{"name": "inv.pdf", "uploaded_at": "…"}]}]
}
```

- `intake` lists only asked questions; `value` is the client's pending answer if any, else the deal's answer.
- `census.people` lists only people with a blank asked cell, and `fields` only those blank required cells (plus the
  person's name for recognition). SSNs are always masked. In `upload` mode, `census` is `{"mode": "upload",
  "uploaded": [...]}`.
- No document ids, internal notes, plan data, commission, owner names or other deals' data ever appear.

### 7.13 Overview — `overview/`

| Method | Path | Auth | Response |
|---|---|---|---|
| GET | `deals/{id}/overview/` | user | `{deal, next_action: {key, label, tab}, review_pending, summaries: {intake, census, quotes, commission, proposals, rfp, review, documents}, notes: [latest 20, pinned first], activity: [latest 15]}` |

---

## 8. Screens

Sketches show structure, not styling. All names in sketches are fictional.

### 8.1 Layout and routes

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Vantage    Clients                                        Admin ▾   Dana ▾  │
└─────────────────────────────────────────────────────────────────────────────┘
```

Top bar: app name and **Clients** both open the dashboard; **Admin** (admins only) → Users, Agency settings; the user
menu → Change password, Sign out.

| Route | Page | Top bar |
|---|---|---|
| `/login` | Sign in | no |
| `/reset-password` | Request a reset link | no |
| `/reset-password/:uid/:token` | Choose a new password | no |
| `/` | Dashboard | yes |
| `/deals/:dealId` | → `/deals/:dealId/overview` | yes |
| `/deals/:dealId/:tab` | Deal page (`overview`, `intake`, `review`, `census`, `rfp`, `commission`, `advisor`, `proposal`, `documents`; anything else → overview) | yes |
| `/admin/users`, `/admin/agency` | Admin pages (non-admins → dashboard) | yes |
| `/portal/:token` | Client portal | no |
| anything else | "Page not found" with a link to the dashboard | yes |

Signed-out visitors to any page except the four without a top bar go to `/login`, then back to where they were going.

### 8.2 Sign-in and account pages

- **Sign in:** username, password, **Sign in**; the server's message on failure; "Forgot your password?" link.
- **Request reset:** email field; after submit always shows "If that email belongs to an account, a reset link is on
  its way."
- **Choose new password:** new password + confirm (must match); on success → sign-in page with "Password updated".
- **Change password** (dialog from the user menu): current, new, confirm. On success the new token replaces the old
  one silently and a toast says "Password changed".

### 8.3 Dashboard

```
Clients                                                         [+ New client]
[ Search clients…                       ]   ( All | New | Existing )
┌────────────────────────┬──────────┬───────────┬────────────┬──────────┬──────────────┐
│ Client ▲▼              │ Type     │ Stage     │ Effective  │ Owner    │ Last updated ▼│
├────────────────────────┼──────────┼───────────┼────────────┼──────────┼──────────────┤
│ Example Co.            │ New      │ Quoting   │ 01/01/2027 │ Dana Lee │ Today 3:04 PM │
│ Sample Manufacturing   │ New      │ Intake    │ 02/01/2027 │ Sam Ruiz │ Yesterday     │
└────────────────────────┴──────────┴───────────┴────────────┴──────────┴──────────────┘
                                         ‹ Prev   Page 1 of 3   Next ›
```

- Search runs on the server, 250 ms after typing stops; filter chips and sorting (Client, Last updated) are query
  parameters; 25 rows per page; the URL keeps the search and filters so Back works.
- Clicking a row opens `/deals/<deal id>/overview`. Lost deals show the stage "Lost" in grey.
- Empty: "No clients yet." with **New client**. No matches: "No clients match "<text>"."
- **New client** dialog: Client name (required), Type (New / Existing, default New), Target effective date
  (optional), Owner (users, default me). While the name is typed, up to 5 existing clients containing it are listed
  ("Already here? Example Co. — open") to prevent duplicates. **Create** → opens the new deal's Intake tab.

### 8.4 Deal page

```
Example Co.  ·  Effective 01/01/2027  ·  Owner: Dana Lee ▾                   [Stage ▾] [Mark lost]
Intake ── Quoting ── Proposal ── Sold
┌──────────────────┬──────────────────────────────────────────────────────────────────────┐
│ Overview         │                                                                      │
│ Intake           │                         (selected tab)                               │
│ Review & request │                                                                      │
│ Census           │                                                                      │
│ RFP              │                                                                      │
│ Commission       │                                                                      │
│ Advisor          │                                                                      │
│ Proposal         │                                                                      │
│ Documents        │                                                                      │
└──────────────────┴──────────────────────────────────────────────────────────────────────┘
```

- Header: client name (links to an edit dialog for the client's name and type), effective date (inline date edit),
  owner (select), the stage stepper with the current stage highlighted, **Stage ▾** (set intake / quoting / proposal),
  **Mark lost** (dialog asking for the reason).
- A lost deal shows a red banner "Lost — <reason>" with **Reopen**; tabs stay readable, editing controls are disabled.
- Only the open tab's code and data load. Switching tabs never reloads the header.

### 8.5 Overview tab

- **Next action** card: the label from §5.9 and a button that opens its tab; beside it, "<n> client answers to review"
  when any are pending.
- **Readiness** cards, one per area, each with one to three figures and a link: Intake (ready to quote ✓/✗,
  answered x / y), Census (people, errors, missing), RFP (carriers picked, drafts sent), Advisor (plans per role on
  the main line, starred), Proposal (last generated), Commission (expected annual), Review & request (open links,
  pending), Documents (files).
- **Notes:** a text box with kind (Note / Call / Email / Meeting) and **Add**; the list shows pinned notes first, then
  newest; each can be pinned, edited or deleted by its author or an admin.
- **Recent activity:** the latest 15 entries (who, what, when) and **Show all** (paginated).

### 8.6 Intake tab

Two columns: the form on the left, a sticky readiness panel on the right.

- **Readiness panel:** "Ready to quote" with a tick or what is missing; answered x of y needed; the missing questions
  (each scrolls to its question); contacts OK; lines requested; BOR on file.
- **Question sections** (one card each, §4.5), rendered from `/api/meta/` by `FieldForm`. A needed question shows a
  "Needed to quote" marker. Hints are placeholders; help text is an ⓘ tooltip. Issues show under the question (error
  red, warning amber, both with an icon).
- **Saving:** text and number inputs save when they lose focus; choices, yes/no and dates save on change. Each save
  sends one key. While saving, a small spinner; then a tick for 2 seconds. On error the typed text stays and the
  message shows under the field. Hidden conditional questions disappear after the save that hides them.
- **Contacts** (client-level): a table with inline add / edit / delete; role select; a "Primary" radio.
- **Current coverage:** a table with line, carrier, funding, effective date, renewal date, in force (checkbox),
  on proposal (checkbox), rate guarantee through, notes; add and delete rows. Row issues show inline.
- **Lines to quote:** a checkbox grid of the 27 lines in §4.1 order; saves on change (`PATCH deals/{id}/`).
- **Authorizations & documents:** BOR typed signature (name + **Sign**; afterwards "Signed by <name> on <date>"
  with **Clear**); upload slots for BOR, carrier authorization, invoice, renewal and claims experience, each listing its
  files (upload creates a document of that kind).

### 8.7 Review & request tab

- **Requests** table: recipient, what is asked (chips: "9 questions", "Census: missing (12 people)", "Invoice"),
  status badge, expires, pending answers, and actions: **Copy link** (marks it sent), **Open as client** (new tab),
  **Extend**, **Revoke** / **Restore**.
- **New request** dialog: recipient name and email; message; **Questions**: "All needed questions still blank (n)" or
  "Choose…" (a searchable checklist grouped by section); **Census**: None / "Fill in missing information (n people)" /
  "Upload a census file"; **Documents**: checkboxes for invoice, renewal, claims experience, BOR, carrier
  authorization, plan document, other; **Expires in** (days, default 14). **Create** shows the link with **Copy**.
- **To review**, grouped by request: each pending answer shows the question (or person + column), current value,
  proposed value, **Approve** / **Reject**; **Approve all** per request. Client uploads show name and kind with
  **View**, **Accept**, **Wrong file**.
- Empty: "No requests yet. Ask the client for anything still missing."

### 8.8 Census tab

```
Employees 152 · Dependents 38 · Errors 4 · Warnings 9 · Missing 9 · Ready 99%
[Upload census] [Blank template] [Export] [+ Employee]                        [Clear census]
Medical: EE 61 · ES 12 · EC 9 · FAM 21 · Waived 8 · Blank 2   Dental: …
( All | With issues | Missing required )   [ Search name… ]
┌───────────┬───────────┬──────────┬────────────┬─────────┬─────┬─────────────┬──────────┐
│ Last name │ First name│ Relation │ DOB        │ SSN     │ ZIP │ Medical Tier│ …        │
├───────────┼───────────┼──────────┼────────────┼─────────┼─────┼─────────────┼──────────┤
│ SMITH     │ Avery     │ Employee │ 04/05/1980 │ ███████ │ …   │ FAM         │          │
│  ↳ Smith  │ Jordan    │ Spouse   │ …          │         │     │             │          │
└───────────┴───────────┴──────────┴────────────┴─────────┴─────┴─────────────┴──────────┘
```

- Summary chips and rollup (§5.3.5, §5.3.6) refresh after each save.
- The grid is the shared `DataGrid` (§8.16). Columns: the deal's in-scope columns (§4.4), last and first name frozen.
  Employees in bold; each followed by its dependents, indented. A missing required cell has a red outline; an error a
  red tint; a warning an amber tint; hovering lists the messages. Coded columns edit with a dropdown (§4.4 choices).
- Row menu: **Add dependent** (employees), **Delete** (with confirmation; deleting an employee deletes dependents).
- 100 employees per page with pager.
- **Upload census:** choose a file → it is stored as a census document → the mapping dialog opens: one row per source
  column with its header, three sample values, the proposed census column (a grouped dropdown, plus "Ignore") and a
  confidence badge (*exact* / *likely* / *check* for low). **Apply** runs the dry run and shows "140 to add, 0 to
  update, 0 to remove"; confirming applies it. Parse errors show in the dialog.

### 8.9 RFP tab

1. **Request:** route (Through Warner Pacific / Direct to carriers); lines (checkboxes, default the requested lines);
   funding (checkboxes); form (Simplified / Small group 2–50 / Large group 51+; Warner route only); due date; notes;
   a size-band chip ("Small group · 32 enrolled"); the commission request text with a link to the Commission tab.
2. **Carriers:** a table of the 25 carriers grouped Medical / Ancillary: select, name, census format, an eligibility
   chip (✓, or the reason in amber), the carrier note; plus an "Other carriers" text field.
3. **Files:** the packet's files: census files (Warner universal plus each selected carrier's own format), the quote
   request form (Warner route) or cover page (direct route), and the deal's documents with include checkboxes. Each
   row has **Download** and an expandable warnings list. **Download RFP packet (.zip)**.
4. **Email drafts:** one card per draft: To, CC, Subject and Body with **Copy** buttons, the attachment list,
   **Download .eml**, and a **Mark sent** toggle showing when it was marked.

Every change saves immediately (`PUT deals/{id}/rfp/`) and the files and drafts refresh.

### 8.10 Commission tab

- A row per requested line: line · rate (type select %, Flat, PEPM + value; the placeholder shows the agency default)
  · source (This deal / Agency default) · basis plan (sold or first starred) · annual premium · expected annual
  revenue. A total row.
- **Producer split:** rows of person (user select, or free-text name) and percentage; **Add person**; a live total that
  must reach 100% before **Save** is enabled.
- **Save** sends both parts; field errors show inline.

### 8.11 Advisor tab

```
[Medical (3·3·4)] [Dental (1·0·2)] [Vision]         [+ Plan] [Enrollment] [Template ▾] [Hide empty rows]
┌──────────────────────┬──────────────────┬──────────────────┬──────────────────┐
│                      │ CURRENT ★        │ RENEWAL of HDHP  │ ALTERNATE → HDHP │
│                      │ Aetna            │ Aetna            │ Cigna            │
│                      │ OA HDHP 3300  ⋯  │ OA HDHP 3300  ⋯  │ LocalPlus 3000 ⋯ │
├──────────────────────┼──────────────────┼──────────────────┼──────────────────┤
│ ▾ Deductibles & max. │                  │                  │                  │
│   Deductible (Single)*│ $3,300          │ $3,300           │ $3,000           │
│ …                    │                  │                  │                  │
│ ▾ Monthly rates      │                  │                  │                  │
│   Rate — EE *        │ $512.34          │ $556.20          │ $498.10          │
├──────────────────────┼──────────────────┼──────────────────┼──────────────────┤
│ Enrollment used      │ 10·3·2·5 (typed) │ 10·3·2·5 (from current) │ …         │
│ Monthly premium      │ $17,306          │ $18,790          │ $16,955          │
│ Annual premium       │ $207,672         │ $225,480         │ $203,460         │
│ Change vs current    │                  │ +$17,808 (+8.6%) │ −$4,212 (−2.0%)  │
└──────────────────────┴──────────────────┴──────────────────┴──────────────────┘
Packages:  Current $362,520/yr · Renewal $393,000 (+8.4% average) · Cigna $358,440 (−1.1%)
```

- **Line picker:** requested lines and lines that have plans, each with counts (current · renewal · alternate).
- **Columns** (one per plan, sticky header): role badge (Current / Renewal of <plan> / Alternate → <plan>), carrier and
  plan name (editable in place), star toggle, sold toggle (one per line), and a menu: Create renewal (current plans),
  Change role & links, Notes, Move left / right, Delete.
- **Rows:** the line's groups (§4.3) as collapsible sections; the first column (labels, `*` for required) is sticky.
  Cells edit in place by type. A required blank cell has a red outline. A cell's source shows as a small icon (typed /
  imported / client / AI); hovering shows who, when, and the document page or sheet cell; clicking opens the Documents
  tab at that place (Phase 6). AI values not yet confirmed are amber (Phase 9).
- **Cost rows** (read-only, from the server): enrollment used with its source, monthly premium, annual premium, change
  vs base ($ and %); renewals also show each tier's rate change. A plan with no price shows the reason in words.
- **Packages** line below the grid (§5.5).
- **Enrollment** card (toolbar): a multi-select list of the line's plans; one row per selected plan with EE, ES, EC,
  FAM inputs and an On/Off switch; "Copy first row to all"; the census rollup for reference; **Save**.
- **+ Plan** dialog: role; for renewals the current plan it renews; for alternates the current plan it replaces
  (optional); carrier; plan name; plan number.
- **Template ▾:** Download plan template; Import plan template (file → dry run → shows "3 plans created, 4 updated" or
  the list of cell errors → **Import**).
- **Hide empty rows** hides rows where every plan is blank.
- Empty line: "No plans on this line yet. Add a plan, or import the plan template."

### 8.12 Proposal tab

- Title and notes.
- For each requested line that has plans: **Plans to present** — a checklist of the line's plans, preselected with the
  **default**: every current plan, its renewal, and the starred alternates (all alternates if none is starred).
  Alternates can be reordered by dragging; current/renewal pairs follow the Advisor order.
- **Preview:** an HTML table built from `preview` — exactly the rows and figures the workbook will contain.
- **Download:** Client Excel (primary button), PowerPoint, PDF; **Internal Excel** (secondary). "Last generated <time>"
  under each.
- Warnings above the preview (e.g. "Medical: 2 plans have no price — enter enrollment in the Advisor").

### 8.13 Documents tab

- **Version 1:** a table of files: name (label), kind, role, carrier, lines, from (staff / client + review state),
  uploaded by and when, size, pages. Actions: **View** (opens inline in a new tab), **Download**, **Edit** (label, kind,
  role, carrier, lines), **Delete** (confirm). **Upload** accepts several files; a dialog sets kind, role ("What is this
  document?" — current plans / renewal / alternates, for quotes, renewals and SBCs), carrier and lines per file. Filter
  by kind.
- **Version 2 (Phase 6):** list on the left, viewer on the right — PDF (page navigation, zoom, find text, highlight),
  spreadsheets (sheet tabs, grid), images. Under the viewer, **Values from this document**: every intake answer,
  census cell and plan value whose source is this document, with field, plan or person, value, page or cell and status.
  Clicking one jumps to and highlights it. **Confirm** one or many (sets `confirmed_by/at`); editing a value in place
  makes it typed.

### 8.14 Admin pages

- **Users:** a table (name, username, email, admin, active, last sign-in) with **Add user** (username, email, names,
  initial password, admin) and **Edit** (names, email, admin, active, set a new password). An admin cannot deactivate
  or demote themselves.
- **Agency settings:** the fields of §6.2 with a logo upload and preview.

### 8.15 Client portal (`/portal/:token`)

```
[logo] Vantage Risk Solutions
Hi Pat — Example Co. needs a few things from you for its 01/01/2027 benefits.
"<message from the broker>"                                  This link works until Nov 30.

Questions ─────────────────────────────────────────────────
  FEIN  [12-3456789]   ⓘ Your 9-digit federal Tax ID…        saved ✓
People ────────────────────────────────────────────────────
  Avery Smith (employee) — Date of birth [  ]  ZIP [  ]
Documents ─────────────────────────────────────────────────
  Current invoice   [Upload]   inv.pdf ✓
                                                             [Submit]
```

- No app chrome; the agency's name, logo and colour. Single column, works on phones.
- Questions use the same field rendering as staff intake, with help text always visible. Each answer saves when the
  field loses focus (`save`); errors show under the field.
- People cards list only the asked blank cells per person. SSNs appear masked; typing a full SSN replaces it.
- Upload slots per asked document kind (and one census upload in upload mode).
- **Submit** works any time; afterwards: "Thanks — your broker has the latest. You can still make changes until <date>."
- Expired or revoked: a friendly page with the agency's phone and email.

### 8.16 The DataGrid component

Shared by Census and Advisor. Generic: it knows nothing about census or plans.

- **Inputs:** columns (key, label, width, frozen, editor type, choices), rows, a `getCell(row, column)` function
  returning value, display text and decoration (status, tooltip), and `onCommit(rowId, key, value) → Promise`.
- **Keyboard:** arrow keys move the selection; Enter or F2 edits; typing a character starts editing with it; Enter
  commits and moves down; Tab commits and moves right (Shift+Tab left); Escape cancels; Delete or Backspace on a
  selected cell commits an empty value; Ctrl/Cmd+C copies the selected cell.
- **Saving:** commits go through a per-cell write queue — one request in flight per cell, the latest value wins, results
  apply in order. A failed commit shows the server's message on the cell and restores the last saved value.
- **Layout:** sticky header rows and frozen leading columns; horizontal and vertical scrolling; row virtualization when
  more than 200 rows are rendered.

### 8.17 Loading, empty and error states

- First load of a tab: a skeleton of its layout. Refetches keep the old data on screen with a small "updating" marker.
- Every list has an empty state that offers the next action.
- A failed request shows an inline error with **Try again**. Save errors appear where the value was typed. A `409` on a
  lost deal shows the lost banner. A `401` returns to sign-in.
- Successful saves are quiet (a tick); actions that create, delete or generate show a toast.

---

## 9. Generated files

File names: `<Client> - <Document>.<ext>` (e.g. `Example Co - Proposal.xlsx`), characters outside
`[A-Za-z0-9 ._-]` removed. Every text value written into a spreadsheet goes through the injection guard (§3.8).

### 9.1 Blank census template (`census/templates.py`)
- Sheet **Census**: row 1 holds the labels of the deal's in-scope columns (§4.4) in order. Required columns (any
  required code) end with ` *`. Header style: bold white on navy `#173a63`, wrapped, row height 28; column widths
  12–28 by label length; freeze panes at `A2`.
- If the deal already has people, rows 2+ are prefilled: each employee followed by its dependents. SSNs are masked
  (`***-**-1234`) only in the copy downloaded from the client portal.
- Sheet **Instructions**: one row per column — Column, Required (Always / Employees / When <line> is quoted / When
  medical is in force / Optional), Accepted values (§4.2, §4.4), Notes.
- Because every label is an exact header synonym (§4.8), a filled template re-imports at full confidence.

### 9.2 Census export (`census/templates.py`)
Staff-only workbook: sheet **Census** with a first column **Type** (Employee / Dependent), then all 45 columns, then
**Issues** (the person's messages joined with "; "). Unmasked. Same header styling as §9.1.

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
| 9 | Renews / replaces plan ID | `link` | id of a current plan on this line, or blank |
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
- Values are cleaned by §5.4; a refused value becomes `<Sheet>!<cell>: <message>`.
- A **blank cell leaves the existing value unchanged** (clear values in the app).
- The `link` cell must name a current plan on the line and obey §5.4's role rules.
- The uploaded file is stored as a document (kind `other`, label "Plan template import"); values get sources
  `{origin: import, doc, cell}`.

### 9.4 Client proposal workbook (`proposals/workbook.py`) — the baseline output

**▲ To confirm** with the benefits team: column order (each current plan beside its renewal, as below) and the row
list. Built to be easy to change: the row list and column order are each one constant.

- One worksheet per presented line, named by its label, in requested-line order. No hidden sheets.
- **Page setup:** landscape, US Letter, fit to 1 page wide × 1 tall, margins 0.4", centred horizontally, gridlines
  off, header rows repeated when printing.
- **Header rows 1–3:** the agency logo at A1 (if set); B1 `<title or "<Client> — <Line> Plan Comparison">` bold 16pt
  navy; B2 `Effective <MM/DD/YYYY>`; B3 `Prepared by <agency> · <date>`.
- **Columns:** A = row labels (width 30); then one column per presented plan (width 18): for each current plan in
  Advisor order, the current plan then its renewal (if presented); then the alternates grouped by carrier (carriers in
  order of first appearance). Header band colours: current grey `#E7E9EE`, renewal blue `#DCE8F7`, alternates green
  `#E3F1E6`.
- **Plan header rows:** *Option* — `C1, C2…` current, `R1…` renewal, `P1…` alternates; *Carrier*; *Plan*.
- **Medical design rows** (omit a row when every presented plan is blank there):

| Row label | Value |
|---|---|
| Plan type · Network · Metal tier · Deductible type | `plan_type`, `network`, `metal_level`, `deductible_type` |
| Deductible (individual / family) | `deductible_single` / `deductible_family` |
| Deductible out of network | `deductible_single_oon` / `deductible_family_oon` |
| Coinsurance (in / out) | `coinsurance` / `coinsurance_oon` |
| Out-of-pocket max (individual / family) | `oop_max_single` / `oop_max_family` |
| Out-of-pocket max out of network | `oop_max_single_oon` / `oop_max_family_oon` |
| Primary care · Specialist · Telehealth | `pcp_copay`, `specialist_copay`, `telehealth` |
| Lab & X-ray · Advanced imaging | `diagnostic_test`, `advanced_imaging` |
| Urgent care · Emergency room | `urgent_care_copay`, `er_copay` |
| Inpatient · Outpatient surgery | `inpatient`, `outpatient_surgery` |
| Rx deductible · Rx tiers 1 / 2 / 3 · Specialty · Mail order | `rx_deductible`, `rx_t1`/`rx_t2`/`rx_t3`, `rx_t4`, `rx_mail_order` |
| Summary of Benefits | `sbc_url` as a "View SBC" hyperlink |

  Paired values print as `$3,300 / $6,600`; numeric amounts as `$#,##0`; percentages as `20%`; text as the carrier
  wrote it. `mental_health_outpatient` is not printed. Other lines print their field set's fields (§4.3) in order,
  excluding rates and contributions.
- **Cost block — composite lines** (after one blank row):
  - *Monthly rates*: EE, ES, EC, FAM (`$#,##0.00`).
  - *Enrollment*: EE, ES, EC, FAM — **input cells** (unlocked, pale yellow), prefilled with the counts the app used
    (§5.5).
  - *Total monthly premium*: `=IF(SUM(<counts>)=0,"",ROUND(SUMPRODUCT(<rates>,<counts>),0))`. If the app priced the
    plan from the carrier's quoted premium, write that number instead, marked `†`.
  - *Total annual premium*: `=IF(<monthly>="","",<monthly>*12)`.
  - *Change vs current ($)*: `=IF(OR(<annual>="",<base annual>=""),"",<annual>-<base annual>)`; blank for current
    plans; base per §5.5.
  - *Change vs current (%)*: `=IF(OR(<annual>="",<base>="",<base>=0),"",ROUND((<annual>-<base>)/<base>,3))` as `0.0%`.
  - When a renewal is presented: *Rate change EE / ES / EC / FAM (%)* rows for renewal columns, same formula shape
    against the current plan's rate.
- **Cost block — other bases:** unit rate; the volume or employee figure the formula uses (input cell); total monthly
  by basis: `=ROUND(V/1000*U,0)`, `=ROUND(V/10*U,0)`, `=ROUND(V/12/100*U,0)`, `=ROUND(U*N,0)`, stop-loss
  `=ROUND((S+A+O)*N,0)` with the three PEPM parts as rows; total annual as above.
- **Packages** (below the cost block): one row per package (§5.5): Package · Plans (option codes) · Monthly · Annual ·
  Change $ · Change %. Monthly = `=IF(COUNTBLANK(<plan monthly cells>)>0,"",SUM(<plan monthly cells>))`. The renewal
  row is labelled "Renewal — average increase".
- **Footnotes:** `† Carrier-stated group premium.` and the agency disclaimer ("Rates and benefits are summaries; the
  carrier's documents govern." — **▲ To confirm** wording).
- **Protection:** each sheet protected without a password; only enrollment and volume input cells are unlocked.
- Formulas may use only `IF`, `OR`, `SUM`, `SUMPRODUCT`, `ROUND`, `COUNTBLANK`.
- **Correctness requirement:** for every plan, evaluating the written formulas on the written cell values gives exactly
  the app's monthly and annual premium (§12 tests this).

### 9.5 Internal comparison workbook (`proposals/internal.py`)
One sheet per line that has plans. Rows 1–3: title, effective date, "INTERNAL — not for clients". Header rows: role,
carrier, plan, plan number, starred, sold. Then every field of the line (§4.3) for every plan, values as stored, then
the cost rows as **values** (enrollment used and its source, monthly, annual, change $ and %). No formulas. Freeze panes
below the header and right of column A.

### 9.6 PowerPoint (`proposals/deck.py`)
- 16:9, built with python-pptx; values only (no formulas).
- Slide 1: client, "Benefits Proposal", effective date, agency name and logo.
- Per presented line: comparison slides of at most 5 plan columns each, keeping each current plan with its renewal;
  further plans continue on the next slide titled "(continued)". **Current plans are always included.** Each slide is a
  table of the workbook's rows (design rows with values, rates, enrollment, monthly, annual, change), 9–10 pt.
- Per line: a package-totals slide. Final slide: disclaimer and the owner's contact details.

### 9.7 PDF (`proposals/pdf.py`)
reportlab, landscape US Letter, the same page plan and content as §9.6; header with the logo and title, footer with page
numbers and the disclaimer.

### 9.8 Carrier census files (`rfp/census_fill.py`)

**Template definition** (one per format, data in `rfp/templates/definitions.py`, files in `assets/carrier_templates/`):

```python
{
  "key": "warner_census", "name": "Warner Pacific census", "carrier": "Warner Pacific",
  "template_file": "warner_census.xlsx", "sheet_name": "Census Template",
  "header_row": 3, "data_row": 7, "origin_col": "B", "clear_ranges": ["A5:X6"], "max_rows": 587,
  "row_scope": "member",            # member = employees and dependents; employee = employees only
  "file_format": "xlsx",            # xlsx, or csv (also delivered as the filled workbook)
  "columns": [ {column}, ... ]      # consecutive columns starting at origin_col
}
# column keys (all optional except header):
#   header, hint, canonical_field, source, transform, value_map, required, employee_only, line, dependent_inherits
```

**Filling rules:**
1. Before writing, check that each column's `header` matches the text in `header_row` at that column (a column whose
   header is empty is not checked). A mismatch refuses the file: `The <name> template has changed (expected "<header>"
   in <cell>)`.
2. Rows: member scope → each employee followed by its dependents in roster order; employee scope → employees only.
   Start at `data_row`; stop at `max_rows` (0 = no limit) with the warning `<n> people didn't fit (the template holds
   <max>)`.
3. Each cell's value, in order:
   - `canonical_field` → the member's value; if blank and `dependent_inherits`, the employee's value.
   - `source`: `row:member_type` → relationship token; `row:enroll:<field>` → `ENROLL` when that amount is present;
     `case:<intake key>` → the intake answer; `derive:age` → §5.3.7; `derive:county` → the typed county, else the ZIP
     crosswalk (asset); `derive:out_of_area` → `IN_AREA` for a contiguous-US ZIP (§5.3.7), else blank with a warning
     naming how many people.
   - `employee_only` → blank on dependent rows. `line` → blank unless that line is in the RFP's lines.
   - `transform`: `tier` → token `EE/ES/EC/FAM/WAIVE` (§4.2); `gender` → `M/F`; `status` → `COBRA` if the text contains
     COBRA, `RETIREE` if it contains RETIRE, `STCON` if it contains "ST CON" or "CONTINU", else `ACTIVE`; `date` → a
     real date cell; `date_mdy` → text `MM/DD/YYYY`; `zip5` → 5 digits (4 digits get a leading zero, ZIP+4 is cut);
     `ssn_digits`, `ssn_dashed`, `upper`, `initial`.
   - **Relationship token:** employee rows → `employee`; dependents: text containing domestic, dp or civil union →
     `domestic_partner`; child, son, daughter, dependent, stepchild or ch → `child`; spouse, wife, husband, partner or
     sp → `spouse`; anything else → `child` with a warning.
   - `value_map` turns a token into the carrier's spelling; a token missing from the map writes blank.
4. A `required` column left blank produces a warning with the count. Columns with neither `canonical_field` nor
   `source` are listed as "not provided".
5. **Write by patching the workbook's XML** inside the `.xlsx` zip — never by loading and re-saving with openpyxl,
   which drops the carrier's images, checkboxes and data validations. Numbers: `<c r="D7" s="…"><v>…</v></c>`; text:
   inline strings `<c r="D7" s="…" t="inlineStr"><is><t>…</t></is></c>`; dates: the serial day number since
   1899-12-30, keeping the cell's existing style. Clear `clear_ranges` values first (keep styles). Every other part of
   the package stays byte-identical.
6. CSV formats also produce `<Client> - Census - <Carrier>.csv` from the filled rows (header row + data, UTF-8).

**Warner Pacific universal census** — the worked example (sheet "Census Template", header row 3, data from row 7,
columns from B, clear A5:X6, at most 587 rows, member scope):

| Col | Header | Maps to | Transform → Warner spelling | Rules |
|---|---|---|---|---|
| B | RELATIONSHIP | `row:member_type` | employee→Employee · spouse→Spouse/Partner · child→Child/Dependent · domestic_partner→Spouse/Partner | required |
| C | MEMBER NAME (First) | `first_name` | | required |
| D | (Last) | `last_name` | | required |
| E | DATE OF BIRTH | `dob` | date | required |
| F | GENDER | `gender` | gender → M / F | required |
| G | ZIP CODE | `zip` | zip5 | required; dependents inherit |
| H | COUNTY | `derive:county` | | |
| I | HOURS (per week) | `hours_per_week` | | |
| J | EE STATUS | `employment_status` | status: ACTIVE→Active · COBRA→COBRA | employees only |
| K | COVERAGE TYPE | `medical_tier` | tier: EE→EE · ES→ES · EC→EC · FAM→EF · WAIVE→Waive | employees only; medical; required |
| L | WAIVE REASON | `waiver_reason` | | |
| M | CURRENT PLAN ELECTION | `medical_plan` | | employees only; medical |
| N | COVERAGE TYPE | `dental_tier` | tier as K | employees only; dental |
| O | CURRENT PLAN ELECTION | `dental_plan` | | employees only; dental |
| P | COVERAGE TYPE | `vision_tier` | tier as K | employees only; vision |
| Q | CURRENT PLAN ELECTION | `vision_plan` | | employees only; vision |
| R | COVERAGE TYPE | `row:enroll:basic_life_amount` | ENROLL→Enroll | employees only; basic_life_add |
| S | CLASSES | `emp_class` | | employees only |
| T | ELECTIONS | `vol_life_amount` | | employees only; voluntary_life |
| U | SALARY | `annual_salary` | | employees only |
| V | PAY MODE | `case:payroll_frequency` | | employees only |
| W | JOB TITLE | `job_title` | | employees only |
| X | CLASSES | `emp_class` | | employees only |

**The other three formats** (full column definitions in the asset pack, Appendix A):

| Key | Carrier | Sheet | Header row | Data row | First column | Scope | Format | Notable mappings |
|---|---|---|---|---|---|---|---|---|
| `aetna_gateway` | Aetna | Census Input | 6 | 7 | A | member | xlsx | tier EEOnly/EESpOnly/EEChren/EEFamily/Waive; relationship EE/SP/CH (DP→SP); status Active/COBRA/St Con/Retiree |
| `angle` | Angle Health | Sheet1 | 9 | 10 | B | member | csv (+ workbook) | tier Employee/Employee+Spouse/Employee+Child(ren)/Employee+Family; relationship Employee/Spouse/Child (DP→Spouse) |
| `uhc` | UnitedHealthcare | Employee Info | 3 | 4 | A | member | xlsx | tier Employee Only/Employee & Spouse/Employee & Child/Employee & Family/Waive; relationship split into type (Employee/Dependent) and kind (Spouse/Child/Domestic Partner); status Active/Cobra; derived age, email, out-of-area (No for in-area), waiver reason; "Waive all products?" derived (below); a group-information tab filled from the group facts |

UHC "Waive all products?": `WAIVE_ALL` when every RFP line the person could elect (medical, dental, vision tier columns)
says waived; `ENROLLED` when any of them holds a tier; blank otherwise (a blank tier is not a waiver).

### 9.9 Warner quote request form and cover page (`rfp/forms.py`)
- **Quote request form:** Warner's own workbook in three versions (Simplified — the default for every size; Small group
  2–50; Large group 51+), filled by XML patching exactly as §9.8. The asset pack supplies each version's cell map: every
  input cell is paired with the label cell beside it, and each label is checked before writing (mismatch → refuse,
  naming the cell). Filled: the group header facts (§5.7), the broker block (agent, agency, email, address, commission
  request), and — on the 2–50 and 51+ versions — the funding boxes, the carrier × column matrix (a mark for each selected
  carrier's columns that cover a requested line) and the notes cell (wrap on). Dates are written as dates, counts as
  numbers. The census travels as a separate file, not inside the form.
- **Cover page** (direct route): one-page PDF, Letter portrait — agency logo and name; "Request for Proposal";
  a facts table (group legal name, address, SIC, effective date, eligible, enrolled, total employees, current carrier
  and funding, requested lines, funding requested, commission request, due date); the owner's name, email and phone;
  the RFP notes. It never names a carrier.

### 9.10 RFP packet (`rfp/packet.py`)
- `<Client> - RFP packet - <YYYY-MM-DD>.zip` containing:
  - `README.txt` — client, effective date, route, lines, funding, due date, commission request, the request summary,
    the file list, every file's warnings, and the "not provided" columns of each census format;
  - the census files: the Warner universal census (whenever the census has people) and each selected carrier's own
    format (Angle in both xlsx and csv);
  - `Quote Request Form - Warner Pacific.xlsx` (Warner route) or `Cover Page.pdf` (direct route);
  - the included deal documents under `Documents/`, original names, duplicates suffixed ` (2)`.
- A file that cannot be built is listed in the README under "Could not include" with the reason. If nothing at all can be
  built → `400 {"detail": "Nothing in the packet could be built."}`.
- **Request summary** (one item per line): Lines; Funding; Carriers (names); Other carriers; Commission; Due date;
  Notes.

### 9.11 Email drafts (`rfp/drafts.py`)
- **Warner route:** one draft — To `FLQuoting@WarnerPacific.com`; Subject
  `Quote request: <group> | eff. <MM/DD/YYYY> | <short lines>`; attachments: the whole packet's files; extra text: the
  request summary.
- **Direct route:** one draft per selected carrier, plus one "Other carriers" draft when that field is filled — To blank
  (the rep fills it in); Subject `RFP: <group> | eff. <MM/DD/YYYY> | <short lines>`; attachments: the cover page, the
  included documents, the universal census and **that carrier's own census format only**; extra text: the RFP notes.
  A direct draft never names another carrier.
- CC: the agency's RFP return email when set. Short lines: §4.1 "Short", comma-separated.
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
<deal owner's full name>
<agency name>
<agency phone>
```

  Opening — Warner: `Please see the attached quote request for <group>, effective <Month D, YYYY>.` with docs line
  `The documents to quote are attached:`. Direct: `Please see the attached RFP for <group>, effective <Month D, YYYY>.`
  with `The documents to quote are also attached:`.
- **`.eml` file:** an RFC 5322 message with header `X-Unsent: 1` (Outlook opens it as an unsent draft), To, CC, Subject
  and **no From** (Outlook sends from the account that opens it); `multipart/mixed` with a UTF-8 `text/plain` body and
  the attachments.

---

## 10. AI document reading (Phase 9)

Built only after the manual workflow (Phases 0–8) works. AI speeds up data entry; it never decides anything on its own.

### 10.1 Principles
- **AI never writes to a deal directly.** A read produces a **staged result**; a person reviews it and applies all or
  part of it. Applied values get `origin: ai` with the document and page, and stay `to_check` until confirmed.
- **The person loading a document says what it is** (document role: current plans, renewal, alternates). The reader
  uses that role; it never decides by itself that a plan is current.
- Every read has a **cost limit**; a read that would exceed it stops and keeps what it has.
- Tests never reach the network (§12).

### 10.2 App `ai/` (placed between `documents` and `intake` in the dependency chain)
- **`Job`** model: `deal` FK, `kind` (`quote`, `sbc`, `census_map`, `intake`), `documents` (JSON list of ids), `params`
  (JSON), `status` (`queued`/`running`/`done`/`failed`/`cancelled`), `progress` (0–100), `log` (JSON list of short
  steps — never document text), `result` (JSON staged output), `error`, `cost_usd`, `resolution`
  (blank/`applied`/`discarded`), `created_by`, `created_at`, `started_at`, `finished_at`, `heartbeat_at`.
- **Worker:** `manage.py run_worker` — a loop that claims one queued job with `select_for_update(skip_locked=True)`,
  runs it, and beats `heartbeat_at` every 15 seconds. Jobs with no heartbeat for 10 minutes are marked failed. It runs
  as its own Compose service (`worker`, same image). Cancelling sets `cancelled`; the worker checks between chunks.
- **`ai/client.py`** — the only module that imports `anthropic`. `call_tool(model, system, content, tool,
  max_tokens)` forces the one tool, marks the static system prompt for caching, returns the tool input, and records
  token usage and cost. It raises `AccountError` (401, 403 or exhausted credit — the read stops), `OverLimit` (raised
  before sending once the job's cost limit is reached) and `OutputTruncated` (the response hit `max_tokens`).
  Prices live in one table, `ai/pricing.py`, filled from the provider's published prices when Phase 9 starts.
- **`ai/chunking.py`:** PDFs in page windows (with a small overlap; a window over the request size limit is split
  again); spreadsheets in row windows that repeat the header rows as context and halve on truncation; images as image
  blocks up to 5 MB.
- Endpoints: `POST deals/{id}/ai/reads/ {kind, document_ids}` → `201 job`; `GET ai/jobs/{id}/` (poll every 2 s while
  running, backing off to 10 s); `POST ai/jobs/{id}/cancel/`; `POST ai/jobs/{id}/apply/ {select?}`;
  `POST ai/jobs/{id}/discard/`.

### 10.3 Readers
- **Quote / renewal reader:** per document window, a tool returns
  `plans: [{carrier, plan_name, plan_number, line, values: {field_key: value}, evidence: {field_key: {page, text}}}]`
  restricted to that line's fields (§4.3). Prompt rules: copy values as printed; coinsurance is the member's share; never
  invent; leave unknown fields out. Plans from several windows merge on a normalized key (carrier + plan number, else
  carrier + plan name, + line). Matching to the deal: current-plans documents → current plans; renewal documents →
  renewals linked to the current plan with the same plan number (else same name, else a person picks); alternates →
  alternates. The staged result lists creates and updates field by field (old → new, with page).
- **SBC reader:** like the quote reader, but only plan-design fields are kept; any rate it returns is dropped.
- **Census mapping assist:** when the heuristic mapping (§5.3.2) leaves columns unmapped or low, sends only the
  headers and up to 3 sample values per column, and proposes targets for the mapping dialog to show.
- **Intake prefill:** reads uploaded company documents for intake answers; staged for review in the Intake tab.
- **Review screens:** the Advisor shows "Review AI read" as a plan × field table of proposed changes with page links;
  **Apply selected**, **Apply all**, **Discard**. Census and intake use their existing review dialogs.
- Settings: `ANTHROPIC_API_KEY`, `AI_MODEL` (chosen by a trial on the team's answer-key deals at the start of Phase 9),
  `AI_READ_LIMIT_USD` (per read). Without a key, AI buttons are hidden and the manual flow is unchanged.

---

## 11. Deployment (Phase 10)

Not built until Phase 10; listed so earlier phases stay compatible.

- **Target:** Google Cloud Run. One container image for the web service: a Node build stage produces the SPA; the
  Python stage serves it through Django (WhiteNoise) on the same origin as the API. `/api/*` and `/admin/*` go to
  Django views; every other path returns the SPA's `index.html`.
- **Database:** Cloud SQL for PostgreSQL (version pinned explicitly), private connectivity, TLS verified.
- **Files:** Cloud Storage via `django-storages`, private bucket. Downloads keep streaming through the authenticated
  endpoints; no public URLs. Earlier phases MUST use Django's storage API only (no direct filesystem paths).
- **Secrets:** Secret Manager (pinned versions). **Images:** Artifact Registry.
- **Migrations:** a Cloud Run Job runs `migrate` before traffic shifts. **AI worker:** a separate Cloud Run service or
  worker pool running `run_worker`.
- **Logs:** request logs must exclude `/api/portal/` paths (tokens are in the URL).
- **Release gate:** tests green, `manage.py check --deploy` clean, `/api/health/` reports the new commit with zero
  pending migrations.
- Regional, contractual (BAA) and cost decisions follow the existing deployment decision record kept with the earlier
  system (Appendix C).

---

## 12. Testing

### 12.1 Tools and layout
- pytest + pytest-django, `DJANGO_SETTINGS_MODULE=backend.settings_test`, `addopts = --reuse-db -q`. After editing an
  existing migration, run once with `--create-db`.
- Tests live in `<app>/tests/test_<topic>.py`. Shared fixtures in the root `conftest.py`: `user`, `admin_user`,
  `api` (a signed-in DRF `APIClient`), `admin_api`, `anon_api`, and factory functions `make_client`, `make_deal`,
  `make_member`, `make_plan`, `make_document`.
- Factories create only the rows a test needs. No demo seeders inside tests. **All data is synthetic.**
- Code that depends on the date reads it through `deals/clock.py` (`today()`, `now()`); tests patch that one module.
- Formula tests evaluate the generated workbook with a small test helper that understands only the six functions §9.4
  allows.

### 12.2 Speed budget
The whole suite runs in **under 60 seconds** and any single app in **under 10 seconds**. A slow test is fixed before
new features land.

### 12.3 Tests that MUST exist

| App | Required tests |
|---|---|
| platform | health 200 / 503 shapes; deploy checks fire only when `ENVIRONMENT=production`; gzip applies to JSON only; `/api/meta/` returns every vocabulary |
| accounts | login success, wrong password, inactive user; logout deletes the token; me GET/PATCH; password change rotates the token and enforces validators; reset request always 200 and sends mail; reset confirm valid / invalid; admin-only user endpoints (403 for members); self-demotion and self-deactivation refused; deactivation deletes the token; token expiry when `TOKEN_TTL_HOURS` > 0 |
| deals | create client → client + first deal; search by text, type, pagination; manual stage changes; `sold`/`lost` refused through PATCH; lost / reopen; 409 on writes to a lost deal (notes and reopen still work); Activity rows written and free of census values; note edit permissions; one primary contact per client |
| documents | upload, list, edit, delete removes the file; download requires sign-in and sets the §3.8 headers; size and extension limits |
| intake | first access creates the `Intake` row with `legal_name` = client name; `clean_value` for every row of §5.2 (table-driven); every shown-when operator; every validation rule (table-driven); readiness; PATCH is all-or-nothing; unknown key 400; BOR sign / clear |
| census | header detection; mapping (exact, label, positional effective date, fuzzy, line guard, one column per key, low flag); dependent linking (subscriber SSN, employee id, last employee, orphan); SSN copied from subscriber SSN; merge by identity with dry-run counts; value cleaning; `is_required` for every code and the dependent exemption; every validation rule; summary and the 99% cap; rollup (own, proxy, waived, blank); FTE; age; contiguous ZIP; blank template → re-import gives identical data at full confidence |
| quotes | value cleaning per type; role and link rules; one sold plan per line (constraint and service); create renewal copies design but not rates; counts precedence (every step of §5.5); **every worked example in §5.5**; comparison base selection; packages; employee cost; plan template round trip; import errors carry cell addresses; import is all-or-nothing |
| commission | `parse_comp` and `comp_label` cases; agency-default fallback; basis plan; expected revenue per type; splits must total 100 |
| proposals | default plan selection; one sheet per presented line; column order; empty rows omitted; formulas evaluate to the app's totals for every plan and package; the `†` quoted-premium case; only input cells unlocked; deck includes current plans; PDF builds; internal workbook contains no formulas; spreadsheet injection guard |
| rfp | size band; defaults (lines, funding, route, form); eligibility reasons; commission request text (one label / grouped); group facts; carrier fill — header-mismatch refusal, each source and transform, employee-only / line / dependent-inherits, `max_rows` warning, untouched zip parts byte-identical, dates as serials; packet contents and README; drafts per route (a direct draft never names another carrier or carries its census); `.eml` has `X-Unsent: 1` and no From; first sent → `quoting` |
| review | link validation and expiry bounds; status derivation; portal 404 / 410; portal payload has exactly the allowlisted keys; SSNs masked; save creates or replaces pending values; unchanged and masked-unchanged values ignored; unasked key 400; upload kinds; approve applies with `origin: client`; reject leaves the deal unchanged |
| overview | next action — one test per row of §5.9; every summary key present |
| ai (Phase 9) | no network without a key; mocked reads produce staged results; apply / discard; cost limit stops before sending; truncation splits and retries; worker claims one job at a time |

### 12.4 Tests we never write
Tests that read source code, templates or documentation; tests that pin counts of anything (tests, rules, files);
parity tests between generated files; snapshot tests of whole payloads (assert the keys and values that matter); tests
that reach the network.

### 12.5 Frontend checks
`npm run lint` (ESLint with the react-hooks rules) and `npm run build` must pass. Behaviour is verified by clicking
through each phase's flow (§13). End-to-end browser tests (Playwright) for the acceptance flow MAY be added after
Phase 5.

---

## 13. Build plan

Build in order. Each **slice** is reviewed and committed by the project owner before the next starts (changes are left
uncommitted for review). A slice is done when its tests and checks pass and its acceptance criteria hold in the browser.

### Phase 0 — Platform
| Slice | Build | Acceptance |
|---|---|---|
| 0.1 Backend skeleton | `backend/` (§3.5): settings, test settings, logging, health, deploy checks, gzip middleware; `requirements.txt` | `pytest` runs; `/api/health/` answers |
| 0.2 Docker | `Dockerfile`, `start.sh`, `docker-compose.yml`, `.dockerignore`, `.env.example` (§3.4) | `docker compose up --build` starts all three services on 4001 / 8004 / 5436 |
| 0.3 Accounts | §7.2 endpoints; `ExpiringTokenAuthentication`; admin user endpoints | accounts tests (§12.3) pass |
| 0.4 Frontend shell | Vite + React + Router + TanStack Query, API client, AuthProvider, sign-in and reset pages, top bar, empty dashboard, `tokens.css`, ESLint | sign in at http://localhost:4001, see the empty dashboard, sign out; hot reload works when a file is edited |
| 0.5 Working docs | `CLAUDE.md` (§14), `README.md` (how to run), `pytest.ini`, `ruff.toml`, `/api/meta/` with stages | ruff and ESLint clean |

### Phase 1 — Dashboard and deal shell
| Slice | Build | Acceptance |
|---|---|---|
| 1.1 Deals models | §6.2 models, `lines.py`, `stages.py`, `clock.py`; meta serves lines, stages, contact roles | migrations apply; deals tests pass |
| 1.2 Clients API | §7.3 | search, create, stage, lost / reopen work through the API |
| 1.3 Dashboard UI | §8.3 + New client dialog | create a client, find it by search, filter New / Existing |
| 1.4 Deal page + Overview v1 | §8.4; Overview with next action (rows available so far), notes, activity | open a deal, change stage, mark lost and reopen, add a pinned note |
| 1.5 Admin pages | §8.14 Users and Agency settings | an admin adds a member; the member cannot open admin pages |

### Phase 2 — Intake and Documents v1
| Slice | Build | Acceptance |
|---|---|---|
| 2.1 Documents | §6.3, §7.4 (without `sheet/`), Documents tab v1 (§8.13) | upload, relabel, view, download, delete a PDF and a spreadsheet |
| 2.2 Intake backend | §4.5 form, §5.2 rules, §6.4 models, §7.5 | intake tests pass |
| 2.3 Intake UI | §8.6 with `FieldForm` | take a new deal from blank to "Ready to quote" in the browser; a bad FEIN shows its message |

### Phase 3 — Census
| Slice | Build | Acceptance |
|---|---|---|
| 3.1 Rules | §4.2, §4.4, §5.3.1, §5.3.3–§5.3.7, Member model | census rule tests pass |
| 3.2 Import | §5.3.2, CensusImport, §7.6 import endpoints | a synthetic 300-person file with dependents imports; a re-import updates in place |
| 3.3 Census UI | §8.8, `DataGrid` (§8.16), templates §9.1–§9.2 | fix flagged errors in the grid; the rollup matches a hand count; the blank template re-imports cleanly |

### Phase 4 — Advisor (manual first)
| Slice | Build | Acceptance |
|---|---|---|
| 4.1 Plans and math | §4.3, §5.4, §5.5, Plan model | every worked example passes |
| 4.2 Comparison API | §7.7 | create current / renewal / alternate plans and see premiums, changes and packages |
| 4.3 Advisor UI | §8.11 including the Enrollment card | 3 current plans + renewals + 3 alternates with per-plan counts price correctly on screen |
| 4.4 Plan template | §9.3 | export → fill in Excel → import changes exactly the edited cells; a bad cell reports its address |

### Phase 5 — Proposal (Excel first)
| Slice | Build | Acceptance |
|---|---|---|
| 5.1 Config + preview | §6.8, §7.9, §8.12 | choose and order plans; the preview shows the workbook's rows |
| 5.2 Client workbook | §9.4 | **the end-to-end acceptance test at the end of this section** passes |
| 5.3 Internal workbook | §9.5 | every Advisor field is present |
| 5.4 PowerPoint | §9.6 | current plans appear; a 9-plan line splits across slides correctly |
| 5.5 PDF | §9.7 | same pages as the deck |

### Phase 6 — Documents v2
| Slice | Build | Acceptance |
|---|---|---|
| 6.1 Viewer | §8.13 v2 viewer, `documents/{id}/sheet/` | read a PDF and a spreadsheet inside the app; find text |
| 6.2 Provenance | document roles at upload; values-from-this-document panel; confirm | from an Advisor cell, jump to its source; confirm values in bulk |

### Phase 7 — RFP and Commission
| Slice | Build | Acceptance |
|---|---|---|
| 7.1 RFP config | §4.7, §5.7, §6.9, §7.10 (config), §8.9 sections 1–2 | band, defaults and eligibility shown correctly |
| 7.2 Carrier census files | §9.8 + assets | the Warner, Aetna, Angle and UHC files open in Excel with the carrier's own formatting intact and correct values |
| 7.3 Forms, packet, drafts | §9.9–§9.11, §8.9 sections 3–4 | packet zip contents match the README; `.eml` opens as a draft in Outlook; marking sent moves the deal to Quoting |
| 7.4 Commission | §5.6, §6.7, §7.8, §8.10 | rates, expected revenue and a 60/40 split save; the RFP shows the commission text |

### Phase 8 — Overview complete and Review & request
| Slice | Build | Acceptance |
|---|---|---|
| 8.1 Overview | §5.9, §5.10, §7.13, §8.5 | next action follows a deal through every step |
| 8.2 Links | §5.8, §6.10, §7.11 (links), §8.7 requests | create, copy, extend, revoke a link |
| 8.3 Portal | §7.12, §8.15 | a client fills answers, people's blanks and uploads on a phone-sized screen |
| 8.4 Review queue | §7.11 (review), §8.7 to-review | approve and reject; approved values appear with source "client" |

### Phase 9 — AI reading (§10)
| Slice | Build | Acceptance |
|---|---|---|
| 9.1 Jobs and worker | §10.2 | a job runs in the worker and survives a web restart |
| 9.2 Quote / SBC reader | §10.3 | a renewal PDF with three plans stages exactly three renewals linked to the right current plans |
| 9.3 Census and intake assists | §10.3 | suggestions appear in the existing review dialogs |

### Phase 10 — Cloud Run (§11)
Planned in detail when Phase 9 is complete.

### End-to-end acceptance (after slice 5.2), synthetic data
1. Create a new client from the dashboard; find it again by search.
2. Fill intake until "Ready to quote".
3. Import a ~150-person census with dependents; fix its errors.
4. In the Advisor add three current medical plans, a renewal for each and three alternates (at least one through the
   plan template import).
5. Type per-plan enrollment on the current plans; the renewals and linked alternates inherit it.
6. Star the plans to present; download the client Excel.
7. Every total in the workbook (per plan and per package) equals the Advisor's to the dollar; current plans appear; each
   line prints on one landscape page.

---

## 14. Working agreement and CLAUDE.md

Phase 0 creates `CLAUDE.md` with this content (keep it under 80 lines; it is loaded into every Claude Code session):

```markdown
# 2Vantage — benefits workflow for new clients (Django 5.2 + DRF · React 19 + Vite · Postgres 15)

The full specification is plan.md. Read the section for the area you are changing before you change it.

## Commands
docker compose up --build -d                    # frontend :4001, backend :8004, postgres :5436
docker compose exec backend python manage.py migrate
docker compose exec backend pytest <app>        # one app, seconds
docker compose exec backend pytest              # everything, < 60 s
docker compose exec backend ruff check .
docker compose exec backend python manage.py makemigrations --check --dry-run
docker compose exec frontend npm run lint && docker compose exec frontend npm run build

## Map (one Django app per tab; frontend folder per tab in frontend/src/deal/<tab>/)
accounts → deals → documents → intake → census → quotes → commission → proposals → rfp → review → overview
An app may import only from apps to its left.

## Rules
1. Vocabularies are Python constants (deals/lines.py, intake/form.py, census/fields.py, quotes/fields.py),
   served by /api/meta/. Never copy them into JS. Never seed them with migrations.
2. Values live in JSON on their row with a parallel `sources` dict. Status and readiness are computed on read.
3. Every write goes through <app>/services.py, logs one Activity row (never census values), and returns only
   what changed. The frontend invalidates only that tab's queries.
4. Money math lives only in quotes/math.py (round half up, like Excel).
5. No file over 300 lines. Split it before it grows past that.
6. Public portal views: AllowAny, no authentication classes, allowlisted payloads, 404 bad token, 410 expired.
7. PHI (census people): never in logs, Activity, error text, file names or URLs. Test data is synthetic.
8. Tests are behavioural. No tests that read source code or docs; no pinned counts.

## How a change is made
1. Read this file and the plan.md section for the area.
2. Change one app (its backend folder and its frontend folder). If another app must change, say why.
3. Run that app's tests and the linters; click through the change at http://localhost:4001.
4. Run the full suite once.
5. Leave the change uncommitted for Daniel. Summarize: files changed, what to check, what is next.
```

There is no decision log, no generated map or digest, and no document whose line counts are tested. When a rule in this
spec changes, update the spec section in the same change.

---

## 15. Deliberate non-goals

These existed in the earlier system and are **not** to be rebuilt. Each made the old system slower to change.

| Do not build | Why |
|---|---|
| Version history with snapshots, diffs, restore, edit sessions and locks | ~600 KB snapshots and a lock protocol on every write. The Activity log answers "who changed what, when" |
| One database row per value (entity–attribute–value) | 60,000+ rows per large census, hand-written SQL counts and parity tests. Use JSON on the row (§3.7) |
| Field definitions in the database, seeded by migrations | Froze the field lists; every new field needed two migrations |
| Per-deal required / waived overrides; marketing checklist attestations; coverage-intent hashes | Multiplied the "required" rule into five copies |
| Confirmation, review-mark, "located" and layer-stamp columns on every value | Replaced by one `sources` entry per value |
| AI chat, agents, "lessons", table-editing agents, sandbox copies | AI is a staged reader (§10) and nothing else |
| An in-app test runner, walkthroughs or guided tours | Tests run from the terminal; tours wove test hooks into product code |
| An in-app assistant, usage analytics, reports module | Out of scope |
| P&C, commission ledger and statements, joint ventures, referrals, workflow boards, form builder | Other products |
| Carrier questionnaires as in-app forms | Upload the carrier's own PDF |
| Benefit guides, implementation board, renewal reminders, task queues | After the sale or for renewals |
| More proposal formats (16:9 "presentation" PDF, paper view, previews, share links with client selection, status reports) | Excel, PowerPoint and PDF only |
| Concessions, priced versions, plan duplicates, merges, slot swaps; saved filter / proposal / bundle templates | Accreted features with low use |
| Data hub connectors | Stubs that never connected |
| A decision log, document line budgets, generated maps or digests, tests that read source | The main cause of 20-minute to 2-hour changes |

---

## 16. Open questions

| # | Question | Needed before | Current answer in this spec |
|---|---|---|---|
| 1 | Client workbook layout: each current plan beside its renewal, or current / renewal / alternate blocks? Row list and colours? Disclaimer wording? | Phase 5 | Pairs side by side; rows and colours as §9.4 |
| 2 | Print the outpatient mental health row, telehealth and mail order on client documents? | Phase 5 | Mental health not printed; telehealth and mail order printed |
| 3 | Is SSN required for dependents (and for prospects at all)? | Phase 3 | Required for everyone (A) |
| 4 | A simple PIN on client portal links (the census carries SSNs and birth dates)? | Phase 8 | No PIN |
| 5 | Sign-in token lifetime | Phase 10 | No expiry (`TOKEN_TTL_HOURS=0`) |
| 6 | Is the carrier list (§4.7) complete? | Phase 7 | 25 carriers |
| 7 | Contacts at client level (they carry across years) | Phase 2 | Client level |
| 8 | AI model and per-read cost limit | Phase 9 | Chosen by trial at the start of Phase 9 |
| 9 | Move any data from the earlier system? | — | No; 2Vantage starts empty |

---

## Appendix A — Assets supplied with this spec

Binary files and data that cannot be written into a document. They come from the earlier system's repository
(`Vantage/`); copy them into 2Vantage when the slice that needs them starts. **Never copy client files or anything from
`Vantage/aBenefitsMeetings/`.**

| Asset | Source in `Vantage/` | Destination in 2Vantage | Used by |
|---|---|---|---|
| Carrier census workbooks | `benefits/templates_xlsx/warner_census.xlsx`, `aetna_gateway_census.xlsx`, `angle_census.xlsx`, `uhc_census.xlsx` | `assets/carrier_templates/` | §9.8 |
| Carrier census column definitions | `benefits/migrations/0054_real_carrier_templates.py` (`TEMPLATES`), as amended by `0061_uhc_waive_all.py`, `0065_census_columns_to_carriers.py`, `0066_uhc_stop_at_x.py` | `rfp/templates/definitions.py` (plain data) | §9.8 |
| Warner quote request forms | `benefits/templates_xlsx/warner_qrf_simplified.xlsx`, `warner_qrf_small_group.xlsx`, `warner_qrf_large_group.xlsx` | `assets/forms/` | §9.9 |
| Quote request form cell maps | the cell / label constants in `benefits/pipeline/quote_request_form.py` | `rfp/form_maps.py` | §9.9 |
| ZIP → county crosswalk | `benefits/data/zip_county.csv.gz` and its `README.md` (source and licence) | `assets/zip_county.csv.gz` | §9.8 `derive:county` |

---

## Appendix B — Background: why 2Vantage exists

The earlier system (`Vantage/`) grew to 18 Django apps, ~350,000 lines of Python and ~170,000 lines of frontend code,
with 257 routes in the benefits app alone and 8,370 tests that took 10–16 minutes per run. A small change took 20
minutes to 2 hours, mostly in the work around the change: full test runs that were usually red, a decision log and
generated digests to keep in sync, tests that read source code, files of 3,000+ lines, and a data model that stored every
value as its own row. On 2026-10-29 the benefits team reset its priorities — proposals first, data before AI, a manual
fallback for everything, Excel as the baseline output — and on 2026-11-10 the project owner chose to rebuild the benefits
workflow from scratch. This specification keeps the earlier system's business knowledge (field lists, rules, carrier
formats, premium math) and leaves its machinery behind (§15).

---

## Appendix C — Where each rule came from

For anyone who wants to check a rule against the earlier system's behaviour. Paths are in `Vantage/`.

| Spec | Earlier source |
|---|---|
| §4.1 lines, field sets, rate bases | `benefits/lines.py` |
| §4.2 tiers and waiver words | `benefits/market/validation.py` (`TIER_ALIASES`, `WAIVE_WORDS`) |
| §4.3 plan fields, §4.4 census columns | `benefits/registry.py` |
| §4.5 intake questions and help | `benefits/market/intake.py` (`INTAKE_FIELD_SEED`, `FIELD_HELP`) |
| §4.7 carriers | `benefits/market/rfp_carriers.py` |
| §4.8 header synonyms | `benefits/market/census_reader.py` (`HEADER_SYNONYMS`) |
| §5.1 stages | `benefits/stages.py` |
| §5.2 intake cleaning, conditions, validation, readiness | `benefits/market/intake_writes.py` (`clean_value`), `intake.py` (`condition_met`, `needs`, `contacts_ok`), `validation.py` (`validate_intake`) |
| §5.3 census import, validation, rollup, FTE, age | `benefits/market/census_reader.py`, `validation.py` (`validate_case`), `pipeline/plan_math.py` |
| §5.5 premium math | `benefits/pipeline/plan_math.py` (`round_money`, `tier_premium`, `group_premium`), `presentation_math.py` |
| §5.6 commission | `benefits/market/validation.py` (`parse_comp`, `comp_label`), `serializers/overview.py` |
| §5.7 RFP rules and facts | `benefits/market/rfp.py` |
| §9.4 client workbook layout | `PlanningDocs/Benefits/proposal-packages-and-outputs.md` §3.7; team meetings of 2026-10-29 and 2026-11-05 |
| §9.8 carrier census fill | `benefits/pipeline/xlsx_fill.py`, `workbooks.py`, `plan_math.py` (`census_rows_for_template`) |
| §9.9–§9.11 forms, packet, emails | `benefits/pipeline/quote_request_form.py`, `rfp_bundle.py`, `rfp_email.py` |
| §10 AI client and chunking | `docscan/client.py`, `docscan/chunking.py` |
| §11 deployment decisions | `PlanningDocs/Platform/production-deployment-plan.md` |
