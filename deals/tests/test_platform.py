"""Platform tests (plan.md §12.3): health, deploy checks, gzip, meta, the agency clock."""

from datetime import UTC, datetime
from unittest import mock

from django.core.checks import run_checks
from django.test import override_settings

from deals import clock


def test_health_ok(client, db):
    body = client.get('/api/health/').json()
    assert body['ok'] is True and body['database'] == 'ok' and body['migrations_pending'] == 0


def test_health_503_names_only_the_error_class(client, db):
    with mock.patch('backend.health.connection.cursor', side_effect=RuntimeError('secret detail')):
        response = client.get('/api/health/')
    assert response.status_code == 503
    assert response.json()['database'] == 'RuntimeError'
    assert 'secret' not in response.content.decode()


def test_deploy_checks_fire_only_in_production():
    with override_settings(ENVIRONMENT='local', DEBUG=True):
        assert not [e for e in run_checks(include_deployment_checks=True) if e.id.startswith('vantage.')]
    with override_settings(ENVIRONMENT='production', DEBUG=True, SECRET_KEY='dev-only-not-secret'):
        ids = {e.id for e in run_checks(include_deployment_checks=True)}
    assert {'vantage.E001', 'vantage.E002'} <= ids


def test_gzip_applies_to_json_only(api):
    json_response = api.get('/api/meta/', HTTP_ACCEPT_ENCODING='gzip')
    assert json_response.get('Content-Encoding') == 'gzip'


def test_meta_returns_every_vocabulary(api):
    """Membership, never counts (Q.3 #10): each section is there and carries the keys the screens use."""
    body = api.get('/api/meta/').json()
    sections = {'lines', 'tiers', 'stages', 'relationships', 'funding', 'document_kinds', 'document_roles', 'plans'}
    assert sections | {'carriers'} <= set(body)
    assert {'medical', 'dental', 'vision'} <= {line['key'] for line in body['lines']}
    assert {'rate_ee', 'deductible_single', 'funding'} <= {field['key'] for field in body['plans']['fields']}
    medical_fields = [k for g in body['plans']['line_groups']['medical'] for k in g['fields']]
    assert 'funding' in medical_fields and 'unit_rate' not in medical_fields


def test_CL9_meta_serves_the_three_statuses_and_the_carriers_with_aliases(api):
    body = api.get('/api/meta/').json()
    assert body['relationships'] == [
        {'key': 'prospect', 'label': 'Prospect', 'create': True},
        {'key': 'new_client', 'label': 'New client', 'create': False},  # only a sale or Convert to client (CL6)
        {'key': 'existing_client', 'label': 'Existing client', 'create': True},
    ]
    uhc = next(carrier for carrier in body['carriers'] if carrier['key'] == 'unitedhealthcare')
    assert uhc == {'key': 'unitedhealthcare', 'name': 'UnitedHealthcare', 'group': 'medical', 'aliases': uhc['aliases']}
    assert 'UHC' in uhc['aliases']


@override_settings(AGENCY_TIME_ZONE='America/New_York')
def test_today_is_the_agencys_date_not_utcs():
    nine_pm_eastern = datetime(2026, 11, 11, 2, 0, tzinfo=UTC)  # 21:00 on the 10th in New York
    with mock.patch.object(clock, 'now', return_value=nine_pm_eastern):
        assert clock.today().isoformat() == '2026-11-10'
