"""Download each golden deal's client files from both apps (the Fidelity lane's first half; stdlib only, on the host).

Old Vantage (the parity stack, :8005) signs in with a DRF token; 2Vantage (:8004) with Django's session and CSRF, as
browser/shared/apps.mjs does. A deal is found by its client's name (the spec's `client`). Both apps' dev servers can
be reloading (other lanes edit code), so a refused connection or a 5xx is retried for a while before it counts.

    <out>/<GDn>/old.xlsx  old.pdf  old.pptx  old.letter  new.xlsx  new.pdf  new.pptx  new.letter (a PDF)
    <out>/<GDn>/fetch.json   per file: the status, the file name the app gave, or the refusal's words
"""

import http.cookiejar
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

OLD_API = os.environ.get('PARITY_OLD_API', 'http://localhost:8005')
NEW_API = os.environ.get('PARITY_NEW_API', 'http://localhost:8004')
OLD_USER = (os.environ.get('PARITY_USER', 'parity-admin'), os.environ.get('PARITY_PASSWORD', 'parity-only-pw'))
NEW_USER = (os.environ.get('LOOK_NEW_USER', 'golden-admin'), os.environ.get('LOOK_NEW_PASSWORD', 'golden-admin-pw'))
# The client files: (extension, old path, new path). Paper, the Letter PDF, is the PDF's pages on US Letter (slice 30).
FILES = (
    ('xlsx', 'presentation-workbook', 'xlsx'),
    ('pdf', 'proposal-pdf', 'pdf'),
    ('pptx', 'proposal-deck', 'pptx'),
    ('letter', 'proposal-paper', 'letter'),
)
RETRY_FOR = 90  # seconds a reloading server may take
TIMEOUT = 120


class Unreachable(Exception):
    pass


def _send(opener, request):
    """(status, headers, body); retries a refused connection and a 5xx for RETRY_FOR seconds."""
    deadline = time.monotonic() + RETRY_FOR
    while True:
        try:
            with opener.open(request, timeout=TIMEOUT) as res:
                return res.status, res.headers, res.read()
        except urllib.error.HTTPError as error:
            if error.code < 500 or time.monotonic() > deadline:
                return error.code, error.headers, error.read()
        except (urllib.error.URLError, ConnectionError, TimeoutError) as error:
            if time.monotonic() > deadline:
                raise Unreachable(f'{request.full_url}: {error}') from error
        time.sleep(3)


def _json(opener, url, data=None, headers=None):
    body = None if data is None else json.dumps(data).encode()
    request = urllib.request.Request(url, data=body, headers={'Content-Type': 'application/json', **(headers or {})})
    status, _headers, raw = _send(opener, request)
    if status >= 400:
        raise Unreachable(f'{url} answered {status}: {raw[:200]!r}')
    return json.loads(raw or b'null')


class OldApp:
    name = 'old'

    def __init__(self):
        self.opener = urllib.request.build_opener()
        login = _json(self.opener, f'{OLD_API}/api/auth/login/', {'username': OLD_USER[0], 'password': OLD_USER[1]})
        self.headers = {'Authorization': f'Token {login["token"]}'}
        self.cases = _json(self.opener, f'{OLD_API}/api/benefits/cases/', headers=self.headers)

    def deal(self, client):
        return next((row['id'] for row in self.cases if row.get('account_name') == client), None)

    def url(self, deal, kind):
        return f'{OLD_API}/api/benefits/cases/{deal}/{dict((f[0], f[1]) for f in FILES)[kind]}/'


class NewApp:
    name = 'new'

    def __init__(self):
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))
        _send(self.opener, urllib.request.Request(f'{NEW_API}/api/auth/csrf/'))
        token = next((c.value for c in self.jar if c.name == 'csrftoken'), '')
        _json(self.opener, f'{NEW_API}/api/auth/login/', {'username': NEW_USER[0], 'password': NEW_USER[1]},
              {'X-CSRFToken': token, 'Referer': NEW_API})  # fmt: skip
        self.headers = {}

    def deal(self, client):
        body = _json(self.opener, f'{NEW_API}/api/clients/?q={urllib.parse.quote(client)}')
        rows = body.get('results', body) if isinstance(body, dict) else body
        hit = next((row for row in rows if row.get('name') == client), None)
        return (hit.get('deal') or {}).get('id') if hit else None

    def url(self, deal, kind):
        return f'{NEW_API}/api/deals/{deal}/proposal/files/{dict((f[0], f[2]) for f in FILES)[kind]}/'


def _filename(headers):
    words = (headers or {}).get('Content-Disposition') or ''
    _, _, name = words.partition('filename=')
    return name.strip().strip('"') or None


def _refusal(raw):
    try:
        body = json.loads(raw)
    except ValueError:
        return raw[:200].decode('utf-8', 'replace')
    if isinstance(body, dict):
        return str(body.get('detail') or body.get('error') or body)
    return str(body)


def fetch(specs, out):
    """Download every spec's files from both apps into `out`; returns {deal key: fetch record}."""
    apps = (OldApp(), NewApp())
    done = {}
    for key, client in specs:
        folder = Path(out) / key
        folder.mkdir(parents=True, exist_ok=True)
        record = {'client': client, 'ids': {}, 'files': {}}
        for app in apps:
            deal = app.deal(client)
            record['ids'][app.name] = deal
            for kind, _old, _new in FILES:
                entry = {'status': None, 'name': None, 'refused': None}
                if deal is not None:
                    request = urllib.request.Request(app.url(deal, kind), headers=app.headers)
                    status, headers, raw = _send(app.opener, request)
                    entry['status'] = status
                    if status == 200:
                        (folder / f'{app.name}.{kind}').write_bytes(raw)
                        entry['name'] = _filename(headers)
                    else:
                        entry['refused'] = _refusal(raw)
                record['files'][f'{app.name}.{kind}'] = entry
        (folder / 'fetch.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
        done[key] = record
        print(f'{key}: old #{record["ids"]["old"]}, new #{record["ids"]["new"]} fetched', flush=True)
    return done
