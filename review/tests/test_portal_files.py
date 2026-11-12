"""What a client adds through their link (plan.md §7.14; L86, L90, L93, L94; C35; B3, B12, B22; OQ86; Q.9 row 54):
files through the one upload door with their slot, only for slots the link asks, named back only when they came
through the request; the blank census template; people who wait whole; the BOR signature with its IP."""

import io

import openpyxl
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from census.models import CensusFacts, Member
from deals.models import Activity
from documents import services as documents
from intake.models import Intake
from synthetic_files import text_pdf

from .portal_world import client, fresh, make_request, page, person, url, verified

pytestmark = pytest.mark.django_db

CSV = b'First Name,Last Name,DOB\r\nRowan,Synthetic,01/02/1980\r\n'


def _send(api, token, slot, name, content, **headers):
    return api.post(url(token, 'files/'), {'slot': slot, 'file': SimpleUploadedFile(name, content)}, **headers)


def test_L94_the_census_file_goes_through_the_upload_door_with_its_slot(user, deal):
    link, token, _pin = make_request(user, deal, {'census': {'file': True}})
    assert link.security == 'link'  # upload-only asks need no PIN (OQ80)
    api = client()
    answer = _send(api, token, 'census_file', 'Rowan census.csv', CSV)
    assert answer.status_code == 201, answer.content
    assert answer.json()['received'][0]['name'] == 'Rowan census.csv'
    document = deal.documents.get()
    stored = (document.kind, document.source, document.link_id, document.slot)
    assert stored == ('census', 'client', link.id, 'census_file')
    assert document.screen  # the member-data screen ran (B12)
    assert fresh(link).last_saved_at is not None
    row = Activity.objects.get(area='documents', action='created')
    assert row.actor_kind == 'client' and 'Rowan' not in row.summary
    assert page(api, token).json()['census_file']['received'][0]['name'] == 'Rowan census.csv'


def test_B12_a_file_whose_bytes_are_not_what_its_name_says_is_refused(user, deal):
    _link, token, _pin = make_request(user, deal, {'census': {'file': True}})
    answer = _send(client(), token, 'census_file', 'roster.xlsx', b'not a workbook at all')
    assert answer.status_code == 400
    assert not deal.documents.exists()


def test_L93_a_slot_the_link_does_not_ask_is_refused(user, deal):
    _link, token, _pin = make_request(user, deal, {'documents': {'slots': ['invoice@medical']}})
    api = client()
    refused = _send(api, token, 'claims', 'claims.pdf', text_pdf('Claims (synthetic)'))
    assert refused.status_code == 400 and not deal.documents.exists()
    taken = _send(api, token, 'invoice@medical', 'invoice.pdf', text_pdf('Invoice (synthetic)'))
    assert taken.status_code == 201
    document = deal.documents.get()
    assert (document.kind, document.lines, document.slot) == ('invoice', ['medical'], 'invoice@medical')


def test_B22_the_page_names_only_files_that_came_through_its_request(user, deal):
    documents.upload(user, deal, SimpleUploadedFile('staff invoice.pdf', text_pdf('Staff (synthetic)')),
                     {'kind': 'invoice'})  # fmt: skip
    _link, token, _pin = make_request(user, deal, {'documents': {'slots': ['invoice']}})
    api = client()
    body = page(api, token).json()
    assert body['documents'][0]['received'] == [] and 'staff invoice' not in str(body)
    _send(api, token, 'invoice', 'our invoice.pdf', text_pdf('Client (synthetic)'))
    names = [entry['name'] for entry in page(api, token).json()['documents'][0]['received']]
    assert names == ['our invoice.pdf']
    assert 'id' not in page(api, token).json()['documents'][0]['received'][0]


def test_B3_the_census_template_on_a_link_is_always_blank(user, deal):
    person(user, deal, 'Avery', 'Synthetic', dob='1980-01-02')
    _link, token, _pin = make_request(user, deal, {'census': {'file': True}})
    answer = client().get(url(token, 'census-template/'))
    assert answer.status_code == 200 and answer['Cache-Control'] == 'private, no-store'
    book = openpyxl.load_workbook(io.BytesIO(b''.join(answer.streaming_content)))
    sheet = book['Census']
    assert sheet.max_row == 1  # the header row only
    assert 'Avery' not in str([cell.value for row in sheet.iter_rows() for cell in row])
    assert not Activity.objects.filter(action='downloaded').exists()


