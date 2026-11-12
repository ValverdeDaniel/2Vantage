"""The PHI gate's Activity scrub (plan.md §11.4 item 6, §3.8; slice 47): rows written before `sl_lasers` became
key-only (commit c543269) are rewritten exactly as deals.activity records a new edit — the laser values gone, the other
keys' before and after kept, the row no longer revertible — and nothing else moves. A dry run writes nothing, and no
value is ever printed."""

from io import StringIO

import pytest
from django.core.management import call_command

from deals import activity
from deals.models import Activity

pytestmark = pytest.mark.django_db
CANARY = 'ZZQ-LASER-CLAIMANT-0047'
MIXED = [{'t': 'plan:41', 'k': {'sl_lasers': ['', CANARY], 'sl_spec_deductible': ['40000', '50000']}}]
ALONE = [{'t': 'plan:42', 'k': {'sl_lasers': [CANARY, f'{CANARY} and one more']}}]
CLEAN = [{'t': 'plan:43', 'k': {'rate_ee': ['612.50', '640']}}]


def old_row(deal, user, changes, action='edited'):
    """A row as the code before c543269 wrote it: values kept, revertible."""
    return Activity.objects.create(
        deal=deal, actor=user, area='quotes', action=action, summary='Edited 2 plan values', changes=changes,
        revertible=True,
    )  # fmt: skip


def run(*args):
    out = StringIO()
    call_command('scrub_key_only_values', *args, stdout=out)
    return out.getvalue()


def test_PHI6_a_dry_run_names_the_rows_and_writes_nothing(user, deal):
    mixed, alone, clean = (old_row(deal, user, changes) for changes in (MIXED, ALONE, CLEAN))
    before = list(Activity.objects.order_by('id').values())
    said = run()
    assert 'sl_lasers' in said and f'ids {mixed.id}, {alone.id}' in said and str(clean.id) not in said.split('ids')[1]
    assert 'Dry run' in said and CANARY not in said
    assert list(Activity.objects.order_by('id').values()) == before


def test_PHI6_apply_rewrites_them_as_a_new_edit_is_recorded_and_moves_nothing_else(user, deal):
    mixed, alone, clean = (old_row(deal, user, changes) for changes in (MIXED, ALONE, CLEAN))
    stamps = dict(Activity.objects.values_list('id', 'updated_at'))
    said = run('--apply')
    assert 'Rewrote 2 row(s); 0 still keep a value.' in said and CANARY not in said
    mixed.refresh_from_db()
    alone.refresh_from_db()
    clean.refresh_from_db()
    recorded_now = activity.record(deal, user, 'quotes', 'edited', 'Edited', changes=MIXED)
    assert mixed.changes == recorded_now.changes
    assert mixed.changes == [
        {'t': 'plan:41', 'k': {'sl_spec_deductible': ['40000', '50000']}},
        {'t': 'plan:41', 'k': ['sl_lasers']},
    ]
    assert alone.changes == [{'t': 'plan:42', 'k': ['sl_lasers']}]
    assert clean.changes == CLEAN and clean.revertible
    assert not mixed.revertible and not alone.revertible
    assert CANARY not in str(list(Activity.objects.values('summary', 'changes')))
    assert {pk: stamp for pk, stamp in Activity.objects.values_list('id', 'updated_at') if pk in stamps} == stamps
    with pytest.raises(activity.Refused) as refused:
        activity.revert(mixed.id, user)
    assert refused.value.sentence == activity.KEYS_ONLY


def test_PHI6_a_second_run_finds_nothing_and_a_reverted_row_is_scrubbed_too(user, deal):
    old_row(deal, user, MIXED, action='reverted')
    assert 'Rewrote 1 row(s)' in run('--apply')
    assert 'Activity rows that keep their values: 0.' in run('--apply')
