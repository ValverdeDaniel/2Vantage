"""Staff answers (plan.md §6.8, §7.9; G18, G27, G33, G40, G123, G136).

`set_answers(user, deal_id, form_key, raw, relay=False)` is the tab's one writer of answers: the batch is cleaned
against the form as it stands (`cleaning.clean_batch`, every drop reported), then applied through
`deals.values.apply` with a `typed` source (`relay` for "From the client — entered by us", G79). Clearing a box that
shows the live prefill adds the slot to `cleared`, which hides only the prefill (G33); typing into it again takes it
off. A locked form refuses (409). One Activity row per burst, coalesced per form, with before and after for ordinary
answers and keys only for sensitive ones. A person's edit of a slot a client's answer waits on closes that answer as
`replaced` (Ch. 13d; slice 58): "Correct" in the review queue and "Enter it" both write here.

`revert(row, user)` puts a burst back (G123): each slot goes back to its earlier value — a slot that was never
written goes back to "not written", so its live prefill shows again. It refuses, naming them, when a later write
touched any of its slots (rule 4, Q.3 #1: G123's "skip what changed since" would leave half a burst), and on a signed
form.
"""

from collections import namedtuple

from django.db import transaction
from rest_framework.exceptions import ValidationError

from deals import activity, clock
from deals.values import apply, source
from intake import client_entries as entries_rule

from .. import cleaning, slots
from ..engine.spec import field_spec
from . import common

Answered = namedtuple('Answered', 'row changed dropped activity facts')
NOT_AN_OBJECT = 'Send the answers as an object of slot: value.'
CLEARED = 'cleared:'


def _split(cleaned, stored, live):
    """(values to apply, slots to clear, slots to unclear): emptying a box that shows the live prefill and holds no
    stored value only hides the prefill; emptying a stored value also hides a prefill behind it."""
    changes, clear, unclear = {}, set(), set()
    for slot, value in cleaned.items():
        if value == '':
            if slot in stored.answers:
                changes[slot] = ''
            if live.get(slot) and slot not in stored.cleared:
                clear.add(slot)
        else:
            changes[slot] = value
            if slot in stored.cleared:
                unclear.add(slot)
    return changes, clear, unclear


@transaction.atomic
def set_answers(user, deal_id, form_key, raw, *, relay=False):
    """Answered(row, changed {slot: [before, after]}, dropped [{slot, reason, options?}], activity, facts)."""
    if not isinstance(raw, dict):
        raise ValidationError({'answers': [NOT_AN_OBJECT]})
    deal = common.lock_deal(deal_id)
    row, _ctx, facts = common.open_row(user, deal, form_key)
    common.refuse_locked(row)
    view = common.view_of(row, facts)
    cleaned, dropped = cleaning.clean_batch(view.form, view.view, view.stored.rows, raw)
    changes, clear, unclear = _split(cleaned, view.stored, view.prefill)
    answers, sources = dict(row.answers), dict(row.sources)
    diff = apply(answers, sources, changes, source('relay' if relay else 'typed', user))
    cleared = [slot for slot in row.cleared if slot not in unclear] + sorted(clear - set(row.cleared))
    for slot in clear - set(row.cleared):
        diff[CLEARED + slot] = [False, True]
    for slot in unclear:
        diff[CLEARED + slot] = [True, False]
    if not diff:
        return Answered(row, {}, dropped, None, facts)
    row.answers, row.sources, row.cleared = answers, sources, cleared
    touched = [key.removeprefix(CLEARED) for key in diff]
    row.client = entries_rule.replaced(row.client or {}, touched, getattr(user, 'id', None), clock.now().isoformat())
    common.restamp(row, facts)
    row.save(update_fields=['answers', 'sources', 'cleared', 'client', 'flags', 'updated_at'])
    plain, hidden = common.record_values(deal, user, row, 'edited', diff)
    return Answered(row, diff, dropped, plain or hidden, facts)


def label_of(form, key):
    slot = key.removeprefix(CLEARED)
    found = slots.parse(slot)
    field = field_spec(form, found[0], found[2]) if found else None
    return (field or {}).get('label', slot)


def revert(row_activity, user, row):
    """Put one `answers` burst back (`questionnaire/revert.py` locked the Deal and the row)."""
    from ..forms import FORMS

    if row.locked:
        raise activity.Refused('This questionnaire is signed: reopen the form before reverting its answers.')
    diff = {}
    for entry in row_activity.changes:
        if isinstance(entry['k'], dict):
            diff.update(entry['k'])
    later = {key for _target, key in activity.later_keys(row_activity)}
    answers, sources, cleared = dict(row.answers), dict(row.sources), list(row.cleared)
    moved = [
        key
        for key, (_before, after) in diff.items()
        if key in later
        or (key.startswith(CLEARED) and (key.removeprefix(CLEARED) in cleared) != bool(after))
        or (not key.startswith(CLEARED) and answers.get(key) != after)
    ]
    if moved:
        raise activity.changed_since([label_of(FORMS[row.form], key) for key in moved], moved)
    written = {}
    for key, (before, after) in diff.items():
        if key.startswith(CLEARED):
            slot = key.removeprefix(CLEARED)
            cleared = [s for s in cleared if s != slot] + ([slot] if before else [])
            written[key] = [after, before]
        else:
            written.update(apply(answers, sources, {key: '' if before is None else before}, source('typed', user)))
    row.answers, row.sources, row.cleared = answers, sources, cleared
    return row, written
