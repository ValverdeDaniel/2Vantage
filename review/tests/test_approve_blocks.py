"""Contacts, current coverage and the lines to shop from the client (plan.md §5.8; L85, L108, B38; OQ84; Ch. 6): they
wait as one entry each and land, once approved, through their owners' services: a contact edited or added (never
removed), a coverage row edited or a line in force added, and "please shop" through the intent service, which adds a
line and never takes one off."""

import pytest

from deals.models import Activity, Contact
from deals.services import create_contact
from intake.models import CurrentCoverage
from intake.services import create_coverage, set_intent

from .decision_world import entry, intake_answers, link_on, submitted

pytestmark = pytest.mark.django_db


def _approve(api, deal, refs):
    answer = api.post(f'/api/deals/{deal.id}/review/approve/', {'refs': refs}, format='json')
    assert answer.status_code == 200, answer.content
    return answer.json()


def test_L85_OQ84_approved_contacts_land_through_the_contacts_service(api, user, deal):
    kept = create_contact(user, deal.client_id, role='hr_admin', name='Dana Diaz', email='dana@example.com')
    link = link_on(user, deal)
    rows = [
        {'id': kept.id, 'role': 'hr_admin', 'name': 'Dana Diaz', 'email': 'dana@example.com', 'phone': '555-0100'},
        {'role': 'billing', 'name': 'Lee Park', 'email': 'lee@example.com'},
    ]
    intake_answers(deal, link, {'block:contacts': rows})
    assert Contact.objects.filter(client=deal.client).count() == 1  # OQ84: nothing lands before approval
    submitted(link)
    body = _approve(api, deal, ['intake:block:contacts'])
    assert body['approved'] == ['intake:block:contacts']
    contacts = {contact.name: contact for contact in Contact.objects.filter(client=deal.client)}
    assert contacts['Dana Diaz'].phone == '555-0100' and contacts['Lee Park'].role == 'billing'
    assert entry(deal, 'block:contacts')['status'] == 'approved'
    row = Activity.objects.get(pk=body['activity_ids'][0])
    assert row.summary == "Approved the client's contacts (1 added, 1 edited)" and not row.revertible
    assert 'Lee' not in str(row.changes)  # contacts are key-only (§3.8)


def test_L85_L108_approved_coverage_edits_its_row_and_adds_a_line_in_force_never_touching_commission(api, user, deal):
    row = create_coverage(user, deal.id, {'line': 'dental', 'carrier': 'Old Dental', 'commission': '10%'}).row
    link = link_on(user, deal)
    answer = [
        {'id': row.id, 'line': 'dental', 'carrier': 'New Dental', 'funding': '', 'renewal_date': '2027-01-01'},
        {'line': 'vision', 'carrier': 'Clear Vision', 'funding': '', 'renewal_date': ''},
    ]
    intake_answers(deal, link, {'block:coverage': answer})
    _approve(api, deal, ['intake:block:coverage'])
    dental = CurrentCoverage.objects.get(pk=row.pk)
    assert (dental.carrier, str(dental.renewal_date), dental.commission) == ('New Dental', '2027-01-01', row.commission)
    vision = CurrentCoverage.objects.get(deal=deal, line='vision')
    assert vision.in_force and vision.carrier == 'Clear Vision'


def test_L85_Ch6_please_shop_adds_lines_through_the_intent_service_and_never_takes_one_off(api, user, deal):
    set_intent(user, deal.id, lines=['dental', 'vision'], shop=False)  # the factory deal shops all three
    link = link_on(user, deal)
    intake_answers(deal, link, {'block:lines': ['dental', 'vision']})  # medical unticked
    _approve(api, deal, ['intake:block:lines'])
    deal.refresh_from_db()
    assert deal.requested_lines == ['medical', 'dental', 'vision']
    intent = Activity.objects.filter(deal=deal, action='intent').latest('id')
    assert intent.changes[0]['k']['requested_lines'] == [['medical'], ['medical', 'dental', 'vision']]


def test_L85_a_block_approval_is_taken_back_from_its_owners_rows_not_by_undo(api, user, deal):
    link = link_on(user, deal)
    intake_answers(deal, link, {'block:lines': ['dental']})
    _approve(api, deal, ['intake:block:lines'])
    refused = api.post(f'/api/deals/{deal.id}/review/undo/', {'refs': ['intake:block:lines']}, format='json')
    assert refused.status_code == 409
