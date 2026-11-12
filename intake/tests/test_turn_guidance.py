"""The client guidance in Work with Claude (plan.md §10.6, §4.5 †; D6, D98, F111; Q.9 row 24: guidance writes through
intake). Claude's `update_client_guidance` lands through intake's one writer as Claude's change, with ↶ Undo; the
drawer's GuidanceBox saves the same answer through `PATCH deals/{id}/intake/`."""

import pytest

from accounts.models import Profile
from ai import services
from ai.testing import text_block, tool_block, turn_key
from deals.models import Activity
from intake.models import Intake

WORDS = 'The client wants to keep Aetna and stay under $40k a month'
GUIDANCE = '- Keep Aetna\n- Stay under $40,000 a month'


@pytest.fixture
def direct(db):
    from django.contrib.auth import get_user_model

    person = get_user_model().objects.create_user('dee', 'dee@example.com', 'pw-Example-1')
    Profile.objects.create(user=person, claude_direct=True)
    return person


def guidance_of(deal):
    row = Intake.objects.filter(deal=deal).first()
    return (row.answers if row else {}).get('client_guidance', '')


def test_D98_claudes_guidance_lands_through_intake_with_undo(direct, deal, fake_claude):
    fake_claude.record(turn_key(WORDS, 1), content=[tool_block('update_client_guidance', {'text': GUIDANCE})])
    fake_claude.record(turn_key(WORDS, 2), content=[text_block('I updated the guidance.')])
    _chat, _message, job = services.send_message(direct, deal, text=WORDS)
    job.refresh_from_db()
    assert job.resolution == 'applied' and guidance_of(deal) == GUIDANCE
    row = Activity.objects.get(pk=job.result['landed']['activity_ids'][0])
    assert (row.area, row.actor_kind, row.coalesce_key) == ('intake', 'claude', '')
    assert job.result['landed']['areas'] == ['intake', 'activity']
    services.undo(direct, job.id)
    assert guidance_of(deal) == ''


def test_D98_the_guidance_reaches_claude_and_an_unchanged_one_proposes_nothing(api, user, deal, fake_claude):
    assert (
        api.patch(
            f'/api/deals/{deal.id}/intake/', {'answers': {'client_guidance': GUIDANCE}}, format='json'
        ).status_code
        == 200
    )
    fake_claude.record(turn_key(WORDS, 1), content=[tool_block('update_client_guidance', {'text': GUIDANCE})])
    fake_claude.record(turn_key(WORDS, 2), content=[text_block('It already says so.')])
    _chat, _message, job = services.send_message(user, deal, text=WORDS)
    job.refresh_from_db()
    context = fake_claude.log[0]['params']['messages'][-1]['content'][-2]['text']
    assert f'Client guidance:\n{GUIDANCE}' in context
    said = fake_claude.log[-1]['params']['messages'][-1]['content'][0]['content']
    assert 'already' in said and job.result['items'] == []
