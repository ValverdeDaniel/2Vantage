"""Django started under one environment, in its own process: `python -m backend.tests.probe <host>`.

settings.py reads the environment once, at import, so staging's settings can only be seen in a fresh process. This
runs the release gate's `check --deploy`, touches the default storage and the database settings, and serves a few
requests through the full middleware stack (no database, no network), then prints what it saw as JSON on stdout.
Log lines go to stderr, as they would on Cloud Run. Used by test_staging.py; writes only to a temporary folder.
"""

import io
import json
import os
import sys
import tempfile
from pathlib import Path

CANARY = 'probe-canary-token'
WORKER = 'assets/pdf.worker.min-Ab3dE5gH.mjs'


def built_files():
    """A stand-in for the production image's built SPA and collected static files."""
    root = Path(tempfile.mkdtemp(prefix='vantage2-probe-'))
    (root / 'spa').mkdir()
    (root / 'spa' / 'index.html').write_text('<!doctype html><div id="root"></div>')
    (root / 'static' / 'assets').mkdir(parents=True)
    (root / 'static' / WORKER).write_text('export {};')
    return root


def main(host):
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
    import django

    django.setup()
    from django.conf import settings
    from django.core.files.storage import default_storage
    from django.core.management import call_command
    from django.core.management.base import SystemCheckError
    from django.db import connection
    from django.test import Client, override_settings

    out = io.StringIO()
    try:
        call_command('check', deploy=True, fail_level='WARNING', stdout=out, stderr=out)
        clean = True
    except SystemCheckError as exc:
        clean, out = False, io.StringIO(str(exc))
    file_url = default_storage.url('deals/1/abc-Renewal (synthetic).pdf')  # builds the storage; a URL needs no network
    seen = {
        'check': {'clean': clean, 'output': out.getvalue()},
        'storage': type(default_storage._wrapped).__name__,
        'file_url': file_url,
        'database': {key: connection.settings_dict[key] for key in ('HOST', 'PORT', 'OPTIONS')},
        'whitenoise': 'whitenoise.middleware.WhiteNoiseMiddleware' in settings.MIDDLEWARE,
    }
    root = built_files()
    with override_settings(SPA_DIR=root / 'spa', STATIC_ROOT=root / 'static'):
        client, answers = Client(), {}
        for name, path, secure in (
            ('page', '/deals/12/advisor', True),
            ('page_http', '/deals/12/advisor', False),
            ('worker', f'/static/{WORKER}', True),
            ('portal_api', f'/api/portal/{CANARY}/', True),
            ('portal_page', f'/portal/{CANARY}', True),
            ('missing_api', '/api/nothing-here/', True),
        ):
            response = client.get(path, secure=secure, HTTP_HOST=host)
            answers[name] = {
                'status': response.status_code,
                'type': response.get('Content-Type', ''),
                'cache': response.get('Cache-Control', ''),
                'location': response.get('Location', ''),
            }
    seen['answers'] = answers
    print(json.dumps(seen))


if __name__ == '__main__':
    main(sys.argv[1])
