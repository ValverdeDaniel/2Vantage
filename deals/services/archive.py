"""Archive and Restore a client (plan.md §5.1, §7.3; A18, M6–M9, M103–M105; OQ46, OQ47).

Archive is a visibility flag, never a delete: it hides the client and its one deal from every list (`live()`), even a
sold deal. The pages still open, the Book keeps their records, and portal writes answer 410
(`rules.client_asks_open`). Neither the stage nor the client's status changes, and `updated_at` stays where it was, so
a restored row lands back in its place (old Vantage's archive.py at 891f1b3). One Activity row each, in area
`archive`; Revert puts the earlier state back (`reverters['archive']`).
"""

from django.db import transaction

from .. import activity, clock
from ..models import Client
from ..values import locked

AREA = 'archive'
WORDS = {True: ('archived', 'Archived the client'), False: ('restored', 'Restored the client')}


def target(client_id):
    return f'client:{client_id}'


def _stamp(client, archived, user):
    """Set or clear the stamps on a locked client; {'archived': [before, after]}, or {} when nothing moved."""
    if (client.archived_at is not None) == archived:
        return {}
    if archived:
        client.archived_at = clock.now()
        client.archived_by = user if getattr(user, 'is_authenticated', False) else None
    else:
        client.archived_at, client.archived_by = None, None
    client.save(update_fields=['archived_at', 'archived_by'])  # not updated_at: archiving is not an edit
    return {'archived': [not archived, archived]}


@transaction.atomic
def set_archived(user, client_id, archived):
    """Archive (`archived=True`) or restore one client. Returns (client, {'archived': [before, after]}); archiving an
    archived client, or restoring a live one, writes nothing. Raises Client.DoesNotExist."""
    client = locked(Client, client_id)
    changed = _stamp(client, bool(archived), user)
    if changed:
        action, summary = WORDS[bool(archived)]
        deal = client.deals.order_by('-id').first()
        activity.record(
            deal,
            user,
            AREA,
            action,
            summary,
            changes=[activity.change(target(client.id), changed)],
            subject='' if deal else target(client.id),
        )
    return client, changed


def revert(row, user):
    """`reverters['archive']`: archive or restore back, refused once a later Archive or Restore moved it again."""
    entry = next((entry for entry in row.changes if entry['t'].startswith('client:')), None)
    if entry is None or 'archived' not in entry['k']:
        raise activity.Refused(activity.NOTHING_TO_PUT_BACK)
    before, after = entry['k']['archived']
    client = Client.objects.select_for_update().filter(pk=int(entry['t'].removeprefix('client:'))).first()
    if client is None:
        raise activity.Refused('This client no longer exists, so the change cannot be reverted.')
    if activity.later_keys(row) or (client.archived_at is not None) != after:
        raise activity.changed_since(['Archived'], ['archived'])
    return [activity.change(entry['t'], _stamp(client, before, user))]
