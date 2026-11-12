"""Claude's `set_table_note` and `set_rows`, and the `<proposal>` context, in a chat turn on GD1 (plan.md §6.11, §10.6;
J60, J62, J160, D120; slice 37; Q.9 row 37: the tools write with Undo). Turns run inline with the fake client; the
tools, `set_config` and the landings are the real ones. Writes roll back with each test."""

import pytest

from accounts.models import Profile
from ai import services
from ai.testing import text_block, tool_block, turn_key
from deals.models import Activity
from proposals import config
from proposals.models import ProposalConfig
from proposals.services import set_config

pytestmark = pytest.mark.django_db

NOTE = '* The PCP copay applies after the deductible on HSA plans.'
WORDS = 'Add a note under the medical table about the asterisk'


@pytest.fixture
def direct(db):
    from django.contrib.auth import get_user_model

    person = get_user_model().objects.create_user('dee', 'dee@example.com', 'pw-Example-1')
    Profile.objects.create(user=person, claude_direct=True)
    return person


def turn(fake, person, deal, words, *calls, **page):
    fake.record(
        turn_key(words, 1), content=[tool_block(name, data, f'toolu_{n}') for n, (name, data) in enumerate(calls)]
    )
    fake.record(turn_key(words, 2), content=[text_block('Done.')])
    _chat, _message, job = services.send_message(person, deal, text=words, **page)
    job.refresh_from_db()
    return job


def stored(deal, path):
    row = ProposalConfig.objects.filter(deal=deal).first()
    return config.get(row.config if row else {}, path)


def said(fake):
    return [block['content'] for block in fake.log[-1]['params']['messages'][-1]['content']]


def test_J160_set_table_note_lands_for_a_direct_person_and_undo_takes_it_back(direct, gd1, fake_claude):
    deal = gd1.deal
    set_config(direct, deal, {'title': 'Benefits 2027'})  # a person's own edit just before: Undo leaves it alone
    job = turn(fake_claude, direct, deal, WORDS, ('set_table_note', {'line': 'medical', 'text': NOTE}))

    assert (job.land, job.resolution) == ('auto', 'applied') and stored(deal, 'lines.medical.table_note') == NOTE
    row = Activity.objects.get(pk=job.activity_id)
    assert (row.area, row.actor_kind) == ('proposal', 'claude')  # Claude's own row, never merged with the person's
    assert 'proposal' in job.result['landed']['areas']
    assert services.undo(direct, job.id)[1]
    assert stored(deal, 'lines.medical.table_note') == '' and stored(deal, 'title') == 'Benefits 2027'


def test_J60_the_note_is_cleaned_as_the_builder_cleans_it_and_a_line_must_have_plans(direct, gd1, fake_claude):
    long_note = '\n'.join(f'Line {n}   with   spaces' for n in range(6))
    job = turn(
        fake_claude,
        direct,
        gd1.deal,
        WORDS,
        ('set_table_note', {'line': 'medical', 'text': long_note}),
        ('set_table_note', {'line': 'pet', 'text': NOTE}),
    )
    answers = said(fake_claude)
    assert 'Line 0 with spaces' in answers[0] and 'no "pet" line' in answers[1]
    assert stored(gd1.deal, 'lines.medical.table_note').split('\n') == [f'Line {n} with spaces' for n in range(4)]
    assert [item['op'] for item in job.result['items']] == ['table_note']


def test_D120_set_rows_chooses_the_rows_and_refuses_one_the_table_cannot_print(user, gd1, fake_claude):
    deal = gd1.deal
    job = turn(
        fake_claude,
        user,
        deal,
        'Only print the deductible and out-of-pocket rows on dental',
        ('set_rows', {'line': 'dental', 'rows': ['den_deductible', 'den_annual_max']}),
        ('set_rows', {'line': 'dental', 'rows': ['sl_lasers']}),
    )
    answers = said(fake_claude)
    assert 'Deductible' in answers[0] and 'is not a row the Dental table can print' in answers[1]
    assert job.land == 'staged' and stored(deal, 'lines.dental.rows') is None  # a producer's change waits
    services.apply(user, job.id)
    assert stored(deal, 'lines.dental.rows') == ['den_deductible', 'den_annual_max']
    assert services.undo(user, job.id)[1] and stored(deal, 'lines.dental.rows') is None


def test_J160_the_proposal_context_tells_the_notes_rows_and_on_the_proposal_tab_the_rows_it_can_print(
    direct, gd1, fake_claude
):
    set_config(direct, gd1.deal, {'lines.medical.table_note': NOTE, 'lines.vision.rows': ['vis_exam_copay']})
    turn(fake_claude, direct, gd1.deal, 'What prints?', tab='proposal')
    context = fake_claude.log[0]['params']['messages'][-1]['content'][-2]['text']
    assert '<proposal>' in context and NOTE in context
    assert 'Vision (vision): its table prints the rows vis_exam_copay' in context
    assert 'Dental (dental): rows its table can print:' in context
