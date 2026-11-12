"""GD1-sold against its answer key (plan.md §13.2 row 49, §13.4; Q.9 row 49; H25–H32, OQ75, OQ101): the sale of two
medical plans books two records and makes the Prospect a New client; un-selling both voids both and returns it to
Prospect."""

import pytest

from commission import selectors
from commission.models import Record
from deals.models import Activity, Client
from quotes import services as quotes

pytestmark = pytest.mark.django_db


def test_GD1_sold_books_both_plans_as_its_key_says(gd1_sold, golden_keys, admin_user):
    key = golden_keys['GD1-sold']
    deal, refs, _spec = gd1_sold
    assert Client.objects.get(pk=deal.client_id).relationship == key['client_status']
    records = {record.carrier: record for record in Record.objects.filter(deal=deal).exclude(status='void')}
    assert set(records) == {row['carrier'] for row in key['records']}
    booking = selectors.deal_payload(deal, admin_user)['booking']
    rows = {row['carrier']: row for row in booking['records']}
    for expected in key['records']:
        record, row = records[expected['carrier']], rows[expected['carrier']]
        assert record.values['plan_ids'] == [refs[ref] for ref in expected['plans']]
        assert record.values['premium_annual'] == expected['premium_annual']
        assert record.values['employees'] == expected['employees']
        assert (row['rate_label'], row['expected'], row['year_number']) == (
            expected['rate'],
            expected['expected'],
            expected['year_number'],
        )
        shares = {share['role']: share for share in row['shares']}
        for role, figures in expected['shares'].items():
            assert (shares[role]['pct'], shares[role]['amount']) == (figures['pct'], figures['amount'])
    assert booking['state'] == 'booked' and booking['totals']['expected'] == key['expected_total']


def test_GD1_sold_unselling_both_plans_voids_both_records_and_returns_the_client_to_prospect(
    sell_gd1, user, django_capture_on_commit_callbacks
):
    deal, refs, spec = sell_gd1
    assert Client.objects.get(pk=deal.client_id).relationship == 'new_client'
    for ref in spec['sold']:
        with django_capture_on_commit_callbacks(execute=True):
            quotes.set_sold(user, refs[ref], False)
    assert set(Record.objects.filter(deal=deal).values_list('status', flat=True)) == {'void'}
    assert Record.objects.filter(deal=deal).count() == 2
    client = Client.objects.get(pk=deal.client_id)
    assert client.relationship == 'prospect' and client.client_since is None
    assert Activity.objects.filter(deal=deal, area='client', action='prospect').exists()
    assert selectors.deal_payload(deal, user)['booking']['state'] == 'none'
