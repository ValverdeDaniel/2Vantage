# Staging on Google Cloud (slice 69, STG-1)

**Status: designed and rehearsed locally, not connected.** No Google Cloud resource exists and no `gcloud` command
below has been run (Daniel, 2026-11-11). Connecting staging is configuration only: fill in `deploy/staging.env`, run
the one-time setup once, then release with `deploy/release.sh`. The design is plan.md §11 (§11.2 Google Cloud,
§11.3 the release gate); choices the plan leaves open follow the old app's deployment plan
(`PlanningDocs/Platform/production-deployment-plan.md` at 891f1b3). Staging holds synthetic data only until the PHI
gate (slice 47, §11.4).

## What runs where

| Piece | On Cloud Run | In the local rehearsal (`docker-compose.prod.yml`) |
|---|---|---|
| Image | `<REGION>-docker.pkg.dev/<PROJECT_ID>/vantage/app:<full commit SHA>` (Artifact Registry) | `vantage2-rehearsal:<commit>` |
| Web | service `vantage-web`: `start.sh web` (gunicorn; API, admin and the built SPA on one origin) | `web`, http://localhost:8014 |
| Worker | service `vantage-worker`: `start.sh worker` (`run_worker`), CPU always on, one instance, internal | `worker` |
| Migrations | job `vantage-migrate`: `start.sh migrate` (`check --deploy`, then `migrate`), before traffic moves | `migrate` |
| One-offs | job `vantage-manage` (`seed_golden`, `createsuperuser`) | `docker compose run` |
| Database | Cloud SQL for PostgreSQL 15, private IP only, TLS verified against its CA | `postgres:15` |
| Files | a private bucket through django-storages (`backend/storage.py`) | a volume; or a Cloud Storage emulator (`--gcs`) |
| Secrets | Secret Manager, each version pinned in `staging.env` | made by `rehearse.sh`, kept in `~/.2vantage-rehearsal` |
| Logs | Cloud Logging; link-token paths excluded (step 7) and dropped by the app | `docker compose logs` |

## The production image

```bash
docker build --target production --build-arg GIT_SHA=$(git rev-parse HEAD) -t <image> .
```

The root `Dockerfile` builds the SPA with Node 22 (`vite build --base=/static/`), copies it into the Python image
without the frontend's sources, and collects static files once, at build. `docker build .` (no target) still builds
the local image that `docker-compose.yml` runs. The production image's entry point is `start.sh`: `web` (the
default), `worker`, `migrate`, or any command (`python manage.py …`). A web instance never migrates or collects at
start. `GIT_SHA` is baked in, and `/api/health/` names it.

## Settings that switch it (only `backend/settings.py` reads the environment)

