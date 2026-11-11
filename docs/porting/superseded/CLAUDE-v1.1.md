# 2Vantage — benefits workflow for new clients (Django 5.2 + DRF · React 19 + Vite · Postgres 15)

The full specification is plan.md. Read the section for the area you are changing before you change it.
Build only what the current slice (plan.md §13) names.

## Commands
docker compose up --build -d                    # frontend :4001, backend :8004, postgres :5436
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py seed_golden   # realistic synthetic deals to click through
docker compose exec backend pytest <app>        # one app, seconds
docker compose exec backend pytest              # everything, < 60 s
docker compose exec backend pytest -m recalc    # LibreOffice recalculation of the golden workbooks
docker compose exec backend ruff check .
docker compose exec backend python manage.py makemigrations --check --dry-run
docker compose exec frontend npm run lint && docker compose exec frontend npm run build

## Map (one Django app per tab; frontend folder per tab in frontend/src/deal/<tab>/)
accounts → deals → documents → [ai] → intake → census → quotes → commission → proposals → rfp → review → overview
An app may import only from apps to its left. A fact read by an app lives in that app or one to its left.
Release 1 builds accounts, deals, documents, quotes, proposals.

## Rules
1. Vocabularies are Python constants (deals/lines.py, intake/form.py, census/fields.py, quotes/fields.py),
   served by /api/meta/. Never copy them into JS. Never seed them with migrations.
2. Values live in JSON on their row with a parallel `sources` dict. Status and readiness are computed on read.
   Writing an unchanged value changes nothing, not even its source.
3. Every write goes through <app>/services.py, locks the row it changes (select_for_update or one JSONB merge),
   is recorded in Activity (never census values), and returns only what changed. Deal-tab queries use staleTime 0.
4. Money math lives only in quotes/math.py (round half up, like Excel). Packages come only from package().
5. No file over 300 lines, except data modules (vocabularies, tables). Split code before it grows past that.
6. Sign-in is Django's session; every write sends X-CSRFToken. Users and agency settings live in Django admin.
7. Public portal views: AllowAny, no authentication classes, allowlisted payloads, 404 bad token, 410 expired.
8. PHI (census people and files that carry them): never in logs, Activity, error text, file names or URLs;
   downloads are logged. Client files print only `client: True` fields. Test data is synthetic.
9. Tests are behavioural. No tests that read source code or docs; no pinned counts.

## How a change is made
1. Read this file and the plan.md section for the area.
2. Change one app (its backend folder and its frontend folder). If another app must change, say why.
3. Run that app's tests and the linters; click through the change at http://localhost:4001 on a golden deal.
4. Run the full suite once.
5. Leave the change uncommitted for Daniel. Summarize: files changed, what to check, what is next.
