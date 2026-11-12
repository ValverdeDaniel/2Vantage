# 2Vantage

The benefits team's internal app: clients, plans side by side, and the client proposal. The specification is
[plan.md](plan.md); working rules for code changes are in [CLAUDE.md](CLAUDE.md).

## Run it locally

Needs Docker Desktop.

```bash
docker compose up --build -d          # frontend http://localhost:4001 · backend :8004 · postgres :5436
docker compose exec backend python manage.py createsuperuser
docker compose exec backend python manage.py seed_golden   # two synthetic deals to click through
```

Sign in at http://localhost:4001. Users and agency settings are managed in Django admin at
http://localhost:4001/admin/ (staff only).

## Check it

```bash
docker compose exec backend pytest            # whole suite, under a minute
docker compose exec backend pytest quotes     # one app
docker compose exec backend ruff check .
docker compose exec backend python manage.py makemigrations --check --dry-run
docker compose exec frontend npm run lint
docker compose exec frontend npm run build
```

## Where things are

| Path | What |
|---|---|
| `backend/` | Django settings, health check, deploy checks, `/api/meta/` |
| `accounts/` | Sign-in API over Django sessions |
| `deals/` | Clients, deals, the Activity log, lines of coverage, stages, the agency clock |
| `documents/` | Uploaded and stored files |
| `quotes/` | Plans, plan fields, premium math, packages, the plan template |
| `proposals/` | What a proposal presents and its preview |
| `golden/` | The golden deals: one JSON spec per deal with its parity profile, the answer keys, `seed_golden` |
| `frontend/` | React app (one folder per deal tab under `src/deal/`) |
| `tools/parity/` | Old Vantage beside 2Vantage, on the golden deals, for the parity lanes ([README](tools/parity/README.md)) |
| `browser/` | The Look and Walk lanes in the installed Chrome (`npm --prefix browser ci`, then `run look` / `run walk`) |
| `deploy/` | Staging on Google Cloud (not connected yet): the production image's rehearsal (`bash deploy/rehearse.sh`), the release gate, Cloud Run definitions ([README](deploy/README.md)) |

Uploaded files live in the `media` Docker volume, never inside this folder.
