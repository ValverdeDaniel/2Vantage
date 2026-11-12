"""Booked records by hand (plan.md §5.6, §7.10; H54–H58, H112, H113): typed facts and their Revert, typed shares, Add to
book with an outside client, and the records surviving archive."""

import pytest
from django.db.models import ProtectedError
from rest_framework.exceptions import ValidationError

from commission import services
from commission.models import Party, Record
from conftest import make_deal
from deals import activity
from deals.models import Activity, Client
from deals.services import delete_client
from deals.services.archive import set_archived

pytestmark = pytest.mark.django_db


@pytest.fixture
def booked(user, deal):
    """A record booked by hand for the deal's client, at 5 % of $100,000."""
    data = {'client': deal.client_id, 'line': 'medical', 'carrier': 'Cigna', 'effective_date': '2027-01-01'}
    return services.add_to_book(user, {**data, 'premium_annual': '100000', 'rate': '5'}).record


def test_H58_add_to_book_creates_an_outside_client_as_an_existing_client_with_no_deal(user):
    written = services.add_to_book(
        user, {'client_name': 'Outside Co. (synthetic)', 'line': 'dental', 'carrier': 'Delta'}
    )
    record = written.record
    client = Client.objects.get(pk=record.client_id)
    assert client.relationship == 'existing_client'
    assert not client.deals.exists()
    assert record.deal_id is None and record.status == 'booked'
    assert record.year_number is None and record.is_renewal  # no earlier record, no typed year: year unknown (OQ72)
    assert written.activity.subject == f'record:{record.id}' and written.activity.deal_id is None
    prospect = services.add_to_book(
        user, {'client_name': 'Newer Co. (synthetic)', 'relationship': 'prospect', 'line': 'vision', 'year_number': 2}
    ).record
    assert Client.objects.get(pk=prospect.client_id).relationship == 'prospect' and prospect.year_number == 2
    with pytest.raises(ValidationError):
        services.add_to_book(user, {'client_name': 'Wrong Co.', 'relationship': 'new_client', 'line': 'vision'})


def test_H58_add_to_book_refuses_a_missing_line_or_client(user):
    with pytest.raises(ValidationError) as refused:
        services.add_to_book(user, {'client_name': 'X', 'line': 'nope'})
    assert 'line' in refused.value.detail
    with pytest.raises(ValidationError) as refused:
        services.add_to_book(user, {'line': 'medical'})
    assert 'client' in refused.value.detail


def test_H54_typed_facts_win_and_revert_puts_back_their_origin(user, booked):
    record = booked
    services.edit_record(user, record.id, {'premium_annual': '90,000'})
    record.refresh_from_db()
    record.sources['premium_annual']['origin'] = 'sale'  # as a sale had booked it
    record.save()
    written = services.edit_record(user, record.id, {'premium_annual': '95000', 'policy_number': 'POL-9'})
    assert written.changed['premium_annual'] == ['90000.00', '95000.00']
    activity.revert(written.activity.id, user)
    record.refresh_from_db()
    assert record.values['premium_annual'] == '90000.00'
    assert record.sources['premium_annual']['origin'] == 'sale'  # a later booking refreshes it again
    assert 'policy_number' not in record.values


def test_H54_an_ended_status_adds_a_term_end_and_bad_values_answer_400(user, booked):
    services.edit_record(user, booked.id, {'status': 'terminated'})
    booked.refresh_from_db()
    assert booked.status == 'terminated' and booked.term_end is not None
    with pytest.raises(ValidationError) as refused:
        services.edit_record(user, booked.id, {'premium_annual': 'lots', 'status': 'gone', 'rate': '-1', 'x': 1})
    assert set(refused.value.detail) == {'premium_annual', 'status', 'rate', 'x'}


def test_H56_notes_are_kept_and_an_unchanged_edit_writes_nothing(user, booked):
    services.edit_record(user, booked.id, {'notes': 'Billed quarterly'})
    before = Activity.objects.count()
    again = services.edit_record(user, booked.id, {'notes': 'Billed quarterly'})
    assert again.changed == {} and again.activity is None and Activity.objects.count() == before


def test_H55_typed_shares_total_100_need_a_reason_and_name_their_parties(user, booked):
    partner = Party.objects.create(kind='partner', name='Riverside Partners (synthetic)')
    with pytest.raises(ValidationError) as refused:
        services.set_shares(user, booked.id, [{'role': 'house', 'pct': '90'}], '')
    assert set(refused.value.detail) == {'shares.total', 'reason'}
    rows = [{'role': 'house', 'pct': '80'}, {'party': partner.id, 'role': 'referral', 'pct': '20'}]
    written = services.set_shares(user, booked.id, rows, 'Referral agreed after the sale')
    booked.refresh_from_db()
    assert partner.id in booked.party_ids
    assert booked.terms['shares'] == [
        {'party': None, 'role': 'house', 'pct': '80'},
        {'party': partner.id, 'role': 'referral', 'pct': '20'},
    ]
    activity.revert(written.activity.id, user)
    booked.refresh_from_db()
    assert booked.terms['shares'] is None and partner.id not in booked.party_ids


def test_H112_archiving_never_touches_the_ledger_and_a_client_with_records_is_not_deleted(user, deal, booked):
    set_archived(user, deal.client_id, True)
    booked.refresh_from_db()
    assert booked.status == 'booked'
    with pytest.raises(ProtectedError):
        delete_client(user, deal.client_id)
    services.forget_client(deal.client_id)  # the seeders' way, before they delete a golden client
    delete_client(user, deal.client_id)
    assert not Record.objects.filter(pk=booked.pk).exists()


def test_H54_a_carrier_typed_onto_another_record_of_the_deal_answers_409(user, django_capture_on_commit_callbacks):
    from quotes import services as quotes

    deal = make_deal(user, name='Two Carriers Co.')
    for carrier in ('Cigna', 'Aetna'):
        made = quotes.create_plan(user, deal, line='medical', role='alternate', carrier=carrier, name='P', values={})
        with django_capture_on_commit_callbacks(execute=True):
            quotes.set_sold(user, made.id, True)
    cigna = Record.objects.get(deal=deal, carrier='Cigna')
    with pytest.raises(activity.Refused):
        services.edit_record(user, cigna.id, {'carrier': 'Aetna'})
