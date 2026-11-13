"""The receipt after Submit (plan.md §7.14, §8.20; L99, the old roadmap's N1; Q.9 row 59): none until the link was
submitted; then what went through this link, by section, with the time — counts and labels, the client's own file
names, never a value, never a file's name (file names are PHI, §3.8), never a colleague's answers or files. All data
is synthetic."""

import json

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from review import services
from synthetic_files import text_pdf

from .portal_world import cell, client, field, make_request, page, person, save, url, verified

pytestmark = pytest.mark.django_db

CSV = b'First Name,Last Name,DOB\r\nRowan,Synthetic,01/02/1980\r\n'
TYPED = 'Zqreceiptcanary Payroll Co.'


def _upload(api, token, slot, name, content, **headers):
    answer = api.post(url(token, 'files/'), {'slot': slot, 'file': SimpleUploadedFile(name, content)}, **headers)
    assert answer.status_code == 201, answer.content
    return answer


def _submit(api, token, **headers):
    answer = api.post(url(token, 'submit/'), {'answers': {}}, format='json', **headers)
    assert answer.status_code == 200, answer.content
    return answer.json()


def test_L99_no_receipt_until_submitted_then_what_went_by_section_with_the_time(user, deal):
    asks = {'intake': {'scope': 'missing'}, 'census': {'file': True}, 'documents': {'slots': ['invoice@medical']}}
    _link, token, _pin = make_request(user, deal, asks)
    api = client()
    body = page(api, token).json()
    assert body['receipt'] is None
    answers = {
        'intake:payroll_vendor': {'value': TYPED, 'base': field(body, 'payroll_vendor')['base']},
        'intake:website': {'value': 'https://example.com/synthetic', 'base': field(body, 'website')['base']},
    }
    assert save(api, token, answers).status_code == 200
    _upload(api, token, 'census_file', 'Zqcanarysurname Rowan census.csv', CSV)
    _upload(api, token, 'invoice@medical', 'invoice (synthetic).pdf', text_pdf('Invoice (synthetic)'))
    _upload(api, token, 'invoice@medical', 'invoice 2 (synthetic).pdf', text_pdf('Invoice 2 (synthetic)'))
    done = _submit(api, token)
    receipt = done['receipt']
    assert receipt['at'] == done['submitted_at']
    assert receipt['sections'] == [
        {'key': 'intake', 'title': 'Company intake form', 'lines': ['2 answers']},
        {
            'key': 'files',
            'title': 'Files',
            'lines': ['Employee census file', 'Current invoice — Medical — 2 files'],
        },
    ]
    assert page(api, token).json()['receipt'] == receipt  # the link opened again shows it
    said = json.dumps(done)
    assert TYPED not in said and 'example.com' not in said  # never a value (L108)
    assert 'Zqcanarysurname' not in said and 'invoice (synthetic)' not in json.dumps(receipt)  # never a file's name


def test_L99_the_receipt_names_only_what_this_link_sent(user, deal):
    people = [{'name': 'Casey (synthetic)'}, {'name': 'Jordan (synthetic)'}]
    asks = {'intake': {'scope': 'missing'}, 'documents': {'slots': ['invoice@medical']}}
    made = services.create(user, deal.id, {'asks': asks, 'people': people})
    (_mine, mine_path, _p1), (_theirs, theirs_path, _p2) = made.links
    mine, theirs = mine_path.rsplit('/', 1)[1], theirs_path.rsplit('/', 1)[1]
    api = client()
    body = page(api, theirs).json()
    save(api, theirs, {'intake:website': {'value': 'https://example.com', 'base': field(body, 'website')['base']}})
    _upload(api, theirs, 'invoice@medical', 'their invoice (synthetic).pdf', text_pdf('Theirs (synthetic)'))
    body = page(api, mine).json()
    save(api, mine, {'intake:payroll_vendor': {'value': TYPED, 'base': field(body, 'payroll_vendor')['base']}})
    receipt = _submit(api, mine)['receipt']
    assert receipt['sections'] == [{'key': 'intake', 'title': 'Company intake form', 'lines': ['1 answer']}]
    assert 'their invoice' not in json.dumps(receipt)


def test_L99_the_receipt_counts_employee_details_and_people_added(user, deal):
    member = person(user, deal, 'Avery', 'Synthetic', zip='33101')
    _link, token, pin = make_request(user, deal, {'census': {'scope': 'all'}})
    api = client()
    headers = verified(api, token, pin)
    body = page(api, token, **headers).json()
    answers = {
        f'census:{member.id}:zip': {'value': '33602', 'base': cell(body, member.id, 'zip')['base']},
        f'census:{member.id}:dob': {'value': '1/2/1985', 'base': cell(body, member.id, 'dob')['base']},
    }
    assert save(api, token, answers, **headers).status_code == 200
    added = api.post(
        url(token, 'people/'),
        {'people': [{'kind': 'employee', 'first_name': 'Rowan', 'last_name': 'Newhire'}]},
        format='json',
        **headers,
    )
    assert added.status_code == 201, added.content
    receipt = _submit(api, token, **headers)['receipt']
    assert receipt['sections'] == [
        {'key': 'people', 'title': 'Employee details', 'lines': ['2 details', '1 person added']}
    ]
    assert '33602' not in json.dumps(receipt) and 'Rowan' not in json.dumps(receipt)
