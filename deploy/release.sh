#!/usr/bin/env bash
# One staging release (slice 69; deploy/README.md, "Each release"). NOT YET RUN: Google Cloud is not connected.
# Run it from a clean checkout of the commit to release, signed in with gcloud, after the one-time setup. It stops at
# the first failure, and the services move only after the migrations job (check --deploy, then migrate) succeeds.
set -euo pipefail
cd "$(dirname "$0")/.."
set -a
. deploy/staging.env
set +a

[ -z "$(git status --porcelain)" ] || { echo "Commit first: staging runs committed code only." >&2; exit 1; }
sha="$(git rev-parse HEAD)"
image="$REGION-docker.pkg.dev/$PROJECT_ID/$REPOSITORY/$IMAGE_NAME:$sha"
out="$(mktemp -d)"
python3 deploy/render.py --commit "$sha" --out "$out" # refuses while deploy/staging.env has a blank

echo "== the production image $image"
docker build --target production --build-arg GIT_SHA="$sha" -t "$image" .
docker push "$image"

echo "== the migrations job: check --deploy, then migrate, before any traffic moves"
gcloud run jobs replace "$out/migrate.yaml" --region "$REGION"
gcloud run jobs execute "$MIGRATE_JOB" --region "$REGION" --wait
gcloud run jobs replace "$out/manage.yaml" --region "$REGION"

echo "== the web service and the worker"
gcloud run services replace "$out/web.yaml" --region "$REGION"
gcloud run services replace "$out/worker.yaml" --region "$REGION"

echo "== the release gate"
python3 deploy/release_gate.py --url "https://$WEB_HOST" --commit "$sha"
echo "Now the smoke check: SMOKE_PASSWORD=… python3 deploy/smoke.py --url https://$WEB_HOST --user <staff user>"
