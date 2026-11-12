#!/usr/bin/env bash
# The Recalc lane (plan.md §12.1, §12.6; Part Q, Q.2): LibreOffice recalculates the client spreadsheets and every
# formula must give the result the app stored. Git Bash or any bash, from the repository root:
#
#   bash tools/parity/recalc.sh            TEST_DB_NAME (default test_recalc) picks the backend's test database
#
# 1. `pytest -m recalc` in the running backend builds the workbooks (GD1, one plan per rate basis, the what-if cases)
#    and writes them to /tmp/recalc-out; the backend has no LibreOffice, so its LibreOffice step skips there.
# 2. The files are copied out of the repository, to %LOCALAPPDATA%/2vantage-recalc/<time>.
# 3. tools/parity/recalc.py recalculates them in the parity tools image (headless LibreOffice, no network) and
#    compares every formula cell with its stored result; it exits 1 on any mismatch.
# Never touches the 2Vantage stack beyond `exec` and `cp`; the tools image is the parity project's (built on demand).
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
export MSYS_NO_PATHCONV=1  # keep container paths as they are under Git Bash
DB="${TEST_DB_NAME:-test_recalc}"
STAMP="$(date +%Y-%m-%dT%H-%M-%S)"
BASE="${RECALC_OUT:-${LOCALAPPDATA:-$HOME}/2vantage-recalc}"
OUT="$BASE/$STAMP"

cd "$ROOT"
echo "1/3 Writing the workbooks (pytest -m recalc, test database $DB)"
docker compose exec -T -e RECALC_EXPORT=/tmp/recalc-out -e TEST_DB_NAME="$DB" backend \
  sh -c 'rm -rf /tmp/recalc-out && pytest -m recalc -rs proposals'

echo "2/3 Copying them to $OUT"
mkdir -p "$BASE"
if command -v cygpath >/dev/null 2>&1; then
  MOUNT="$(cygpath -w "$OUT")"  # docker on Windows takes C:\… paths
else
  MOUNT="$OUT"
fi
docker compose cp backend:/tmp/recalc-out "$MOUNT"

echo "3/3 Recalculating in LibreOffice (the parity tools image)"
docker compose -p vantage-parity -f tools/parity/docker-compose.yml --profile tools run --rm \
  -v "$MOUNT:/data:ro" tools python /work/tools/parity/recalc.py /data
