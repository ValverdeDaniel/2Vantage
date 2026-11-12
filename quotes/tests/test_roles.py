"""Roles, links and the limited PATCH through the API (plan.md §5.4, §7.8; F52, F53, F71, J74; slice 7 "done when")."""

import pytest

from deals.models import Activity
from quotes import services
from quotes.models import Plan


@pytest.fixture
def line(user, deal):
    a = services.create_plan(user, deal, line='medical', role='current', carrier='Aetna', name='HDHP 3300')
    b = services.create_plan(user, deal, line='medical', role='current', carrier='Aetna', name='PPO 1500')
    renewal = services.create_renewal(user, a.id)
    quote = services.create_plan(
        user, deal, line='medical', role='alternate', carrier='Cigna', name='LocalPlus', replaces_ids=[a.id]
    )
    return {'a': a, 'b': b, 'renewal': renewal, 'quote': quote}


def role(api, deal, plans, to, **links):
    return api.post(
        f'/api/deals/{deal.id}/plans/role/', {'plan_ids': [p.id for p in plans], 'role': to, **links}, format='json'
    )


def links_of(plan):
    return sorted(Plan.objects.get(pk=plan.id).replaces.values_list('id', flat=True))


def test_F53_done_when_a_starred_quote_made_current_loses_its_star_and_links(api, user, deal, line):
    quote = line['quote']
    services.star(user, deal, [quote.id], True)
    services.set_recommended(user, quote.id, True)
    body = role(api, deal, [quote], 'current').json()
    after = Plan.objects.get(pk=quote.id)
    assert (after.role, after.starred, after.star_reason) == ('current', False, '')
    assert after.recommended  # OQ37: a recommended plan made current means "Keep this plan", as in the old app
    assert links_of(quote) == [] and after.renews_id is None
    current_ids = list(
        Plan.objects.filter(deal=deal, role='current').order_by('sort_order').values_list('id', flat=True)
    )
    assert current_ids[-1] == quote.id  # it joins the end of the current plans
    assert Activity.objects.get(pk=body['activity_id']).summary == 'Made Cigna LocalPlus current'


def test_F53_a_plan_that_stops_being_current_turns_its_renewal_into_an_alternate(api, deal, line):
    body = role(api, deal, [line['a']], 'alternate', replaces_ids=[line['b'].id]).json()
    renewal = Plan.objects.get(pk=line['renewal'].id)
    assert (renewal.role, renewal.renews_id) == ('alternate', None)
    assert links_of(line['quote']) == []  # it left every replaces list
    assert links_of(line['a']) == [line['b'].id]
    assert {p['id'] for p in body['plans']} == {line['a'].id, line['renewal'].id, line['quote'].id}


@pytest.mark.parametrize(
    'case, sold, derived, sentence',
    [
        (
            'a sold plan',
            True,
            {},
            "Cigna LocalPlus is sold: the plan the client is buying can't also be the plan they have in force today.",
        ),
        (
            'a priced version',
            False,
            {'kind': 'concession'},
            "Cigna LocalPlus is a priced version: the plan in force is the carrier's own column.",
        ),
    ],
)
def test_F53_what_never_becomes_current(api, deal, line, case, sold, derived, sentence):
    Plan.objects.filter(pk=line['quote'].id).update(
        sold=sold, derived=derived, derived_from=line['a'] if derived else None
    )
    refused = role(api, deal, [line['quote']], 'current')
    assert (refused.status_code, refused.json()) == (409, {'detail': sentence}), case


def test_F53_a_renewal_needs_its_plan_and_one_renewal_each(api, deal, line):
    assert role(api, deal, [line['quote']], 'renewal').status_code == 400
    taken = role(api, deal, [line['quote']], 'renewal', renews_id=line['a'].id)
    assert taken.status_code == 400 and 'HDHP 3300 already has a renewal.' in str(taken.json())
    made = role(api, deal, [line['quote']], 'renewal', renews_id=line['b'].id)
    assert made.status_code == 200 and Plan.objects.get(pk=line['quote'].id).renews_id == line['b'].id


