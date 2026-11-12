"""Creating and editing clients (plan.md §5.1, §7.3). The status is not edited here: see `status.py`."""

from django.db import transaction
from rest_framework.exceptions import ValidationError

from .. import activity, lifecycle, lines
from ..models import Client, Deal
from ..values import locked
from .snapshots import diff, snapshot

CLIENT_FIELDS = ('name', 'owner_id', 'notes')


def clean_lines(raw):
    if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
        raise ValidationError({'requested_lines': ['Lines must be a list of line keys.']})
    unknown = [key for key in raw if key not in lines.BY_KEY]
    if unknown:
        raise ValidationError({'requested_lines': [f'Unknown line: {", ".join(unknown)}']})
    return [key for key in lines.LINE_KEYS if key in raw]  # §4.1 order, de-duplicated


@transaction.atomic
def create_client(
    user, *, name, relationship=lifecycle.PROSPECT, effective_date=None, requested_lines=None, owner=None
):
    """The client and its first deal. A client starts as a Prospect or an Existing client (CL6); its deal opens as
    that status, so a deal for an Existing client is a Renewal (`rules.deal_type`)."""
    name = (name or '').strip()
    if not name:
        raise ValidationError({'name': ['Client name is required.']})
    refusal = lifecycle.creation_refusal(relationship)
    if refusal:
        raise ValidationError({'relationship': [refusal]})
    owner = owner or user
    client = Client.objects.create(name=name[:200], relationship=relationship, owner=owner, created_by=user)
    deal = Deal.objects.create(
        client=client,
        effective_date=effective_date,
        requested_lines=clean_lines(requested_lines or []),
        opened_as=relationship,
        owner=owner,
        created_by=user,
    )
    activity.record(deal, user, 'deal', 'created', f'Created {client.name}')
    return client, deal


@transaction.atomic
def update_client(user, client_id, **changes):
    """Name, owner and notes. The status changes only through `set_status` (§7.3)."""
    if 'relationship' in changes:
        raise ValidationError({'relationship': [f'Change the status through clients/{client_id}/status/.']})
    client = locked(Client, client_id)
    before = snapshot(client, CLIENT_FIELDS)
    if 'name' in changes:
        name = (changes['name'] or '').strip()
        if not name:
            raise ValidationError({'name': ['Client name is required.']})
        client.name = name[:200]
    for field in ('owner', 'notes'):
        if field in changes:
            setattr(client, field, changes[field])
    changed = diff(before, snapshot(client, CLIENT_FIELDS))
    if changed:  # an unchanged write saves nothing and records nothing (§3.7)
        client.save()
        for deal in client.deals.all():
            entries = [activity.change(f'client:{client.id}', changed)]
            activity.record(deal, user, 'deal', 'updated', 'Edited client details', changes=entries)
    return client


@transaction.atomic
def delete_client(user, client_id):
    """Deletes the client, its deals and their documents; stored files go with their rows (§7.3; 405 from slice 38)."""
    client = locked(Client, client_id)
    for deal in client.deals.all():
        for document in deal.documents.all():
            document.delete()
    client.delete()
