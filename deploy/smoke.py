"""The smoke check (slice 69; deploy/README.md): a person's first minute, scripted, on synthetic data only.

    SMOKE_PASSWORD=… python deploy/smoke.py --url https://<web service URL> --user <staff username>
    # the local rehearsal, inside the production image (deploy/rehearse.sh):
    SMOKE_PASSWORD=… python deploy/smoke.py --url http://web:8080 --user rehearsal-admin --forwarded-proto https

It signs in, opens GD1's Advisor (its page and its plans), uploads a synthetic PDF to GD1 through the app (stored by
whatever storage the settings chose: the filesystem locally, the private bucket on Cloud Run), downloads it back
byte for byte, runs "Check this file" on it in the worker service, then removes the file (an admin purges it; anyone
else archives it). Run it from the repository root or the image's /app: it borrows the root's synthetic_files.py.
"""

import argparse
import os
import sys
import time
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT), str(ROOT.parent)]
from http_client import Checks, Client  # noqa: E402

import synthetic_files  # noqa: E402

GD1 = 'Golden Manufacturing (synthetic)'
FINISHED = ('done', 'failed', 'cancelled')


def sign_in(checks, client, user, password):
    client.get('/api/auth/csrf/')
    signed = client.post_json('/api/auth/login/', {'username': user, 'password': password})
    checks.check(f'{user} signs in', signed.status == 200, str(signed.status))
    return signed.json() if signed.status == 200 else {}


def open_advisor(checks, client, name):
    rows = client.get(f'/api/clients/?q={quote(name)}')
    found = [row for row in rows.json().get('results', []) if row['name'] == name] if rows.status == 200 else []
    if not checks.check(f'{name} is listed', bool(found), '' if found else f'{rows.status}; run seed_golden first'):
        return None
    deal_id = found[0]['deal']['id']
    page = client.get(f'/deals/{deal_id}/advisor')
    checks.check("GD1's Advisor page opens", page.status == 200 and 'id="root"' in page.text(), str(page.status))
    # What the Advisor asks for: its lines, then the first line's plans side by side.
    lines = client.get(f'/api/deals/{deal_id}/plans/lines/')
    line = lines.json()[0]['line'] if lines.status == 200 and lines.json() else ''
    checks.check("GD1's Advisor lists its lines", bool(line), str(lines.status))
    plans = client.get(f'/api/deals/{deal_id}/plans/?line={line}')
    checks.check(
        f"GD1's Advisor shows its {line} plans", plans.status == 200 and len(plans.body) > 2, str(plans.status)
    )
    return deal_id


def upload_and_download(checks, client, deal_id):
    content = synthetic_files.pdf([[(72, 720, 'Smoke check (synthetic): no member data', 14)]])
    sent = client.post_file(
        f'/api/deals/{deal_id}/documents/', {'kind': 'quote'}, 'Smoke check (synthetic).pdf', content, 'application/pdf'
    )
    uploaded = sent.status == 201
    if not checks.check('a synthetic PDF uploads through the app', uploaded, '' if uploaded else sent.text()[:300]):
        return None
    document = sent.json()
    back = client.get(f'/api/documents/{document["id"]}/download/')
    checks.check('it downloads through the app, byte for byte', back.status == 200 and back.body == content)
    checks.check('the download is an attachment', back.header('Content-Disposition').startswith('attachment'))
    checks.check('the download is never cached', 'no-store' in back.header('Cache-Control'))
    return document


def check_in_worker(checks, client, deal_id, document_id, wait):
    started = client.post_json(f'/api/deals/{deal_id}/ai/locate/', {'document_ids': [document_id]})
    if not checks.check('"Check this file" starts a job', started.status in (200, 201), str(started.status)):
        return
    job, deadline = started.json(), time.monotonic() + wait
    while job.get('status') not in FINISHED and time.monotonic() < deadline:
        time.sleep(1)
        job = client.get(f'/api/ai/jobs/{job["id"]}/').json()
    checks.check('the worker service runs it to the end', job.get('status') == 'done', str(job.get('status')))


def remove(checks, client, document_id, is_admin):
    gone = client.request('DELETE', f'/api/documents/{document_id}/') if is_admin else None
    if gone is None or gone.status != 204:
        gone = client.request('POST', f'/api/documents/{document_id}/archive/')
    checks.check('the smoke file is removed', gone.status in (200, 204), str(gone.status))
    if is_admin:
        after = client.get(f'/api/documents/{document_id}/download/')
        checks.check('its bytes are gone from storage', after.status == 404, str(after.status))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--url', required=True)
    parser.add_argument('--user', required=True, help='a staff username; the password comes from SMOKE_PASSWORD')
    parser.add_argument('--client', default=GD1, help=f'the golden client to open (default: {GD1})')
    parser.add_argument('--forwarded-proto', help='send X-Forwarded-Proto, as Cloud Run does (local rehearsal)')
    parser.add_argument('--wait', type=int, default=120, help='seconds to wait for the worker (default 120)')
    args = parser.parse_args()
    checks, client = Checks(), Client(args.url, args.forwarded_proto)
    me = sign_in(checks, client, args.user, os.environ.get('SMOKE_PASSWORD', ''))
    deal_id = open_advisor(checks, client, args.client) if me else None
    document = upload_and_download(checks, client, deal_id) if deal_id else None
    if document:
        check_in_worker(checks, client, deal_id, document['id'], args.wait)
        remove(checks, client, document['id'], bool(me.get('is_admin')))
    client.request('POST', '/api/auth/logout/')
    return checks.done('Smoke check')


if __name__ == '__main__':
    sys.exit(main())
