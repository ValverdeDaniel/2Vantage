"""Reviewing plan values (plan.md §10.7; E85–E89, F63, F65, F67, OQ28): quotes' marks writer, its Activity row and
its Revert, and `Plan.flags` kept equal to a rebuild after every service (Q.3 #9)."""

from datetime import UTC, datetime
from unittest import mock

import pytest
from rest_framework.exceptions import ValidationError

from conftest import make_deal
from deals import activity, clock
from deals.models import Activity
from quotes import facts, flags, services
from quotes.models import Plan
from quotes.services import review

from .review_world import add_file, read_into, world


@pytest.fixture
def w(user):
    return world(user)


def entry(plan, key):
    return Plan.objects.get(pk=plan.id).sources[key]


def stored(plan):
    return Plan.objects.get(pk=plan.id).flags


def leaves(value):
    """Every scalar inside a JSON value (dict keys left out), each whole."""
    if isinstance(value, dict):
        return [leaf for item in value.values() for leaf in leaves(item)]
    if isinstance(value, list):
        return [leaf for item in value for leaf in leaves(item)]
    return [value]


def test_OQ28_flags_count_only_doubted_and_unfound_read_values(w):
    assert stored(w['cigna']) == 2  # two doubted rates; the two values Claude was sure of need nothing
    assert stored(w['uhc']) == 1  # the rate the file does not print
    assert stored(w['current']) == 0  # typed
    assert flags.rebuild([w['deal'].id]) == []


def test_OQ28_a_typed_value_the_file_does_not_print_is_no_warning(user, w):
    services.update_plan(user, w['uhc'].id, {'values': {'rate_ee': '531'}})
    plan = Plan.objects.get(pk=w['uhc'].id)
    plan.sources['rate_ee']['loc'] = {'state': 'absent', 'v': 1}  # what a later check would say of it
    plan.save()
    assert plan.flags == 0 and plan.sources['rate_ee']['doc'] == w['doc'].id
    assert 'rate_ee' not in facts.statuses('medical', plan.values, plan.sources)


def test_E86_refs_name_exactly_those_values(user, w):
    cigna = w['cigna']
    marked = review.mark_values(user, w['deal'], 'check', refs=[f'plan:{cigna.id}:network'])
    assert [(plan.id, key) for plan, key in marked.values] == [(cigna.id, 'network')]
    assert entry(cigna, 'network')['mark']['state'] == 'check'
    assert stored(cigna) == 3  # a flag a person raised is an open warning, whatever the origin


def test_E86_plans_and_files_take_only_their_open_warnings(user, w):
    marked = review.mark_values(user, w['deal'], 'approve', plan_ids=[w['cigna'].id])
    assert sorted(key for _plan, key in marked.values) == ['rate_ee', 'rate_fam']
    assert stored(w['cigna']) == 0 and stored(w['uhc']) == 1
    marked = review.mark_values(user, w['deal'], 'ignore', document_ids=[w['doc'].id])
    assert [(plan.id, key) for plan, key in marked.values] == [(w['uhc'].id, 'rate_ee')]
    assert stored(w['uhc']) == 0


def test_E86_no_target_means_the_whole_deal_and_clear_takes_the_marked(user, w):
    marked = review.mark_values(user, w['deal'], 'check')
    assert len(marked.values) == 3
    cleared = review.mark_values(user, w['deal'], 'clear')
    assert len(cleared.values) == 3
    assert stored(w['cigna']) == 2 and stored(w['uhc']) == 1  # back to the reader's doubts


def test_E86_blank_values_take_no_mark(user, w):
    marked = review.mark_values(user, w['deal'], 'approve', refs=[f'plan:{w["cigna"].id}:oop_max_single'])
    assert marked.values == [] and marked.row is None


@pytest.mark.parametrize(
    'call',
    [
        {'refs': []},
        {'plan_ids': []},
        {'document_ids': []},
        {'refs': ['plan:x:rate_ee']},
        {'refs': ['member:4:dob']},
        {'plan_ids': ['one']},
    ],
)
def test_E86_bad_targets_answer_400(user, w, call):
    with pytest.raises(ValidationError):
        review.mark_values(user, w['deal'], 'approve', **call)


