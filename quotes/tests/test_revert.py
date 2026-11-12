"""Revert of plan values and enrollment, and slice 5's "done when" (plan.md §3.7, §13.6 row 5; A34, E54, F141).

The deal is shaped like GD1: a current medical plan whose rates and deductible were read from a carrier file
(origin ai, with the file, page, printed line and read value), as the reader will write them (slice 17).
"""

import pytest
from django.db import transaction

from conftest import write_path_contract
from contract_helpers import later_clock
from deals import activity
from deals.models import Activity
from deals.values import apply as apply_values
from deals.values import locked, source
from documents.models import Document
from quotes import services
from quotes.models import Plan

READ = {'rate_ee': '612.50', 'rate_es': '1287.40', 'deductible_single': '3300'}


def read_from_file(plan, document, values, page=2):
    """What the reader stores: each value with its file, page, printed line and read value."""
    with transaction.atomic():
        plan = locked(Plan, plan.id)
        for key, value in values.items():
            entry = source('ai', doc=document.id, page=page, line=f'{key} {value}', read_value=value, low='blurred')
            entry['loc'] = {'state': 'found', 'page': page, 'hits': 1}
            apply_values(plan.values, plan.sources, {key: value}, entry)
        plan.save()
    return plan


@pytest.fixture
def document(deal, user):
    return Document.objects.create(deal=deal, original_name='renewal.pdf', kind='renewal', uploaded_by=user)


@pytest.fixture
def plan(user, deal, document):
    current = services.create_plan(user, deal, line='medical', role='current', carrier='Aetna', name='HMO 1500')
    return read_from_file(current, document, READ)


def patch(api, plan, values):
    response = api.patch(f'/api/plans/{plan.id}/', {'values': values}, format='json')
    assert response.status_code == 200, response.json()
    return response.json()


def revert(api, activity_id):
    return api.post(f'/api/activity/{activity_id}/revert/')


def fresh(plan):
    return Plan.objects.get(pk=plan.pk)


def test_F141_a_hand_edit_over_a_read_value_keeps_its_file(api, plan, document):
    patch(api, plan, {'rate_ee': '640'})
    entry = fresh(plan).sources['rate_ee']
    assert entry['origin'] == 'typed' and fresh(plan).values['rate_ee'] == '640'
    assert (entry['doc'], entry['page'], entry['read_value']) == (document.id, 2, '612.50')  # ↗ still opens the file
    assert 'low' not in entry and 'loc' not in entry


def test_A34_done_when_revert_restores_a_plan_value_then_says_already_undone(api, plan, document):
    edited = patch(api, plan, {'rate_ee': '640'})
    response = revert(api, edited['activity_id'])
    assert response.status_code == 200, response.json()
    restored = fresh(plan)
    assert restored.values['rate_ee'] == '612.50'
    assert restored.sources['rate_ee']['origin'] == 'ai' and restored.sources['rate_ee']['doc'] == document.id
    again = revert(api, edited['activity_id'])
    assert again.status_code == 409 and again.json()['detail'] == 'This change was already undone.'


def test_A34_done_when_revert_after_a_later_edit_is_refused_naming_the_keys(api, plan):
    first = patch(api, plan, {'rate_ee': '640', 'deductible_single': '3500'})
    with later_clock():
        patch(api, plan, {'rate_ee': '650'})
    response = revert(api, first['activity_id'])
    assert response.status_code == 409
    assert response.json() == {
        'detail': 'Rate — EE was changed after this, so this change cannot be reverted.',
        'keys': ['rate_ee'],
    }
    assert fresh(plan).values['rate_ee'] == '650' and fresh(plan).values['deductible_single'] == '3500'


def test_A34_a_burst_of_edits_reverts_together_to_the_first_values(api, plan):
    first = patch(api, plan, {'rate_ee': '640'})
    second = patch(api, plan, {'rate_ee': '645', 'rate_es': '1300'})
    assert second['activity_id'] == first['activity_id']
    row = Activity.objects.get(pk=first['activity_id'])
    assert row.changes == [
        {'t': f'plan:{plan.id}', 'k': {'rate_ee': ['612.50', '645'], 'rate_es': ['1287.40', '1300']}}
    ]
    assert revert(api, row.id).status_code == 200
    assert {k: fresh(plan).values[k] for k in ('rate_ee', 'rate_es')} == {'rate_ee': '612.50', 'rate_es': '1287.40'}


def test_E54_a_write_that_can_be_undone_returns_its_activity_id(api, deal, plan):
    assert patch(api, plan, {'rate_ee': '640'})['activity_id']
    assert patch(api, plan, {'rate_ee': '640'})['activity_id'] is None  # nothing changed, nothing to undo
    response = api.post(
        f'/api/deals/{deal.id}/plans/enrollment/',
        {'line': 'medical', 'plans': [{'id': plan.id, 'enrollment': {'EE': 10, 'ES': 3, 'EC': 2, 'FAM': 5}}]},
        format='json',
    )
    assert Activity.objects.get(pk=response.json()['activity_id']).area == 'enrollment'


