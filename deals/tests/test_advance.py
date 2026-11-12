"""`deals.services.advance`: automatic stage moves reload and lock the Deal, go only forward, and write one Activity
row that never merges (plan.md §5.1; A30; Q.9 row 6)."""

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from deals import services
from deals.models import Activity, Deal


def stage_rows(deal):
    return Activity.objects.filter(deal=deal, changes__contains=[{'t': f'deal:{deal.id}'}])


def test_A30_advance_reloads_and_locks_the_deal_row(user, deal):
    with CaptureQueriesContext(connection) as queries:
        services.advance(deal, user, 'quoting', 'the first quote read landed')
    locks = [q['sql'] for q in queries.captured_queries if 'FOR UPDATE' in q['sql'] and '"deals_deal"' in q['sql']]
    assert locks, 'advance did not lock the Deal row'
    assert Deal.objects.get(pk=deal.id).stage == 'quoting' and deal.stage == 'quoting'
    (row,) = stage_rows(deal).filter(summary__startswith='Moved to')
    assert row.summary == 'Moved to Quoting (the first quote read landed)'
    assert row.changes == [{'t': f'deal:{deal.id}', 'k': {'stage': ['intake', 'quoting']}}]


def test_A30_a_stale_copy_never_moves_the_stage_back(user, deal):
    stale = Deal.objects.get(pk=deal.id)
    services.update_deal(user, deal.id, stage='proposal')
    services.advance(stale, user, 'quoting', 'the first quote read landed')
    assert Deal.objects.get(pk=deal.id).stage == 'proposal'
    assert stale.stage == 'proposal'  # the caller's copy carries the stage the deal has


@pytest.mark.parametrize('start', ['proposal', 'sold', 'lost'])
def test_A30_advance_moves_only_forward_and_a_lost_deal_stays_lost(user, deal, start):
    Deal.objects.filter(pk=deal.id).update(stage=start)
    before = Activity.objects.count()
    services.advance(Deal.objects.get(pk=deal.id), user, 'quoting', 'a read landed')
    assert Deal.objects.get(pk=deal.id).stage == start
    assert Activity.objects.count() == before


def test_A30_each_stage_move_is_its_own_row(user, deal):
    services.advance(deal, user, 'quoting', 'a read landed')
    services.advance(deal, user, 'proposal', 'the proposal was issued')
    summaries = list(stage_rows(deal).order_by('id').values_list('summary', flat=True))
    assert summaries == ['Moved to Quoting (a read landed)', 'Moved to Proposal (the proposal was issued)']
