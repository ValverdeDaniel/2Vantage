"""Ready to market (plan.md §5.2 Readiness; B9, B13, B33; Q.9 row 40): contacts OK, BOR on file, census OK, the
needed questions answered with no open warning and the checklist clear; the gaps in the banner's order; the contacts
on the intake payload with their email check."""

import pytest

from deals.services import create_contact, update_contact
from intake import providers, readiness, services

pytestmark = pytest.mark.django_db


def payload(api, deal):
    return api.get(f'/api/deals/{deal.id}/intake/').json()


def test_B13_contacts_ok_needs_an_hr_or_benefit_admin_with_a_name_and_an_email():
    ok = readiness.contacts_ok
    assert not ok([])
    assert not ok([{'role': 'hr_admin', 'name': 'Riley', 'email': ''}])
    assert not ok([{'role': 'owner', 'name': 'Riley', 'email': 'r@example.test'}])
    assert ok([{'role': 'benefit_admin', 'name': 'Riley', 'email': 'r@example.test'}])


def test_B33_the_gaps_come_in_the_banners_order_then_the_checklist_once_each():
    items = [
        {'key': 'census', 'label': 'Member-level census', 'status': 'missing'},
        {'key': 'cobra', 'label': 'COBRA participants', 'status': 'missing'},
        {'key': 'renewal', 'label': 'Current benefits renewal & rates', 'status': 'done'},
        {'key': 'invoice', 'label': 'Current invoice(s)', 'status': 'waived'},
    ]
    found = readiness.gaps(
        missing=[('fein', 'FEIN')],
        to_check=[('sic_code', 'SIC Code')],
        contacts_ok=False,
        bor_on_file=False,
        census_ok=False,
        items=items,
    )
    assert [gap['label'] for gap in found] == [
        'FEIN',
        'SIC Code (to check)',
        'HR contact',
        'Signed BOR',
        'Census',
        'COBRA participants',
    ]
    assert readiness.state(None, found) == 'blocked' and readiness.state(None, []) == 'ready'
    assert readiness.state('2027-01-02T00:00:00Z', found) == 'submitted'


def test_B13_the_payload_carries_the_clients_contacts_with_their_email_check(user, api, deal):
    contact = create_contact(user, deal.client_id, role='hr_admin', name='Riley Example', email='riley@example.test')
    body = payload(api, deal)
    assert [c['name'] for c in body['contacts']] == ['Riley Example'] and body['primary_id'] == contact.id
    assert body['contacts_ok'] is True and 'contacts' not in [gap['key'] for gap in body['ready']['gaps']]
    type(contact).objects.filter(pk=contact.pk).update(email='not-an-email')  # a value that reached the row another way
    body = payload(api, deal)
    assert body['contacts'][0]['issues'][0]['code'] == 'email_format'
    assert body['issues'][f'contact:{contact.id}'][0]['severity'] == 'error'
    update_contact(user, contact.id, email='')
    assert payload(api, deal)['contacts_ok'] is False


def test_B33_a_needed_question_with_an_open_warning_blocks_until_approved(user, api, deal):
    services.update_answers(user, deal.id, {'legal_name': 'Example Co. LLC'})
    services.mark_answers(user, deal.id, 'check', refs=['intake:legal_name'])
    gaps = payload(api, deal)['ready']['gaps']
    assert {'kind': 'to_check', 'key': 'legal_name', 'label': 'Legal Company Name (to check)'} in gaps
    services.mark_answers(user, deal.id, 'approve', refs=['intake:legal_name'])
    assert 'legal_name' not in [gap['key'] for gap in payload(api, deal)['ready']['gaps']]


def test_B25_the_checklist_reads_the_tier_from_the_headcount_provider(api, deal, monkeypatch):
    for count, tier in ((50, 'small'), (51, 'mid')):
        monkeypatch.setitem(
            providers._slots, 'headcount', lambda _id, n=count: {'count': n, 'source': 'advisor', 'estimate': False}
        )
        card = payload(api, deal)['checklist']
        assert (card['enrolled'], card['tier']) == (count, tier)


def test_B33_census_ok_comes_from_censuss_provider(api, deal, monkeypatch):
    monkeypatch.setitem(providers._slots, 'census_state', lambda _id: {'ok': True})
    body = payload(api, deal)
    assert body['ready']['census_ok'] is True and 'census' not in [gap['key'] for gap in body['ready']['gaps']]
