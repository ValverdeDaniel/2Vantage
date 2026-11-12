"""Slice 69 STG-1: staging's settings, the release gate and production serving (plan.md §11, §3.5; Q.9 row 69).

Staging's settings are read from the environment once, at import. The tests that need a running Django start one in
a fresh process (probe.py) with staging's variables, as Cloud Run would, and read back what it did; the ones that
need only the settings execute settings.py afresh under a patched environment. Nothing here reaches Google or any
network: the bucket is named, never called.
"""

import json
import logging
import os
import runpy
import secrets
import subprocess
import sys
from datetime import timedelta
from types import SimpleNamespace

import pytest
from django.conf import settings
from django.core.checks import run_checks
from django.core.files.storage import FileSystemStorage, default_storage
from django.test import override_settings

from backend.logs import DropTokenPaths

HOST = 'vantage-web-staging.example.run.app'
# What deploy/cloudrun/app-env.yaml gives every service and job (secrets as Secret Manager passes them), synthetic.
STAGING = {
    'ENVIRONMENT': 'production',
    'DJANGO_DEBUG': 'False',
    'DJANGO_SECRET_KEY': secrets.token_urlsafe(50),
    'ALLOWED_HOSTS': HOST,
    'FRONTEND_URL': f'https://{HOST}',
    'GIT_SHA': '0123456789abcdef0123456789abcdef01234567',
    'DB_NAME': 'vantage2',
    'DB_USER': 'vantage',
    'DB_PASSWORD': 'synthetic-not-secret',
    'DB_HOST': '10.20.0.3',
    'DB_SSLMODE': 'verify-ca',
    'DB_SSLROOTCERT': '/secrets/db/server-ca.pem',
    'GS_BUCKET_NAME': 'vantage-staging-files',
    'EMAIL_HOST': 'smtp.example.com',
    'EMAIL_HOST_USER': 'mailer@example.com',
    'EMAIL_HOST_PASSWORD': 'synthetic-not-secret',
    'K_SERVICE': 'vantage-web',
}
CARRIED = ('PATH', 'HOME', 'LANG', 'LC_ALL', 'PYTHONDONTWRITEBYTECODE', 'PYTHONUNBUFFERED')


