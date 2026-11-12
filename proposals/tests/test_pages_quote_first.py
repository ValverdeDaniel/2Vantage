"""Pages on GD3, the quote-first deal (Q.3 #5; Q.9 row 14): the premiums the pages print come from typed counts at
checkpoint A, from each current plan's split once two arrive, and from the census at B, equal to GD3's hand-worked
key. `gd3` is checkpoint A, read only; `quote_first` moves a fresh GD3 through its checkpoints."""

import pytest

pytestmark = pytest.mark.django_db

QUOTES = ['QA1', 'QA2', 'QA3', 'QC1', 'QC2', 'QC3', 'QU1', 'QU2', 'QU3', 'QV1']


def read(api, built):
    response = api.get(f'/api/deals/{built.deal.id}/proposal/pages/', {'line': 'medical'})
    assert response.status_code == 200, response.content
    return response.json()


def monthly(body, built):
    names = {plan_id: ref for ref, plan_id in built.refs.items()}
    return {names[entry['plan_id']]: entry['monthly'] for entry in body['plans']}


def keyed(plans, refs):
    return {ref: f'${plans[ref]["monthly"]:,}' for ref in refs}


def pages_of(body, built):
    names = {plan_id: ref for ref, plan_id in built.refs.items()}
    return [[names[pid] for pid in page['plan_ids']] for page in body['pages']]


def test_Q3_5_F37_GD3_A_pages_print_the_typed_counts_premiums(api, gd3, golden_keys):
    body = read(api, gd3)
    assert monthly(body, gd3) == keyed(golden_keys['GD3']['checkpoints']['A']['plans'], QUOTES)
    assert body['nothing_starred'] and not body['currents']  # every quote prints, a page per carrier
    assert pages_of(body, gd3) == [QUOTES[0:3], QUOTES[3:6], QUOTES[6:9], QUOTES[9:]]


def test_Q3_5_F37_GD3_the_split_prints_each_current_plans_page(api, quote_first, golden_keys):
    built = quote_first.arrive('D').arrive('F').split().built
    body = read(api, built)
    plans = golden_keys['GD3']['checkpoints']['A_split']['plans']
    assert monthly(body, built) == keyed(plans, ['D', 'F', *QUOTES])
    assert pages_of(body, built) == [
        ['D', 'QA1', 'QA2', 'QA3', 'QC1', 'QC2'],
        ['D', 'QC3'],
        ['F', 'QU1', 'QU2', 'QU3', 'QV1'],
    ]


def test_Q3_5_F37_GD3_B_the_census_prices_the_pages(api, quote_first, golden_keys):
    built = quote_first.arrive('D').arrive('F').split().census().built
    plans = golden_keys['GD3']['checkpoints']['B']['plans']
    assert monthly(read(api, built), built) == keyed(plans, ['D', 'F', *QUOTES])
