"""GD3 at its checkpoints and GD4 by plan name, against their hand-worked keys (plan.md §13.6 row 13, "done when";
Q.3 #5, Q.4, Q.9 row 13). `gd3` is checkpoint A as seeded, read only; `quote_first` builds a fresh GD3 for a test that
moves it through the packet's arrival, the split and the census (the root conftest; app tests never import golden)."""

import pytest

from deals import activity
from quotes import facts, services
from quotes.selectors import comparison, line_state

pytestmark = pytest.mark.django_db

QUOTES = ['QA1', 'QA2', 'QA3', 'QC1', 'QC2', 'QC3', 'QU1', 'QU2', 'QU3', 'QV1']


def priced(built, line):
    """{ref: (monthly, annual, enrollment, source)} of the line's plans, from the comparison the board reads."""
    names = {plan_id: ref for ref, plan_id in built.refs.items()}
    rows = comparison(built.deal, line)['plans']
    return {
        names[row['id']]: (
            row['premium']['monthly'],
            row['premium']['annual'],
            row['enrollment_used'],
            row['enrollment_source'],
        )
        for row in rows
    }


def expected(plans, refs):
    return {
        ref: (plans[ref]['monthly'], plans[ref]['annual'], plans[ref]['enrollment'], plans[ref]['source'])
        for ref in refs
    }


def check(built, plans):
    medical = [ref for ref in plans if ref not in ('AC', 'TH')]
    assert priced(built, 'medical') == expected(plans, medical)
    assert priced(built, 'accident') == expected(plans, ['AC'])
    assert priced(built, 'telehealth') == expected(plans, ['TH'])


def test_Q3_5_GD3_A_every_plan_prices_from_typed_counts(gd3, golden_keys):
    key = golden_keys['GD3']['checkpoints']['A']
    check(gd3, key['plans'])  # the medical figure, borrowed by accident (OQ19); telehealth's typed lives (F92)
    assert {k: facts.enrolled_headcount(gd3.deal)[k] for k in ('count', 'source', 'estimate')} == {
        k: key['headcount'][k] for k in ('count', 'source', 'estimate')
    }


def test_F88_GD3_a_current_plan_arriving_takes_no_price_away(quote_first, golden_keys):
    key = golden_keys['GD3']['checkpoints']['A_one_current']
    check(quote_first.arrive('D').built, key['plans'])


def test_F88_OQ20_GD3_a_second_current_plan_names_the_plans_that_lost_their_price(quote_first, golden_keys):
    key = golden_keys['GD3']['checkpoints']['A_two_current']
    built = quote_first.arrive('D').arrive('F').built
    body = comparison(built.deal, 'medical')
    names = {plan_id: ref for ref, plan_id in built.refs.items()}
    split = body['enrollment']['split']
    assert sorted(names[pid] for pid in split['lost']) == sorted(key['no_price'])
    assert sorted(names[pid] for pid in split['unlinked']) == sorted(key['unlinked'])  # they ask what they replace
    assert split['figure'] == built.spec['line_enrollment']['medical']  # the figure to split
    assert all(row['premium']['reason'] == 'per_plan_counts_needed' for row in body['plans'])
    assert priced(built, 'accident') == expected(key['priced'], ['AC'])  # borrowing keeps the line figure
    assert facts.enrolled_headcount(built.deal)['count'] == key['headcount']['count']


def test_F88_GD3_the_split_prices_each_current_plan_and_its_quotes(quote_first, golden_keys):
    key = golden_keys['GD3']['checkpoints']['A_split']
    built = quote_first.arrive('D').arrive('F').split().built
    check(built, key['plans'])
    assert comparison(built.deal, 'medical')['enrollment']['split'] is None
    assert facts.enrolled_headcount(built.deal)['count'] == key['headcount']['count']


