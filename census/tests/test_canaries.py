"""PHI canaries through the census import (plan.md §3.8, §12.9; Q.8). Unique synthetic strings go into every PHI
column of a census file; none may reach Activity (changes included), logs, error bodies, the stored import, the stored
counts or the non-PHI payloads (the deal header and its feed)."""

import logging

import pytest

from census import services
from census.models import CensusFacts, CensusImport
from deals.models import Activity

from .helpers import import_file, upload, xlsx

pytestmark = pytest.mark.django_db

CANARIES = {
    'first_name': 'Quillonia',
    'last_name': 'Vexcanary',
    'dob': '03/14/1957',
    'ssn': '123-45-6780',
    'address1': '17 Canarywood Lane',
    'city': 'Canaryville',
    'phone': '555-0199-77',
    'email': 'quillonia@canary.test',
    'annual_salary': '91234',
}
SPOUSE = {'first_name': 'Zephyrine', 'dob': '07/23/1961', 'ssn': '123-45-6781'}
STORED_FORMS = ['1957-03-14', '1961-07-23']  # the dates as stored


def strings():
    return [*CANARIES.values(), *SPOUSE.values(), *STORED_FORMS]


def census_file():
    headers = [
        'First Name',
        'Last Name',
        'DOB',
        'SSN',
        'Address',
        'City',
        'Phone',
        'Email',
        'Annual Salary',
        'Relationship',
    ]
    employee = [
        CANARIES[key]
        for key in ('first_name', 'last_name', 'dob', 'ssn', 'address1', 'city', 'phone', 'email', 'annual_salary')
    ]
    spouse = [SPOUSE['first_name'], CANARIES['last_name'], SPOUSE['dob'], SPOUSE['ssn'], '', '', '', '', '', 'Spouse']
    return xlsx([headers, [*employee, 'Employee'], spouse])


def leaked(text):
    return [canary for canary in strings() if canary.lower() in str(text).lower()]


def test_Q8_census_canaries_never_leave_the_roster(user, api, deal, caplog):
    caplog.set_level(logging.DEBUG)
    imp = import_file(user, deal, census_file(), name='payroll export (synthetic).xlsx')
    bodies = [
        api.patch(f'/api/census/imports/{imp.id}/', {'mapping': [{'column': 1, 'field': 'first_name'}]}, format='json'),
        api.patch(f'/api/census/imports/{imp.id}/', {'sheet_name': 7}, format='json'),
    ]
    assert [answer.status_code for answer in bodies] == [400, 400]
    assert api.post(f'/api/census/imports/{imp.id}/apply/', {}, format='json').status_code == 200
    bodies.append(api.post(f'/api/census/imports/{imp.id}/apply/', {}, format='json'))  # 409: already applied
    bad = upload(user, deal, xlsx([['only', 'two']]))
    bodies.append(api.post(f'/api/deals/{deal.id}/census/imports/', {'document_id': bad.id}, format='json'))
    again = import_file(user, deal, census_file())
    services.dry_run(again.id)
    services.apply_import(user, again.id)

    for row in Activity.objects.filter(deal=deal).values('summary', 'changes'):
        assert leaked(row) == [], row
    for row in CensusImport.objects.filter(deal=deal).values():
        assert leaked(row) == []
    counts = CensusFacts.objects.filter(deal=deal).values().get()
    counts['rollup'].pop('volumes')  # Σ salary prices LTD (§4.1): a figure pricing needs, not a person's details
    assert leaked(counts) == []
    for answer in bodies:
        assert answer.status_code in (400, 409)
        assert leaked(answer.content.decode()) == []
    assert leaked(caplog.text) == []
    assert leaked(api.get(f'/api/deals/{deal.id}/').content.decode()) == []
    assert leaked(api.get(f'/api/deals/{deal.id}/activity/').content.decode()) == []


def test_Q8_OQ16_the_census_page_shows_ssns_masked(user, api, deal):
    imp = import_file(user, deal, census_file())
    services.apply_import(user, imp.id)
    page = api.get(f'/api/deals/{deal.id}/census/').content.decode()
    assert '123-45-6780' not in page and '***-**-6780' in page
    sample = api.get(f'/api/census/imports/{imp.id}/').content.decode()
    assert '123-45-6780' not in sample


def test_Q8_C6_C7_hand_edits_files_and_refusals_carry_no_canary(user, api, deal, caplog):
    caplog.set_level(logging.DEBUG)
    imp = import_file(user, deal, census_file())
    services.apply_import(user, imp.id)
    from census.models import Member

    employee = Member.objects.get(deal=deal, kind='employee')
    url = f'/api/census/members/{employee.id}/'
    bodies = [
        api.patch(url, {'values': {'city': 'Canarytown'}, 'expect': {'city': 'Nowhere'}}, format='json'),  # 409
        api.patch(url, {'values': {'ssn': '***-**-0000'}}, format='json'),  # 400: a mask not on file
        api.patch(url, {'values': {'Quillonia': 'x'}}, format='json'),  # 400: not a column (cut, never a value)
    ]
    assert [answer.status_code for answer in bodies] == [409, 400, 400]
    assert (
        api.patch(url, {'values': {'email': 'zz@canary.test', 'dob': '03/15/1957'}}, format='json').status_code == 200
    )
    made = api.post(
        f'/api/deals/{deal.id}/census/members/',
        {'kind': 'dependent', 'employee_id': employee.id, 'values': {'first_name': 'Canarella', 'dob': '01/02/2010'}},
        format='json',
    ).json()['member']
    api.post(
        f'/api/deals/{deal.id}/census/marks/', {'action': 'check', 'refs': [f'census:{made["id"]}:dob']}, format='json'
    )
    api.delete(f'/api/census/members/{made["id"]}/')
    files = [api.get(f'/api/deals/{deal.id}/census/template/'), api.get(f'/api/deals/{deal.id}/census/export/')]
    extra = ['Canarytown', 'zz@canary.test', '1957-03-15', 'Canarella', '2010-01-02']
    for row in Activity.objects.filter(deal=deal).values('summary', 'changes'):
        assert leaked(row) == [] and not [word for word in extra if word in str(row)], row
    for answer in bodies:
        assert leaked(answer.content.decode()) == []
        assert not [word for word in extra if word in answer.content.decode()]
    for answer in files:
        assert leaked(answer['Content-Disposition']) == []
    assert leaked(caplog.text) == [] and not [word for word in extra if word in caplog.text]
