"""Mark as marketed (plan.md §5.2, §7.6; B33, B34; OQ52; Q.9 row 40): a 409 lists the gaps until the deal is ready;
Market anyway records the skipped items and Undo takes it back; the first date is kept; a lost deal refuses it; no
stage moves."""

import pytest

from conftest import write_path_contract
from deals import activity
from deals.models import Activity, Deal
from deals.services import mark_lost
from intake import services
from intake.models import Intake

pytestmark = pytest.mark.django_db


def url(deal):
    return f'/api/deals/{deal.id}/intake/marketed/'


def test_B34_while_blocked_a_409_lists_the_gaps_and_nothing_is_written(api, deal):
    answer = api.post(url(deal), {}, format='json')
    assert answer.status_code == 409
    body = answer.json()
    keys = [gap['key'] for gap in body['gaps']]
    assert {'contacts', 'bor', 'census', 'coverage_intent', 'cobra'} <= set(keys) and body['keys'] == keys
    assert body['detail'].startswith('This deal is not ready to market yet. Still open: Legal Company Name, FEIN')
    assert body['detail'].endswith(f'and {len(keys) - 6} more.')
    assert not Intake.objects.filter(deal=deal).exists() and not Activity.objects.filter(deal=deal, action='marketed')


def test_B34_market_anyway_records_the_skipped_items_and_undo_takes_it_back(user, api, deal):
    stage = deal.stage
    body = api.post(url(deal), {'override': True}, format='json').json()
    assert body['ready']['state'] == 'submitted' and body['ready']['label'] == 'Sent to market'
    assert body['marketed']['at'] and body['marketed']['by'] == user.id
    skipped = [gap['label'] for gap in body['skipped']]
    assert {'HR contact', 'Signed BOR', 'Census', 'COBRA participants'} <= set(skipped)
    row = Activity.objects.get(pk=body['activity_id'])
    assert row.summary.startswith(f'Marked as marketed anyway, skipping {len(skipped)}: Legal Company Name, FEIN')
    assert row.changes[0]['t'] == f'marketed:{deal.id}' and row.changes[0]['k']['skipped'] == [None, skipped]
    assert Deal.objects.get(pk=deal.pk).stage == stage  # OQ52: no stage move
    activity.revert(row.id, user)
    after = api.get(f'/api/deals/{deal.id}/intake/').json()
    assert after['marketed'] is None and after['ready']['state'] == 'blocked'


def test_Q3_1_B34_marking_keeps_the_first_date_and_reverts(user, deal):
    intake = Intake.objects.create(deal=deal)
    write_path_contract(
        user,
        intake,
        lambda: services.mark_marketed(user, deal.id, override=True),
        lambda found: found.marketed_at,
        lambda: services.unmark_marketed(user, deal.id),
    )


def test_B34_a_repeat_changes_nothing(user, api, deal):
    first = services.mark_marketed(user, deal.id, override=True)
    stamp = Intake.objects.get(deal=deal).marketed_at
    again = api.post(url(deal), {}, format='json')  # already marketed: no 409, nothing written
    assert again.status_code == 200 and again.json()['activity_id'] is None and again.json()['skipped'] == []
    assert Intake.objects.get(deal=deal).marketed_at == stamp and first.activity


def test_B34_unmark_takes_the_stamp_off(user, api, deal):
    services.mark_marketed(user, deal.id, override=True)
    body = api.delete(url(deal)).json()
    assert body['marketed'] is None and body['ready']['state'] == 'blocked' and body['activity_id']
    assert api.delete(url(deal)).json()['activity_id'] is None


def test_A19_a_lost_deal_refuses_mark_as_marketed_even_anyway(user, api, deal):
    mark_lost(user, deal.id)
    answer = api.post(url(deal), {'override': True}, format='json')
    assert answer.status_code == 409 and 'reopen it before sending it to market' in answer.json()['detail']


def test_B34_override_is_true_or_false(api, deal):
    assert api.post(url(deal), {'override': 'yes'}, format='json').status_code == 400
