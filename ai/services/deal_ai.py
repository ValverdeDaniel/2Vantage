"""The deal's AI settings: the table lock and the budget (plan.md §7.5, §10.3; D100, D104, F113, OQ34; slice 24).

- `set_lock(user, deal, locked)`: anyone on the deal locks the plan table from Claude, or unlocks it (the old
  ClaudeLockSwitch). Locked, Claude still reads and answers, and its changes wait for review even for a direct person
  (`land.decide`, `land.decide_turn`).
- `set_budget(user, deal, amount)`: only an admin changes a deal's AI budget (OQ34's default); None gives back the
  setting's (`AI_DEAL_BUDGET_USD`).
Each locks the Deal, then its DealAi row (created on the first write), writes only a change, and records Activity
(area `ai`) with before and after; `revert` (registered for the area) puts it back, refused after a later change.
The locate job's `checked` rows in the same area are not revertible (slice 16).
"""

from decimal import Decimal, InvalidOperation

from django.db import transaction
from rest_framework.exceptions import PermissionDenied, ValidationError

from deals import activity, clock
from deals.models import Deal

from ..models import DealAi

AREA = 'ai'
MAX_BUDGET = Decimal('10000')
ONLY_ADMINS = 'Only an admin can change a deal’s AI budget.'
BAD_BUDGET = f'The budget is a dollar amount from $0 to ${MAX_BUDGET:,.0f}, or blank for the default.'
NOT_A_SWITCH = 'Locked is true or false.'


def _row(deal_id):
    Deal.objects.select_for_update().only('id').get(pk=deal_id)
    row, _ = DealAi.objects.select_for_update().get_or_create(deal_id=deal_id)
    return row


def _target(deal_id):
    return f'deal_ai:{deal_id}'


def set_lock(user, deal, locked):
    """The Activity row, or None when nothing changed."""
    if not isinstance(locked, bool):
        raise ValidationError({'locked': [NOT_A_SWITCH]})
    with transaction.atomic():
        row = _row(deal.id)
        before = row.locked_at is not None
        if before == locked:
            return None
        row.locked_at, row.locked_by = (clock.now(), user) if locked else (None, None)
        row.save(update_fields=['locked_at', 'locked_by'])
        summary = 'Locked the plan table from Claude' if locked else 'Let Claude change the plan table again'
        return activity.record(
            deal,
            user,
            AREA,
            'locked' if locked else 'unlocked',
            summary,
            changes=[activity.change(_target(deal.id), {'locked': [before, locked]})],
        )


def money(raw):
    if raw in (None, ''):
        return None
    if isinstance(raw, bool):
        raise ValidationError({'budget_usd': [BAD_BUDGET]})
    try:
        amount = Decimal(str(raw).replace('$', '').replace(',', '').strip())
    except (InvalidOperation, ValueError):
        raise ValidationError({'budget_usd': [BAD_BUDGET]}) from None
    if not amount.is_finite() or amount < 0 or amount > MAX_BUDGET:
        raise ValidationError({'budget_usd': [BAD_BUDGET]})
    return amount.quantize(Decimal('0.01'))


def set_budget(user, deal, raw):
    """The Activity row, or None when nothing changed."""
    if not getattr(user, 'is_staff', False):
        raise PermissionDenied(ONLY_ADMINS)
    amount = money(raw)
    with transaction.atomic():
        row = _row(deal.id)
        if row.budget_usd == amount:
            return None
        before = row.budget_usd
        row.budget_usd = amount
        row.save(update_fields=['budget_usd'])
        words = f'${amount:,.2f}' if amount is not None else 'the default'
        return activity.record(
            deal,
            user,
            AREA,
            'budget',
            f'Set the deal’s AI budget to {words}',
            changes=[
                activity.change(
                    _target(deal.id),
                    {'budget_usd': [None if before is None else str(before), None if amount is None else str(amount)]},
                )
            ],
        )


def revert(row, user):
    """The reverter of area `ai`: the lock or the budget back as it was; refused after a later change to it."""
    entry = next((e for e in row.changes if e['t'].startswith('deal_ai:')), None)
    if entry is None:
        raise activity.Refused(activity.NOTHING_TO_PUT_BACK)
    deal_id = int(entry['t'].split(':', 1)[1])
    later = activity.later_keys(row)
    if later:
        raise activity.changed_since(['The AI setting'], [key for _target_, key in later])
    current = _row(deal_id)
    written = {}
    if 'locked' in entry['k']:
        before, after = entry['k']['locked']
        current.locked_at, current.locked_by = (clock.now(), user) if before else (None, None)
        written['locked'] = [after, before]
    if 'budget_usd' in entry['k']:
        if not getattr(user, 'is_staff', False):
            raise activity.Refused(ONLY_ADMINS)
        before, after = entry['k']['budget_usd']
        current.budget_usd = Decimal(before) if before is not None else None
        written['budget_usd'] = [after, before]
    current.save(update_fields=['locked_at', 'locked_by', 'budget_usd'])
    return [activity.change(entry['t'], written)]