def test_F52_links_name_none_one_or_several_current_plans(api, deal, line):
    url = f'/api/deals/{deal.id}/plans/links/'
    quote = line['quote']
    several = api.post(url, {'plan_id': quote.id, 'replaces_ids': [line['a'].id, line['b'].id]}, format='json')
    assert several.status_code == 200 and links_of(quote) == sorted([line['a'].id, line['b'].id])
    assert api.post(url, {'plan_id': quote.id, 'replaces_ids': []}, format='json').status_code == 200
    assert links_of(quote) == []
    not_current = api.post(url, {'plan_id': quote.id, 'replaces_ids': [line['renewal'].id]}, format='json')
    assert not_current.status_code == 400
    current = api.post(url, {'plan_id': line['a'].id, 'replaces_ids': []}, format='json')
    assert current.json() == {'detail': 'Aetna HDHP 3300 is a current plan: only a proposed plan takes a link.'}
    again = api.post(url, {'plan_id': quote.id, 'replaces_ids': []}, format='json').json()
    assert again == {'plans': [], 'activity_id': None}  # an unchanged write writes nothing


def test_F71_PATCH_ignores_role_star_and_links(api, deal, line):
    quote = line['quote']
    response = api.patch(
        f'/api/plans/{quote.id}/',
        {
            'role': 'current',
            'starred': True,
            'replaces_ids': [],
            'recommended': True,
            'sold': True,
            'name': 'LocalPlus 2',
        },
        format='json',
    )
    after = Plan.objects.get(pk=quote.id)
    assert response.status_code == 200 and after.name == 'LocalPlus 2'
    assert (after.role, after.starred, after.recommended, after.sold) == ('alternate', False, False, False)
    assert links_of(quote) == [line['a'].id]


def test_J14_PATCH_takes_the_name_on_client_documents(api, line):
    response = api.patch(f'/api/plans/{line["quote"].id}/', {'client_name': 'Option A — LocalPlus'}, format='json')
    assert response.json()['client_name'] == 'Option A — LocalPlus'


def test_J74_a_stale_expect_refuses_the_write_naming_the_keys(api, user, line):
    quote = line['quote']
    services.update_plan(user, quote.id, {'values': {'rate_ee': '500'}})
    stale = api.patch(
        f'/api/plans/{quote.id}/', {'values': {'rate_ee': '520'}, 'expect': {'rate_ee': '480'}}, format='json'
    )
    assert stale.status_code == 409
    assert stale.json() == {
        'detail': 'Rate — EE changed since you last saw it, so nothing was saved. Reload to see the new value.',
        'keys': ['rate_ee'],
    }
    assert Plan.objects.get(pk=quote.id).values['rate_ee'] == '500'
    fresh = api.patch(
        f'/api/plans/{quote.id}/', {'values': {'rate_ee': '520'}, 'expect': {'rate_ee': '500'}}, format='json'
    )
    assert fresh.status_code == 200 and fresh.json()['values']['rate_ee'] == '520'


@pytest.mark.parametrize(
    'path, body',
    [
        ('plans/role/', {'plan_ids': ['x'], 'role': 'current'}),
        ('plans/links/', {'plan_id': None}),
        ('plans/star/', {'plan_ids': 'all', 'starred': True}),
        ('plans/order/', {'line': 'medical', 'move': {'plan_id': 'x', 'step': 1}}),
        ('plans/slot/', {'line': 'medical', 'plan_id': '1.5'}),
        ('plans/', {'line': 'medical', 'role': 'renewal', 'carrier': 'A', 'name': 'B', 'renews_id': 'one'}),
    ],
)
def test_3_6_a_bad_id_answers_400_never_500(api, deal, line, path, body):
    assert api.post(f'/api/deals/{deal.id}/{path}', body, format='json').status_code == 400
