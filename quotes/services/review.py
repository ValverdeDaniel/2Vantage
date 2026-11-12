"""Reviewing plan values: approve, ignore, needs checking and clear (plan.md §10.7; E85–E89, F63, F65, F67; the old
market/value_review.py `targets`, `mark_and_record` and `revert_batch`).

`mark_values` is quotes' one marks writer, behind `POST deals/{id}/plans/marks/` (the station's List, keys and strip,
the Advisor's flags chip and review strip). It names its values one of three ways (E86):
- `refs`: exactly those values ("plan:41:rate_ee"), whatever their state;
- `plan_ids` and/or `document_ids`: the open warnings on those plans, read from those files (for `clear`, the marked
  values), so a strip never approves more than it shows;
- neither: the open warnings on the whole deal.
It locks the Deal, then the plans by id (O.3.7), applies `review_rules.apply_mark` to each, rewrites `flags` in the
same statement, and records one Activity row (action `marked`, never merged) that holds each value's marks before and
after under `mark.<key>`, never the value (E74). Marks are bookkeeping: no `updated_at`, no plans signal, and a lost
deal is reviewed like any other.

Revert (E88): each value still as the row left it gets its marks back; a value changed or reviewed since stays as it
is. When none can go back, the Revert is refused, naming them (Q.3 #1). Sold plans refuse it (rule 4).
"""

from dataclasses import dataclass, field

from django.db import transaction
from rest_framework.exceptions import ValidationError

from deals import activity, clock
from documents.models import Document
from documents.review_rules import ACTIONS, CLEAR, apply_mark, mark_state, marks_of, open_warning, with_marks

from .. import fields, flags
from ..models import Plan
from . import locks

MARKED = 'marked'
PREFIX = 'mark.'
DONE = {'approve': 'Approved', 'ignore': 'Ignored', 'check': 'Flagged', 'clear': 'Unmarked'}
NOT_HERE = 'Some of those values are not on this deal.'
NO_PLANS = 'Some of the selected plans are not on this deal.'
NO_FILES = 'That document is not on this deal.'


@dataclass
class Marked:
    action: str
    values: list = field(default_factory=list)  # [(plan, key)] whose marks changed
    plans: list = field(default_factory=list)  # the plans they are on
    row: object = None


def _ids(raw, name, sentence):
    if not isinstance(raw, list) or not raw:
        raise ValidationError({name: [sentence]})
    out = []
    for item in raw:
        if isinstance(item, bool):
            raise ValidationError({name: ['Give a list of ids.']})
        try:
            out.append(int(item))
        except (TypeError, ValueError) as exc:
            raise ValidationError({name: ['Give a list of ids.']}) from exc
    return sorted(set(out))


def parse_refs(raw):
    """["plan:41:rate_ee", ...] → {plan id: [keys]}; 400 for an empty list or a ref that is not a plan value's."""
    if not isinstance(raw, list) or not raw:
        raise ValidationError({'refs': ['Name the values to review.']})
    out = {}
    for ref in raw:
        kind, _, rest = str(ref).partition(':')
        plan_id, _, key = rest.partition(':')
        if kind != 'plan' or not plan_id.isdigit() or not key or int(plan_id) > 2**63 - 1:
            raise ValidationError({'refs': [NOT_HERE]})
        out.setdefault(int(plan_id), []).append(key)
    return out


def _check_action(action):
    if action not in ACTIONS:
        raise ValidationError({'action': ['The action is approve, ignore, check or clear.']})


def _named(deal, wanted):
    """{plan id: [keys]} from refs, every plan a live plan of the deal and every key one of its line's fields."""
    rows = list(Plan.objects.select_for_update().filter(deal=deal, id__in=sorted(wanted)).order_by('id'))
    if len(rows) != len(wanted):
        raise ValidationError({'refs': [NOT_HERE]})
    picked = []
    for plan in rows:
        allowed = set(fields.keys_for(plan.line))
        keys = list(dict.fromkeys(wanted[plan.id]))
        if any(key not in allowed for key in keys):
            raise ValidationError({'refs': [NOT_HERE]})
        picked.append((plan, keys))
    return picked


def _scoped(deal, action, plan_ids, document_ids):
    """The open warnings (for clear, the marked values) on these plans, read from these files."""
    plans = Plan.objects.select_for_update().filter(deal=deal).order_by('id')
    if plan_ids is not None:
        plans = plans.filter(id__in=plan_ids)
    rows = list(plans)
    if plan_ids is not None and len(rows) != len(plan_ids):
        raise ValidationError({'plan_ids': [NO_PLANS]})
    wanted = mark_state if action == CLEAR else open_warning
    picked = []
    for plan in rows:
        keys = [
            key
            for key in fields.keys_for(plan.line)
            if key in plan.values
            and wanted(plan.sources.get(key))
            and (document_ids is None or (plan.sources.get(key) or {}).get('doc') in document_ids)
        ]
        if keys:
            picked.append((plan, keys))
    return picked


