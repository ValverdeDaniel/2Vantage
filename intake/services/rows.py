"""Locks and Activity helpers the intake services share (plan.md §3.7, O.3.7).

Lock order: the Deal, then the Intake row, then the deal's coverage rows by id. A coverage row's Activity entry is
`coverage:<id>` with before and after per field; a row created by the change has `line` [None, line] and a removed row
keeps every field it had as [value, None], so Revert can delete or rebuild it (intake/revert.py).
"""

from deals.models import Deal
from deals.services.snapshots import diff, snapshot
from deals.values import locked

from ..models import CurrentCoverage, Intake

AREA = 'intake'
FIELDS = (
    'line',
    'carrier',
    'funding',
    'effective_date',
    'renewal_date',
    'rate_guarantee_through',
    'in_force',
    'notes',
    'sort_order',
    'on_proposal',
    'commission',
    'commission_source',
)
DATES = ('effective_date', 'renewal_date', 'rate_guarantee_through')


def target(row_id):
    return f'coverage:{row_id}'


def intake_target(deal_id):
    return f'intake:{deal_id}'


def lock_deal(deal_id):
    """The Deal row, locked first (O.3.7). Raises Deal.DoesNotExist."""
    return locked(Deal, deal_id)


def lock_intake(deal_id):
    """The deal's Intake row, created on the first write and locked (§6.5: never created by a GET)."""
    Intake.objects.get_or_create(deal_id=deal_id)
    return locked(Intake, deal_id)


def lock_coverage(deal_id, ids=None):
    """The deal's coverage rows (or only `ids`), locked by id, returned in sort order."""
    rows = CurrentCoverage.objects.select_for_update().filter(deal_id=deal_id)
    if ids is not None:
        rows = rows.filter(pk__in=ids)
    locked_rows = list(rows.order_by('id'))
    return sorted(locked_rows, key=lambda row: (row.sort_order, row.id))


def next_sort_order(deal_id):
    last = CurrentCoverage.objects.filter(deal_id=deal_id).order_by('-sort_order').values_list('sort_order', flat=True)
    first = last.first()
    return 0 if first is None else first + 1


def state(row):
    return snapshot(row, FIELDS)


def created(row):
    """The entry for a row the change created: its line and the fields that are not the model's defaults."""
    now = state(row)
    blank = state(CurrentCoverage(line=''))
    return {key: [None, value] for key, value in now.items() if key == 'line' or value != blank[key]}


def removed(before):
    """The entry for a row the change deleted: every field it had, so Revert can rebuild it."""
    return {key: [value, None] for key, value in before.items()}


def changed(before, row):
    return diff(before, state(row))