| Variable | Effect |
|---|---|
| `ENVIRONMENT=production` | WhiteNoise serves `/static/` (`.mjs` as JavaScript, hashed assets cached for good); HTTPS redirect except `/api/health/`; HSTS; X-Forwarded-Proto trusted; secure cookies; logs drop records about `/api/portal/`, `/portal/` and `/b/` |
| `GS_BUCKET_NAME` | Files go to that private bucket. Google's libraries load only then. The storage hands out no URL, signed or public: downloads stream through the app and are logged (§3.6, §3.8) |
| `DB_HOST`, `DB_SSLMODE`, `DB_SSLROOTCERT` | Private IP with TLS verified (staging's shape, `cloudrun/app-env.yaml`) |
| `CLOUD_SQL_INSTANCE` | The other shape: Cloud Run's Cloud SQL connection, through its socket at `/cloudsql/<instance>` |
| `K_SERVICE` / `CLOUD_RUN_JOB` (set by Cloud Run) | `vantage.E005` fails `check --deploy` if files would stay on the instance |
| `AUTH_OIDC_TENANT_ID`, `AUTH_OIDC_CLIENT_ID`, `AUTH_OIDC_CLIENT_SECRET` (slice 47) | Microsoft 365 sign-in against the firm's Entra ID app registration (step 5b); the sign-in page shows "Sign in with Microsoft" |
| `AUTH_PASSWORD_SIGNIN` (slice 47) | `false` at the PHI gate: username and password stop working on the sign-in page and in Django admin |
| `AI_PHI_READERS` (slice 47) | The PHI-gate switch, turned on last (`deploy/phi-gate.md`); `vantage.E006` refuses it before the two above |

Every page path that is not `/api/`, `/admin/`, `/accounts/` or `/static/` answers the SPA's `index.html`
(`backend/spa.py`); a client link's page (`/portal/…`, `/b/…`) adds `no-referrer`, `no-store` and `noindex`.

## The local rehearsal

```bash
bash deploy/rehearse.sh           # files on a volume
bash deploy/rehearse.sh --gcs     # files in a local Cloud Storage emulator: the bucket path's real code
bash deploy/rehearse.sh --down    # ...and remove it afterwards
```

On a fresh database, with the image built from the working tree: the migrations job, the web service and the
worker, `seed_golden`, the release gate, the smoke check, where the files landed, and a log scan for the gate's
token canary. It uses its own Compose project (`vantage2-rehearsal`) and port 8014, never the dev or parity stacks.
It speaks plain HTTP inside Docker and sends `X-Forwarded-Proto: https` as Cloud Run's front end would. Sign in on
http://localhost:8014 as `rehearsal-admin` (password in `~/.2vantage-rehearsal/admin_password`); a browser needs that
header too (any header extension), since the rehearsal redirects plain HTTP exactly as staging does.

## The release gate (§11.3)

1. `check --deploy --fail-level WARNING` is clean: the migrations job's first step, with the deployment's settings.
2. `python deploy/release_gate.py --url https://<WEB_HOST> --commit <sha>`: `/api/health/` names the commit with no
   pending migration; the SPA answers its page paths and leaves `/api/` to Django; the entry script is cached for
   good; pdf.js's `.mjs` worker is served as JavaScript; a client link page keeps its token; HSTS, nosniff, DENY.
3. `SMOKE_PASSWORD=… python deploy/smoke.py --url https://<WEB_HOST> --user <staff user>`: signs in, opens GD1's
   Advisor, uploads a synthetic PDF to GD1 through the app and downloads it back byte for byte, runs "Check this
   file" in the worker, then purges it. The rest of §11.3 (lanes green; a PDF opens in Chrome and Edge) is by hand.

## Connecting staging (not yet run)

Needs: the gcloud CLI signed in as an admin of the firm's Google Cloud identity (the old plan: Cloud Identity on the
firm's domain, never a personal Gmail), a billing account, Docker, Python 3. Fill in `deploy/staging.env` as the
steps reveal its blanks, then load it into the shell before each step:

```bash
set -a; . deploy/staging.env; set +a
SA=$RUN_SERVICE_ACCOUNT@$PROJECT_ID.iam.gserviceaccount.com
```

**1. Project and APIs.** Then put the project number in `PROJECT_NUMBER`, and
`WEB_HOST=$WEB_SERVICE-$PROJECT_NUMBER.$REGION.run.app`.

```bash
gcloud projects create $PROJECT_ID
gcloud billing projects link $PROJECT_ID --billing-account=<BILLING_ACCOUNT_ID>
gcloud config set project $PROJECT_ID
gcloud services enable run.googleapis.com sqladmin.googleapis.com secretmanager.googleapis.com \
  artifactregistry.googleapis.com compute.googleapis.com servicenetworking.googleapis.com storage.googleapis.com \
  logging.googleapis.com
gcloud projects describe $PROJECT_ID --format='value(projectNumber)'
```

**2. Artifact Registry**, with a clean-up policy from day one.

```bash
gcloud artifacts repositories create $REPOSITORY --repository-format=docker --location=$REGION
gcloud artifacts repositories set-cleanup-policies $REPOSITORY --location=$REGION \
  --policy=deploy/gcp/registry-cleanup.json --no-dry-run
gcloud auth configure-docker $REGION-docker.pkg.dev
```

**3. The runtime service account** (every service and job runs as it).

```bash
gcloud iam service-accounts create $RUN_SERVICE_ACCOUNT --display-name="2Vantage on Cloud Run"
```

**4. Private networking and Cloud SQL** (PostgreSQL 15 pinned; backups and point-in-time recovery set explicitly,
since the CLI leaves them off). Then put the private IP in `DB_PRIVATE_IP`.

```bash
gcloud compute addresses create google-managed-services-$VPC_NETWORK --global --purpose=VPC_PEERING \
  --prefix-length=16 --network=$VPC_NETWORK
gcloud services vpc-peerings connect --service=servicenetworking.googleapis.com \
  --ranges=google-managed-services-$VPC_NETWORK --network=$VPC_NETWORK
gcloud sql instances create $SQL_INSTANCE --database-version=POSTGRES_15 --edition=ENTERPRISE --tier=$SQL_TIER \
  --region=$REGION --network=$VPC_NETWORK --no-assign-ip --ssl-mode=ENCRYPTED_ONLY \
  --backup-start-time=07:00 --enable-point-in-time-recovery --deletion-protection
gcloud sql databases create $DB_NAME --instance=$SQL_INSTANCE --charset=UTF8 --collation=en_US.UTF8
gcloud sql instances describe $SQL_INSTANCE --format='value(ipAddresses[0].ipAddress)'
```

**5. Secrets** (made in place, never typed on screen; each service reads the version `staging.env` pins).

```bash
openssl rand -base64 48 | tr -d '\n' | gcloud secrets create $SECRET_DJANGO_KEY --data-file=-
openssl rand -base64 32 | tr -d '\n/+=' | gcloud secrets create $SECRET_DB_PASSWORD --data-file=-
gcloud sql users create $DB_USER --instance=$SQL_INSTANCE \
  --password="$(gcloud secrets versions access $SECRET_DB_PASSWORD_VERSION --secret=$SECRET_DB_PASSWORD)"
gcloud sql instances describe $SQL_INSTANCE --format='value(serverCaCert.cert)' \
  | gcloud secrets create $SECRET_DB_CA --data-file=-
read -rsp 'Mailbox password: ' P; printf '%s' "$P" | gcloud secrets create $SECRET_EMAIL_PASSWORD --data-file=-; unset P
openssl rand -base64 18 | tr -d '\n' | gcloud secrets create $SECRET_FIRST_ADMIN_PASSWORD --data-file=-
for secret in $SECRET_DJANGO_KEY $SECRET_DB_PASSWORD $SECRET_DB_CA $SECRET_EMAIL_PASSWORD $SECRET_FIRST_ADMIN_PASSWORD; do
  gcloud secrets add-iam-policy-binding $secret --member=serviceAccount:$SA --role=roles/secretmanager.secretAccessor
done
```

**5b. Microsoft 365 sign-in** (slice 47; `deploy/phi-gate.md` item 3), by an admin of the firm's Entra ID: a
single-tenant app registration whose one redirect URI is the web service's callback, asking only `openid email
profile` (delegated; grant admin consent once, in the portal's API permissions), assignment required, and a client
secret kept in Secret Manager. Nothing in this step has been run (Microsoft 365 is not connected in this build).
Then put the directory id in `ENTRA_TENANT_ID` and the application id in `ENTRA_CLIENT_ID`. Require MFA for the app
with a Conditional Access policy, and calendar the secret's expiry: an expired secret stops every sign-in.

```bash
az login --tenant <the firm's Entra directory>
APP_ID=$(az ad app create --display-name "2Vantage staging" --sign-in-audience AzureADMyOrg \
  --web-redirect-uris "https://$WEB_HOST/api/auth/microsoft/callback/" --query appId -o tsv)
az ad sp create --id $APP_ID
az ad sp update --id $APP_ID --set appRoleAssignmentRequired=true   # then assign the staff group to it
az account show --query tenantId -o tsv                               # ENTRA_TENANT_ID; $APP_ID is ENTRA_CLIENT_ID
az ad app credential reset --id $APP_ID --display-name staging --years 1 --query password -o tsv \
  | gcloud secrets create $SECRET_ENTRA_CLIENT --data-file=-
gcloud secrets add-iam-policy-binding $SECRET_ENTRA_CLIENT --member=serviceAccount:$SA \
  --role=roles/secretmanager.secretAccessor
```

Each person who signs in needs a Django user with the same email (Django admin); nobody is created at sign-in.

**6. The private bucket**: uniform access, public access prevented, versioned, old versions deleted after 30 days.

```bash
gcloud storage buckets create gs://$BUCKET --location=$REGION --uniform-bucket-level-access --public-access-prevention
gcloud storage buckets update gs://$BUCKET --versioning --lifecycle-file=deploy/gcp/bucket-lifecycle.json
gcloud storage buckets add-iam-policy-binding gs://$BUCKET --member=serviceAccount:$SA --role=roles/storage.objectUser
```

**7. Logs and spending.** Cloud Run's own request logs carry the URL and the Referer, so the token paths are kept
out of storage here (§11.2); the app already drops them from its own logs. A budget alerts; never set a spend cap,
which stops every service.

```bash
gcloud logging sinks update _Default --add-exclusion=name=link-tokens,filter='resource.type="cloud_run_revision"
  AND (httpRequest.requestUrl:"/api/portal/" OR httpRequest.requestUrl:"/portal/" OR httpRequest.requestUrl:"/b/"
  OR httpRequest.referer:"/portal/" OR httpRequest.referer:"/b/")'
gcloud billing budgets create --billing-account=<BILLING_ACCOUNT_ID> --display-name="2Vantage staging" \
  --budget-amount=100USD --threshold-rule=percent=0.5 --threshold-rule=percent=0.9 --threshold-rule=percent=1.0
```

**8. The first release**, then what only the first one needs: open the web service to browsers (the app signs
people in itself), load the golden deals, create the first admin, and run the smoke check.

```bash
bash deploy/release.sh
gcloud run services add-iam-policy-binding $WEB_SERVICE --region=$REGION --member=allUsers --role=roles/run.invoker
gcloud run jobs execute $MANAGE_JOB --region=$REGION --wait --args=python,manage.py,seed_golden
gcloud run jobs execute $MANAGE_JOB --region=$REGION --wait \
  --update-env-vars=DJANGO_SUPERUSER_USERNAME=<username>,DJANGO_SUPERUSER_EMAIL=<email> \
  --args=python,manage.py,createsuperuser,--noinput
SMOKE_PASSWORD="$(gcloud secrets versions access $SECRET_FIRST_ADMIN_PASSWORD_VERSION \
  --secret=$SECRET_FIRST_ADMIN_PASSWORD)" python3 deploy/smoke.py --url https://$WEB_HOST --user <username>
```

## Each release

`bash deploy/release.sh` from a clean checkout of the commit: it renders `cloudrun/*.yaml` from `staging.env`
(`deploy/render.py` refuses a blank), builds and pushes the production image tagged with the full commit, replaces and
runs the migrations job, replaces the web service and the worker, then runs the release gate. The smoke check
follows (step 8's last command). Cloud Run resolves the tag to a digest per revision; a rollback is
`gcloud run services update-traffic $WEB_SERVICE --to-revisions=<previous revision>=100` (migrations stay applied).

## Not tested against Google

Everything above ran locally only. Rehearsed: the production image, gunicorn and WhiteNoise, the worker, the
migrations job, the release gate, the smoke check, the log filters, and the bucket path's code (django-storages and
Google's client) against the fsouza/fake-gcs-server emulator. Not tried anywhere: the `gcloud` commands, Cloud Run's
acceptance of the four YAML files (they parse as YAML), Direct VPC egress, Cloud SQL's TLS with `verify-ca`, Secret
Manager mounts, IAM, the log exclusion filter, and the worker service's start-up probe on `$PORT`.

## Later, not in this slice

- Production's front door: a global external load balancer with a managed certificate (Cloud Run domain mappings are
  pre-GA, so not for PHI), then ingress `internal-and-cloud-load-balancing` on the web service.
- The worker as a Cloud Run worker pool (cheaper for always-on work): the same image with `args: [worker]`.
- CI: GitHub Actions with Workload Identity Federation, promoting one digest from staging to production.
- The PHI gate (slice 47): its checklist, with the staging canary scan and the order of the last switches, is
  `deploy/phi-gate.md`. Microsoft 365 sign-in is step 5b; `deploy/canary_scan.sh` runs the scan on the dev stack.
