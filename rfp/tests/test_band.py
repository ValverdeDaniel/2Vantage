"""The band from the one headcount, three ways, and the cross-check (plan.md §5.7; K8, K17–K19; Q.9 row 44; Q.3 #5).

The page reads `quotes.facts.enrollment_check`; these tests read it back through the endpoint the RFP tab calls.
"""

import pytest

from census import facts as census_facts
from census.models import Member
from conftest import make_deal
from deals.models import AgencySettings
from intake import services as intake_services
from quotes import services as quote_services

pytestmark = pytest.mark.django_db


def rfp(api, deal):
    response = api.get(f'/api/deals/{deal.id}/rfp/')
    assert response.status_code == 200
    return response.json()


def test_Q3_5_K17_GD3_A_the_band_comes_from_the_summary_counts_alone(api, gd3, golden_keys):
    key = golden_keys['GD3']['checkpoints']['A']['headcount']
    body = rfp(api, gd3.deal)
    assert (body['band']['count'], body['band']['source'], body['band']['estimate']) == (
        key['count'],
        key['source'],
        key['estimate'],
    )
    assert body['band']['key'] == key['band'] == 'large'
    assert body['band']['from'] == 'the Advisor'
    assert (body['request']['route'], body['request']['route_default']) == ('direct', 'direct')
    assert body['census']['has_roster'] is False  # the census line then names where the count came from (K8)


def test_Q3_5_K17_GD3_B_the_census_takes_the_band_under_51(api, quote_first, golden_keys):
    key = golden_keys['GD3']['checkpoints']['B']['headcount']
    built = quote_first.arrive('D').arrive('F').split().census().built
    body = rfp(api, built.deal)
    assert (body['band']['count'], body['band']['key'], body['band']['source']) == (
        key['count'],
        key['band'],
        key['source'],
    )
    assert body['request']['route'] == 'warner'  # the route follows the band (K20)
    assert body['census']['has_roster'] is True
    assert body['census']['employees'] == census_facts.stored(built.deal.id)['employees']


def test_K17_K18_120_eligible_is_an_estimate_and_large(user, api):
    deal = make_deal(user)
    intake_services.update_answers(user, deal.id, {'employee_count': '120'})
    band = rfp(api, deal)['band']
    assert (band['count'], band['key'], band['estimate'], band['source']) == (
        120,
        'large',
        True,
        'intake.employee_count',
    )
    assert band['from'] == "intake's eligible employees"


@pytest.mark.parametrize(('enrolled', 'band', 'route'), [('50', 'small', 'warner'), ('51', 'large', 'direct')])
def test_K18_OQ53_the_band_at_50_and_51_enrolled(user, api, enrolled, band, route):
    deal = make_deal(user)
    intake_services.update_answers(user, deal.id, {'enrolled_count': enrolled, 'employee_count': '200'})
    body = rfp(api, deal)
    assert (body['band']['key'], body['band']['estimate'], body['request']['route']) == (band, False, route)


def test_K18_no_headcount_at_all_is_small_with_no_count(user, api):
    body = rfp(api, make_deal(user))
    assert (body['band']['key'], body['band']['count'], body['band']['from']) == ('small', None, '')
    assert body['enrollment']['warning'] is None


def _census(deal, counts):
    """Employees on the census by medical tier, the counts refreshed (a factory: only the rows the test needs)."""
    position = 0
    for tier, count in counts.items():
        for _ in range(count):
            position += 1
            Member.objects.create(deal=deal, kind='employee', position=position, values={'medical_tier': tier})
    census_facts.refresh(deal.id)


def test_K19_the_cross_check_names_the_intake_census_and_advisor_counts(user, api):
    deal = make_deal(user, requested_lines=('medical',))
    intake_services.update_answers(user, deal.id, {'enrolled_count': '42'})
    _census(deal, {'EE': 20, 'ES': 8, 'EC': 6, 'FAM': 6})  # 40
    quote_services.set_enrollment(user, deal, 'medical', whole_line={'EE': 20, 'ES': 8, 'EC': 6, 'FAM': 7})  # 41
    body = rfp(api, deal)
    enrollment = body['enrollment']
    assert (enrollment['intake'], enrollment['census'], enrollment['advisor']) == (42, 40, 41)
    assert enrollment['differ'] is True
    assert enrollment['warning'] == 'Enrolled: intake 42 · census 40 · Advisor 41 — the band uses the Advisor, 41.'
    assert (body['band']['count'], body['band']['source']) == (41, 'advisor')


def test_K17_GD6_sixty_enrolled_goes_direct_and_the_three_counts_agree(api, gd6, golden_keys):
    body = rfp(api, gd6.deal)
    assert body['band']['count'] == golden_keys['GD6']['ready']['enrolled']
    assert (body['band']['key'], body['request']['route']) == ('large', 'direct')
    assert body['enrollment']['differ'] is False
    assert body['client_name'] == gd6.spec['intake']['answers']['legal_name']  # the legal name, else the client (K4)


def test_K29_the_commission_text_comes_from_the_agency_default(user, api):
    deal = make_deal(user, requested_lines=('medical', 'dental'))
    assert rfp(api, deal)['commission'] == {'text': '', 'breakdown': [], 'source': ''}
    agency = AgencySettings.get()
    agency.default_commission = {'type': 'pct', 'value': '5'}
    agency.save()
    assert rfp(api, deal)['commission'] == {
        'text': '5%',
        'breakdown': ['Medical: 5%', 'Dental: 5%'],
        'source': 'agency',
    }
