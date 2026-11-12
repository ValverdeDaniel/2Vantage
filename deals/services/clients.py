"""Creating and editing clients (plan.md §5.1, §7.3). The status is not edited here (`status.py`), nor the owner
(`facts.set_owner`), nor the archive stamps (`archive.py`). Clients are never deleted over HTTP (405, OQ47)."""

from django.db import transaction
from rest_framework.exceptions import ValidationError

from .. import activity, lifecycle
from ..models import Client, Deal
from ..values import locked
from .facts import set_owner
from .snapshots import diff, snapshot

CLIENT_FIELDS = ('name', 'notes')


@transaction.atomic
def create_client(user, *, name, relationship=lifecycle.PROSPECT, effective_date=None, owner=None, first_deal=True):
    """The client and its first deal. A client starts as a Prospect or an Existing client (CL6); its deal opens as
    that status, so a deal for an Existing client is a Renewal (`rules.deal_type`). Its lines to quote are written
    afterwards through intake's `set_intent`, their only writer (B17; slice 11). `first_deal=False` makes a client with
    no deal (commission's Add to book, H58; review 22): (client, None), its Activity a firm row about the client."""
    name = (name or '').strip()
    if not name:
        raise ValidationError({'name': ['Client name is required.']})
    refusal = lifecycle.creation_refusal(relationship)
    if refusal:
        raise ValidationError({'relationship': [refusal]})
    owner = owner or user
    client = Client.objects.create(name=name[:200], relationship=relationship, owner=owner, created_by=user)
    if not first_deal:
        activity.record(None, user, 'deal', 'created', f'Created {client.name}', subject=f'client:{client.id}')
        return client, None
    deal = Deal.objects.create(
        client=client,
        effective_date=effective_date,
        opened_as=relationship,
        owner=owner,
        created_by=user,
    )
    activity.record(deal, user, 'deal', 'created', f'Created {client.name}')
    return client, deal


@transaction.atomic
def update_client(user, client_id, **changes):
    """Name and notes, and the owner through `set_owner`. The status changes only through `set_status` (§7.3)."""
    if 'relationship' in changes:
        raise ValidationError({'relationship': [f'Change the status through clients/{client_id}/status/.']})
    client = locked(Client, client_id)
    before = snapshot(client, CLIENT_FIELDS)
    if 'name' in changes:
        name = (changes['name'] or '').strip()
        if not name:
            raise ValidationError({'name': ['Client name is required.']})
        client.name = name[:200]
    if 'notes' in changes:
        client.notes = changes['notes']
    changed = diff(before, snapshot(client, CLIENT_FIELDS))
    if changed:  # an unchanged write saves nothing and records nothing (§3.7)
        client.save(update_fields=[*CLIENT_FIELDS, 'updated_at'])
        for deal in client.deals.all():
            entries = [activity.change(f'client:{client.id}', changed)]
            activity.record(deal, user, 'deal', 'updated', 'Edited client details', changes=entries)
    if 'owner' in changes and set_owner(user, changes['owner'], client_id=client.id):
        client.refresh_from_db()
    return client


@transaction.atomic
def delete_client(user, client_id):
    """Deletes the client, its deals and their documents; stored files go with their rows. For the seeders and tests
    only (`seed_golden`, GD-Big): over HTTP a client is archived, never deleted (`DELETE clients/{id}` answers 405;
    M104, OQ47)."""
    client = locked(Client, client_id)
    for deal in client.deals.all():
        # Protected files (an issued proposal, a signed form) go with the client below, in one cascade: an issued
        # version holds its files under RESTRICT, which refuses a file deleted alone (slice 32).
        for document in deal.documents.filter(protected=False):
            document.delete()
    client.delete()
