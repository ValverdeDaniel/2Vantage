"""The Q.3 contracts for quotes (plan.md §12.3): GETs that write nothing, the permission matrix, and the write path of
every multi-plan door (one Activity row with before and after; the same call again changes nothing; Revert once, then
refused after a later write). The write path of plan values, details and enrollment is in test_revert.py; removal,
moves and merges in test_removal.py, test_moves.py and test_merge.py.
"""

import pytest

from conftest import check_permissions, make_deal, sweep_gets, write_path_contract
from quotes import services
from quotes.selectors.state import replaced_ids


@pytest.fixture
def world(user):
    deal = make_deal(user)
    current = services.create_plan(user, deal, line='medical', role='current', carrier='Aetna', name='HMO 1500')
    other = services.create_plan(user, deal, line='medical', role='current', carrier='Aetna', name='PPO 2000')
    alternate = services.create_plan(
        user, deal, line='medical', role='alternate', carrier='Cigna', name='Open Access', replaces_ids=[current.id]
    )
    second = services.create_plan(
        user, deal, line='medical', role='alternate', carrier='UHC', name='Choice', replaces_ids=[current.id]
    )
    package = services.create_package(user, deal, 'medical', 'Keep', [current.id])
    saved = services.saved_views.create(user, {'name': 'Shared setup', 'shared': True, 'config': {}})  # slice 10
    return {
        'deal': deal,
        'current': current,
        'other': other,
        'alternate': alternate,
        'second': second,
        'package': package,
        'saved': saved,
    }


def samples(world):
    deal, line = {'pk': world['deal'].id}, {'query': {'line': 'medical'}}
    return {
        'api/deals/<int:pk>/plans/lines/': deal,
        'api/deals/<int:pk>/plans/': {**deal, **line},
        'api/deals/<int:pk>/plans/star/': deal,
        'api/deals/<int:pk>/plans/shortlist/clear/': deal,
        'api/deals/<int:pk>/plans/role/': deal,
        'api/deals/<int:pk>/plans/links/': deal,
        'api/deals/<int:pk>/plans/order/': deal,
        'api/deals/<int:pk>/plans/slot/': deal,
        'api/deals/<int:pk>/plans/move-line/': deal,
        'api/deals/<int:pk>/plans/delete/': deal,
        'api/deals/<int:pk>/plans/clear/': deal,
        'api/deals/<int:pk>/plans/enrollment/': deal,
        'api/deals/<int:pk>/plans/packages/': {**deal, **line},
        'api/deals/<int:pk>/plans/template/': deal,
        'api/deals/<int:pk>/plans/import/': deal,
        'api/deals/<int:pk>/plans/board-export/': {**deal, **line},  # slice 9: ⤓ Export (F93)
        'api/plans/<int:plan_id>/': {'plan_id': world['alternate'].id},
        'api/plans/<int:plan_id>/source/': {'plan_id': world['current'].id, 'query': {'key': 'rate_ee'}},
        'api/plans/<int:plan_id>/renewal/': {'plan_id': world['current'].id},
        'api/plans/<int:plan_id>/copy/': {'plan_id': world['current'].id},
        'api/plans/<int:plan_id>/sold/': {'plan_id': world['alternate'].id},
        'api/plans/<int:plan_id>/recommend/': {'plan_id': world['alternate'].id},
        'api/packages/<int:package_id>/': {'package_id': world['package'].id},
        'api/deals/<int:pk>/plans/find/': deal,  # slice 10: the finder's index (F14)
        'api/saved-views/<int:view_id>/': {'view_id': world['saved'].id},  # slice 10: saved setups (F28)
        'api/deals/<int:pk>/plans/sources/': deal,  # slice 17: the station's List (E56)
        'api/deals/<int:pk>/plans/marks/': deal,  # slice 17: approve, ignore, check, clear (E85)
        'api/deals/<int:pk>/plans/priced/': deal,  # slice 35: priced versions (F76)
        'api/plans/<int:plan_id>/priced/': {'plan_id': world['alternate'].id},  # slice 35: ✎ re-price (F82)
        'api/deals/<int:pk>/plans/as-quoted/': deal,  # slice 21: the printed tables (F42, E42)
        'api/plans/<int:plan_id>/sbc/': {'plan_id': world['current'].id},  # slice 22: Attach SBC… (D38)
    }


FIVE_OFF = {'kind': 'concession', 'all': {'op': 'pct_off', 'value': 5}}


