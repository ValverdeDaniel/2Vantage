"""Every write to the RFP request (plan.md §6.10, §7.11; K.6 services; K9, K10, K20–K27, K115).

- `update(user, deal_id, changes)`: the request's settings (route, carriers and funding as `{add, remove}`, other
  carriers, due date, notes), cleaned by `cleaners.apply`. An unchanged value writes nothing. Each edit takes the
  completed mark off the card that owns it, in the same transaction (K10; `CARD_OF`). One Activity row per call
  (area `rfp`), coalesced as `rfp:request:<deal>`: a burst of chip clicks is one row whose first "before" and last
  "after" an Undo puts back (K115). Notes are free text for the carriers and never enter Activity: their edit gets a
  row of its own that names the key only (K115's "a summary only"), coalesced as `rfp:notes:<deal>`.
- `set_done(user, deal_id, card, done)`: a card marked completed ({by: user id, at}) or not (K9); never coalesced.
- `clear_coverage_mark`: intake's `coverage_changed` receiver: an intent or coverage edit takes the coverage card's
  mark off inside intake's transaction (K10; the proposal builder's J46 does the same), one JSONB `-`, no Activity.
  The checklist card's mark comes off from the page after a checklist edit there (K10: intake never sees rfp).

Lost deals keep every edit (K111); sends, refused there, arrive with slice 46. The row is made by the first write, never
by a GET. Lock order (rule 3): the Deal first (it serializes the row's creation), then the RfpRequest row.
"""

from collections import namedtuple
from datetime import date

from django.db import transaction
from django.db.models.expressions import RawSQL
from rest_framework.exceptions import ValidationError

from deals import activity, clock
from deals.models import Deal
from quotes import facts as quote_facts

from . import cleaners, request
from .models import RfpRequest

AREA = 'rfp'
MARKED = 'marked'  # a mark's Activity action: never merged (deals.activity.NEVER_MERGE)
COVERAGE, REQUEST, CHECKLIST, PACKET, EMAILS = 'coverage', 'request', 'checklist', 'packet', 'emails'
# The page's cards in page order, with their titles (old CarriersTab.jsx RFP_CARDS and its BuilderCard titles).
CARDS = (
    (COVERAGE, 'Coverage & marketing intent'),
    (REQUEST, 'What we’re requesting'),
    (CHECKLIST, 'Marketing readiness checklist'),
    (PACKET, 'RFP packet'),
    (EMAILS, 'Emails to send'),
)
CARD_KEYS = tuple(key for key, _ in CARDS)
CARD_TITLES = dict(CARDS)
CARD_OF = dict.fromkeys(cleaners.SETTINGS, REQUEST)  # the packet's include and form chip join with slices 45–46
PRIVATE = ('notes',)  # never in Activity, by value

Updated = namedtuple('Updated', 'changed cleared activity')  # {key: after}, [cards whose mark came off], last row
Done = namedtuple('Done', 'done activity')  # every mark now, Activity row or None


def target(deal_id):
    return f'rfp:{deal_id}'


def _locked(deal_id):
    """(the Deal, the RfpRequest row or None), locked in that order."""
    deal = Deal.objects.select_for_update().get(pk=deal_id)
    return deal, RfpRequest.objects.select_for_update().filter(deal_id=deal_id).first()


def default_funding(deal):
    """The funding asked while none is picked (K22): the medical incumbent's, else fully insured and level-funded."""
    found = quote_facts.incumbent(deal, 'medical') or {}
    return request.default_funding(found.get('funding'))


def put(row, values):
    """Write cleaned settings onto the row, in memory (the due date arrives as ISO text)."""
    for key, value in values.items():
        setattr(row, key, date.fromisoformat(value) if key == 'due_date' and value else value)


def _take_off(row, cards):
    """{'done.<card>': [stamp, None]} for the marks of `cards` removed from `row.done`, in memory."""
    out = {}
    for card in sorted(cards):
        before = (row.done or {}).get(card)
        if before:
            row.done = {key: stamp for key, stamp in row.done.items() if key != card}
            out[f'done.{card}'] = [before, None]
    return out


