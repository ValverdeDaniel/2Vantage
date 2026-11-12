"""Claude's plan tools in a chat turn on GD1 (plan.md §10.6, §13.7 row 24 "done when"; D80, D85, D86, D88, D92, F61,
F108–F110, F114; Q.9 row 24: `set_board` writes nothing, `clear_line` stages, string tool inputs parsed). Every turn
runs inline with the fake client: Claude's tool calls are scripted, the tools and landings are the real ones. Writes
roll back with each test, so GD1 stays as built."""

import pytest

from accounts.models import Profile
from ai import land, services
from ai.models import Job
from ai.testing import text_block, tool_block, turn_key
from deals.models import Activity
from quotes.models import Plan
from quotes.services.copies import copy_plan
from quotes.services.marks import set_sold

pytestmark = pytest.mark.django_db

PPOS = 'Show PPOs under $40,000 a month'
DELETE = 'Delete the duplicate Aetna plan'


@pytest.fixture
def direct(db):
    from django.contrib.auth import get_user_model

    person = get_user_model().objects.create_user('dee', 'dee@example.com', 'pw-Example-1')
    Profile.objects.create(user=person, claude_direct=True)
    return person


def turn(fake, person, deal, words, *calls, reply='Done.', **page):
    fake.record(
        turn_key(words, 1), content=[tool_block(name, data, f'toolu_{n}') for n, (name, data) in enumerate(calls)]
    )
    fake.record(turn_key(words, 2), content=[text_block(reply)])
    _chat, _message, job = services.send_message(person, deal, text=words, **page)
    job.refresh_from_db()
    return job


def answers(fake):
    """What the tools said back to Claude in the last round."""
    return [block['content'] for block in fake.log[-1]['params']['messages'][-1]['content']]


def test_D80_F108_show_ppos_under_40000_sets_the_board_and_writes_nothing(gd1, user, fake_claude):
    rules = [
        {'key': 'plan_type', 'op': 'contains', 'value': 'PPO', 'line': ''},
        {'key': 'total', 'op': '<=', 'value': '$40,000', 'line': ''},  # a number as text is read (Q.9)
    ]
    before = (Activity.objects.count(), list(Plan.objects.filter(deal=gd1.deal).values_list('values', flat=True)))
    job = turn(fake_claude, user, gd1.deal, PPOS, ('set_board', {'line': 'medical', 'rules': rules}), tab='advisor')
    assert job.result['board'] == {
        'line': 'medical',
        'clear': False,
        'config': {
            'rules': [
                {'key': 'plan_type', 'op': 'contains', 'value': 'PPO'},
                {'key': 'total', 'op': '<=', 'value': 40000, 'line': 'medical'},  # the total is capped per line (F19)
            ]
        },
    }
    assert job.result['items'] == [] and job.land == ''
    assert (
        Activity.objects.count(),
        list(Plan.objects.filter(deal=gd1.deal).values_list('values', flat=True)),
    ) == before
    assert 'Nothing on the deal changes' in answers(fake_claude)[0]


def test_F110_F25_F109_a_bad_setting_is_refused_in_words_and_a_pick_names_only_listed_plans(gd1, user, fake_claude):
    refs = gd1.refs
    job = turn(
        fake_claude,
        user,
        gd1.deal,
        'Pick the HMOs',
        ('set_board', {'sort': {'key': 'nonsense', 'dir': 1}}),
        (
            'set_board',
            {'pick': {'label': 'HMO plans', 'plan_ids': [refs['C2'], refs['C'], 999999], 'keys': ['plan_type']}},
        ),
    )
    refused, picked = answers(fake_claude)
    assert 'sort' in refused.lower() and job.result['board']['config'] == {}
    pick = job.result['board']['pick']
    assert pick['plan_ids'] == [refs['C2']]  # a current plan and an unknown id are not on the pick's list (F109)
    assert refs['C'] not in pick['judged_ids'] and pick['keys'] == ['plan_type'] and pick['line'] == 'medical'
    assert 'picked' not in refused


def test_F114_the_table_carries_each_plans_own_monthly_total(gd1, user, fake_claude):
    turn(fake_claude, user, gd1.deal, PPOS)
    context = fake_claude.log[0]['params']['messages'][-1]['content'][-2]['text']
    a2 = next(line for line in context.splitlines() if line.startswith(f'- id {gd1.refs["A2"]} '))
    assert '/mo' in a2 and 'renews id' in a2 and '<board>' not in context