def ok(code=200):
    return {'signed_out': 401, 'producer': code, 'admin': code}


def matrix(world):
    current, alternate, second = world['current'], world['alternate'], world['second']
    medical = {'line': 'medical'}
    return [
        ('GET', 'api/deals/<int:pk>/plans/lines/', ok()),
        ('GET', 'api/deals/<int:pk>/plans/', ok()),
        (
            'POST',
            'api/deals/<int:pk>/plans/',
            ok(201),
            {'line': 'medical', 'role': 'current', 'carrier': 'UHC', 'name': 'Choice'},
        ),
        ('POST', 'api/deals/<int:pk>/plans/star/', ok(), {'plan_ids': [alternate.id], 'starred': True}),
        ('POST', 'api/deals/<int:pk>/plans/shortlist/clear/', ok(), medical),
        ('POST', 'api/deals/<int:pk>/plans/role/', ok(), {'plan_ids': [alternate.id], 'role': 'current'}),
        ('POST', 'api/deals/<int:pk>/plans/links/', ok(), {'plan_id': alternate.id, 'replaces_ids': []}),
        ('POST', 'api/deals/<int:pk>/plans/order/', ok(), {**medical, 'move': {'plan_id': second.id, 'step': -1}}),
        ('POST', 'api/deals/<int:pk>/plans/slot/', ok(), {**medical, 'plan_id': second.id, 'at': alternate.id}),
        ('POST', 'api/deals/<int:pk>/plans/move-line/', ok(), {'plan_ids': [second.id], 'line': 'dental'}),
        ('POST', 'api/deals/<int:pk>/plans/delete/', ok(), {'plan_ids': [second.id]}),
        ('POST', 'api/deals/<int:pk>/plans/clear/', ok(), medical),
        (
            'POST',
            'api/deals/<int:pk>/plans/enrollment/',
            ok(),
            {**medical, 'plans': [{'id': current.id, 'enrollment': {'EE': 4}}]},
        ),
        ('GET', 'api/deals/<int:pk>/plans/packages/', ok()),
        ('POST', 'api/deals/<int:pk>/plans/packages/', ok(201), {'name': 'Switch', 'plan_ids': []}),
        ('GET', 'api/deals/<int:pk>/plans/template/', ok()),
        ('POST', 'api/deals/<int:pk>/plans/import/', ok(400)),  # no file: refused after the permission check
        ('GET', 'api/deals/<int:pk>/plans/board-export/', ok()),  # slice 9: ⤓ Export (F93)
        ('GET', 'api/plans/<int:plan_id>/source/', ok()),  # slice 15: ↗ open in file (E18)
        ('PATCH', 'api/plans/<int:plan_id>/', ok(), {'values': {'rate_ee': '500'}}),
        ('POST', 'api/plans/<int:plan_id>/renewal/', ok(201)),
        ('POST', 'api/plans/<int:plan_id>/copy/', ok(201), {'name': 'HMO 1500 negotiated'}),
        ('POST', 'api/plans/<int:plan_id>/sold/', ok(), {'sold': True}),
        ('POST', 'api/plans/<int:plan_id>/recommend/', ok(), {'recommended': True}),
        ('PATCH', 'api/packages/<int:package_id>/', ok(), {'name': 'Keep all'}),
        ('DELETE', 'api/packages/<int:package_id>/', ok(204)),
        # slice 10: the finder's index and saved setups; the producer owns the shared setup, an admin may change it
        # (another person's private setup is 404 and a shared one 403: test_saved_views.py)
        ('GET', 'api/deals/<int:pk>/plans/find/', ok()),
        ('GET', 'api/saved-views/', ok()),
        ('POST', 'api/saved-views/', ok(201), {'name': 'New setup', 'config': {'find': 'UHC'}}),
        ('GET', 'api/saved-views/<int:view_id>/', ok()),
        ('PATCH', 'api/saved-views/<int:view_id>/', ok(), {'name': 'Renamed setup'}),
        ('DELETE', 'api/saved-views/<int:view_id>/', ok(204)),
        # slice 17: the station's List and the marks door (E56, E85); no open warning here, so nothing changes
        ('GET', 'api/deals/<int:pk>/plans/sources/', ok()),
        ('POST', 'api/deals/<int:pk>/plans/marks/', ok(), {'action': 'approve', 'plan_ids': [alternate.id]}),
        # slice 35: a priced version of a quote; ✎ on a plan that is not a version answers 409 past the permission check
        ('POST', 'api/deals/<int:pk>/plans/priced/', ok(201), {'plan_ids': [alternate.id], **FIVE_OFF}),
        ('POST', 'api/plans/<int:plan_id>/priced/', ok(409), {**FIVE_OFF, 'dry_run': True}),
        ('GET', 'api/deals/<int:pk>/plans/as-quoted/', ok()),  # slice 21: the printed tables (F42, E42)
        # slice 22: Attach SBC… reads nothing without a key (D26): refused before anything is stored
        ('POST', 'api/plans/<int:plan_id>/sbc/', ok(409)),
    ]


