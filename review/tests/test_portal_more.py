"""The portal's other doors (plan.md §7.14, §8.20; L78, L103, L136; §12.9; Q.9 row 54): View as client for staff,
the moved page's agency, the poll's stamp, the nested allowlists, and the PHI canary through the whole flow."""

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from deals.models import Activity, AgencySettings

from .portal_world import cell, client, field, fresh, make_request, page, person, save, url, verified

pytestmark = pytest.mark.django_db

ALL = {'intake': {'scope': 'all', 'blocks': ['contacts', 'coverage', 'lines', 'bor']}, 'census': {'scope': 'all',
       'file': True}, 'documents': {'slots': ['invoice']}}  # fmt: skip
FIELD = {'key', 'label', 'type', 'options', 'hint', 'help', 'needed', 'value', 'base', 'locked', 'we_read',
         'by_colleague', 'shown', 'shown_when'}  # fmt: skip
CELL = {'column', 'label', 'type', 'group', 'group_label', 'help', 'choices', 'required', 'value', 'base',
        'by_colleague'}  # fmt: skip
PERSON = {'id', 'title', 'kind', 'employee_id', 'added', 'fields'}
DOCUMENT = {'slot', 'label', 'detail', 'accept', 'note', 'received'}


def test_L76_every_nested_part_carries_exactly_its_allowlisted_keys(user, deal):
    person(user, deal, 'Avery', 'Synthetic')
    _link, token, pin = make_request(user, deal, ALL)
    api = client()
    body = page(api, token, **verified(api, token, pin)).json()
    assert all(set(f) == FIELD for s in body['intake']['sections'] for f in s['fields'])
    blocks = body['intake']['blocks']
    assert set(blocks) == {'contacts', 'coverage', 'lines', 'bor'}
    assert set(blocks['contacts']) == {'value', 'base', 'by_colleague', 'roles'}
    assert set(blocks['coverage']) == {'value', 'base', 'by_colleague', 'lines', 'funding'}
    assert set(blocks['lines']) == {'value', 'base', 'by_colleague', 'lines', 'note'}
    assert set(blocks['bor']) == {'signed', 'name', 'signed_at', 'on_file'}
    assert all(set(p) == PERSON for p in body['people']) and all(set(c) == CELL for c in body['people'][0]['fields'])
    assert set(body['add_people']) == {'left', 'relationships'}
    assert set(body['census_file']) == {'detail', 'accept', 'received'}
    assert all(set(d) == DOCUMENT for d in body['documents'])
    assert set(body['checklist']) == {'items', 'done', 'total'}


def test_L78_view_as_client_shows_staff_the_page_and_records_nothing(user, deal, api, anon_api):
    link, _token, _pin = make_request(user, deal, ALL)
    answer = api.get(f'/api/links/{link.id}/preview/')
    assert answer.status_code == 200
    body = answer.json()
    assert (body['preview'], body['staff'], body['can_write']) == (True, True, False)
    assert fresh(link).open_count == 0
    assert anon_api.get(f'/api/links/{link.id}/preview/').status_code == 401
    assert api.get(f'/api/links/{2**64}/preview/').status_code == 404


def test_L136_the_moved_page_names_the_agency_and_takes_no_token(db):
    row = AgencySettings.get()
    row.phone, row.email = '555-0142', 'help@agency.example'
    row.save()
    answer = client().get('/api/portal/moved/')
    assert answer.status_code == 200
    assert answer.json() == {'agency': {'name': row.name, 'phone': '555-0142', 'email': 'help@agency.example'}}
    assert answer['Cache-Control'] == 'private, no-store'


def test_L103_the_stamp_reads_without_writing_and_moves_on_submit(user, deal):
    link, token, _pin = make_request(user, deal, {'intake': {'scope': 'missing'}})
    api = client()
    with CaptureQueriesContext(connection) as queries:
        first = api.get(url(token, 'stamp/')).json()
    assert not [q for q in queries.captured_queries if q['sql'].lstrip().upper().startswith(('INSERT', 'UPDATE'))]
    assert fresh(link).open_count == 0
    api.post(url(token, 'submit/'), {'answers': {}}, format='json')
    assert api.get(url(token, 'stamp/')).json()['form_stamp'] != first['form_stamp']


CANARIES = {'first': 'Zqportalia', 'last': 'Vexportal', 'city': 'Canaryportalville', 'file': 'Vexportal roster.csv'}


def test_PHI_canaries_from_the_portal_stay_out_of_activity_and_error_bodies(user, deal):
    member = person(user, deal, 'Avery', 'Synthetic')
    _link, token, pin = make_request(user, deal, ALL)
    api = client()
    headers = verified(api, token, pin)
    body = page(api, token, **headers).json()
    city = {'value': CANARIES['city'], 'base': cell(body, member.id, 'city')['base']}
    saved = save(api, token, {f'census:{member.id}:city': city}, **headers)
    assert saved.status_code == 200
    added = {'people': [{'first_name': CANARIES['first'], 'last_name': CANARIES['last']}]}
    assert api.post(url(token, 'people/'), added, format='json', **headers).status_code == 201
    from django.core.files.uploadedfile import SimpleUploadedFile

    sent = {'slot': 'census_file', 'file': SimpleUploadedFile(CANARIES['file'], b'First Name\r\nA\r\n')}
    assert api.post(url(token, 'files/'), sent, **headers).status_code == 201
    stale = save(api, token, {f'census:{member.id}:city': {'value': 'Other', 'base': 'stale'}}, **headers)
    refused = save(api, token, {f'census:{member.id}:ssn': {'value': '123-45-6789', 'base': ''}}, **headers)
    log = str(list(Activity.objects.values()))
    for canary in CANARIES.values():
        assert canary.lower() not in log.lower(), canary
        assert canary not in refused.content.decode()
    assert stale.status_code == 409 and CANARIES['first'] not in stale.content.decode()
    assert field(body, 'fein') is not None