def test_A34_a_sold_plan_refuses_revert_with_a_sentence(api, plan):
    edited = patch(api, plan, {'rate_ee': '640'})
    Plan.objects.filter(pk=plan.pk).update(sold=True)
    response = revert(api, edited['activity_id'])
    assert response.status_code == 409
    assert (
        response.json()['detail']
        == 'Aetna HMO 1500 is marked sold, so this change cannot be reverted. Un-sell it first.'
    )
    assert fresh(plan).values['rate_ee'] == '640'


def test_A34_adding_a_plan_is_not_reverted_nor_an_edit_to_a_removed_plan(api, user, deal, plan):
    added = Activity.objects.filter(deal=deal, action='created', area='quotes').latest('id')
    assert revert(api, added.id).json()['detail'] == activity.NOTHING_TO_PUT_BACK
    alternate = services.create_plan(user, deal, line='medical', role='alternate', carrier='Cigna', name='Open Access')
    edited, _ = services.update_plan(user, alternate.id, {'values': {'rate_ee': '500'}})
    services.delete_plans(user, deal, [alternate.id])
    assert 'has been removed' in revert(api, edited.activity_id).json()['detail']


def test_F53_a_role_change_reverts_with_its_star_and_links(api, user, deal, plan):
    alternate = services.create_plan(
        user, deal, line='medical', role='alternate', carrier='Cigna', name='Open Access', replaces_ids=[plan.id]
    )
    services.star(user, deal, [alternate.id], True)
    _, row = services.set_role(user, deal, [alternate.id], 'current')
    assert fresh(alternate).role == 'current' and not fresh(alternate).starred
    assert revert(api, row.id).status_code == 200
    back = fresh(alternate)
    assert (back.role, back.starred, back.star_reason) == ('alternate', True, 'Hand-picked')
    assert list(back.replaces.values_list('id', flat=True)) == [plan.id]


def test_F53_a_revert_that_would_break_a_line_is_refused_with_a_sentence(api, user, deal, plan):
    renewal = services.create_renewal(user, plan.id)
    _, row = services.set_role(user, deal, [renewal.id], 'alternate')
    services.create_renewal(user, plan.id)  # a new renewal takes the plan's one place
    response = revert(api, row.id)
    assert response.status_code == 409
    assert response.json()['detail'] == 'This change cannot be reverted: Aetna HMO 1500 already has a renewal.'


def test_Q3_plan_values_write_path(user, plan):
    write_path_contract(
        user,
        plan,
        call=lambda: services.update_plan(user, plan.id, {'values': {'rate_ee': '640', 'pcp_copay': '25'}}),
        read=lambda p: (p.values, {k: p.sources[k].get('doc') for k in p.values}),
        later=lambda: services.update_plan(user, plan.id, {'values': {'pcp_copay': '30'}}),
    )


def test_Q3_plan_details_write_path(user, plan):
    write_path_contract(
        user,
        plan,
        call=lambda: services.update_plan(user, plan.id, {'name': 'HMO 1500 Plus', 'notes': 'Ask about the network'}),
        read=lambda p: (p.name, p.notes),
        later=lambda: services.update_plan(user, plan.id, {'name': 'HMO 2000'}),
    )


def test_Q3_enrollment_write_path(user, deal, plan):
    def enroll(counts):
        return lambda: services.set_enrollment(user, deal, 'medical', plans=[{'id': plan.id, 'enrollment': counts}])

    write_path_contract(
        user,
        plan,
        call=enroll({'EE': 10, 'ES': 3, 'EC': 2, 'FAM': 5}),
        read=lambda p: p.enrollment,
        later=enroll({'EE': 11, 'ES': 3, 'EC': 2, 'FAM': 5}),
    )


def test_rule10_lasers_enter_activity_as_their_key_only(api, user, deal):
    """Lasers are claimant data (PHI, rule 10, plan.md §3.8): an edit records `sl_lasers` by key alone, never its
    before or after, while the other keys of the same edit keep theirs; a row with a hidden key cannot be reverted."""
    stop_loss = services.create_plan(user, deal, line='stop_loss', role='current', carrier='Sun Life', name='Spec')
    body = patch(api, stop_loss, {'sl_lasers': 'ZZQ-LASER-ONE ZZQ-LASER-TWO', 'sl_spec_deductible': '50000'})
    row = Activity.objects.get(pk=body['activity_id'])
    assert 'ZZQ-LASER' not in str(row.changes)
    hidden = [entry['k'] for entry in row.changes if isinstance(entry['k'], list)]
    assert hidden == [['sl_lasers']]
    kept = [entry['k'] for entry in row.changes if isinstance(entry['k'], dict)]
    assert kept and all('sl_lasers' not in keys for keys in kept)
    assert revert(api, row.id).status_code == 409
