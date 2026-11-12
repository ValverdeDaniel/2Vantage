"""The log query of the staging canary scan (slice 47; plan.md §11.4 item 5, §12.9; Q.8; deploy/phi-gate.md).

After the walk (deploy/canary_walk.py), no log of the deployment may hold one of the run's canaries: not a request
line (a URL), not an error report, not a worker or database message. Feed it every log since the walk began:

    python deploy/canary_scan.py --canaries canaries.json <log file>...      (- reads standard input)
    # staging: every log of the project since the walk started, as JSON (Cloud Run's web and worker services and
    # their request logs, the jobs, Cloud SQL, audit logs), once Cloud Logging has caught up (a minute or two):
    gcloud logging read "timestamp>=\"<started_at>\"" --project=<PROJECT_ID> --format=json > staging-logs.json
    # the dev stack: deploy/canary_scan.sh (docker compose logs of every service since the walk)

Case is ignored; a canary also counts URL-encoded or JSON-escaped (deploy/canaries.py). It prints each canary field
found, how often, and the first lines holding it (synthetic, so safe to show), and exits 1 if one is found, or if the
logs do not even show the walk's requests (a scan of the wrong logs proves nothing). Standard library only.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import canaries as made  # noqa: E402

WALKED = '/census/imports/'  # a path every walk requests: the logs must show it, or they are not this deployment's
SHOWN = 3


def lines_of(paths):
    for path in paths:
        handle = sys.stdin if path == '-' else open(path, encoding='utf-8', errors='replace')  # noqa: SIM115
        with handle:
            yield from ((path, number, line.rstrip('\n')) for number, line in enumerate(handle, 1))


def scan(lines, searched):
    """({field: [(source, line number, text)]}, lines read, whether the walk's requests show)."""
    found, count, walked = {}, 0, False
    for source, number, text in lines:
        count += 1
        lower = text.lower()
        walked = walked or WALKED in lower
        for field, forms in searched.items():
            if any(form in lower for form in forms):
                found.setdefault(field, []).append((source, number, text))
    return found, count, walked


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--canaries', required=True, help="the walk's --out file")
    parser.add_argument('logs', nargs='+', help='log files (- for standard input)')
    args = parser.parse_args()
    canaries = made.load(args.canaries)
    found, count, walked = scan(lines_of(args.logs), made.searched(canaries))
    print(f'Canary run {canaries["run"]} (walk started {canaries["started_at"]}): {count} log lines scanned.')
    failed = False
    if not walked:
        print(f'FAIL  the logs show the walk ("{WALKED}" never appears): query the logs since the walk started')
        failed = True
    for field in made.searched(canaries):
        hits = found.get(field, [])
        print(f'{"FAIL" if hits else "PASS"}  {field}{f": in {len(hits)} line(s)" if hits else ""}')
        for source, number, text in hits[:SHOWN]:
            print(f'        {source}:{number}: {text[:300]}')
        failed = failed or bool(hits)
    print('Canary scan: a canary reached the logs.' if found else 'Canary scan: no canary in the logs.')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
