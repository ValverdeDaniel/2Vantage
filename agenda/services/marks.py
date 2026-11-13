"""The one writer of `StepMark` (I15–I26; I.6 `services/marks.py`): Later, Done anyway, clearing either, and logging a
follow-up. Each runs in one transaction, locks the Deal and then the mark, records Activity and returns what changed;
the same call again writes nothing. The facts are read once, outside the lock, to find the step as the system sees it
now (`selectors.marked_steps`); a mark is always decided against that, never against what the browser sent.

- `set_later(user, deal_id, step_key, until, note='')`: back on `until`, a day after the agency's today (I15). The note
  stays on the mark for the detail line and is also written as a deal Note "Back to “<title>” on <day>: <note>" in the
  same transaction, so it outlives the mark (I18).
- `set_done_anyway(user, deal_id, step_key, note='')`: counts the step done while its signature holds (I19–I21).
- `clear_mark(user, deal_id, step_key)`: Bring back, or Undo (I22).
- `log_follow_up(user, deal_id, step_key, kind, body)`: a deal Note (a call or an email) and a Later mark for the
  step's wait, all or nothing (I24).
Each returns {step, next_step} (log_follow_up: {step, note}). Marks are firm-wide (OQ92): one row per step.
"""

from datetime import timedelta

from django.db import transaction

from deals import clock
from deals.services import add_note
from deals.services.notes import clean_body

from .. import catalogue, marks, rules, selectors
from ..models import StepMark
from .common import lock_deal, mark_target, record, refuse

NONE = {'kind': None, 'until': None, 'sig': ''}
NOT_A_FOLLOW_UP = 'Only a follow-up is logged: mark this step Later or Done anyway instead.'
FOLLOW_UP_KIND = 'Say how you followed up: a call or an email.'
NOTE_TOO_LONG = f'Keep the note under {rules.MARK_NOTE_MAX:,} characters.'
NO_MARK = 'This step has no mark to clear.'


def _state(mark):
    if mark is None:
        return dict(NONE)
    return {'kind': mark.kind, 'until': mark.until.isoformat() if mark.until else None, 'sig': mark.sig}


def _note(raw):
    note = str(raw or '').strip()
    if len(note) > rules.MARK_NOTE_MAX:
        refuse(400, NOTE_TOO_LONG)
    return note


def _decide(deal_id, step_key, kind, until):
    """(facts, unmarked steps, today, the step) once checked, else the refusal is raised."""
    facts, unmarked, _marked, today = selectors.marked_steps(deal_id)
    step = next((row for row in unmarked if row['key'] == step_key), None)
    refusal = marks.check_mark(step_key, step, kind, until, today, lost=facts['deal']['lost'])
    if refusal:
        refuse(*refusal)
    return facts, unmarked, today, step


def _summary(kind, step_key, until):
    title = catalogue.title(step_key)
    if kind == rules.LATER:
        return f'Later: {title} (back {rules.short_day(until)})'
    return f'Done anyway: {title}'


def _write(user, deal, step_key, kind, until, step, note):
    """Upsert the mark under the Deal's lock; record Activity when it changed. Returns True when anything changed."""
    mark = StepMark.objects.select_for_update().filter(deal=deal, step_key=step_key).first()
    before = _state(mark)
    after = {
        'kind': kind,
        'until': until.isoformat() if kind == rules.LATER else None,
        'sig': marks.sig(step) if kind == rules.DONE else '',
    }
    if before == after and mark.note == note:
        return False
    who = user if getattr(user, 'is_authenticated', False) else None
    StepMark.objects.update_or_create(
        deal=deal,
        step_key=step_key,
        defaults={
            'kind': kind,
            'until': until if kind == rules.LATER else None,
            'sig': after['sig'],
            'note': note,
            'by': who,
            'at': clock.now(),
        },
    )
    diff = {key: [before[key], after[key]] for key in after if before[key] != after[key]}
    changes = [{'t': mark_target(step_key), 'k': diff}] if diff else [{'t': mark_target(step_key), 'k': ['note']}]
    record(deal, user, 'marked' if diff else 'updated', _summary(kind, step_key, until), changes)
    return True


def _answer(deal_id, unmarked, step_key, facts):
    marked = marks.apply_marks(unmarked, selectors.stored_marks(deal_id), clock.today())
    return selectors.step_payload(deal_id, step_key, marked, facts)


def set_later(user, deal_id, step_key, until, note=''):
    note, day = _note(note), rules.parse_day(until)
    facts, unmarked, _today, step = _decide(deal_id, step_key, rules.LATER, day)
    with transaction.atomic():
        deal = lock_deal(deal_id)
        changed = _write(user, deal, step_key, rules.LATER, day, step, note)
        if changed and note:
            body = f'Back to “{catalogue.title(step_key)}” on {rules.short_day(day)}: {note}'
            add_note(user, deal_id, body=body[: rules.FOLLOW_UP_MAX])
    return _answer(deal_id, unmarked, step_key, facts)


def set_done_anyway(user, deal_id, step_key, note=''):
    note = _note(note)
    facts, unmarked, _today, step = _decide(deal_id, step_key, rules.DONE, None)
    with transaction.atomic():
        _write(user, lock_deal(deal_id), step_key, rules.DONE, None, step, note)
    return _answer(deal_id, unmarked, step_key, facts)


def clear_mark(user, deal_id, step_key):
    facts, unmarked, _marked, _today = selectors.marked_steps(deal_id)
    with transaction.atomic():
        deal = lock_deal(deal_id)
        mark = StepMark.objects.select_for_update().filter(deal=deal, step_key=step_key).first()
        if mark is None:
            refuse(409, NO_MARK)
        before = _state(mark)
        mark.delete()
        verb = 'Brought back' if before['kind'] == rules.LATER else 'Undid Done anyway'
        summary = f'{verb}: {catalogue.title(step_key)}'
        diff = {key: [before[key], NONE[key]] for key in NONE if before[key] != NONE[key]}
        record(deal, user, 'unmarked', summary, [{'t': mark_target(step_key), 'k': diff}])
    return _answer(deal_id, unmarked, step_key, facts)


def log_follow_up(user, deal_id, step_key, kind, body):
    """The follow-up done the way it is done (I24): what was said as a deal Note, then the step waits again."""
    if kind not in rules.FOLLOW_UP_KINDS:
        refuse(400, FOLLOW_UP_KIND)
    if not rules.is_follow_up(step_key):
        refuse(400, NOT_A_FOLLOW_UP)
    text = clean_body(str(body or '').strip() or 'Followed up.')
    today = clock.today()
    until = today + timedelta(days=max(1, rules.wait_days(step_key)))
    facts, unmarked, _today, step = _decide(deal_id, step_key, rules.LATER, until)
    with transaction.atomic():
        deal = lock_deal(deal_id)
        note = add_note(user, deal_id, body=text, kind=kind)
        _write(user, deal, step_key, rules.LATER, until, step, '')
    answer = _answer(deal_id, unmarked, step_key, facts)
    return {'step': answer['step'], 'next_step': answer['next_step'], 'note': note}
