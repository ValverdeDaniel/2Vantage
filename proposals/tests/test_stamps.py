"""The builder's `stamps` (plan.md §8.14; J.6.5; F3, J107): the Export viewer builds a preview again only when
something a client file prints may have changed: a recorded write or the firm's pages, never a completed mark or a
download."""

import pytest

from deals import activity
from proposals import services, stamps
from proposals.models import FirmPages, TeamMember
from quotes import services as plans

pytestmark = pytest.mark.django_db


def test_J107_F3_files_stamp_moves_with_a_write_but_not_a_mark_or_a_download(user, deal):
    plans.create_plan(user, deal, line='medical', role='current', carrier='Aetna', name='Today')
    before = stamps.files(deal)
    services.set_mark(user, deal, 'output', None, True, ['medical'])
    activity.log_access(deal, user, 'downloaded', 'the client PDF (draft)', None, area=services.AREA)
    assert stamps.files(deal) == before
    services.set_config(user, deal, {'title': 'Plan comparison'})
    assert stamps.files(deal) != before


def test_J107_F3_firm_stamp_moves_with_the_firm_pages_and_the_team(db):
    before = stamps.firm()
    FirmPages.objects.create(about_text='We place group benefits.')
    after_pages = stamps.firm()
    assert after_pages != before
    TeamMember.objects.create(name='Pat Example', title='Account manager')
    assert stamps.firm() != after_pages


def test_J107_the_builder_payload_carries_both_stamps(api, deal):
    body = api.get(f'/api/deals/{deal.id}/proposal/').json()
    assert set(body['stamps']) == {'files', 'firm'}
    assert body['stamps'] == api.get(f'/api/deals/{deal.id}/proposal/').json()['stamps']
