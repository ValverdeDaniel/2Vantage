"""The request tray's writes before anything is sent (plan.md §5.8; L49–L51, L54; B12; OQ87; old 891f1b3
`review/notes.py` `ask_many`, `ask_census`, `queue_for_client`, `remove_drafts`).

Every "＋ Ask", every send-back (X) and every "＋ Ask N" waits here, whichever tab it came from, until a person sends
it (`services.send`): nothing reaches the client before then (OQ87's default: a new ask waits in the tray).

- `ask(user, deal_id, refs, kind=, text=, request_id=, skip_out=)`: one draft per item (B7: the partial unique
  constraint, and the Deal locked first, so two asks at once leave one). Asking again updates the draft: its kind, its
  author and, when one is given, its note and the request it is named for; a blank note keeps the draft's own (old
  `_queue_many`). `skip_out` (a bulk "＋ Ask all") leaves what is already in the tray or out with the client. Refused
  whole before any write when a ref names nothing on the deal (400 naming it), and 409 when the deal may no longer
  ask its client (lost, archived, a past year). At most 500 at once: past that, their census file is the better ask.
- `ask_census(user, deal_id, columns, scope=)`: "＋ Ask N" over census columns (L46): each live person's blank (or, for
  `missing`, required blank) cell in those columns, one draft each.
- `remove(user, deal_id, ids)`: back out of the tray; only drafts (what went out stays on the record), and an id that
  is no such draft is passed over (a colleague may have sent it a moment ago).
Activity: key-only rows ("Added 3 items to the request tray", coalesced; "Took 2 items out of the request tray").
"""

from collections import namedtuple

from django.db import transaction
from rest_framework.exceptions import ValidationError

from census import facts as census_facts
from census import fields as census_fields
from census.models import Member
from deals import activity, clock, rules
from deals.models import Deal

from ..models import ASK_KINDS, ClientRequest, ReviewNote
from ..rules.asks import CELL_LIMIT
from ..selectors import items as item_rows
from ..selectors import notes as note_rows
from . import common

Asked = namedtuple('Asked', 'drafts activity')
Removed = namedtuple('Removed', 'ids activity')

TEXT_LIMIT = 1000
CENSUS_SCOPES = ('blank', 'missing')
NOTHING = 'Send the items to ask for.'
TOO_MANY = f'Ask for up to {CELL_LIMIT} items at a time, or ask for their census file.'
NOT_HERE = 'Not on this deal: {refs}.'
NOT_A_KIND = 'Send kind as ask or sendback.'
TEXT_LONG = f'Keep the note under {TEXT_LIMIT} characters.'
NOT_A_REQUEST = 'That request is not on this deal.'
NOTHING_THERE = 'There is nothing there to ask the client for.'
NO_COLUMNS = 'Tick the census columns to ask about first.'


def locked_deal(deal_id):
    return Deal.objects.select_for_update(of=('self',)).select_related('client').get(pk=deal_id)


def refuse_unless_asking(deal):
    sentence = rules.client_asks_open(deal)
    if sentence:
        raise activity.Refused(sentence)


def clean_text(text):
    text = str(text or '').strip()
    if len(text) > TEXT_LIMIT:
        raise ValidationError({'text': [TEXT_LONG]})
    return text


def items_of(deal, refs):
    """{ref: Item} for refs that all name something on the deal, else a 400 naming those that do not."""
    if not isinstance(refs, list) or not refs or not all(isinstance(ref, str) for ref in refs):
        raise ValidationError({'refs': [NOTHING]})
    if len(refs) > CELL_LIMIT:
        raise ValidationError({'refs': [TOO_MANY]})
    found = item_rows.resolve(deal, refs)
    bad = [ref[:80] for ref in dict.fromkeys(refs) if ref not in found or found[ref].gone]
    if bad:
        raise ValidationError({'refs': [NOT_HERE.format(refs=', '.join(bad[:20]))]})
    return found


def _named(deal, request_id):
    if request_id in (None, ''):
        return None
    try:
        request_id = int(request_id)
    except (TypeError, ValueError):
        raise ValidationError({'request_id': [NOT_A_REQUEST]}) from None
    if not ClientRequest.objects.filter(pk=request_id, deal=deal).exists():
        raise ValidationError({'request_id': [NOT_A_REQUEST]})
    return request_id


def _out(deal_id):
    """The refs already in the tray or out with the client and not answered (a bulk ask leaves them be)."""
    taken = {note_rows.ref_of(note) for note in note_rows.drafts(deal_id)}
    return taken | {note_rows.ref_of(note) for note in note_rows.sent_asks([deal_id]).get(deal_id, [])}


def _key(surface, key, member_id):
    return (surface, key, member_id)