def test_F91_GD3_B_the_census_takes_over_counts_typed_before_it(quote_first, golden_keys):
    key = golden_keys['GD3']['checkpoints']['B']
    built = quote_first.arrive('D').arrive('F').split().census().built
    check(built, key['plans'])
    names = {plan_id: ref for ref, plan_id in built.refs.items()}
    block = comparison(built.deal, 'medical')['enrollment']
    assert sorted(names[pid] for pid in block['census_now']) == sorted(key['census_now'])
    assert block['stale'] is True
    assert {row['text']: row['how'] for row in block['texts']} == {
        'BlueOptions PPO 2500': 'name',
        'BlueCare HMO 1500': 'name',
    }
    found = facts.enrolled_headcount(built.deal)
    assert (found['count'], found['source']) == (key['headcount']['count'], key['headcount']['source'])


def test_F91_GD3_keep_my_typed_counts_wins_again_and_undo_gives_way_again(quote_first, golden_keys):
    key = golden_keys['GD3']['checkpoints']['B_kept']
    built = quote_first.arrive('D').arrive('F').split().census().built
    saved = services.set_enrollment(quote_first.user, built.deal, 'medical', keep=True)
    check(built, key['plans'])
    assert comparison(built.deal, 'medical')['enrollment']['census_now'] == []
    assert facts.enrolled_headcount(built.deal)['count'] == key['headcount']['count']
    check_row = facts.enrollment_check(built.deal)
    assert (check_row['census'], check_row['advisor'], check_row['differ']) == (48, 52, True)
    assert check_row['warning'] == 'Enrolled: intake none · census 48 · Advisor 52 — the band uses the Advisor, 52.'
    assert services.set_enrollment(quote_first.user, built.deal, 'medical', keep=True).activity is None  # kept already
    activity.revert(saved.activity.id, quote_first.user)
    check(built, golden_keys['GD3']['checkpoints']['B']['plans'])


def test_F91_GD3_counts_typed_after_the_import_win(quote_first, golden_keys):
    built = quote_first.arrive('D').arrive('F').split().census().built
    d, f = built.refs['D'], built.refs['F']
    retyped = [
        {'id': d, 'enrollment': {'EE': 17, 'ES': 5, 'EC': 4, 'FAM': 5}},
        {'id': f, 'enrollment': {'EE': 12, 'ES': 3, 'EC': 2, 'FAM': 3}},
    ]
    services.set_enrollment(quote_first.user, built.deal, 'medical', plans=retyped)
    plans = priced(built, 'medical')
    assert plans['D'][2:] == ({'EE': 17, 'ES': 5, 'EC': 4, 'FAM': 5}, 'typed')
    assert plans['F'][3] == 'typed'  # one save stamps the line's typed set: F's counts win again too
    assert plans['QU1'][3] == 'from replaced plan'


def test_F90_GD4_prices_each_current_plan_from_its_own_members_once_every_text_is_matched(golden, golden_keys, user):
    gd4, key, hand = golden['GD4'], golden_keys['GD4']['plans'], golden_keys['GD4']['census_names']
    refs = gd4.refs
    state = line_state(gd4.deal, 'medical')
    assert {state.results[refs[ref]]['reason'] for ref in ('P1', 'P2', 'P3')} == {'per_plan_counts_needed'}
    unmatched = [
        row['text'] for row in comparison(gd4.deal, 'medical')['enrollment']['texts'] if row['plan_id'] is None
    ]
    assert sorted(unmatched) == sorted(text for texts in hand.values() for text in texts)
    names = {str(refs[ref]): texts for ref, texts in hand.items()}
    services.set_enrollment(user, gd4.deal, 'medical', census_names=names)
    got = priced(gd4, 'medical')
    assert {ref: got[ref][:3] for ref in ('P1', 'P2', 'P3')} == {
        ref: (key[ref]['monthly'], key[ref]['annual'], key[ref]['enrollment']) for ref in ('P1', 'P2', 'P3')
    }
    assert {ref: got[ref][3] for ref in ('P1', 'P2', 'P3')} == dict.fromkeys(('P1', 'P2', 'P3'), 'census')
    for line, ref in (('dental', 'DN'), ('vision', 'VS')):  # one current plan, matched by its name
        assert priced(gd4, line)[ref][:2] == (key[ref]['monthly'], key[ref]['annual'])
