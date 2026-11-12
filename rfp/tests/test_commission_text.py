"""The commission the request asks for (plan.md §5.7; K29, H109; slice 48): each requested line's rate comes from
commission's `requested_rates`, the deal's agreed rate before the agency default, so an agreed rate set on the
Commission tab is what the form and the emails print."""

import pytest

from commission import services as commission
from conftest import make_deal
from deals.models import AgencySettings

pytestmark = pytest.mark.django_db


def text(api, deal):
    return api.get(f'/api/deals/{deal.id}/rfp/').json()['commission']


def test_H109_K29_the_agreed_rates_print_grouped_and_the_agency_default_fills_the_rest(user, api):
    deal = make_deal(user, requested_lines=('medical', 'dental', 'vision'))
    agency = AgencySettings.get()
    agency.default_commission = {'type': 'pct', 'value': '5'}
    agency.save()
    commission.update(user, deal.id, {'rates': {'dental': '15', 'vision': '15'}})
    assert text(api, deal) == {
        'text': '15% Den/Vis · 5% Med',
        'breakdown': ['Medical: 5%', 'Dental: 15%', 'Vision: 15%'],
        'source': 'deal',
    }


def test_H109_K29_an_agreed_rate_prints_without_an_agency_default(user, api):
    deal = make_deal(user, requested_lines=('medical',))
    commission.update(user, deal.id, {'rates': {'medical': {'type': 'pepm', 'value': '32.5'}}})
    assert text(api, deal) == {'text': '$32.50 PEPM', 'breakdown': ['Medical: $32.50 PEPM'], 'source': 'deal'}
    commission.update(user, deal.id, {'rates': {'vision': '8'}})  # a line not requested never prints
    assert text(api, deal)['text'] == '$32.50 PEPM'
