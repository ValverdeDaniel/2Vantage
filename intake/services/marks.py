"""Reviewing intake answers: approve, ignore, needs checking and clear (plan.md §10.7; B10, B11; E85–E88; the old
`reviewCaseValues` door, scope `case_fields`).

`mark_answers` is intake's one marks writer, behind `POST deals/{id}/intake/marks/` (the form's ☑ Select fields bar and
its review bar; the station's intake view later). It names its answers one of two ways (E86):
- `refs`: exactly those answers ("intake:fein"), whatever their state — a blank takes no mark;
- none: the open warnings on the shown answers (for `clear`, the marked ones), so the review bar never touches more
  than it counts.
It locks the Deal, then the Intake row (O.3.7), applies `documents.review_rules.apply_mark` to each entry, restamps
`Intake.flags`, and records one Activity row (action `marked`, never merged) holding each answer's marks before and
after under `mark.<key>`, never the answer. Marks are bookkeeping: `updated_at` stays (§3.7). Revert (E88) puts back
the marks of the answers still as it left them, and is refused, naming them, when none is.
"""

from collections import namedtuple

from django.db import transaction
from rest_framework.exceptions import ValidationError

from deals import activity, clock
from documents.review_rules import ACTIONS, CLEAR, apply_mark, mark_state, marks_of, open_warning, with_marks

from .. import flags, form, values
from ..models import Intake
from . import rows

Marked = namedtuple('Marked', 'action keys sources row')  # keys: the answers whose marks changed

MARKED = 'marked'
PREFIX = 'mark.'
DONE = {'approve': 'Approved', 'ignore': 'Ignored', 'check': 'Flagged', 'clear': 'Unmarked'}
NOT_HERE = 'Some of those are not intake questions.'


def parse_refs(raw):
    """["intake:fein", ...] → [keys]; 400 for an empty list or a ref that is not an intake answer's."""
    if not isinstance(raw, list) or not raw:
        raise ValidationError({'refs': ['Name the answers to review.']})
    keys = []
    for ref in raw:
        kind, _, key = str(ref).partition(':')
        if kind != 'intake' or key not in form.ANSWER_KEYS:
            raise ValidationError({'refs': [NOT_HERE]})
        keys.append(key)
    return list(dict.fromkeys(keys))


def _summary(action, count):
    what = 'intake answer' if count == 1 else 'intake answers'
    tail = ' as needing checking' if action == 'check' else ''
    return f'{DONE[action]} {count} {what}{tail}'


def _scoped(intake, action, answers):
    hidden = set(values.hidden(answers))
    wanted = mark_state if action == CLEAR else open_warning
    return [key for key in form.ANSWER_KEYS if key not in hidden and wanted(intake.sources.get(key))]


@transaction.atomic
def mark_answers(user, deal_id, action, *, refs=None):
    """Mark intake answers; returns Marked(action, keys changed, {key: entry}, Activity row or None)."""
    if action not in ACTIONS:
        raise ValidationError({'action': ['The action is approve, ignore, check or clear.']})
    keys = parse_refs(refs) if refs is not None else None
    deal = rows.lock_deal(deal_id)
    intake = Intake.objects.select_for_update().filter(deal_id=deal_id).first()
    if intake is None:
        return Marked(action, [], {}, None)  # nothing answered, nothing to mark; a read never makes the row
    from ..selectors import answers_of

    answers = answers_of(deal, intake)
    picked = keys if keys is not None else _scoped(intake, action, answers)
    by = getattr(user, 'id', None) if getattr(user, 'is_authenticated', False) else None
    at = clock.now().isoformat()
    sources, diff, changed = dict(intake.sources), {}, []
    for key in picked:
        if values.blank(answers.get(key)):
            continue  # a blank takes no mark
        entry = sources.get(key)
        after = apply_mark(entry, action, by, at)
        if after is None:
            continue
        sources[key] = after
        diff[PREFIX + key] = [marks_of(entry), marks_of(after)]
        changed.append(key)
    if not changed:
        return Marked(action, [], {}, None)
    intake.sources = sources
    flags.stamp(deal, intake)
    intake.save(update_fields=['sources', 'flags'])  # bookkeeping: `updated_at` stays (§3.7)
    row = activity.record(
        deal,
        user,
        rows.AREA,
        MARKED,
        _summary(action, len(changed)),
        count=len(changed),
        changes=[activity.change(rows.intake_target(deal_id), diff)],
    )
    return Marked(action, changed, {key: sources[key] for key in changed}, row)


def revert(row, user):
    """Put back the marks of one `marked` row on the answers still as it left them (E88). Runs inside
    `deals.activity.revert`'s transaction, after the Deal lock."""
    from deals.models import Deal

    intake = Intake.objects.select_for_update().filter(deal_id=row.deal_id).first()
    sources = dict(intake.sources) if intake else {}
    written, missed = {}, []
    for entry in row.changes:
        for name, (before, after) in entry['k'].items():
            key = name.removeprefix(PREFIX)
            current = sources.get(key)
            if current is None or marks_of(current) != after:
                missed.append((name, key))
                continue
            sources[key] = with_marks(current, before)
            written[name] = [after, before]
    if not written:
        labels = [form.BY_KEY[key]['label'] if key in form.BY_KEY else key for _name, key in missed]
        raise activity.changed_since(labels, [name for name, _key in missed])
    intake.sources = sources
    flags.stamp(Deal.objects.get(pk=row.deal_id), intake)
    intake.save(update_fields=['sources', 'flags'])
    return [activity.change(rows.intake_target(row.deal_id), written)]