def test_E86_other_deals_and_fields_answer_400(user, w):
    other = make_deal(user, name='Other Co.')
    elsewhere = services.create_plan(user, other, line='medical', role='current', carrier='Aetna', name='PPO')
    for call in (
        {'refs': [f'plan:{elsewhere.id}:rate_ee']},
        {'plan_ids': [elsewhere.id]},
        {'document_ids': [add_file(user, other).id]},
        {'refs': [f'plan:{w["cigna"].id}:den_annual_max']},  # not a medical field
    ):
        with pytest.raises(ValidationError):
            review.mark_values(user, w['deal'], 'approve', **call)
    with pytest.raises(ValidationError):
        review.mark_values(user, w['deal'], 'confirm', plan_ids=[w['cigna'].id])


def test_E87_one_activity_row_that_holds_marks_never_values(user, w):
    at = datetime(2026, 11, 12, 15, 30, 5, 530530, tzinfo=UTC)  # the marks' time carries a value's digits, '530'
    with mock.patch.object(clock, 'now', return_value=at):
        marked = review.mark_values(user, w['deal'], 'approve', plan_ids=[w['cigna'].id, w['uhc'].id])
    row = marked.row
    assert row.action == 'marked' and row.area == 'quotes' and row.count == 3 and row.revertible
    keys = {key for change in row.changes for key in change['k']}
    assert keys == {'mark.rate_ee', 'mark.rate_fam'}
    for change in row.changes:
        for before, after in change['k'].values():
            assert before is None and set(after) == {'confirmed'}
    # Marks, never values (E74): no value anywhere in the row, each compared whole, never as a substring of the text,
    # where the marks' time ("….530…") or an id ("plan:1530") can carry a value's digits.
    held = set(leaves(row.changes)) | set(row.summary.split())
    assert not held & {'512.34', '1580.47', '530'}
    again = review.mark_values(user, w['deal'], 'check', refs=[f'plan:{w["cigna"].id}:rate_ee'])
    assert again.row.id != row.id  # review rows never merge


def test_E85_the_same_call_again_changes_nothing(user, w):
    ref = f'plan:{w["cigna"].id}:rate_ee'
    review.mark_values(user, w['deal'], 'ignore', refs=[ref])
    before, rows = entry(w['cigna'], 'rate_ee'), Activity.objects.count()
    updated = Plan.objects.get(pk=w['cigna'].id).updated_at
    again = review.mark_values(user, w['deal'], 'ignore', refs=[ref])
    assert again.values == [] and again.row is None
    assert entry(w['cigna'], 'rate_ee') == before and Activity.objects.count() == rows
    assert Plan.objects.get(pk=w['cigna'].id).updated_at == updated  # marks are bookkeeping


def test_E88_undo_restores_the_marks_once(user, w):
    cigna = w['cigna']
    review.mark_values(user, w['deal'], 'check', refs=[f'plan:{cigna.id}:rate_ee'])
    before = entry(cigna, 'rate_ee')
    row = review.mark_values(user, w['deal'], 'approve', plan_ids=[cigna.id]).row
    assert stored(cigna) == 0
    activity.revert(row.id, user)
    assert entry(cigna, 'rate_ee') == before and stored(cigna) == 2
    assert flags.rebuild([w['deal'].id]) == []
    with pytest.raises(activity.Refused) as refused:
        activity.revert(row.id, user)
    assert refused.value.sentence == activity.ALREADY_UNDONE


def test_F67_undo_an_ignore_with_clear(user, w):
    ref = f'plan:{w["uhc"].id}:rate_ee'
    review.mark_values(user, w['deal'], 'ignore', refs=[ref])
    assert stored(w['uhc']) == 0
    review.mark_values(user, w['deal'], 'clear', refs=[ref])
    assert 'mark' not in entry(w['uhc'], 'rate_ee') and stored(w['uhc']) == 1


