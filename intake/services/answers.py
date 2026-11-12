"""The intake answers: the form's one writer (plan.md §5.2, §7.6; B1, B3, B4, B.6).

`update_answers` takes the raw answers of one request, cleans every key with the one cleaner (`values.clean_answers`:
the producer, Claude and the portal share it, B.5), and saves all of them or none (400 naming each refused key).
Values and sources go through `deals.values.apply()` (§3.7): an unchanged answer writes nothing, not its source, the
row's `updated_at` or Activity; '' clears an answer; None puts back what was read. The Intake row is created by the
first write that changes something, never by a read.

- `target_effective_date` is a door onto the deal's one effective date (B1, N.1): its value lives on the Deal, written
  through `deals.services.set_effective_date`; only its source entry is kept here.
- `expect` ({key: the value the person last saw}) refuses the whole write with a 409 naming the questions that
  changed since (O.6 #33).
- `origin` is `typed`, or `relay` when a person enters the client's answers for them ("These came from the client").
  Either closes a client's answer still waiting on the same question as `replaced` (L.6 Ch. 13d, slice 55), so the
  portal never reads it as rejected; Claude's edits leave it waiting.
Lock order: the Deal, then the Intake row (O.3.7). One Activity row (area `intake`), coalescing a burst of edits
("Edited 3 intake answers"); intake's reverter puts it back. `Intake.flags` is rewritten in the same transaction.
"""

import datetime
from collections import namedtuple

from django.db import transaction
from rest_framework.exceptions import ValidationError

from deals import activity, clock
from deals.services import set_effective_date
from deals.values import apply as apply_values
from deals.values import source

from .. import client_entries, flags, form, values
from ..models import Intake
from . import rows

Answered = namedtuple('Answered', 'changed sources activity')  # changed: {key: [before, after]}; sources: {key: entry}

ORIGINS = ('typed', 'relay')
STALE = '{names} changed since you last saw {it}, so nothing was saved. Reload to see the new {value}.'
NOT_ANSWERS = 'Send the answers as an object of question keys.'
NOT_EXPECT = 'Expect must be an object of question keys.'
SUMMARY = {'typed': ('Edited', 'intake answer'), 'relay': ('Entered', "client's intake answer")}


def label(key):
    return 'Client guidance' if key == form.GUIDANCE else form.BY_KEY[key]['label']


def _same(stored, seen):
    """Whether a stored answer is what the person saw: blanks match, a list matches its list."""
    if values.blank(stored) and values.blank(seen):
        return True
    if isinstance(stored, list) or isinstance(seen, list):
        return list(stored or []) == list(seen or [])
    return str(stored).strip() == str(seen).strip()


def _refuse_stale(current, expect):
    if not isinstance(expect, dict):
        raise ValidationError({'expect': [NOT_EXPECT]})
    keys = [key for key, seen in expect.items() if key in form.ANSWER_KEYS and not _same(current.get(key), seen)]
    if not keys:
        return
    labels = [label(key) for key in keys]
    names = labels[0] if len(labels) == 1 else ', '.join(labels[:-1]) + ' and ' + labels[-1]
    one = len(labels) == 1
    text = STALE.format(names=names, it='it' if one else 'them', value='answer' if one else 'answers')
    raise activity.Refused(text, keys)


def _date(value):
    return datetime.date.fromisoformat(value) if value else None


@transaction.atomic
def update_answers(user, deal_id, raw, *, expect=None, origin='typed', by_claude=False):
    """Save the answers that changed. Returns Answered({key: [before, after]}, {key: source entry or None}, Activity
    row or None). `by_claude`: Claude's change from a chat turn (slice 24), recorded as Claude's in a row of its own
    that never merges with the person's edits, so ↶ Undo this run puts back only what Claude changed."""
    if not isinstance(raw, dict) or not raw:
        raise ValidationError({'answers': [NOT_ANSWERS]})
    if origin not in ORIGINS:
        raise ValueError(f'Not an answer origin: {origin}')
    cleaned, errors = values.clean_answers(raw)
    if errors:
        raise ValidationError({'answers': errors})
    deal = rows.lock_deal(deal_id)
    intake = Intake.objects.select_for_update().filter(deal_id=deal_id).first()
    from ..selectors import answers_of

    answers = answers_of(deal, intake)
    if expect is not None:
        _refuse_stale(answers, expect)
    sources = dict(intake.sources) if intake else {}
    changed = apply_values(answers, sources, cleaned, source(origin, user))
    if not changed:
        return Answered({}, {}, None)
    entries = []
    if form.EFFECTIVE_DATE in changed:
        deal.effective_date = _date(answers.get(form.EFFECTIVE_DATE))
        moved = set_effective_date(deal_id, deal.effective_date)
        entries.append(activity.change(f'deal:{deal_id}', moved))
    if intake is None:
        intake = Intake.objects.create(deal_id=deal_id)
    intake.answers = {key: value for key, value in answers.items() if key != form.EFFECTIVE_DATE}
    intake.sources = sources
    if not by_claude:  # a person's edit closes a client answer waiting on the same question (Ch. 13d)
        by, at = getattr(user, 'id', None), clock.now().isoformat()
        intake.client = client_entries.replaced(intake.client, changed, by, at)
    flags.stamp(deal, intake)
    intake.save(update_fields=['answers', 'sources', 'flags', 'client', 'updated_at'])
    kept = {key: pair for key, pair in changed.items() if key != form.EFFECTIVE_DATE}
    if kept:
        entries.insert(0, activity.change(rows.intake_target(deal_id), kept))
    summary, noun = SUMMARY[origin]
    coalesce = f'intake:answers:{origin}'
    if by_claude:
        summary, coalesce = f'Claude edited {len(changed)} {noun}{"" if len(changed) == 1 else "s"}', ''
    row = activity.record(
        deal,
        user,
        rows.AREA,
        'answers',
        summary,
        len(changed),
        coalesce,
        noun,
        changes=entries,
        actor_kind='claude' if by_claude else None,
    )
    return Answered(changed, {key: sources.get(key) for key in changed}, row)