def probe(env, host):
    """(what Django did, its log lines) under exactly this environment."""
    carried = {name: os.environ[name] for name in CARRIED if name in os.environ}
    run = subprocess.run(
        [sys.executable, '-m', 'backend.tests.probe', host],
        env={**carried, **env},
        cwd=settings.BASE_DIR,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert run.returncode == 0, run.stderr
    return json.loads(run.stdout.strip().splitlines()[-1]), run.stderr


@pytest.fixture(scope='module')
def staging():
    return probe(STAGING, HOST)


def test_STG1_the_release_gate_passes_with_staging_settings(staging):
    seen, _ = staging
    assert seen['check']['clean'], seen['check']['output']
    assert 'no issues' in seen['check']['output']


def test_STG1_staging_keeps_files_in_the_private_bucket_and_hands_out_no_link(staging):
    seen, _ = staging
    assert seen['storage'] == 'PrivateBucket'
    assert seen['file_url'] == '/media-not-served/deals/1/abc-Renewal%20(synthetic).pdf'  # never a signed link


def test_STG1_local_runs_keep_the_filesystem_and_never_load_google(client):
    # This process runs local settings: the storage is built and a request served, and Google's libraries stay out.
    default_storage.url('deals/1/abc-Renewal.pdf')
    client.get('/api/nothing-here/')
    assert isinstance(default_storage._wrapped, FileSystemStorage)
    assert 'whitenoise.middleware.WhiteNoiseMiddleware' not in settings.MIDDLEWARE
    assert 'storages.backends.gcloud' not in sys.modules and 'google.cloud.storage' not in sys.modules


def test_STG1_staging_reaches_cloud_sql_privately_and_verifies_its_certificate(staging):
    database = staging[0]['database']
    assert database['HOST'] == '10.20.0.3'
    assert database['OPTIONS'] == {'sslmode': 'verify-ca', 'sslrootcert': '/secrets/db/server-ca.pem'}


def settings_under(monkeypatch, **env):
    """settings.py's names, executed afresh under this environment (on top of the dev stack's)."""
    for name in ('GS_BUCKET_NAME', 'CLOUD_SQL_INSTANCE', 'DB_SSLMODE', 'DB_SSLROOTCERT', 'K_SERVICE', 'CLOUD_RUN_JOB'):
        monkeypatch.delenv(name, raising=False)
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    return runpy.run_path(str(settings.BASE_DIR / 'backend' / 'settings.py'))


def test_STG1_cloud_sql_through_its_socket_when_the_instance_is_named(monkeypatch):
    named = settings_under(monkeypatch, CLOUD_SQL_INSTANCE='vantage-staging:us-east1:vantage-db')
    assert named['DATABASES']['default']['HOST'] == '/cloudsql/vantage-staging:us-east1:vantage-db'
    assert named['DATABASES']['default']['PORT'] == ''
    assert 'OPTIONS' not in settings_under(monkeypatch)['DATABASES']['default']


def test_STG1_a_bucket_name_alone_moves_the_files_to_the_private_bucket(monkeypatch):
    bucket = settings_under(monkeypatch, GS_BUCKET_NAME='vantage-staging-files')['STORAGES']['default']
    assert bucket['BACKEND'] == 'backend.storage.PrivateBucket'
    assert bucket['OPTIONS'] == {'bucket_name': 'vantage-staging-files', 'default_acl': None, 'file_overwrite': False}
    unnamed = settings_under(monkeypatch)
    assert unnamed['STORAGES']['default']['BACKEND'] == 'django.core.files.storage.FileSystemStorage'
    assert not unnamed['ON_CLOUD_RUN'] and settings_under(monkeypatch, CLOUD_RUN_JOB='vantage-migrate')['ON_CLOUD_RUN']


def test_STG1_whitenoise_serves_the_pdf_worker_as_javascript_for_good(staging):
    worker = staging[0]['answers']['worker']
    assert worker['status'] == 200
    assert worker['type'].startswith('text/javascript')
    assert 'immutable' in worker['cache']


def test_STG1_staging_answers_the_spa_and_moves_plain_http_to_https(staging):
    answers = staging[0]['answers']
    assert answers['page']['status'] == 200 and answers['page']['type'].startswith('text/html')
    assert answers['page_http']['status'] == 301
    assert answers['page_http']['location'] == f'https://{HOST}/deals/12/advisor'


def test_STG1_token_paths_never_reach_staging_logs(staging):
    seen, logged = staging
    assert seen['answers']['portal_api']['status'] == 404  # logged by Django as "Not Found", then dropped
    assert 'probe-canary-token' not in logged
    assert 'Not Found: /api/nothing-here/' in logged  # other requests still log


def test_STG1_the_log_filter_drops_records_about_token_paths():
    keep = DropTokenPaths().filter

    def record(message, *args, path=None):
        entry = logging.LogRecord('django.request', logging.WARNING, __file__, 1, message, args, None)
        if path:
            entry.request = SimpleNamespace(path=path)
        return entry

    assert not keep(record('Not Found: %s', '/api/portal/tok-1/'))
    assert not keep(record('Internal Server Error: %s', '/b/tok-2'))
    assert not keep(record('Forbidden (CSRF cookie not set.)', path='/portal/tok-3'))
    assert keep(record('Not Found: %s', '/api/deals/7/'))
    assert keep(record('Not Found: %s', '/api/deals/7/b/'))  # "/b/" inside another path is not the token path


def test_STG1_gunicorn_logs_no_request_on_or_from_a_token_page():
    from gunicorn.config import Config

    from backend.gunicorn_log import TokenSafeLogger

    config = Config()
    config.set('accesslog', '-')
    log = TokenSafeLogger(config)
    lines = []
    collector = logging.Handler()
    collector.emit = lambda entry: lines.append(entry.getMessage())
    log.access_log.addHandler(collector)
    try:
        for path, referer in (
            ('/api/health/', ''),
            ('/api/portal/tok-1/', ''),
            ('/portal/tok-2', ''),
            ('/static/assets/index-Ab3dE5gH.js', f'https://{HOST}/portal/tok-3'),
        ):
            environ = {
                'REQUEST_METHOD': 'GET',
                'RAW_URI': path,
                'PATH_INFO': path,
                'QUERY_STRING': '',
                'SERVER_PROTOCOL': 'HTTP/1.1',
                'HTTP_REFERER': referer,
            }
            log.access(
                SimpleNamespace(status='200 OK', sent=5, headers=[]),
                SimpleNamespace(headers=[]),
                environ,
                timedelta(milliseconds=3),
            )
    finally:
        log.access_log.removeHandler(collector)
    assert any('GET /api/health/' in line for line in lines)
    assert not any('tok-' in line for line in lines)


def test_STG1_cloud_run_without_a_bucket_fails_the_gate():
    def ids():
        return {check.id for check in run_checks(include_deployment_checks=True)}

    with override_settings(ENVIRONMENT='production', ON_CLOUD_RUN=True, GS_BUCKET_NAME=''):
        assert 'vantage.E005' in ids()
    with override_settings(ENVIRONMENT='production', ON_CLOUD_RUN=True, GS_BUCKET_NAME='vantage-staging-files'):
        assert 'vantage.E005' not in ids()
    with override_settings(ENVIRONMENT='production', ON_CLOUD_RUN=False, GS_BUCKET_NAME=''):
        assert 'vantage.E005' not in ids()  # the local rehearsal keeps its files on a volume


@pytest.fixture
def built_spa(settings, tmp_path):
    (tmp_path / 'index.html').write_text('<!doctype html><div id="root"></div>')
    settings.SPA_DIR = tmp_path
    return tmp_path


@pytest.mark.parametrize('path', ['/', '/login', '/deals/12/advisor', '/deals/12/documents/4/window'])
def test_STG1_every_page_path_answers_the_built_spa(client, built_spa, path):
    page = client.get(path)
    assert page.status_code == 200 and b'id="root"' in page.content
    assert page['Content-Type'].startswith('text/html') and page['Cache-Control'] == 'no-cache'


def test_STG1_the_spa_leaves_django_its_paths(client, built_spa):
    assert b'id="root"' not in client.get('/api/nothing-here/').content
    assert client.get('/api/nothing-here/').status_code == 404
    assert client.get('/admin').status_code == 301  # Django's own slash, not the SPA
    assert client.get('/static/assets/missing-Ab3dE5gH.js').status_code == 404
    assert client.post('/deals/12/advisor').status_code == 405


def test_STG1_a_client_link_page_keeps_its_token_to_itself(client, built_spa):
    page = client.get('/portal/tok-7')
    assert page['Referrer-Policy'] == 'no-referrer'
    assert page['Cache-Control'] == 'private, no-store' and page['X-Robots-Tag'] == 'noindex'


def test_STG1_no_built_spa_answers_404(client, settings, tmp_path):
    settings.SPA_DIR = tmp_path / 'not-built'
    assert client.get('/deals/12/advisor').status_code == 404


def test_STG1_gd1_opens_on_the_built_spa_and_health_names_the_commit(api, gd1, built_spa, settings):
    settings.GIT_SHA = STAGING['GIT_SHA']
    assert api.get(f'/deals/{gd1.deal.id}/advisor').status_code == 200
    plans = api.get(f'/api/deals/{gd1.deal.id}/plans/?line=medical')
    assert plans.status_code == 200 and plans['Content-Type'].startswith('application/json')
    health = api.get('/api/health/').json()
    assert health['commit'] == STAGING['GIT_SHA'] and health['migrations_pending'] == 0
