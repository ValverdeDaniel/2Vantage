"""The deal's own rule for an intake question (plan.md §5.2, §6.5 `Intake.rules`; B37, OQ17; old 891f1b3
`intake_review.set_requirements`): Auto, Required or Waived, and the note the client reads on their link instead of
our help text. Written from Review & requests' Intake board (slice 57), never anywhere else.

`set_rules(user, deal_id, changes)`: `changes` {question key: {state?: '' | 'required' | 'waived', note?: text ≤ 300}}.
Required makes the deal need the question, Waived lets it go (and wins), '' is Auto again (§5.2 readiness, the
`required` ask and the star all read `values.needed`, so they follow at once). A rule is stored as its state, or as
{state, note} when it carries a note; Auto with no note is removed. Lock order: the Deal, then the Intake row (created
on this first write). One Activity row (area intake, target `rules:<deal>`, before and after per key; a rule is not a
value), revertible through intake's reverter (`revert`). An unchanged rule writes nothing.
"""

from django.db import transaction
from rest_framework.exceptions import ValidationError

from deals import activity

from .. import flags, form, values
from . import rows

STATES = ('', values.REQUIRED, values.WAIVED)
NOTE_LIMIT = 300
NOTHING = 'Send the rules as an object of question keys.'


def target(deal_id):
    return f'rules:{deal_id}'


def stored(state, note):
    """What `Intake.rules` keeps for a question: None (Auto, no note), the state, or {state, note}."""
    if note:
        return {'state': state, 'note': note}
    return state or None


def note_of(rule):
    return (rule.get('note') or '') if isinstance(rule, dict) else ''


def _clean(changes, current):
    if not isinstance(changes, dict) or not changes:
        raise ValidationError({'rules': [NOTHING]})
    out, errors = {}, []
    for key, wanted in changes.items():
        if key not in form.BY_KEY or not isinstance(wanted, dict):
            errors.append(f'Not an intake question: {str(key)[:60]}.')
            continue
        rule = current.get(key)
        state = wanted.get('state', values.rule_of(current, key))
        note = str(wanted.get('note', note_of(rule)) or '').strip()
        if state not in STATES:
            errors.append('Name the rule as Auto (""), required or waived.')
        elif len(note) > NOTE_LIMIT:
            errors.append(f'Keep the note under {NOTE_LIMIT} characters.')
        else:
            out[key] = stored(state, note)
    if errors:
        raise ValidationError({'rules': errors})
    return out


@transaction.atomic
def set_rules(user, deal_id, changes):
    """{key: [before, after]} written, and the Activity row (or None)."""
    deal = rows.lock_deal(deal_id)
    intake = rows.lock_intake(deal_id)
    current = dict(intake.rules or {})
    wanted = _clean(changes, current)
    diff = {key: [current.get(key), rule] for key, rule in wanted.items() if current.get(key) != rule}
    if not diff:
        return {}, None
    for key, (_before, after) in diff.items():
        if after is None:
            current.pop(key, None)
        else:
            current[key] = after
    intake.rules = current
    flags.stamp(deal, intake)
    intake.save(update_fields=['rules', 'flags', 'updated_at'])
    count = len(diff)
    summary = f'Changed what this deal needs on {count} intake question{"" if count == 1 else "s"}'
    row = activity.record(deal, user, rows.AREA, 'rules', summary, changes=[activity.change(target(deal_id), diff)])
    return diff, row


def revert(deal_id, diff):
    """Put the rules of one entry back (intake/revert.py, after the Deal and Intake locks). Returns the diff written."""
    intake = rows.lock_intake(deal_id)
    current, written = dict(intake.rules or {}), {}
    for key, (before, _after) in diff.items():
        if current.get(key) == before:
            continue
        written[key] = [current.get(key), before]
        if before is None:
            current.pop(key, None)
        else:
            current[key] = before
    if written:
        intake.rules = current
        intake.save(update_fields=['rules', 'updated_at'])
    return written
