"""Quotes' locate hooks and "Check this file" on GD1 (plan.md §10.7, §13.7 row 16; E59, E81, E83, D95). GD1's
synthetic files print its Cigna and Aetna values; each check rolls back with its test, so GD1 stays as built."""

from types import SimpleNamespace

import pytest

from documents.locate import NOCHECK, VERSION, Located
from documents.models import Document
from quotes import locate_hooks, services
from quotes.models import Plan

pytestmark = pytest.mark.django_db

PLAN = SimpleNamespace(carrier='Cigna', name='LocalPlus HDHP 3000')


def ask(key, value, **entry):
    return locate_hooks.query_for(PLAN, key, value, {'doc': 1, **entry})


def test_E81_each_field_is_asked_about_by_the_readers_rules():
    coinsurance = ask('coinsurance', '20')
    assert coinsurance.alternatives == (('80', 'complement'),)
    assert {'coinsurance', 'coins'} <= set(' '.join(coinsurance.anchors).lower().split())
    copay = ask('pcp_copay', '0', page=3, line='Primary care No charge')
    assert ('no charge', 'no_charge') in copay.wordings and copay.tolerance == 1.0
    assert (copay.page, copay.snippet, copay.hint) == (3, 'Primary care No charge', 'Cigna LocalPlus HDHP 3000')
    assert 'LocalPlus HDHP 3000' in copay.anchors and 'PCP Copay' in copay.anchors
    assert ask('rate_ee', '512.34').tolerance == 0.0  # rates are copied to the cent
    assert ask('sl_agg_corridor', '1.25').alternatives == (('125', 'percent'),)
    funding = ask('funding', 'fully_insured')
    assert (funding.value, funding.strict) == ('Fully insured', False)  # a choice is printed as its label
    assert ask('network', 'Open Access Plus').strict is False  # words the reader may shorten: weak, never absent
    assert ask('sbc_url', 'https://example.com/sbc/123').kind == 'code'
    assert ask('minimum_value', 'Yes') == Located(NOCHECK, why='choice')
    assert ask('benefit_summary', 'Covers most things') == Located(NOCHECK, why='summary')


def _file(gd1, kind):
    return Document.objects.get(deal=gd1.deal, kind=kind)


def _check(api, gd1, document, **body):
    answer = api.post(f'/api/deals/{gd1.deal.id}/ai/locate/', {'document_ids': [document.id], **body}, format='json')
    assert answer.status_code in (200, 201)
    return answer.json()


def test_E59_GD1_check_this_file_finds_every_cigna_value_at_its_own_cell(api, gd1):
    quote = _file(gd1, 'quote')
    before = {plan.id: plan.updated_at for plan in Plan.objects.filter(deal=gd1.deal)}
    job = _check(api, gd1, quote)
    assert job['status'] == 'done'
    # CG1N, the negotiated copy, keeps the file on its values (E66) but its typed rates are printed nowhere in it.
    copy = Plan.objects.get(pk=gd1.refs['CG1N'])
    absent = sorted(key for key, entry in copy.sources.items() if entry['loc']['state'] == 'absent')
    assert absent == ['rate_ec', 'rate_ee', 'rate_es', 'rate_fam'] and job['counts']['absent'] == 4
    checked = len(copy.sources)
    for ref in ('CG1', 'CG2', 'CG3', 'CG4'):
        plan = Plan.objects.get(pk=gd1.refs[ref])
        for key, entry in plan.sources.items():
            loc = entry['loc']
            assert loc['state'] in ('found', 'weak') and loc['v'] == VERSION, (ref, key, loc)
            assert f'{loc["sheet"]}!{loc["cell"]}' == entry['cell'], (ref, key, loc)
            checked += 1
    assert job['counts']['checked'] == checked
    after = {plan.id: plan.updated_at for plan in Plan.objects.filter(deal=gd1.deal)}
    assert after == before  # the answers are bookkeeping: no plan moves "Last updated"


def test_E59_GD1_the_renewal_rates_are_found_on_the_exhibit_page(api, gd1):
    job = _check(api, gd1, _file(gd1, 'renewal'))
    assert job['counts'] == {'checked': 12, 'found': 12, 'derived': 0, 'weak': 0, 'absent': 0, 'nocheck': 0}
    for ref in ('A2', 'B2', 'C2'):
        plan = Plan.objects.get(pk=gd1.refs[ref])
        locs = [plan.sources[key]['loc'] for key in ('rate_ee', 'rate_es', 'rate_ec', 'rate_fam')]
        assert all((loc['state'], loc['page']) == ('found', 2) for loc in locs), (ref, locs)


def test_E83_GD1_a_value_typed_over_the_file_is_not_in_the_file(api, user, gd1):
    quote = _file(gd1, 'quote')
    _check(api, gd1, quote)
    plan_id = gd1.refs['CG1']
    services.update_plan(user, plan_id, {'values': {'rate_ee': '499.99'}})  # typed: keeps its file, drops `loc`
    source = api.get(f'/api/plans/{plan_id}/source/', {'key': 'rate_ee'}).json()['source']
    assert source['doc'] == quote.id and source['loc'] is None
    job = _check(api, gd1, quote)
    assert job['counts']['checked'] == 1 and job['counts']['absent'] == 1  # only the unchecked value is looked for
    source = api.get(f'/api/plans/{plan_id}/source/', {'key': 'rate_ee'}).json()['source']
    assert source['loc']['state'] == 'absent' and source['origin'] == 'typed'


def test_E84_GD1_a_second_check_writes_nothing_and_a_recheck_finds_the_same(api, gd1):
    renewal = _file(gd1, 'renewal')
    first = _check(api, gd1, renewal)
    sources = {plan.id: plan.sources for plan in Plan.objects.filter(deal=gd1.deal)}
    assert _check(api, gd1, renewal)['counts']['checked'] == 0
    again = _check(api, gd1, renewal, recheck=True)
    assert again['counts'] == first['counts'] and again['activity_id'] is None
    assert {plan.id: plan.sources for plan in Plan.objects.filter(deal=gd1.deal)} == sources


def test_E83_an_answer_about_a_value_changed_meanwhile_is_not_stored(user, gd1):
    quote = _file(gd1, 'quote')
    plan_id = gd1.refs['CG2']
    answers = [((plan_id, 'rate_ee', '478.20'), {'state': 'found', 'cell': 'C10', 'v': VERSION, 'at': 'now'})]
    services.update_plan(user, plan_id, {'values': {'rate_ee': '480.00'}})
    assert locate_hooks.save(user, gd1.deal, quote, answers) == {'saved': 0, 'areas': []}
    assert 'loc' not in Plan.objects.get(pk=plan_id).sources['rate_ee']
