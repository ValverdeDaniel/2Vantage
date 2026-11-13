#!/usr/bin/env bash
# Everyday commands for old Vantage beside 2Vantage (plan.md §12.7; README.md in this folder). Git Bash or any bash.
#
#   bash tools/parity/parity.sh export        export 891f1b3 from git into the export folder (outside the repo)
#   bash tools/parity/parity.sh up            build and start the project, wait for the old API
#   bash tools/parity/parity.sh load [GD1,…]  load the golden specs and variants into the old app (default: all)
#   bash tools/parity/parity.sh tools <cmd>   run a command in the tools image (no network)
#   bash tools/parity/parity.sh down          stop it (keeps its database)
#   bash tools/parity/parity.sh reset         stop it and drop its database and media volumes
#
# Never touches the 2Vantage project's containers: every command names this compose file and its project.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE=(docker compose -p vantage-parity -f "$HERE/docker-compose.yml")
export MSYS_NO_PATHCONV=1  # keep container paths as they are under Git Bash
API="http://localhost:${PARITY_API_PORT:-8005}"

wait_for_api() {
  for _ in $(seq 1 120); do
    if [ "$(curl -s -m 3 -o /dev/null -w '%{http_code}' "$API/api/health/")" = 200 ]; then
      echo "Old Vantage answers at $API (frontend http://localhost:4002)"
      return 0
    fi
    sleep 3
  done
  echo "Old Vantage did not answer at $API; see: ${COMPOSE[*]} logs backend" >&2
  return 1
}

# The golden variants (golden/variants/*.json; GD1-sold, slice 67) as one JSON array: only the specs are mounted.
variants_json() {
  local first=1
  printf '['
  for file in "$HERE/../../golden/variants/"*.json; do
    [ -e "$file" ] || continue
    [ "$first" = 1 ] || printf ','
    first=0
    cat "$file"
  done
  printf ']'
}

case "${1:-}" in
  export) bash "$HERE/export_old.sh" ;;
  up) "${COMPOSE[@]}" up -d --build && wait_for_api ;;
  load)
    "${COMPOSE[@]}" exec -T -e PARITY_DEALS="${2:-}" -e PARITY_VARIANTS_JSON="$(variants_json)" backend \
      python manage.py shell -c "exec(open('/parity/old_loader.py').read())"
    ;;
  tools) shift; "${COMPOSE[@]}" --profile tools run --rm tools "$@" ;;
  down) "${COMPOSE[@]}" down ;;
  reset) "${COMPOSE[@]}" down -v ;;
  *) sed -n '2,11p' "$0"; exit 2 ;;
esac
