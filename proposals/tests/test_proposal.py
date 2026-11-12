"""Proposal selection and configuration (plan.md §7.9, §8.12)."""

from quotes import services as plans


def setup_line(user, deal):
    a = plans.create_plan(
        user, deal, line='medical', role='current', carrier='Aetna', name='HDHP', values={'rate_ee': '500'}
    )
    renewal = plans.create_renewal(user, a.id)
    x = plans.create_plan(
        user,
        deal,
        line='medical',
        role='alternate',
        carrier='Cigna',
        name='X',
        replaces_ids=[a.id],
        values={'rate_ee': '450'},
    )
    y = plans.create_plan(
        user,
        deal,
        line='medical',
        role='alternate',
        carrier='UHC',
        name='Y',
        replaces_ids=[a.id],
        values={'rate_ee': '440'},
    )
    z = plans.create_plan(user, deal, line='medical', role='alternate', carrier='Cigna', name='Z', replaces_ids=[a.id])
    plans.set_enrollment(user, deal, [{'id': a.id, 'enrollment': {'EE': 10}, 'on': True}])
    return a, renewal, x, y, z


def medical(api, deal):
    return next(
        line for line in api.get(f'/api/deals/{deal.id}/proposal/').json()['lines'] if line['line'] == 'medical'
    )


def test_F119_F120_the_proposal_presents_quotes_set_in_their_one_order(api, user, deal):
    """Rewritten in slice 7 (Q.3 #10): 2V's carrier sort and its own membership list retired; the proposal reads
    quotes' `presented()` and `order.layout()`."""
    a, renewal, x, y, z = setup_line(user, deal)
    line = medical(api, deal)
    assert line['is_default'] and line['plan_ids'] == [a.id, renewal.id, x.id, y.id, z.id]  # as added, not by carrier
    plans.star(user, deal, [y.id], True)
    assert medical(api, deal)['plan_ids'] == [a.id, y.id]  # OQ11: a starred line prints its renewal only when picked
    plans.set_recommended(user, renewal.id, True)
    assert medical(api, deal)['plan_ids'] == [a.id, renewal.id, y.id]


def test_J13_taking_a_plan_off_an_unstarred_line_stars_every_other_quote(api, user, deal):
    a, renewal, x, y, z = setup_line(user, deal)
    response = api.put(
        f'/api/deals/{deal.id}/proposal/', {'lines': {'medical': [a.id, renewal.id, x.id, z.id]}}, format='json'
    )
    assert response.status_code == 200
    line = medical(api, deal)
    assert line['plan_ids'] == [a.id, renewal.id, x.id, z.id] and line['is_default'] is False
    assert api.put(f'/api/deals/{deal.id}/proposal/', {'lines': {'medical': []}}, format='json').status_code == 200
    assert medical(api, deal)['is_default'] is True  # an empty list clears the line's shortlist (F55)


def test_F43_the_proposal_arrows_move_a_plan_with_the_order_door(api, user, deal):
    a, renewal, x, y, z = setup_line(user, deal)
    swapped = [a.id, renewal.id, y.id, x.id, z.id]
    assert api.put(f'/api/deals/{deal.id}/proposal/', {'lines': {'medical': swapped}}, format='json').status_code == 200
    assert medical(api, deal)['plan_ids'] == swapped


def test_current_and_recommended_plans_cannot_be_dropped(api, user, deal):
    a, renewal, x, y, z = setup_line(user, deal)
    plans.set_recommended(user, x.id, True)
    response = api.put(f'/api/deals/{deal.id}/proposal/', {'lines': {'medical': [y.id]}}, format='json')
    assert response.status_code == 200
    line = medical(api, deal)
    assert set(line['plan_ids']) == {a.id, x.id, y.id} and line['is_default'] is False


def test_issue_blockers_name_the_uncovered_plan(api, user, deal):
    setup_line(user, deal)
    body = api.get(f'/api/deals/{deal.id}/proposal/').json()
    assert body['issue_blockers'] == ['Medical: Nothing recommended for HDHP']
    assert body['can_issue'] is False


def test_config_validation(api, user, deal):
    setup_line(user, deal)
    other = plans.create_plan(user, deal, line='dental', role='current', carrier='Guardian', name='D')
    bad = api.put(f'/api/deals/{deal.id}/proposal/', {'lines': {'medical': [other.id]}}, format='json')
    assert bad.status_code == 400
    long = api.put(f'/api/deals/{deal.id}/proposal/', {'reasons': {'medical': 'x' * 2001}}, format='json')
    assert long.status_code == 400
    ok = api.put(
        f'/api/deals/{deal.id}/proposal/', {'title': 'Plan year 2027', 'reasons': {'medical': 'Why'}}, format='json'
    )
    assert ok.json()['title'] == 'Plan year 2027' and ok.json()['reasons'] == {'medical': 'Why'}


def test_unpriced_plans_warn(api, user, deal):
    _, renewal, *_ = setup_line(user, deal)
    plans.update_plan(user, renewal.id, {'values': {'rate_ee': '540'}})  # Create renewal copies no rates
    warnings = api.get(f'/api/deals/{deal.id}/proposal/').json()['warnings']
    assert warnings == ['Medical: 1 plan has no price — enter enrollment in the Advisor']


def test_OQ37_a_recommended_current_plan_prints_keep_this_plan(api, user, deal):
    a, *_ = setup_line(user, deal)
    plans.set_recommended(user, a.id, True)
    body = api.get(f'/api/deals/{deal.id}/proposal/').json()
    group = medical(api, deal)['preview']['summary']['groups'][0]
    assert group['options'][0]['plan_id'] == a.id and group['options'][0]['note'] == 'Keep this plan'
    assert body['issue_blockers'] == [] and body['can_issue'] is True