def _write(user, deal, items, kind, text, request_id, now):
    have = {
        _key(note.surface, note.key, note.member_id): note
        for note in ReviewNote.objects.filter(
            deal=deal, kind__in=ASK_KINDS, sent_at__isnull=True, resolved_at__isnull=True
        ).select_for_update()
    }
    old, new = [], []
    for item in items:
        draft = have.get(_key(item.surface, item.key, item.member_id))
        if draft is None:
            new.append(
                ReviewNote(
                    deal=deal, surface=item.surface, key=item.key, member_id=item.member_id, request_id=request_id,
                    audience='client', kind=kind, text=text, author_id=common.user_id(user), at=now,
                )
            )  # fmt: skip
            continue
        draft.text = text or draft.text
        draft.kind, draft.author_id, draft.at = kind, common.user_id(user), now
        if request_id is not None:
            draft.request_id = request_id
        old.append(draft)
    if old:
        ReviewNote.objects.bulk_update(old, ['text', 'kind', 'author', 'at', 'request'])
    return old + ReviewNote.objects.bulk_create(new)


def _plural(count, noun):
    return f'{count} {noun}{"" if count == 1 else "s"}'


@transaction.atomic
def ask(user, deal_id, refs, *, kind='ask', text='', request_id=None, skip_out=False):
    """Asked([draft], Activity row or None)."""
    if kind not in ASK_KINDS:
        raise ValidationError({'kind': [NOT_A_KIND]})
    deal = locked_deal(deal_id)
    refuse_unless_asking(deal)
    found = items_of(deal, refs)
    text, named = clean_text(text), _named(deal, request_id)
    items = list(found.values())
    if skip_out:
        out = _out(deal.id)
        items = [item for item in items if item.ref not in out]
        if not items:
            return Asked([], None)
    drafts = _write(user, deal, items, kind, text, named, clock.now())
    keys = sorted(item.ref for item in items)
    change = activity.change('tray', keys)
    row = activity.record(
        deal, user, common.AREA, 'asked', 'Added to the request tray', len(items), f'review:tray:{deal.id}', 'item',
        changes=[change], keys_only=True, revertible=False,
    )  # fmt: skip
    return Asked(drafts, row)


def census_refs(deal, columns, scope):
    """The census values "＋ Ask N" over `columns` asks: each live person's blank (or required blank) cell there."""
    if scope not in CENSUS_SCOPES:
        raise ValidationError({'scope': [f'Ask for one of: {", ".join(CENSUS_SCOPES)}.']})
    if not isinstance(columns, list) or not columns or not all(isinstance(key, str) for key in columns):
        raise ValidationError({'columns': [NO_COLUMNS]})
    if bad := [key for key in columns if key not in census_fields.BY_KEY or key in census_fields.SSN_KEYS]:
        raise ValidationError({'columns': [NOT_HERE.format(refs=', '.join(bad[:20]))]})
    needed = census_facts.needed(deal) if scope == 'missing' else None
    refs = []
    for member in Member.objects.filter(deal_id=deal.id).order_by('position', 'id').only('id', 'kind', 'values'):
        for key in columns:
            if (member.values or {}).get(key) not in (None, ''):
                continue
            if needed is not None and key not in needed.get(member.kind, ()):
                continue
            refs.append(f'census:{member.id}:{key}')
    if not refs:
        raise activity.Refused(NOTHING_THERE)
    return refs


@transaction.atomic
def ask_census(user, deal_id, columns, *, scope='blank', text=''):
    deal = locked_deal(deal_id)
    refuse_unless_asking(deal)
    return ask(user, deal_id, census_refs(deal, columns, scope), text=text, skip_out=True)


@transaction.atomic
def remove(user, deal_id, ids):
    """Removed([ids taken out], Activity row or None)."""
    if not isinstance(ids, list) or not all(isinstance(pk, int) and not isinstance(pk, bool) for pk in ids):
        raise ValidationError({'ids': ['Send the ids as a list of numbers.']})
    deal = locked_deal(deal_id)
    drafts = list(
        ReviewNote.objects.filter(
            deal=deal, pk__in=ids, kind__in=ASK_KINDS, sent_at__isnull=True, resolved_at__isnull=True
        ).select_for_update()
    )
    if not drafts:
        return Removed([], None)
    keys = sorted(note_rows.ref_of(note) for note in drafts)
    gone = [note.id for note in drafts]
    ReviewNote.objects.filter(pk__in=gone).delete()
    change = activity.change('tray', keys)
    summary = f'Took {_plural(len(gone), "item")} out of the request tray'
    row = activity.record(deal, user, common.AREA, 'unasked', summary, changes=[change], keys_only=True)
    return Removed(gone, row)