def test_D86_done_when_a_direct_persons_delete_of_the_duplicate_changes_the_table_with_undo(gd1, direct, fake_claude):
    copy = copy_plan(direct, gd1.refs['C2'])
    job = turn(
        fake_claude,
        direct,
        gd1.deal,
        DELETE,
        (
            'propose_changes',
            {'changes': [{'op': 'remove_plan', 'plan_id': str(copy.id), 'values': [], 'reason': 'copy'}]},
        ),
    )
    assert (job.land, job.resolution) == (land.AUTO, 'applied')
    assert not Plan.objects.filter(pk=copy.id).exists() and Plan.all_objects.get(pk=copy.id).removed_at
    assert 'go on the table when your turn ends' in answers(fake_claude)[0]
    services.undo(direct, job.id)
    assert Plan.objects.filter(pk=copy.id).exists()  # ↶ Undo this run brings it back


def test_D86_D71_a_producers_delete_waits_and_sold_or_recommended_plans_are_refused(gd1, user, fake_claude):
    copy = copy_plan(user, gd1.refs['C2'])
    set_sold(user, gd1.refs['U1'], True)
    recommended = gd1.refs[gd1.spec['recommended'][0]]
    remove = [
        {'op': 'remove_plan', 'plan_id': pid, 'values': [], 'reason': ''}
        for pid in (copy.id, gd1.refs['U1'], recommended)
    ]
    job = turn(fake_claude, user, gd1.deal, DELETE, ('propose_changes', {'changes': remove}))
    said = answers(fake_claude)[0]
    assert 'is sold, so it stays' in said and 'recommended for the client' in said
    assert [item['plan'] for item in job.result['items']] == [copy.id]
    assert (job.land, job.wait_reason) == (land.STAGED, land.TURN_WAITS) and Plan.objects.filter(pk=copy.id).exists()
    services.apply(user, job.id)
    assert not Plan.objects.filter(pk=copy.id).exists()


def test_D85_D92_D88_values_are_cleaned_dictated_ones_land_typed_and_checks_answer_claude(gd1, direct, fake_claude):
    plan = gd1.refs['C2']
    values = [
        {'key': 'deductible_single', 'value': '$1,250', 'dictated': True},
        {'key': 'rate_es', 'value': '1', 'dictated': False},  # below EE: a soft check, said to Claude
        {'key': 'not_a_field', 'value': 'x', 'dictated': False},
    ]
    job = turn(
        fake_claude,
        direct,
        gd1.deal,
        'Fix C2',
        ('propose_changes', {'changes': [{'op': 'set_values', 'plan_id': plan, 'values': values, 'reason': ''}]}),
    )
    said = answers(fake_claude)[0]
    assert '"not_a_field" is not a field' in said and 'EE + Spouse is not above EE' in said
    row = Plan.objects.get(pk=plan)
    assert row.values['deductible_single'] == '1250' and row.sources['deductible_single']['origin'] == 'typed'
    assert row.sources['rate_es']['origin'] == 'ai'
    rows = Activity.objects.filter(pk__in=job.result['landed']['activity_ids'])
    assert {r.actor_kind for r in rows} == {'claude'} and job.result['findings'][0]['hard'] is False


def test_F61_clear_line_stages_and_keeps_current_and_sold_plans(gd1, direct, fake_claude):
    services.set_lock(direct, gd1.deal, True)
    job = turn(fake_claude, direct, gd1.deal, 'Start dental over', ('clear_line', {'line': 'dental'}))
    item = job.result['items'][0]
    assert (item['op'], job.land, job.wait_reason) == ('clear_line', land.STAGED, land.TURN_LOCKED)
    staying = set(Plan.objects.filter(deal=gd1.deal, line='dental', role='current').values_list('id', flat=True))
    assert staying and not staying & set(item['plans'])
    services.apply(direct, job.id)
    assert set(Plan.objects.filter(deal=gd1.deal, line='dental').values_list('id', flat=True)) == staying
    assert Job.objects.get(pk=job.id).result['landed']['summary'].startswith('Cleared')
