"""Claude's `merge_plans` and `check_values` in a chat turn (plan.md §10.6, §5.4; F142, O.6 #32, D93; slice 22): a rate
page's plan and its SBC's design-only plan become one through the one merge service, with ↶ Undo this run; the two
halves of one plan are refused (pairing is not merging, D-219); asked to check, Claude starts a re-check that waits for
a person. Claude's calls are scripted with the fake client; the tools and landings are the real ones."""

import pytest

from accounts.models import Profile
from ai import services
from ai.models import Job
from ai.testing import text_block, tool_block, turn_key
from quotes import services as quotes
from quotes.models import Plan
from quotes.tests.sbc_world import add_sbc, file_hash, quote_world, read_sbc

pytestmark = pytest.mark.django_db


@pytest.fixture
def direct(db):
    from django.contrib.auth import get_user_model

    person = get_user_model().objects.create_user('dee', 'dee@example.com', 'pw-Example-1')
    Profile.objects.create(user=person, claude_direct=True)
    return person


def turn(fake, person, deal, words, *calls):
    fake.record(
        turn_key(words, 1), content=[tool_block(name, data, f'toolu_{n}') for n, (name, data) in enumerate(calls)]
    )
    fake.record(turn_key(words, 2), content=[text_block('Done.')])
    _chat, _message, job = services.send_message(person, deal, text=words, tab='advisor')
    job.refresh_from_db()
    return job


def answers(fake):
    return [block['content'] for block in fake.log[-1]['params']['messages'][-1]['content']]


def test_F142_merge_plans_joins_a_design_only_plan_into_its_rated_plan_with_undo(direct, fake_claude):
    deal, _current, _renewal, cigna = quote_world(direct)
    design = quotes.create_plan(
        direct, deal, line='medical', role='alternate', carrier='Cigna', name='OAP Gold SBC', values={'er_copay': '300'}
    )
    words = 'Merge the Cigna SBC plan into Open Access 2500'
    job = turn(
        fake_claude,
        direct,
        deal,
        words,
        ('merge_plans', {'keep_id': cigna.id, 'merge_ids': [design.id], 'overwrite': []}),
    )
    assert job.resolution == 'applied'
    kept = Plan.objects.get(pk=cigna.id)
    assert kept.values['er_copay'] == '300' and kept.values['pcp_copay'] == '30'
    assert not Plan.objects.filter(pk=design.id).exists()  # merged plans leave the table
    services.undo(direct, job.id)
    assert Plan.objects.filter(pk=design.id).exists() and 'er_copay' not in Plan.objects.get(pk=cigna.id).values


def test_D116_merge_plans_refuses_two_halves_of_one_plan(direct, fake_claude):
    deal, *_plans = quote_world(direct)
    first = quotes.create_plan(
        direct, deal, line='medical', role='alternate', carrier='Florida Blue', name='HSA 05182', plan_number='05182'
    )
    second = quotes.create_plan(
        direct, deal, line='medical', role='alternate', carrier='Florida Blue', name='HSA 05183', plan_number='05183'
    )
    job = turn(
        fake_claude,
        direct,
        deal,
        'Merge the two HSA halves',
        ('merge_plans', {'keep_id': first.id, 'merge_ids': [second.id], 'overwrite': []}),
    )
    assert 'stay two plans' in answers(fake_claude)[0]
    assert not job.result['items'] and Plan.objects.filter(pk=second.id).exists()


def test_D93_check_values_starts_a_recheck_that_waits_for_a_person(direct, fake_claude):
    deal, _current, _renewal, cigna = quote_world(direct)
    document = add_sbc(direct, deal, fake_claude, 'Cigna', 'Open Access 2500', {'pcp_copay': '35'})
    services.apply(direct, read_sbc(direct, deal, document).id)
    ref = f'plan:{cigna.id}:pcp_copay'
    check = {'ref': ref, 'verdict': 'agree', 'found_value': '', 'page': 1, 'confidence': 'high', 'note': ''}
    fake_claude.record(('recheck', file_hash(document), 'p1#1'), {'checks': [check]})
    words = 'Check the flagged Cigna values'
    turn(fake_claude, direct, deal, words, ('check_values', {'plan_ids': [cigna.id], 'document_id': 0}))
    assert 'Started a re-check of 1 flagged value' in answers(fake_claude)[0]
    recheck = Job.objects.get(deal=deal, kind='recheck')
    assert recheck.params['refs'] == [ref] and recheck.land == 'staged'  # a direct person's too: a person applies it
    assert 'confirmed' not in Plan.objects.get(pk=cigna.id).sources['pcp_copay']
