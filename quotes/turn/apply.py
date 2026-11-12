"""Landing a chat turn's plan changes (plan.md §10.6; D72, D85, D86, F60, F61; slice 24): quotes' turn owner.

`apply(user, deal, job, items)` writes the items through the Advisor's own services, in the caller's transaction
(the Deal and the job locked first): values through `update_plan` (dictated ones as typed, D85; the rest as Claude's,
`origin: ai`), each plan's in an Activity row of its own marked as Claude's (`by_claude`), so ↶ Undo this run puts
back only what the turn changed; removals through `delete_plans` (F60) and a line's clear through `clear_line`
(F61), each its own `removed` row whose Revert restores the plans; a merge through the one merge service (F142; slice
22), its `merged` row; a pair or a split through the pair service (D-219, J161; slice 37), its `plan.pair_of`
row. A value lands only while the table still holds what Claude saw (else it is skipped and named); a
plan sold or recommended since is never removed (D86).
"""

from rest_framework.exceptions import ValidationError

from deals.activity import Refused

from ..models import Plan
from ..services.merge import merge_plans
from ..services.pairs import pair, split
from ..services.plans import update_plan
from ..services.read_apply import AREAS
from ..services.removal import clear_line, delete_plans


def _label(plan):
    return f'{plan.carrier} {plan.name}'


def _values(user, item, wrote):
    plan = Plan.objects.filter(pk=item['plan']).first()
    if plan is None:
        wrote['skipped'].append('A plan Claude edited is no longer on the table.')
        return
    current = plan.values or {}
    fresh = [value for value in item['values'] if current.get(value['key'], '') == value['old']]
    if len(fresh) < len(item['values']):
        wrote['skipped'].append(f'{_label(plan)}: values changed since Claude read them were left as they are.')
    for dictated in (True, False):
        values = {value['key']: value['new'] for value in fresh if bool(value.get('dictated')) == dictated}
        if not values:
            continue
        changed, keys = update_plan(
            user, plan.id, {'values': values}, source_origin='typed' if dictated else 'ai', by_claude=True
        )
        if changed.activity_id:
            wrote['activity_ids'].append(changed.activity_id)
            wrote['plan_ids'].append(plan.id)
            wrote['said'].append(f'{len(keys)} value{"s" if len(keys) != 1 else ""} on {_label(plan)}')


def _remove(user, deal, item, wrote):
    plan = Plan.objects.filter(pk=item['plan']).first()
    if plan is None:
        return  # already removed: nothing to do
    if plan.sold or plan.recommended:
        wrote['skipped'].append(f'{_label(plan)} is {"sold" if plan.sold else "recommended"} now, so it stays.')
        return
    removal = delete_plans(user, deal, [plan.id])
    if removal.row:
        wrote['activity_ids'].append(removal.row.id)
        wrote['said'].append(f'removed {_label(plan)}')


def _clear(user, deal, item, wrote):
    removal = clear_line(user, deal, item['line'])
    if removal.row:
        wrote['activity_ids'].append(removal.row.id)
        wrote['said'].append(f'cleared {len(removal.removed)} plans')
    if removal.note:
        wrote['skipped'].append(removal.note)


def _merge(user, deal, item, wrote):
    _keep, _changed, row = merge_plans(user, deal, item['plan'], item['merge'], item.get('overwrite') or ())
    if row is not None:
        wrote['activity_ids'].append(row.id)
        wrote['plan_ids'].append(item['plan'])
        wrote['said'].append(item['label'][:1].lower() + item['label'][1:])


def _pair(user, deal, item, wrote):
    if item['op'] == 'pair_plans':
        _changed, row = pair(user, deal, item['plan'], item['with'])
    else:
        _changed, row = split(user, deal, item['plan'])
    if row is not None:
        wrote['activity_ids'].append(row.id)
        wrote['plan_ids'] += [item['plan'], item['with']]
        wrote['said'].append(item['label'][:1].lower() + item['label'][1:])


def apply(user, deal, job, items):
    wrote = {'activity_ids': [], 'plan_ids': [], 'said': [], 'skipped': []}
    for item in items:
        try:
            if item['op'] == 'set_values':
                _values(user, item, wrote)
            elif item['op'] == 'remove_plan':
                _remove(user, deal, item, wrote)
            elif item['op'] == 'clear_line':
                _clear(user, deal, item, wrote)
            elif item['op'] == 'merge_plans':
                _merge(user, deal, item, wrote)
            elif item['op'] in ('pair_plans', 'split_pair'):
                _pair(user, deal, item, wrote)
        except (Refused, ValidationError) as exc:
            detail = getattr(exc, 'sentence', '') or 'One change could not be made.'
            wrote['skipped'].append(str(detail)[:200])
    said = wrote.pop('said')
    return {
        **wrote,
        'summary': _sentence('; '.join(said)),
        'areas': AREAS if wrote['activity_ids'] else [],
    }


def _sentence(text):
    return text[:1].upper() + text[1:] if text else ''
