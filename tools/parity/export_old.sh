#!/usr/bin/env bash
# Export old Vantage at the commit the port follows, from git, into a folder OUTSIDE this repository (plan.md §3.4).
#
#   bash tools/parity/export_old.sh
#
# Only the folders the old app needs to run are exported, by name: the old commit also tracks meeting notes,
# reference files and client material, which must never be exported, opened or listed (CLAUDE.md rule 10).
# Never reads the old working tree (it has unrelated changes) and never writes into the old repository.
#
#   OLD_REPO           the old repository (default: ../Vantage beside this repository)
#   PARITY_COMMIT      default 891f1b3 (§13.3)
#   PARITY_EXPORT_DIR  default $LOCALAPPDATA/2vantage-parity/old-<commit>
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OLD_REPO="${OLD_REPO:-$(cd "$HERE/../../../Vantage" && pwd)}"
COMMIT="${PARITY_COMMIT:-891f1b3}"
DEST="${PARITY_EXPORT_DIR:-${LOCALAPPDATA:?set PARITY_EXPORT_DIR}/2vantage-parity/old-$COMMIT}"
if command -v cygpath >/dev/null 2>&1; then DEST="$(cygpath -u "$DEST")"; fi

# What the old app needs to run: its Django project, every app in its INSTALLED_APPS, the SPA, the stock images.
PATHS=(
  manage.py requirements.txt start.sh Dockerfile .dockerignore
  backend users notes referrals benibridge benefits commissions jointventures workflows docscan lessons reports
  reviewrequest linkguard formbuilder devtools assistant usage
  frontend assets
)
EXCLUDES=(':(exclude)devtools/e2e' ':(exclude,glob)**/CLAUDE.md')
# Tracked in the old commit, never exported (a guard in case a path above ever widens).
FORBIDDEN='^(aBenefitsMeetings|aBrotherMeetings|aPropertyCasualtyMeetings|aSecurityMeetings|referenceFiles|media)(/|$)'

archive() { git -C "$OLD_REPO" -c core.autocrlf=false archive --format=tar "$COMMIT" -- "${PATHS[@]}" "${EXCLUDES[@]}"; }

if archive | tar -t | grep -Eq "$FORBIDDEN"; then
  echo "Refusing: the export would include a forbidden folder." >&2
  exit 1
fi

case "$DEST" in
  */2vantage-parity/*) ;;
  *) echo "Refusing to clear $DEST: the export folder must sit under a 2vantage-parity folder." >&2; exit 1 ;;
esac
rm -rf "$DEST"
mkdir -p "$DEST"
archive | tar -x -C "$DEST"
# Mount points for the writable volumes, so the read-only code mount can hold them.
mkdir -p "$DEST/media" "$DEST/referenceFiles" "$DEST/staticfiles" "$DEST/frontend/node_modules"
echo "$COMMIT" > "$DEST/.parity-commit"
echo "Exported old Vantage $COMMIT to $DEST ($(find "$DEST" -type f | wc -l) files)"
