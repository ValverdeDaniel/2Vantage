"""A link's own stamps as its person uses it (plan.md §5.8, §7.14; L62, L79, L98, L116; OQ81, OQ86).

- `record_open(link_id)`: the page's GET counts an open in one conditional UPDATE: the first open stamps `opened_at`,
  and a re-read within 30 minutes adds nothing (L79). The first open writes its own Activity row ("Client opened their
  link"). Staff and previews never call it. It is the one write a GET makes (rule 11).
- `saved(link, now)`: a client's save (an answer, a file, people, a signature) stamps `last_saved_at` and slides the
  expiry at most once a day, never past the ceiling and never once a person picked a date (`policy.slid_on_save`).
  The caller holds the link locked.
- `client_row(...)`: one Activity row for something the client did (actor_kind `client`, area `review`), naming the
  link and, key-only, what it touched: never a value, a member's name or a file name (§3.8, L.6).
"""

from datetime import timedelta

from django.db import transaction
from django.db.models import F, Q
from django.db.models.functions import Coalesce

from deals import activity, clock

from ..models import ClientLink
from ..rules import policy
from . import common

REOPEN = timedelta(minutes=30)


@transaction.atomic
def record_open(link_id):
    """True when this GET counted an open."""
    now = clock.now()
    first = ClientLink.objects.filter(pk=link_id, opened_at__isnull=True).update(
        opened_at=now, last_opened_at=now, open_count=1
    )
    if first:
        link = ClientLink.objects.select_related('request__deal').get(pk=link_id)
        client_row(link.request.deal, link, 'client_opened', 'Client opened their link', [], count=1)
        return True
    again = (
        ClientLink.objects.filter(pk=link_id)
        .filter(Q(last_opened_at__isnull=True) | Q(last_opened_at__lt=now - REOPEN))
        .update(last_opened_at=now, open_count=F('open_count') + 1, opened_at=Coalesce('opened_at', now))
    )
    return bool(again)


def saved(link, now):
    """Stamp a client's save on a locked link. Returns the fields written."""
    link.last_saved_at = now
    fields = ['last_saved_at']
    moved = policy.slid_on_save(link, now)
    if moved is not None:
        link.expires_at = moved
        fields.append('expires_at')
    link.save(update_fields=fields)
    return fields


def client_row(deal, link, action, summary, keys, *, count=1, coalesce='', noun=''):
    changes = [activity.change(common.link_target(link), sorted(keys))] if keys else []
    return activity.record(
        deal,
        None,
        common.AREA,
        action,
        summary,
        count,
        coalesce,
        noun,
        changes=changes,
        keys_only=True,
        actor_kind='client',
        revertible=False,
    )
