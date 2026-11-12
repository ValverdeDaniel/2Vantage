"""The release gate (plan.md §11.3): run after the migrations job, whose first step is the same `check --deploy`
(start.sh migrate), and before Daniel calls a release done.

    python deploy/release_gate.py --url https://<web service URL> --commit <full commit SHA>
    # inside the production image, with the deployment's environment (the local rehearsal, deploy/rehearse.sh):
    python deploy/release_gate.py --url http://web:8080 --commit <sha> --forwarded-proto https --check-deploy

It passes when `manage.py check --deploy` is clean (with --check-deploy); /api/health/ names the commit with no pending
migrations; the SPA answers its page paths and leaves /api/ to Django; WhiteNoise serves the hashed assets for good
and pdf.js's `.mjs` worker as JavaScript (E.6); a client link's page keeps its token to itself (§3.8); and the
security headers are on. Standard library only. Exit 0 when every check passes.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from http_client import Checks, Client  # noqa: E402

JS_TYPES = ('text/javascript', 'application/javascript')
ASSET = r'[A-Za-z0-9_.-]+-[A-Za-z0-9_-]{8}\.m?js'  # a Vite chunk or module, by its hashed name
CANARY = 'release-gate-canary-token'  # requested on the token paths; it must never reach a log (rehearse.sh)


def check_deploy(checks):
    run = subprocess.run(
        [sys.executable, 'manage.py', 'check', '--deploy', '--fail-level', 'WARNING'], capture_output=True, text=True
    )
    lines = (run.stdout + run.stderr).strip().splitlines()
    checks.check('manage.py check --deploy is clean', run.returncode == 0, lines[-1] if lines else '')


def check_health(checks, client, commit):
    health = client.get('/api/health/')
    body = health.json() if health.status in (200, 503) else {}
    checks.check(
        '/api/health/ answers 200, database ok', health.status == 200 and body.get('ok') is True, health.text()
    )
    checks.check('/api/health/ names the commit', body.get('commit') == commit, f'{body.get("commit")} vs {commit}')
    checks.check('no migration is pending', body.get('migrations_pending') == 0, str(body.get('migrations_pending')))


def check_spa(checks, client):
    """Returns the asset paths the SPA's index.html names."""
    assets = []
    for path in ('/', '/deals/1/advisor', '/login'):
        page = client.get(path)
        is_spa = (
            page.status == 200 and page.header('Content-Type').startswith('text/html') and 'id="root"' in page.text()
        )
        checks.check(f'{path} answers the SPA', is_spa, f'{page.status} {page.header("Content-Type")}')
        checks.check(f'{path} is asked for again on each visit', 'no-cache' in page.header('Cache-Control'))
        assets = assets or re.findall(r'(?:src|href)="(/static/assets/[^"]+)"', page.text())
        if path == '/':
            hsts = page.header('Strict-Transport-Security')
            checks.check('HSTS is on', 'max-age=' in hsts, hsts)
            checks.check('nosniff is on', page.header('X-Content-Type-Options') == 'nosniff')
            checks.check('frames are refused', page.header('X-Frame-Options') == 'DENY')
    api = client.get('/api/auth/me/')
    checks.check('/api/ stays with Django (signed out: 401)', api.status == 401, str(api.status))
    return assets


def find_workers(client, entry, limit=200):
    """The `.mjs` files the SPA's chunks name: the entry names the lazy chunks (tabs, then each tab's), and the
    viewer's chunk names pdf.js's worker. Breadth-first over Vite's hashed names, at most `limit` fetches."""
    queue, seen, workers = list(entry), set(entry), set()
    while queue and len(seen) <= limit:
        chunk = client.get(f'/static/assets/{queue.pop(0)}')
        if chunk.status != 200:
            continue
        for name in re.findall(ASSET, chunk.text()):
            if name.endswith('.mjs'):
                workers.add(name)
            elif name not in seen:
                seen.add(name)
                queue.append(name)
    return workers


def check_assets(checks, client, assets):
    scripts = [path for path in assets if path.endswith('.js')]
    checks.check('index.html names its script under /static/assets/', bool(scripts), ', '.join(assets))
    for path in scripts:
        script = client.get(path)
        checks.check(f'{path} is JavaScript', script.header('Content-Type').startswith(JS_TYPES))
        checks.check(f'{path} is cached for good', 'immutable' in script.header('Cache-Control'))
    workers = find_workers(client, [path.rsplit('/', 1)[-1] for path in scripts])
    checks.check("the SPA names pdf.js's .mjs worker", bool(workers), ', '.join(sorted(workers)))
    for name in sorted(workers):
        module = client.get(f'/static/assets/{name}')
        kind = module.header('Content-Type')
        checks.check(f'{name} is served as JavaScript', module.status == 200 and kind.startswith(JS_TYPES), kind)


def check_token_pages(checks, client):
    page = client.get(f'/portal/{CANARY}')
    checks.check('a client link page keeps no Referer', page.header('Referrer-Policy') == 'no-referrer')
    checks.check('a client link page is never stored', 'no-store' in page.header('Cache-Control'))
    checks.check('a client link page is not indexed', page.header('X-Robots-Tag') == 'noindex')
    client.get(f'/api/portal/{CANARY}/')  # a 404 until slice 54; either way its path must not be logged


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--url', required=True, help='the web service, e.g. https://vantage-web-…run.app')
    parser.add_argument('--commit', required=True, help='the commit the image was built from (GIT_SHA)')
    parser.add_argument('--forwarded-proto', help='send X-Forwarded-Proto, as Cloud Run does (local rehearsal)')
    parser.add_argument('--check-deploy', action='store_true', help='also run manage.py check --deploy (in the image)')
    args = parser.parse_args()
    checks, client = Checks(), Client(args.url, args.forwarded_proto)
    if args.check_deploy:
        check_deploy(checks)
    check_health(checks, client, args.commit)
    check_assets(checks, client, check_spa(checks, client))
    check_token_pages(checks, client)
    return checks.done('Release gate')


if __name__ == '__main__':
    sys.exit(main())
