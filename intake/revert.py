"""Revert of an intake Activity row (plan.md §3.7, O.3.2): the answers (and the deal's effective date, their door), a
coverage row's fields, a row added or removed, the lines to quote and the intent confirmation. Registered as
`activity.reverters['intake']` in IntakeConfig.ready().

`deals.activity.revert` has already locked the Deal; this locks the Intake row and the coverage rows the change names,
by id. It refuses after a later write to the same key, and after any later write to a row this change added or
removed (putting it back would drop that write). The lines to quote go back through `deals.services.set_lines`, their
one writer, and the effective date through `set_effective_date`. An answer goes back through `values.apply`: one that
goes back to what was read gets its read source back. Returns the changes it wrote, which the revert row records.
"""

import datetime

from deals import activity
from deals.models import Activity, Deal
from deals.services import set_effective_date, set_lines
from deals.values import apply as apply_values
from deals.values import source

from . import checklist as checklist_rules
from . import flags, form
from .models import CurrentCoverage
from .services import approvals, bor, checklist, marketed, marks, rows
from .services import rules as question_rules
from .signals import announce

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
    'cobra': 'The COBRA check',
    'name': 'The BOR signature',
    'signed_at': 'The BOR signature',
    'signed_by': 'The BOR signature',
    'marketed_at': 'Sent to market',
    'marketed_by': 'Sent to market',
}
TOUCHED_SINCE = 'This coverage line was changed after this, so this change cannot be reverted.'
APPROVE_AGAIN = 'Taking back an approval is not reverted: approve the answer again from the review queue.'
DOORS = {'checklist': checklist.revert, 'bor': bor.revert, 'marketed': marketed.revert}  # slice 40's gate
DOORS['rules'] = question_rules.revert  # the deal's own rule per question (B37; slice 57)


def _label(key):
    if key in form.BY_KEY:
        return form.BY_KEY[key]['label']
    if key == form.GUIDANCE:
        return 'Client guidance'
    if key in checklist_rules.LABELS and key not in LABELS:
        return checklist_rules.LABELS[key]
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


def _answers_back(deal_id, intake, diff, user):
    """The answers' "before" back, through `values.apply`: an added answer is cleared, and one that goes back to
    what was read takes its read source (None)."""
    wanted = {}
    for key, (before, _after) in diff.items():
        if before is None:
            wanted[key] = ''
        elif (intake.sources.get(key) or {}).get('read_value') == before:
            wanted[key] = None
        else:
            wanted[key] = before
    answers, sources = dict(intake.answers), dict(intake.sources)
    changed = apply_values(answers, sources, wanted, source('typed', user))
    if changed:
        intake.answers, intake.sources = answers, sources
        flags.stamp(Deal.objects.get(pk=deal_id), intake)
        intake.save(update_fields=['answers', 'sources', 'flags', 'updated_at'])
    return changed


def _date_back(deal_id, before, user):
    """The deal's effective date back, with the answer's source entry following it."""
    changed = set_effective_date(deal_id, datetime.date.fromisoformat(before) if before else None)
    if changed:
        intake = rows.lock_intake(deal_id)
        sources = dict(intake.sources)
        if before:
            sources[form.EFFECTIVE_DATE] = source('typed', user)
        else:
            sources.pop(form.EFFECTIVE_DATE, None)
        intake.sources = sources
        flags.stamp(Deal.objects.get(pk=deal_id), intake)
        intake.save(update_fields=['sources', 'flags', 'updated_at'])
    return changed


def _reopen(deal_id, row):
    """An approval of the client's answers undone (slice 55): those answers wait for review again."""
    keys = [key for entry in row.changes if entry['t'].partition(':')[0] in ('intake', 'deal') for key in entry['k']]
    intake = rows.lock_intake(deal_id)
    approvals.reopen(intake, [form.EFFECTIVE_DATE if key == 'effective_date' else key for key in keys])
    intake.save(update_fields=['client', 'updated_at'])


def revert(row, user):
    if row.action == marks.MARKED:
        return marks.revert(row, user)  # review marks: back where the answer is still as the row left it (E88)
    if row.action == approvals.UNAPPROVED:
        raise activity.Refused(APPROVE_AGAIN)
    written = _revert(row, user)
    if row.action == approvals.APPROVED:
        _reopen(row.deal_id, row)
    return written


def _revert(row, user):
    _refuse_later(row)
    deal_id = row.deal_id
    kinds = {entry['t'].partition(':')[0] for entry in row.changes}
    if kinds & {'intake', *DOORS}:
        rows.lock_intake(deal_id)  # lock order: the Deal (already), the Intake row, then coverage rows by id
    ids = [int(entry['t'].partition(':')[2]) for entry in row.changes if entry['t'].startswith('coverage:')]
    if ids:
        rows.lock_coverage(deal_id, ids)
    written = []
    for entry in sorted(row.changes, key=lambda e: e['t']):
        kind, _, ident = entry['t'].partition(':')
        if kind == 'deal':
            diff = {}
            if 'requested_lines' in entry['k']:
                diff.update(set_lines(deal_id, entry['k']['requested_lines'][0]))
            if 'effective_date' in entry['k']:
                diff.update(_date_back(deal_id, entry['k']['effective_date'][0], user))
            if diff:
                written.append(activity.change(entry['t'], diff))
        elif kind == 'intake':
            intake = rows.lock_intake(deal_id)
            diff = {}
            if 'intent_confirmed' in entry['k']:
                was = entry['k']['intent_confirmed'][0]
                if intake.intent_confirmed != was:
                    diff['intent_confirmed'] = [intake.intent_confirmed, was]
                    intake.intent_confirmed = was
                    intake.save(update_fields=['intent_confirmed', 'updated_at'])
            answered = {key: pair for key, pair in entry['k'].items() if key != 'intent_confirmed'}
            if answered:
                diff.update(_answers_back(deal_id, intake, answered, user))
            if diff:
                written.append(activity.change(entry['t'], diff))
        elif kind in DOORS:
            diff = DOORS[kind](deal_id, entry['k'])  # a checklist item, the BOR signature, the marketed stamp
            if diff:
                written.append(activity.change(entry['t'], diff))
        elif kind == 'coverage':
            change = _put_back(int(ident), entry['k'], deal_id)
            if change and change['k']:
                written.append(change)
    if any(entry['t'].partition(':')[0] not in DOORS for entry in written):
        announce(deal_id)  # the lines to quote or a coverage row came back: census's required columns follow
    return written