def test_E88_undo_leaves_values_changed_since(user, w):
    cigna = w['cigna']
    row = review.mark_values(user, w['deal'], 'approve', plan_ids=[cigna.id]).row
    services.update_plan(user, cigna.id, {'values': {'rate_fam': '1590'}})  # a person retypes one of them
    written = activity.revert(row.id, user).changes
    assert [key for change in written for key in change['k']] == ['mark.rate_ee']
    assert 'confirmed' not in entry(cigna, 'rate_ee')
    assert entry(cigna, 'rate_fam')['origin'] == 'typed'  # left as the later write left it
    assert flags.rebuild([w['deal'].id]) == []


def test_E88_undo_is_refused_naming_the_values_when_every_one_changed(user, w):
    ref = f'plan:{w["uhc"].id}:rate_ee'
    row = review.mark_values(user, w['deal'], 'ignore', refs=[ref]).row
    review.mark_values(user, w['deal'], 'check', refs=[ref])
    with pytest.raises(activity.Refused) as refused:
        activity.revert(row.id, user)
    assert refused.value.keys == ['mark.rate_ee'] and 'Rate — EE' in refused.value.sentence


def test_E88_undo_on_a_sold_plan_is_refused(user, w):
    row = review.mark_values(user, w['deal'], 'approve', plan_ids=[w['cigna'].id]).row
    services.set_sold(user, w['cigna'].id, True)
    with pytest.raises(activity.Refused) as refused:
        activity.revert(row.id, user)
    assert 'marked sold' in refused.value.sentence


def test_E88_a_value_revert_is_not_blocked_by_a_later_review(user, w):
    plan, _ = services.update_plan(user, w['current'].id, {'values': {'deductible_single': '1000'}})
    review.mark_values(user, w['deal'], 'check', refs=[f'plan:{plan.id}:deductible_single'])
    activity.revert(plan.activity_id, user)  # marks sit under their own keys, so the edit still reverts
    assert 'deductible_single' not in Plan.objects.get(pk=plan.id).values


def test_Q3_9_flags_equal_a_rebuild_after_every_service(user, w):
    deal, cigna, uhc, current = w['deal'], w['cigna'], w['uhc'], w['current']

    def holds():
        assert flags.rebuild([deal.id]) == []

    copy = services.copy_plan(user, cigna.id)
    holds()
    renewal = services.create_renewal(user, current.id)
    holds()
    services.update_plan(user, cigna.id, {'values': {'rate_ee': '515'}})
    holds()
    marked = review.mark_values(user, deal, 'check', plan_ids=[uhc.id, copy.id])
    holds()
    services.merge_plans(user, deal, cigna.id, [copy.id])
    holds()
    moved, row = services.move_line(user, deal, [uhc.id], 'dental')
    holds()
    activity.revert(row.id, user)
    holds()
    removal = services.delete_plans(user, deal, [renewal.id])
    holds()
    activity.revert(removal.row.id, user)
    holds()
    activity.revert(marked.row.id, user)
    holds()
    assert moved and Plan.objects.filter(deal=deal).exclude(flags=0).exists()


def test_Q3_9_rebuild_facts_reports_and_puts_right_a_wrong_count(user, w):
    from io import StringIO

    from django.core.management import call_command
    from django.core.management.base import CommandError

    Plan.objects.filter(pk=w['cigna'].id).update(flags=9)
    out = StringIO()
    with pytest.raises(CommandError):
        call_command('rebuild_facts', '--deal', str(w['deal'].id), stdout=out)
    assert f'plan:{w["cigna"].id}: flags stored 9, rebuilt 2' in out.getvalue()
    assert stored(w['cigna']) == 9
    call_command('rebuild_facts', '--fix', stdout=StringIO())
    assert stored(w['cigna']) == 2


def test_E84_a_check_that_finds_a_value_missing_raises_the_count(user, w):
    from quotes import locate_hooks

    cigna = read_into(w['cigna'], {'oop_max_single': '6500'}, w['doc'])
    assert stored(cigna) == 2
    answer = [((cigna.id, 'oop_max_single', '6500'), {'state': 'absent', 'v': 1})]
    locate_hooks.save(user, w['deal'], w['doc'], answer)
    assert stored(cigna) == 3 and flags.rebuild([w['deal'].id]) == []