def _record(deal, user, diff, cleared):
    """The values row (settings by value, marks cleared) and, for notes, a row naming the key only."""
    shown = {key: pair for key, pair in diff.items() if key not in PRIVATE}
    hidden = [key for key in diff if key in PRIVATE]
    row = None
    if shown:
        change = activity.change(target(deal.id), {**shown, **cleared})
        row = activity.record(
            deal, user, AREA, 'updated', 'Edited', len(shown), f'rfp:request:{deal.id}', 'RFP setting', changes=[change]
        )
    if hidden:
        keys = hidden + ([] if shown else sorted(cleared))
        row = activity.record(
            deal,
            user,
            AREA,
            'updated',
            'Edited the notes for the carriers',
            coalesce_key=f'rfp:notes:{deal.id}',
            changes=[activity.change(target(deal.id), keys)],
        )
    return row


@transaction.atomic
def update(user, deal_id, changes):
    """Returns Updated({key: new value}, [cards whose mark came off], the last Activity row or None).
    Raises ValidationError (400) with a sentence per field."""
    deal, row = _locked(deal_id)
    current = cleaners.stored(row)
    try:
        wanted = cleaners.apply(current, changes, lambda: default_funding(deal))
    except cleaners.Invalid as exc:
        raise ValidationError(exc.errors) from exc
    diff = {key: [current[key], value] for key, value in wanted.items() if value != current[key]}
    if not diff:
        return Updated({}, [], None)
    row = row or RfpRequest.objects.create(deal=deal)
    put(row, {key: after for key, (_before, after) in diff.items()})
    cleared = _take_off(row, {CARD_OF[key] for key in diff})
    row.save(update_fields=[*diff, 'done', 'updated_at'])
    written = _record(deal, user, diff, cleared)
    changed = {key: after for key, (_before, after) in diff.items()}
    return Updated(changed, [key.removeprefix('done.') for key in cleared], written)


def stamp(user):
    return {'by': user.id if getattr(user, 'is_authenticated', False) else None, 'at': clock.now().isoformat()}


@transaction.atomic
def set_done(user, deal_id, card, done):
    """Mark a card completed (`done=True`) or take the mark off. Returns Done(every mark, Activity row or None)."""
    if card not in CARD_KEYS:
        raise ValidationError({'card': [f'There is no RFP card called "{card}".']})
    if not isinstance(done, bool):
        raise ValidationError({'done': ['done must be true or false.']})
    deal, row = _locked(deal_id)
    before = ((row.done if row else None) or {}).get(card)
    if bool(before) == done:
        return Done(dict(row.done) if row else {}, None)
    row = row or RfpRequest.objects.create(deal=deal)
    after = stamp(user) if done else None
    marks = {key: value for key, value in (row.done or {}).items() if key != card}
    row.done = {**marks, card: after} if done else marks
    row.save(update_fields=['done', 'updated_at'])
    title = CARD_TITLES[card]
    summary = f'Marked {title} completed' if done else f'Took the completed mark off {title}'
    change = activity.change(target(deal.id), {f'done.{card}': [before, after]})
    return Done(dict(row.done), activity.record(deal, user, AREA, MARKED, summary, changes=[change]))


def clear_marks(deal_id, cards):
    """Take cards' marks off in one UPDATE (`done - card` per card); no Activity, no read."""
    if not cards:
        return 0
    sql = '"done"' + ' - %s::text' * len(cards)
    return RfpRequest.objects.filter(deal_id=deal_id).update(done=RawSQL(sql, list(cards)))


def clear_coverage_mark(sender, **kwargs):
    """intake's `coverage_changed` receiver (O.1; K10): inside intake's transaction, after its locks and census's."""
    clear_marks(kwargs['deal_id'], (COVERAGE,))
