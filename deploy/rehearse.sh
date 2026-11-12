#!/usr/bin/env bash
# The local production rehearsal (slice 69; plan.md §11.3; deploy/README.md). On a fresh database, with the
# production image built from the working tree: the migrations job (check --deploy, migrate), the web service and the
# worker, seed_golden, the release gate, the smoke check and a log scan for the gate's token canary. Synthetic only.
#   bash deploy/rehearse.sh            files on a local volume (the default storage)
#   bash deploy/rehearse.sh --gcs      files in a local Cloud Storage emulator: the bucket path's real code
#   bash deploy/rehearse.sh --down     ...then remove the rehearsal (otherwise it stays up on http://localhost:8014)
# It never touches the dev stack: its own Compose project (vantage2-rehearsal), port and volumes.
set -euo pipefail
cd "$(dirname "$0")/.."
export MSYS_NO_PATHCONV=1 # Git Bash on Windows: hand container paths over untouched

gcs=0
down=0
for arg in "$@"; do
    case "$arg" in
        --gcs) gcs=1 ;;
        --down) down=1 ;;
        *) echo "usage: bash deploy/rehearse.sh [--gcs] [--down]" >&2; exit 2 ;;
    esac
done

compose() { docker compose -f docker-compose.prod.yml --profile gcs "$@"; }
in_image() { compose run --rm -T --no-deps "$@"; }

# Secrets the rehearsal makes for itself, outside the repository, reused by later runs.
state="${REHEARSAL_STATE:-$HOME/.2vantage-rehearsal}"
mkdir -p "$state"
token() { head -c 48 /dev/urandom | base64 | tr -d '\n+/='; }
[ -s "$state/secret_key" ] || token >"$state/secret_key"
[ -s "$state/admin_password" ] || token >"$state/admin_password"
export REHEARSAL_SECRET_KEY="$(cat "$state/secret_key")"
export SMOKE_PASSWORD="$(cat "$state/admin_password")"
export GIT_SHA="$(git rev-parse HEAD)"
[ -z "$(git status --porcelain)" ] || GIT_SHA="$GIT_SHA-dirty"
bucket=vantage-rehearsal-files
if [ "$gcs" = 1 ]; then
    export REHEARSAL_BUCKET="$bucket" REHEARSAL_EMULATOR=http://gcs:4443
else
    export REHEARSAL_BUCKET= REHEARSAL_EMULATOR=
fi
failed=0
step() { printf '\n== %s\n' "$1"; }
verdict() { if [ "$1" = 0 ]; then echo "PASS  $2"; else echo "FAIL  $2"; failed=1; fi; }
# expect "<what>" <command...>: runs the command as a check (set -e never stops the script on it).
expect() {
    local what="$1"
    shift
    if "$@"; then verdict 0 "$what"; else verdict 1 "$what"; fi
}

step "a fresh rehearsal: commit $GIT_SHA, files in $([ "$gcs" = 1 ] && echo "the emulated bucket" || echo "the media volume")"
compose down -v --remove-orphans >/dev/null 2>&1 || true
compose build migrate

if [ "$gcs" = 1 ]; then
    step "the bucket, in the Cloud Storage emulator"
    compose up -d gcs
    in_image migrate python - <<PY
import time
from google.cloud import storage
for attempt in range(30):
    try:
        storage.Client(project='rehearsal').create_bucket('$bucket')
        break
    except Exception:
        time.sleep(1)
else:
    raise SystemExit('The emulator never answered.')
print('Bucket $bucket is ready.')
PY
fi

step "the migrations job, then the web service and the worker"
compose up -d --wait web worker
compose logs --no-color migrate | tail -n 3

step "seed_golden, and the rehearsal's admin (rehearsal-admin; its password is in $state/admin_password)"
in_image web python manage.py seed_golden
in_image -e SMOKE_PASSWORD web python manage.py shell -c "
import os
from django.contrib.auth import get_user_model
user, _ = get_user_model().objects.get_or_create(username='rehearsal-admin')
user.is_staff = user.is_superuser = True
user.set_password(os.environ['SMOKE_PASSWORD'])
user.save()
print('rehearsal-admin is ready.')"

step "the release gate"
gate=0
in_image web python deploy/release_gate.py --url http://web:8080 --commit "$GIT_SHA" --forwarded-proto https \
    --check-deploy || gate=$?
verdict "$gate" "the release gate"

step "the smoke check"
smoke=0
in_image -e SMOKE_PASSWORD web python deploy/smoke.py --url http://web:8080 --user rehearsal-admin \
    --forwarded-proto https || smoke=$?
verdict "$smoke" "the smoke check"

step "where the files went"
if [ "$gcs" = 1 ]; then
    stored=$(in_image migrate python -c "
from google.cloud import storage
print(sum(1 for _ in storage.Client(project='rehearsal').list_blobs('$bucket', prefix='deals/')))")
    on_disk=$(in_image web sh -c 'find /data/media -type f | wc -l')
    echo "objects in the bucket: $stored; files on the media volume: $on_disk"
    expect "seed_golden's files landed in the bucket" test "$stored" -gt 0
    expect "no file landed on the instance's disk" test "$on_disk" -eq 0
else
    on_disk=$(in_image web sh -c 'find /data/media/deals -type f | wc -l')
    echo "files on the media volume: $on_disk"
    expect "seed_golden's files landed on the media volume" test "$on_disk" -gt 0
fi

step "the logs keep link tokens out (§11.2)"
compose logs --no-color web worker >"$state/rehearsal.log"
expect "no log line names the gate's token canary" test "$(grep -c 'release-gate-canary-token' "$state/rehearsal.log")" = 0
expect "gunicorn's access log still logs other requests" grep -q '"GET /api/health/' "$state/rehearsal.log"

if [ "$down" = 1 ]; then
    step "removing the rehearsal"
    compose down -v --remove-orphans
else
    printf '\nThe rehearsal stays up: http://localhost:%s (rehearsal-admin). Remove it with:\n' "${REHEARSAL_PORT:-8014}"
    echo "  docker compose -f docker-compose.prod.yml --profile gcs down -v"
fi
[ "$failed" = 0 ] && echo "Rehearsal passed." || echo "Rehearsal FAILED."
exit "$failed"
