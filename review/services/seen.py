"""The last look at a deal's threads (plan.md §6.12 `Seen`; L33, L44, L103; old 891f1b3 `notes.mark_seen`): one stamp
per viewer per deal, a person of ours or one client link, the one writer of `Seen`.

`mark(deal_id, user=, link=, at=)`: an upsert that only moves forward: `at` (now, or the stamp the page last read, so
what landed after it stays new) is clamped to now, and an older `at` leaves a newer look. `seen_at(deal_id, user=,
link=)` reads it (None: never looked). Not a value write: no Activity row (a look changes nothing anyone decided).
"""

from django.db import IntegrityError, transaction

from deals import clock

from ..models import Seen
from ..rules import tray as tray_rules


def _viewer(user, link):
    if (user is None) == (link is None):
        raise ValueError('Name exactly one viewer: a person or a link.')
    return {'user': user} if user is not None else {'link': link}


def mark(deal_id, *, user=None, link=None, at=None):
    who = _viewer(user, link)
    now = clock.now()
    parsed = tray_rules.moment(at)
    at = min(parsed, now) if parsed is not None and parsed.tzinfo is not None else now
    try:
        with transaction.atomic():
            row, made = Seen.objects.get_or_create(deal_id=deal_id, **who, defaults={'seen_at': at})
    except IntegrityError:
        row, made = Seen.objects.get(deal_id=deal_id, **who), False  # the viewer's other tab made it a moment ago
    if not made and row.seen_at < at:
        Seen.objects.filter(pk=row.pk, seen_at__lt=at).update(seen_at=at)
        row.seen_at = at
    return row.seen_at


def seen_at(deal_id, *, user=None, link=None):
    return Seen.objects.filter(deal_id=deal_id, **_viewer(user, link)).values_list('seen_at', flat=True).first()