def _summary(action, count, plans):
    one = plans[0] if len(plans) == 1 else None
    where = f' on {one.carrier} {one.name}' if one else ''
    what = 'plan value' if count == 1 else 'plan values'
    tail = ' as needing checking' if action == 'check' else ''
    return f'{DONE[action]} {count} {what}{tail}{where}'


@transaction.atomic
def mark_values(user, deal, action, *, refs=None, plan_ids=None, document_ids=None, via=''):
    """Mark plan values; returns `Marked` (only what changed, and the Activity row, None when nothing did). `via`
    'recheck': approvals a person applied from Claude's re-check (E77; slice 22), said so on the value and the row."""
    _check_action(action)
    wanted = parse_refs(refs) if refs is not None else None
    plan_ids = _ids(plan_ids, 'plan_ids', 'Name the plans to review.') if plan_ids is not None else None
    if document_ids is not None:
        document_ids = _ids(document_ids, 'document_ids', 'Name the files to review.')
        found = Document.all_objects.filter(deal=deal, id__in=document_ids).count()
        if found != len(document_ids):
            raise ValidationError({'document_ids': [NO_FILES]})
    deal = locks.deal(deal.id)
    if wanted is not None:
        picked = _named(deal, wanted)
    else:
        picked = _scoped(deal, action, plan_ids, set(document_ids) if document_ids is not None else None)
    by = getattr(user, 'id', None) if getattr(user, 'is_authenticated', False) else None
    at = clock.now().isoformat()
    result, changes = Marked(action), []
    for plan, keys in picked:
        diff = {}
        for key in keys:
            if key not in plan.values:
                continue  # a blank takes no mark
            entry = plan.sources.get(key)
            after = apply_mark(entry, action, by, at, via)
            if after is None:
                continue
            plan.sources[key] = after
            diff[PREFIX + key] = [marks_of(entry), marks_of(after)]
            result.values.append((plan, key))
        if diff:
            flags.stamp(plan)
            result.plans.append(plan)
            changes.append(activity.change(f'plan:{plan.id}', diff))
    if not result.values:
        return result
    Plan.objects.bulk_update(result.plans, ['sources', 'flags'])  # bookkeeping: `updated_at` stays (§3.7)
    count = len(result.values)
    result.row = activity.record(
        deal,
        user,
        'quotes',
        MARKED,
        _summary(action, count, result.plans) + (' from Claude’s re-check' if via == 'recheck' else ''),
        count=count,
        changes=changes,
        document_id=document_ids[0] if document_ids and len(document_ids) == 1 else None,
    )
    return result


def _label(key, plan, many):
    label = fields.BY_KEY[key]['label'] if key in fields.BY_KEY else key
    return f'{label} on {plan.carrier} {plan.name}' if many else label


def revert(row, user):
    """Put back the marks of one `marked` row on the values still as it left them (E88). Runs inside
    `deals.activity.revert`'s transaction, after the Deal lock; locks the plans by id."""
    targets = {}
    for entry in row.changes:
        kind, _, plan_id = entry['t'].partition(':')
        if kind != 'plan' or not plan_id.isdigit():
            raise activity.Refused(activity.NO_REVERTER)
        targets[int(plan_id)] = entry['k']
    rows = Plan.all_objects.select_for_update().filter(deal_id=row.deal_id, id__in=sorted(targets)).order_by('id')
    plans = {plan.id: plan for plan in rows}
    sold = [plan for plan in plans.values() if plan.sold]
    if sold:
        names = ' and '.join(f'{plan.carrier} {plan.name}' for plan in sold)
        one = len(sold) == 1
        raise activity.Refused(
            f'{names} {"is" if one else "are"} marked sold, so this change cannot be reverted. '
            f'Un-sell {"it" if one else "them"} first.'
        )
    written, missed, changed = [], [], []
    for plan_id, keys in targets.items():
        plan = plans.get(plan_id)
        diff = {}
        for name, (before, after) in keys.items():
            key = name.removeprefix(PREFIX)
            entry = plan.sources.get(key) if plan and not plan.removed_at and key in plan.values else None
            if entry is None or marks_of(entry) != after:
                missed.append((plan_id, name, key))
                continue
            plan.sources[key] = with_marks(entry, before)
            diff[name] = [after, before]
        if diff:
            flags.stamp(plan)
            changed.append(plan)
            written.append(activity.change(f'plan:{plan_id}', diff))
    if not written:
        many = len(targets) > 1
        labels = [_label(key, plans[pid], many) if pid in plans else key for pid, _name, key in missed]
        raise activity.changed_since(labels, [name for _pid, name, _key in missed])
    Plan.all_objects.bulk_update(changed, ['sources', 'flags'])
    return written
