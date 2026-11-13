"""The Work queue on the golden deals and at scale (Q.9 row 61 with §13.2's added row; I122 as changed by OQ101 c, OQ91,
OQ95; Q.3 #4): Prospects lists only Prospect clients and Clients only New and Existing ones; selling GD2's plan moves
its row at once and shows its commission step, or "Sold"; GD3's row is its Agenda's lead step; the feed runs the
same queries for N deals and 3N. GD2 and GD3 are built per test (they write or are walked); GD-Big's shape by size."""

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from agenda import selectors, services
from conftest import make_big_deal
from quotes import services as quote_services

pytestmark = pytest.mark.django_db


def feed(api, **params):
    response = api.get('/api/work-queue/', params)
    assert response.status_code == 200
    return response.json()


def deal_row(payload, deal):
    return next((row for row in payload['rows'] if row['kind'] == 'deal' and row['deal_id'] == deal.id), None)


def listed(api, deal, relationship):
    rows = api.get('/api/clients/', {'relationship': relationship}).json()['results']
    return deal.client_id in {row['id'] for row in rows}


def test_I122_OQ91_selling_GD2s_plan_moves_it_from_prospects_to_clients_at_once(
    api, user, fresh_gd2, django_capture_on_commit_callbacks
):
    deal = fresh_gd2.deal
    before = feed(api)
    assert deal_row(before, deal)['client_status'] == 'prospect'
    assert listed(api, deal, 'prospect') and not listed(api, deal, 'new_client,existing_client')
    with django_capture_on_commit_callbacks(execute=True):
        quote_services.set_sold(user, fresh_gd2.refs['SA'], True)
    after = feed(api, include='closed')
    row = deal_row(after, deal)
    assert row['client_status'] == 'new_client' and row['stage'] == 'sold'
    assert row['key'] in ('commission', 'mark_sold') and row['label'] == selectors.next_step(deal)['label']
    assert not listed(api, deal, 'prospect') and listed(api, deal, 'new_client,existing_client')
    assert after['cards']['prospects']['count'] == before['cards']['prospects']['count'] - 1


def test_I63_GD2_sold_without_a_rate_reads_its_commission_step(api, user, fresh_gd2):
    """With no rate on the deal and no agency default, the sold line wants its commission (I63; slice 60's words)."""
    deal = fresh_gd2.deal
    quote_services.set_sold(user, fresh_gd2.refs['SA'], True)
    agenda = selectors.deal_agenda(deal, user)
    commission = next((row for row in agenda['rows'] if row.get('key') == 'commission'), None)
    row = deal_row(feed(api, include='closed'), deal)
    if commission and commission['section'] == 'up_next':
        assert row['label'] == commission['label'] and row['finished'] is False
        assert deal_row(feed(api), deal) is not None  # still work: on the queue without include=closed
    else:
        assert row['label'] == 'Sold' and row['finished'] is True


def test_I68_GD3s_row_is_its_agendas_lead_step(api, user, quote_first):
    deal = quote_first.built.deal
    row = deal_row(feed(api), deal)
    assert row['label'] == selectors.deal_agenda(deal, user)['next_step']['label'] == 'Read carrier quotes'
    assert row['client_status'] == 'prospect' and row['type'] == 'new_business'


def test_Q3_4_I118_the_feed_reads_in_the_same_queries_for_n_deals_and_3n(api, user):
    def unit(n):
        deal = make_big_deal(user, plans=12, name=f'Scale {n} (synthetic)')
        services.add_task(user, deal.id, title='Call the client', due='2099-01-01', assigned_to=user.id)
        services.set_later(user, deal.id, 'complete_intake', '2099-01-01')
        return deal

    def queries():
        with CaptureQueriesContext(connection) as found:
            feed(api, include='closed')
        return len(found.captured_queries)

    for n in range(2):
        unit(n)
    small = queries()
    for n in range(2, 6):
        unit(n)
    assert queries() == small
