#!/usr/bin/env bash
# The staging canary scan, run against the local dev stack (slice 47; plan.md §11.4 item 5, §12.9; deploy/phi-gate.md):
# the walk with this run's canary census (deploy/canary_walk.py, inside the backend container), then the log query
# over every service's log since the walk began (docker compose logs: backend, worker, frontend, db), scanned by
# deploy/canary_scan.py. Synthetic only: it makes its own client, and archives it at the end.
#   CANARY_PASSWORD=<golden-admin's password> bash deploy/canary_scan.sh [--user golden-admin]
# Staging runs the same two scripts against https://<WEB_HOST> and a Cloud Logging query (deploy/phi-gate.md, item 5).
# Its files (canaries, logs) go to $CANARY_STATE (default ~/.2vantage-canary), outside the repository.
set -euo pipefail
cd "$(dirname "$0")/.."
export MSYS_NO_PATHCONV=1 # Git Bash on Windows: hand container paths over untouched

user=golden-admin
while [ $# -gt 0 ]; do
    case "$1" in
        --user) user="$2"; shift 2 ;;
        *) echo "usage: CANARY_PASSWORD=… bash deploy/canary_scan.sh [--user <staff username>]" >&2; exit 2 ;;
    esac
done
: "${CANARY_PASSWORD:?set CANARY_PASSWORD to the password of the staff user}"
export CANARY_PASSWORD
state="${CANARY_STATE:-$HOME/.2vantage-canary}"
mkdir -p "$state"
inside=/tmp/2vantage-canaries.json

# The log window opens a little before the walk: Docker Desktop's VM clock can run seconds behind the host's (2.6 s
# seen, slice 58), and `docker compose logs --since` reads the VM's timestamps, so a window opened at the host's "now"
# cut the walk's first second. Lines from just before the walk only widen the scan.
skew=10
start=$(($(date -u +%s) - skew))
since="$(date -u -d "@$start" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -r "$start" +%Y-%m-%dT%H:%M:%SZ)"
echo "== the walk (logs since $since, ${skew} s before it)"
walk=0
docker compose exec -T -e CANARY_PASSWORD backend python deploy/canary_walk.py --url http://localhost:8000 \
    --user "$user" --out "$inside" || walk=$?
docker compose exec -T backend cat "$inside" >"$state/canaries.json"

echo
echo "== the log query: every service's log since the walk began"
sleep 2 # let the last lines reach the log driver
docker compose logs --no-color --since "$since" >"$state/logs.txt" 2>&1
echo "$(wc -l <"$state/logs.txt") lines in $state/logs.txt"
scan=0
docker compose exec -T backend python deploy/canary_scan.py --canaries "$inside" - <"$state/logs.txt" || scan=$?

echo
[ "$walk" = 0 ] && echo "PASS  the walk" || echo "FAIL  the walk"
[ "$scan" = 0 ] && echo "PASS  the log query" || echo "FAIL  the log query"
[ "$walk" = 0 ] && [ "$scan" = 0 ]
