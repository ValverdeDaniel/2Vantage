"""The order and slot doors through the API (plan.md §5.4, §7.8; F43–F48, F120, J4–J11; OQ13; slice 7's "done when")."""

import pytest

from deals.models import Activity
from quotes import services
from quotes.models import Plan


def make(user, deal, line, role, name, **links):
    return services.create_plan(user, deal, line=line, role=role, carrier='Carrier', name=name, **links)


@pytest.fixture
def medical(user, deal):
    a = make(user, deal, 'medical', 'current', 'A')
    b = make(user, deal, 'medical', 'current', 'B')
    x = make(user, deal, 'medical', 'alternate', 'X', replaces_ids=[a.id])
    y = make(user, deal, 'medical', 'alternate', 'Y', replaces_ids=[b.id])
    z = make(user, deal, 'medical', 'alternate', 'Z', replaces_ids=[a.id])
    renewal = services.create_renewal(user, a.id)
    return {'a': a, 'b': b, 'x': x, 'y': y, 'z': z, 'renewal': renewal}


def comparison_ids(api, deal, line='medical'):
    return [p['id'] for p in api.get(f'/api/deals/{deal.id}/plans/?line={line}').json()['plans']]


def order(api, deal, line='medical', **how):
    return api.post(f'/api/deals/{deal.id}/plans/order/', {'line': line, **how}, format='json')


def test_F120_the_comparison_comes_in_the_one_order(api, deal, medical):
    m = medical
    # The current plans, then each one's group (the renewal leads it, arriving after the quotes), unlinked last.
    assert comparison_ids(api, deal) == [m['a'].id, m['b'].id, m['renewal'].id, m['x'].id, m['z'].id, m['y'].id]


def test_F120_done_when_a_rate_edit_moves_nothing(api, user, deal, medical):
    before = comparison_ids(api, deal)
    for name, rate in (('x', '900'), ('z', '100'), ('y', '50')):
        api.patch(f'/api/plans/{medical[name].id}/', {'values': {'rate_ee': rate}}, format='json')
    assert comparison_ids(api, deal) == before


def test_F43_move_answers_the_new_order_and_one_revertible_row(api, deal, medical):
    m = medical
    body = order(api, deal, move={'plan_id': m['z'].id, 'step': -1}).json()
    assert body['order'] == [m['a'].id, m['b'].id, m['renewal'].id, m['z'].id, m['x'].id, m['y'].id]
    assert comparison_ids(api, deal) == body['order']
    row = Activity.objects.get(pk=body['activity_id'])
    assert row.summary == 'Moved Carrier Z earlier on Medical' and row.revertible
    assert api.post(f'/api/activity/{row.id}/revert/').status_code == 200
    assert comparison_ids(api, deal)[3:5] == [m['x'].id, m['z'].id]


def test_F43_a_refused_move_says_why(api, deal, medical):
    refused = order(api, deal, move={'plan_id': medical['z'].id, 'step': 1})
    assert refused.status_code == 409
    assert refused.json() == {'detail': 'Carrier Z is already last among the plans compared with Carrier A.'}


def test_F43_a_move_passes_the_plans_the_screen_hides(api, deal, medical):
    m = medical
    shown = [m['a'].id, m['b'].id, m['renewal'].id, m['z'].id]
    body = order(api, deal, move={'plan_id': m['z'].id, 'step': -1, 'among': shown}).json()
    assert body['order'][2:5] == [m['z'].id, m['renewal'].id, m['x'].id]  # past hidden X, in front of the renewal


def test_F44_a_current_plan_moves_as_a_slot_and_its_group_follows(api, deal, medical):
    m = medical
    body = order(api, deal, move={'plan_id': m['b'].id, 'step': -1}).json()
    assert body['order'] == [m['b'].id, m['a'].id, m['y'].id, m['renewal'].id, m['x'].id, m['z'].id]


def test_F48_back_to_the_default_order(api, deal, medical):
    m = medical
    order(api, deal, swap=[m['x'].id, m['z'].id])
    body = order(api, deal, reset=True).json()
    assert body['order'] == [m['a'].id, m['b'].id, m['renewal'].id, m['x'].id, m['z'].id, m['y'].id]
    assert order(api, deal, reset=True).json()['activity_id'] is None  # already in it: nothing written


def test_OQ13_a_stop_loss_quote_moves_with_the_arrows_and_takes_a_slot_pick(api, user, deal):
    current = make(user, deal, 'stop_loss', 'current', 'Contract')
    first = make(user, deal, 'stop_loss', 'alternate', 'First')
    second = make(user, deal, 'stop_loss', 'alternate', 'Second')
    moved = order(api, deal, line='stop_loss', move={'plan_id': second.id, 'step': -1}).json()
    assert moved['order'] == [current.id, second.id, first.id]
    services.star(user, deal, [second.id], True)
    picked = api.post(
        f'/api/deals/{deal.id}/plans/slot/', {'line': 'stop_loss', 'plan_id': first.id, 'at': second.id}, format='json'
    ).json()
    assert picked['order'] == [current.id, first.id, second.id]
    assert Plan.objects.get(pk=first.id).starred and not Plan.objects.get(pk=second.id).starred


def test_F45_a_pick_takes_the_spots_place_star_and_links(api, user, deal, medical):
    m = medical
    services.star(user, deal, [m['x'].id], True)
    services.set_recommended(user, m['x'].id, True)
    body = api.post(
        f'/api/deals/{deal.id}/plans/slot/', {'line': 'medical', 'plan_id': m['y'].id, 'at': m['x'].id}, format='json'
    ).json()
    y, x = Plan.objects.get(pk=m['y'].id), Plan.objects.get(pk=m['x'].id)
    assert (y.starred, y.star_reason, list(y.replaces.values_list('id', flat=True))) == (
        True,
        'Hand-picked',
        [m['a'].id],
    )
    assert (x.starred, x.recommended) == (False, False)  # the plan that leaves loses its pick
    assert body['order'].index(y.id) < body['order'].index(m['z'].id)  # in X's place, in A's group
    assert Plan.objects.filter(deal=deal, starred=True).count() == 1  # the star count never changes
    assert Activity.objects.get(pk=body['activity_id']).summary == (
        'Put Carrier Y in the place of Carrier X on the Medical proposal'
    )


def test_F46_add_a_plan_beside_a_current_plan(api, user, deal, medical):
    m = medical
    services.star(user, deal, [m['x'].id], True)
    body = api.post(
        f'/api/deals/{deal.id}/plans/slot/',
        {'line': 'medical', 'plan_id': m['z'].id, 'beside': m['b'].id},
        format='json',
    ).json()
    z = Plan.objects.get(pk=m['z'].id)
    assert z.starred and list(z.replaces.values_list('id', flat=True)) == [m['b'].id]
    assert body['order'][-1] == z.id  # last among the plans compared with B
