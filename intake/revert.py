"""Revert of an intake Activity row (plan.md §3.7, O.3.2): a coverage row's fields, a row added or removed, the lines
to quote and the intent confirmation. Registered as `activity.reverters['intake']` in IntakeConfig.ready().

`deals.activity.revert` has already locked the Deal; this locks the Intake row and the coverage rows the change names,
by id. It refuses after a later write to the same key, and after any later write to a row this change added or
removed (putting it back would drop that write). The lines to quote go back through `deals.services.set_lines`, their
one writer. Returns the changes it wrote, which the revert row records.
"""

import datetime

from deals import activity
from deals.models import Activity
from deals.services import set_lines

from .models import CurrentCoverage
from .services import rows

LABELS = {
    'requested_lines': 'The lines to quote',
    'intent_confirmed': 'The confirmation',
    'in_force': 'In force',
    'on_proposal': 'On the proposal',
    'rate_guarantee_through': 'Rate guarantee',
    'renewal_date': 'Renewal date',
    'effective_date': 'Effective date',
    'commission_source': 'Commission source',
    'line': 'The coverage line',
}
TOUCHED_SINCE = 'This coverage line was changed after this, so this change cannot be reverted.'


def _label(key):
    return LABELS.get(key, key.replace('_', ' ').capitalize())


def _whole_row(entry):
    """'added' or 'removed' when the entry made or deleted its row, else ''."""
    pair = entry['k'].get('line') if isinstance(entry['k'], dict) else None
    if not pair:
        return ''
    return 'added' if pair[0] is None else ('removed' if pair[1] is None else '')


def _refuse_later(row):
    later = activity.later_keys(row)
    if later:
        keys = sorted(later)
        raise activity.changed_since([_label(key) for _target, key in keys], [key for _target, key in keys])
    whole = [entry['t'] for entry in row.changes if _whole_row(entry)]
    for target in whole:
        if Activity.objects.filter(deal_id=row.deal_id, pk__gt=row.pk, changes__contains=[{'t': target}]).exists():
            raise activity.Refused(TOUCHED_SINCE)


def _value(key, value):
    if key in rows.DATES and value:
        return datetime.date.fromisoformat(value)
    if key == 'commission':
        return value or {}
    return value


def _put_back(row_id, diff, deal_id):
    """One coverage entry back: delete an added row, rebuild a removed one under its id, or set fields back."""
    target = rows.target(row_id)
    whole = _whole_row({'k': diff})
    existing = rows.lock_coverage(deal_id, [row_id])
    if whole == 'added':
        if not existing:
            return None
        before = rows.state(existing[0])
        existing[0].delete()
        return activity.change(target, rows.removed(before))
    if whole == 'removed':
        fields = {key: _value(key, before) for key, (before, _after) in diff.items() if before is not None}
        rebuilt = CurrentCoverage.objects.create(pk=row_id, deal_id=deal_id, **fields)
        return activity.change(target, rows.created(rebuilt))
    if not existing:
        raise activity.Refused(TOUCHED_SINCE)
    current = existing[0]
    before = rows.state(current)
    for key, (was, _after) in diff.items():
        setattr(current, key, _value(key, was))
    changed = rows.changed(before, current)
    if changed:
        current.save(update_fields=list(changed))
    return activity.change(target, changed)


def revert(row, user):
    _refuse_later(row)
    deal_id = row.deal_id
    kinds = {entry['t'].partition(':')[0] for entry in row.changes}
    if 'intake' in kinds:
        rows.lock_intake(deal_id)  # lock order: the Deal (already), the Intake row, then coverage rows by id
    ids = [int(entry['t'].partition(':')[2]) for entry in row.changes if entry['t'].startswith('coverage:')]
    if ids:
        rows.lock_coverage(deal_id, ids)
    written = []
    for entry in sorted(row.changes, key=lambda e: e['t']):
        kind, _, ident = entry['t'].partition(':')
        if kind == 'deal' and 'requested_lines' in entry['k']:
            diff = set_lines(deal_id, entry['k']['requested_lines'][0])
            if diff:
                written.append(activity.change(entry['t'], diff))
        elif kind == 'intake':
            intake = rows.lock_intake(deal_id)
            was = entry['k']['intent_confirmed'][0]
            if intake.intent_confirmed != was:
                written.append(activity.change(entry['t'], {'intent_confirmed': [intake.intent_confirmed, was]}))
                intake.intent_confirmed = was
                intake.save(update_fields=['intent_confirmed', 'updated_at'])
        elif kind == 'coverage':
            change = _put_back(int(ident), entry['k'], deal_id)
            if change and change['k']:
                written.append(change)
    return written
