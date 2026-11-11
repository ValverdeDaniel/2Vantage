"""Every write to clients and deals (plan.md §3.2, §5.1, §7.3)."""

from django.db import transaction
from rest_framework.exceptions import ValidationError

from . import activity, clock, lines, stages
from .models import Client, Deal
from .values import locked


def _clean_lines(raw):
    if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
        raise ValidationError({'requested_lines': ['Lines must be a list of line keys.']})
    unknown = [key for key in raw if key not in lines.BY_KEY]
    if unknown:
        raise ValidationError({'requested_lines': [f'Unknown line: {", ".join(unknown)}']})
    ordered = [key for key in lines.LINE_KEYS if key in raw]  # §4.1 order, de-duplicated
    return ordered


@transaction.atomic
def create_client(user, *, name, relationship='new', effective_date=None, requested_lines=None, owner=None):
    name = (name or '').strip()
    if not name:
        raise ValidationError({'name': ['Client name is required.']})
    if relationship not in ('new', 'existing'):
        raise ValidationError({'relationship': ['Type must be New or Existing.']})
    owner = owner or user
    client = Client.objects.create(name=name[:200], relationship=relationship, owner=owner, created_by=user)
    deal = Deal.objects.create(
        client=client,
        effective_date=effective_date,
        requested_lines=_clean_lines(requested_lines or []),
        owner=owner,
        created_by=user,
    )
    activity.record(deal, user, 'deal', 'created', f'Created {client.name}')
    return client, deal


@transaction.atomic
def update_client(user, client_id, **changes):
    client = locked(Client, client_id)
    if 'name' in changes:
        name = (changes['name'] or '').strip()
        if not name:
            raise ValidationError({'name': ['Client name is required.']})
        client.name = name[:200]
    if 'relationship' in changes:
        if changes['relationship'] not in ('new', 'existing'):
            raise ValidationError({'relationship': ['Type must be New or Existing.']})
        client.relationship = changes['relationship']
    for field in ('owner', 'notes'):
        if field in changes:
            setattr(client, field, changes[field])
    client.save()
    for deal in client.deals.all():
        activity.record(deal, user, 'deal', 'updated', 'Edited client details')
    return client


@transaction.atomic
def delete_client(user, client_id):
    """Deletes the client, its deals and their documents; stored files go with their rows (§7.3)."""
    client = locked(Client, client_id)
    for deal in client.deals.all():
        for document in deal.documents.all():
            document.delete()
    client.delete()


@transaction.atomic
def update_deal(user, deal_id, **changes):
    deal = locked(Deal, deal_id)
    notes = []
    if 'stage' in changes:
        stage = changes['stage']
        if stage in ('sold', 'lost'):
            raise ValidationError({'stage': ['Mark a plan sold or use Mark lost.']})
        if stage not in stages.MANUAL:
            raise ValidationError({'stage': ['Unknown stage.']})
        if deal.stage == 'lost':
            raise ValidationError({'stage': ['Reopen the deal first.']})
        if stage != deal.stage:
            deal.stage = stage
            notes.append(f'Moved to {stages.label(stage)}')
    if 'requested_lines' in changes:
        new_lines = _clean_lines(changes['requested_lines'])
        if new_lines != deal.requested_lines:
            deal.requested_lines = new_lines
            notes.append('Changed the lines to quote')
    if 'effective_date' in changes and changes['effective_date'] != deal.effective_date:
        deal.effective_date = changes['effective_date']
        notes.append('Changed the effective date')
    if 'owner' in changes and changes['owner'] != deal.owner:
        deal.owner = changes['owner']
        notes.append('Changed the owner')
    if notes:
        deal.save()
        for note in notes:
            activity.record(deal, user, 'deal', 'updated', note)
    return deal


def advance(deal, user, target, reason):
    """Automatic forward move (issue → proposal, sold → sold). Caller holds the transaction."""
    new_stage = stages.forward(deal.stage, target)
    if new_stage != deal.stage:
        deal.stage = new_stage
        deal.save(update_fields=['stage', 'updated_at'])
        activity.record(deal, user, 'deal', 'updated', f'Moved to {stages.label(new_stage)} ({reason})')
    return deal


@transaction.atomic
def mark_lost(user, deal_id, reason):
    deal = locked(Deal, deal_id)
    reason = (reason or '').strip()
    if not reason:
        raise ValidationError({'reason': ['Give a reason.']})
    if len(reason) > 300:
        raise ValidationError({'reason': ['Keep the reason under 300 characters.']})
    if deal.stage == 'sold':
        return None  # the view answers 409
    if deal.stage != 'lost':
        deal.lost_from_stage = deal.stage
    deal.stage = 'lost'
    deal.lost_reason = reason
    deal.lost_at = clock.now()
    deal.save()
    activity.record(deal, user, 'deal', 'lost', 'Marked lost')
    return deal


@transaction.atomic
def reopen(user, deal_id):
    deal = locked(Deal, deal_id)
    if deal.stage == 'lost':
        deal.stage = deal.lost_from_stage or 'intake'
        deal.lost_reason, deal.lost_at, deal.lost_from_stage = '', None, ''
        deal.save()
        activity.record(deal, user, 'deal', 'reopened', 'Reopened')
    return deal