def test_Q3_quotes_gets_write_nothing(admin_api, world):
    sweep_gets(admin_api, ('quotes',), samples(world))


def test_Q3_quotes_permission_matrix(actors, no_csrf_api, world):
    check_permissions(actors, ('quotes',), matrix(world), samples(world), no_csrf_api)


def stars(plan):
    return (plan.starred, plan.star_reason, plan.starred_by_id)


def links(plan):
    return (plan.role, plan.renews_id, sorted(replaced_ids(from_plan_id=plan.id).get(plan.id, [])))


def test_F50_Q3_star_write_path(user, world):
    deal, plan = world['deal'], world['alternate']
    write_path_contract(
        user,
        plan,
        call=lambda: services.star(user, deal, [plan.id], True),
        read=stars,
        later=lambda: services.star(user, deal, [plan.id], False),
    )


def test_F55_Q3_clear_shortlist_write_path(user, world):
    deal, plan = world['deal'], world['alternate']
    services.star(user, deal, [plan.id, world['second'].id], True)
    write_path_contract(
        user,
        plan,
        call=lambda: services.clear_shortlist(user, deal, 'medical'),
        read=stars,
        later=lambda: services.star(user, deal, [plan.id], True),
    )


def test_OQ37_Q3_recommend_write_path(user, world):
    plan = world['alternate']
    write_path_contract(
        user,
        plan,
        call=lambda: services.set_recommended(user, plan.id, True),
        read=lambda p: p.recommended,
        later=lambda: services.set_recommended(user, plan.id, False),
    )


def test_F53_Q3_role_write_path(user, world):
    deal, plan = world['deal'], world['alternate']
    services.star(user, deal, [plan.id], True)
    write_path_contract(
        user,
        plan,
        call=lambda: services.set_role(user, deal, [plan.id], 'current'),
        read=lambda p: (links(p), stars(p)),
        later=lambda: services.set_role(user, deal, [plan.id], 'alternate', replaces_ids=[world['other'].id]),
    )


def test_F52_Q3_links_write_path(user, world):
    deal, plan = world['deal'], world['alternate']
    write_path_contract(
        user,
        plan,
        call=lambda: services.set_links(user, deal, plan.id, [world['current'].id, world['other'].id]),
        read=links,
        later=lambda: services.set_links(user, deal, plan.id, []),
    )


def test_F48_Q3_order_write_path(user, world):
    """A move is a step, so the contract's door is "Back to the default order": the same call again changes nothing."""
    deal, plan = world['deal'], world['second']
    services.arrange(user, deal, 'medical', ('move', plan.id, -1, None))
    write_path_contract(
        user,
        plan,
        call=lambda: services.arrange(user, deal, 'medical', ('reset',)),
        read=lambda p: p.sort_order,
        later=lambda: services.arrange(user, deal, 'medical', ('move', plan.id, -1, None)),
    )


def test_F46_Q3_slot_write_path(user, world):
    """ "＋ Add a plan" beside a current plan: on the proposal, linked to that plan, last among its quotes."""
    deal, picked = world['deal'], world['second']
    services.star(user, deal, [world['alternate'].id], True)

    def state(plan):
        return (stars(plan), links(plan), plan.sort_order)

    write_path_contract(
        user,
        picked,
        call=lambda: services.put_in_slot(user, deal, 'medical', picked.id, beside=world['other'].id),
        read=state,
        later=lambda: services.star(user, deal, [picked.id], False),
    )


def test_Q3_order_rows_record_only_sort_order(user, world):
    deal = world['deal']
    _, row = services.arrange(user, deal, 'medical', ('move', world['second'].id, -1, None))
    assert {key for entry in row.changes for key in entry['k']} == {'plan.sort_order'}
    passed = {f'plan:{world["second"].id}', f'plan:{world["alternate"].id}'}
    assert {entry['t'] for entry in row.changes} == passed  # the plan and the one it passed; nothing else
