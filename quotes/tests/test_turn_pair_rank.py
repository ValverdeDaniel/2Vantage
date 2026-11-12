"""Claude's `pair_plans` and `rank_plans` in a chat turn on GD1 (plan.md §10.6; D-219, J15, J161, D96, F111, OQ44;
slice 37; Q.9 row 37: the tools write with Undo). Turns run inline with the fake client: Claude's tool calls are
scripted, the tools, the pair service, the rank job and the landings are the real ones. Writes roll back with each
test, so GD1 stays as built (FB1 and FB2 paired)."""

import pytest

from accounts.models import Profile
from ai import services
from ai.models import Job
from ai.testing import text_block, tool_block, turn_key
from intake.services import update_answers
from quotes.models import Plan
from quotes.rank.job import rank_key
from quotes.services import split_pair

pytestmark = pytest.mark.django_db

PAIR = 'Print the two Florida Blue HSA halves as one column'
RANK = 'Rank the medical quotes against what the client wants'


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
    return [block['content'] for block in fake.log[-1]['params']['messages'][-1]['content']]


def paired(gd1):
    return Plan.objects.get(pk=gd1.refs['FB2']).pair_of_id


def test_J161_pair_plans_lands_for_a_direct_person_with_undo(direct, gd1, fake_claude):
    deal, refs = gd1.deal, gd1.refs
    split_pair(direct, deal, refs['FB1'])  # two columns, as a read leaves them
    assert paired(gd1) is None

    job = turn(
        fake_claude, direct, deal, PAIR, ('pair_plans', {'plan_ids': [refs['FB1'], refs['FB2']], 'split': False})
    )

    assert 'print as one column in the client documents' in answers(fake_claude)[0]
    assert (job.land, job.resolution) == ('auto', 'applied') and paired(gd1) == refs['FB1']
    assert job.result['summary'].startswith('Print Florida Blue BlueOptions HSA Compatible 05182 and')
    assert services.undo(direct, job.id)[1] and paired(gd1) is None  # ↶ Undo this run: two columns again


def test_J161_pair_plans_says_why_it_will_not_pair(direct, gd1, fake_claude):
    refs = gd1.refs
    job = turn(
        fake_claude,
        direct,
        gd1.deal,
        PAIR,
        ('pair_plans', {'plan_ids': [refs['FB1'], refs['FB2']], 'split': False}),  # already one column
        ('pair_plans', {'plan_ids': [refs['CG2'], refs['U3']], 'split': False}),  # two carriers
        ('pair_plans', {'plan_ids': [refs['FB1']], 'split': False}),  # one plan
    )
    said = answers(fake_claude)
    assert 'already print as one column' in said[0]
    assert 'different carriers' in said[1] and 'Name the two plans' in said[2]
    assert job.result['items'] == [] and paired(gd1) == refs['FB1']


def test_J161_split_true_proposes_two_columns_and_a_producer_waits(user, gd1, fake_claude):
    refs = gd1.refs
    job = turn(
        fake_claude,
        user,
        gd1.deal,
        'Split the Florida Blue pair',
        ('pair_plans', {'plan_ids': [refs['FB2']], 'split': True}),
    )
    assert [item['op'] for item in job.result['items']] == ['split_pair']
    assert job.land == 'staged' and paired(gd1) == refs['FB1']  # a producer's change waits for Apply
    services.apply(user, job.id)
    assert paired(gd1) is None


def test_J161_the_plan_table_marks_a_second_half(direct, gd1, fake_claude):
    turn(fake_claude, direct, gd1.deal, 'What is paired?', reply='FB1 and FB2.')
    context = fake_claude.log[0]['params']['messages'][-1]['content'][-2]['text']
    assert f'one column with id {gd1.refs["FB1"]} in client files' in context


def test_D96_rank_plans_starts_the_rank_whose_stars_land_with_undo(direct, gd1, fake_claude):
    deal, refs = gd1.deal, gd1.refs
    update_answers(direct, deal.id, {'client_guidance': '- Lowest premium with an HSA option'})
    picks = [refs[ref] for ref in ('U1', 'CG2', 'FB1', 'FB2', 'CG4')]
    fake_claude.record(rank_key('medical'), {'shortlist': [{'plan_id': pid, 'reason': 'Low premium'} for pid in picks]})

    turn(fake_claude, direct, deal, RANK, ('rank_plans', {'line': 'medical', 'plan_ids': []}))

    assert 'Started ranking the Medical plans' in answers(fake_claude)[0]
    starred = set(Plan.objects.filter(deal=deal, line='medical', starred=True).values_list('id', flat=True))
    assert starred == set(picks)
    rank_job = Job.objects.get(deal=deal, kind='rank')
    assert services.undo(direct, rank_job.id)[1]
    assert Plan.objects.filter(deal=deal, line='medical', starred=True).count() > len(picks)  # GD1's stars are back


def test_F111_rank_plans_without_guidance_is_refused_in_words(direct, gd1, fake_claude):
    turn(fake_claude, direct, gd1.deal, RANK, ('rank_plans', {'line': 'medical', 'plan_ids': []}))
    assert answers(fake_claude)[0].startswith('Add client guidance first')


def test_D81_slice_37s_tools_are_sent_without_strict_to_keep_the_grammar_within_the_apis_limit(
    direct, gd1, fake_claude
):
    turn(fake_claude, direct, gd1.deal, 'Hello', reply='Hi.')
    sent = {tool['name']: tool['strict'] for tool in fake_claude.log[0]['params']['tools']}
    assert sent['set_board'] and sent['propose_changes']  # slice 24's stay strict
    assert not any(sent[name] for name in ('pair_plans', 'rank_plans', 'set_table_note', 'set_rows'))