def test_L90_added_people_wait_whole_and_hide_from_every_read(user, deal):
    employee = person(user, deal, 'Avery', 'Synthetic')
    link, token, pin = make_request(user, deal, {'census': {'scope': 'missing'}})
    api = client()
    headers = verified(api, token, pin)
    sent = [
        {'kind': 'employee', 'first_name': 'Rowan', 'last_name': 'Newhire'},
        {'kind': 'dependent', 'first_name': 'Sky', 'last_name': 'Synthetic', 'employee_id': employee.id,
         'relationship': 'Child', 'dob': '3/4/2015'},
    ]  # fmt: skip
    answer = api.post(url(token, 'people/'), {'people': sent}, format='json', **headers)
    assert answer.status_code == 201, answer.content
    made = answer.json()['people']
    assert {entry['title'] for entry in made} == {'Rowan Newhire', 'Sky Synthetic'}
    assert all(entry['added'] for entry in made)
    assert Member.objects.filter(deal=deal).count() == 1  # the default manager hides them (Ch. 12)
    waiting = Member.all_objects.filter(deal=deal, added_by_link=link.id)
    assert waiting.count() == 2 and all(m.client['*']['status'] == 'pending' for m in waiting)
    assert CensusFacts.objects.get(deal=deal).pending_people == 2
    row = Activity.objects.get(action='client_added')
    assert row.summary == 'Client added 2 people to the census' and 'Rowan' not in str(row.changes)
    titles = [entry['title'] for entry in page(api, token, **headers).json()['people']]
    assert titles[:2] == ['Avery Synthetic', 'Sky Synthetic'] and 'Rowan Newhire' in titles


def test_L90_names_are_required_and_a_dependent_needs_an_employee_here(user, deal):
    _link, token, pin = make_request(user, deal, {'census': {'scope': 'all'}})
    api = client()
    headers = verified(api, token, pin)
    nameless = api.post(url(token, 'people/'), {'people': [{'first_name': 'Only'}]}, format='json', **headers)
    assert nameless.status_code == 400
    orphan = [{'kind': 'dependent', 'first_name': 'A', 'last_name': 'B', 'employee_id': 999999}]
    assert api.post(url(token, 'people/'), {'people': orphan}, format='json', **headers).status_code == 400
    assert not Member.all_objects.filter(deal=deal).exists()


def test_L90_a_file_only_ask_adds_nobody(user, deal):
    _link, token, _pin = make_request(user, deal, {'census': {'file': True}})
    sent = {'people': [{'first_name': 'A', 'last_name': 'B'}]}
    assert client().post(url(token, 'people/'), sent, format='json').status_code == 400


def test_L86_OQ86_the_bor_signature_keeps_its_link_ip_and_browser(user, deal):
    link, token, _pin = make_request(user, deal, {'intake': {'scope': 'selected', 'keys': ['fein'], 'blocks': ['bor']}})
    api = client()
    signed = {'name': 'Jordan Example'}
    answer = api.post(url(token, 'sign/'), signed, format='json', HTTP_USER_AGENT='Phone (synthetic)')
    assert answer.status_code == 200, answer.content
    assert answer.json()['bor']['signed'] is True and answer.json()['bor']['name'] == 'Jordan Example'
    intake = Intake.objects.get(deal=deal)
    assert intake.bor_signed_by is None and intake.bor_name == 'Jordan Example'
    assert intake.bor_via == {'link': link.id, 'ip': '127.0.0.1', 'agent': 'Phone (synthetic)'}
    row = Activity.objects.get(area='intake', action='bor')
    assert row.actor_kind == 'client' and '127.0.0.1' not in str(row.changes)
    unasked, token2, _ = make_request(user, deal, {'intake': {'scope': 'missing'}})
    assert api.post(url(token2, 'sign/'), {'name': 'X Y'}, format='json').status_code == 400
