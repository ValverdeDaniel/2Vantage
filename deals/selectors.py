"""Reads and payloads for clients and deals (plan.md §7.3)."""

from django.conf import settings as django_settings
from django.db.models import Count, F, OuterRef, Prefetch, Q, Subquery
from django.db.models.functions import Coalesce
from rest_framework.exceptions import ValidationError

from . import activity, contacts, lifecycle, providers, rules
from .models import Activity, AgencySettings, Client, Deal
from .services import archive, notes


def person(user):
    if not user:
        return None
    return {'id': user.id, 'name': user.get_full_name() or user.username}


def money(value):
    """A Decimal as exact text ('250000.00'), never a float; None stays None."""
    return None if value is None else str(value)


def archived_block(client):
    """{at, by} while the client is archived, else None (M7's banner; the deal is archived with its client)."""
    if client.archived_at is None:
        return None
    return {'at': client.archived_at, 'by': person(client.archived_by)}


def deal_header(deal):
    return {
        'id': deal.id,
        'client': {
            'id': deal.client_id,
            'name': deal.client.name,
            'relationship': deal.client.relationship,
            'client_since': deal.client.client_since,
        },
        'effective_date': deal.effective_date,
        'stage': deal.stage,
        'deal_type': rules.deal_type(deal),  # the builder's RENEWAL chip (J22), never the client's status (M14)
        'lost_reason': deal.lost_reason,
        'lost_at': deal.lost_at,
        'requested_lines': deal.requested_lines,
        'owner': person(deal.owner),
        'deal_size': money(deal.deal_size),
        'agent_of_record': deal.agent_of_record,
        'agent_default': rules.agent_default(deal),  # what a blank agent of record prints, shown in grey (M27)
        'archived': archived_block(deal.client),
        'created_at': deal.created_at,
        'updated_at': deal.updated_at,
    }


def statuses(raw):
    """`?relationship=prospect` or a comma list (`new_client,existing_client`; §7.3). '' means every status; an
    unknown status is a 400."""
    keys = [key.strip() for key in str(raw or '').split(',') if key.strip()]
    unknown = [key for key in keys if key not in lifecycle.LABELS]
    if unknown:
        raise ValidationError({'relationship': [f'Unknown status: {", ".join(unknown)}.']})
    return keys


def client_rows(*, q='', relationship='', stage='', owner=None, ordering='-last_activity'):
    """One row per client with its current deal (version 1: one deal per client)."""
    # Downloads and views never move "Last updated" (§3.8, E99).
    # Archive and Restore are not edits either: a restored row lands back in its place (old archive.py, 891f1b3).
    last_activity = (
        Activity.objects.filter(deal=OuterRef('pk'))
        .exclude(action__in=activity.ACCESS)
        .exclude(area=archive.AREA)
        .order_by('-updated_at')
        .values('updated_at')[:1]
    )
    # Archived clients leave every list (A18, OQ46).
    deals = (
        Deal.objects.live()
        .select_related('client', 'owner')
        .annotate(last_activity_at=Coalesce(Subquery(last_activity), F('created_at')))
    )
    if q:
        deals = deals.filter(client__name__icontains=q.strip())
    wanted = statuses(relationship)
    if wanted:
        deals = deals.filter(client__relationship__in=wanted)
    if stage:
        deals = deals.filter(stage=stage)
    if owner is not None:
        deals = deals.filter(Q(owner=owner) | Q(owner__isnull=True, client__owner=owner))
    order = ['client__name', 'id'] if ordering == 'name' else ['-last_activity_at', '-id']
    return deals.order_by(*order)


def client_row(deal):
    return {
        'id': deal.client_id,
        'name': deal.client.name,
        'relationship': deal.client.relationship,
        'client_since': deal.client.client_since,
        'owner': person(deal.owner or deal.client.owner),
        'deal': {
            'id': deal.id,
            'stage': deal.stage,
            'effective_date': deal.effective_date,
            'deal_size': money(deal.deal_size),
            'deal_type': rules.deal_type(deal),
        },
        'last_activity_at': deal.last_activity_at,
    }


def status_moves(client, deals):
    """The moves the client dialog offers, each allowed or refused with its sentence (§5.1), worked out here."""
    return lifecycle.moves(
        client.relationship, has_sold=providers.client_has_sold(client.id), lost=rules.convert_refusal(deals)
    )


def contact_row(contact):
    return {
        'id': contact.id,
        'client_id': contact.client_id,
        'role': contact.role,
        'role_label': contacts.label(contact.role),
        'name': contact.name,
        'title': contact.title,
        'email': contact.email,
        'phone': contact.phone,
        'is_primary': contact.is_primary,
    }


def client_contacts(client):
    """{contacts: [...], primary_id}: every contact in order, and which one `contacts.primary` picks (M30)."""
    rows = list(client.contacts.all())
    main = contacts.primary(rows)
    return {'contacts': [contact_row(contact) for contact in rows], 'primary_id': main.id if main else None}


def client_detail(client):
    deals = list(client.deals.order_by('id'))
    return {
        'id': client.id,
        'name': client.name,
        'relationship': client.relationship,
        'client_since': client.client_since,
        'owner': person(client.owner),
        'notes': client.notes,
        'archived': archived_block(client),
        'deals': [{'id': d.id, 'effective_date': d.effective_date, 'stage': d.stage} for d in deals],
        **client_contacts(client),
        'moves': status_moves(client, deals),
    }


def archived_clients():
    """The Archived page (M105): archived clients, latest first, each with its status and its deal (version 1: one;
    else the one with the latest effective date). A fixed number of queries at any size."""
    current = Prefetch('deals', Deal.objects.order_by(F('effective_date').desc(nulls_last=True), '-id'))
    clients = (
        Client.objects.filter(archived_at__isnull=False)
        .select_related('archived_by')
        .prefetch_related(current)
        .annotate(deal_count=Count('deals'))
        .order_by('-archived_at', '-id')
    )
    rows = []
    for client in clients:
        deal = next(iter(client.deals.all()), None)
        rows.append(
            {
                'id': client.id,
                'name': client.name,
                'relationship': client.relationship,
                'client_since': client.client_since,
                'archived': archived_block(client),
                'deal': {'id': deal.id, 'stage': deal.stage, 'effective_date': deal.effective_date} if deal else None,
                'deal_count': client.deal_count,
            }
        )
    return rows


def note_rows(deal, viewer):
    """The deal's notes, pinned first, newest first (M74); deleted notes are left out (the default manager)."""
    return [note_row(note, viewer) for note in deal.notes.select_related('author')]


def note_row(note, viewer):
    return {
        'id': note.id,
        'deal_id': note.deal_id,
        'body': note.body,
        'kind': note.kind,
        'kind_label': notes.KINDS[note.kind],
        'pinned': note.pinned,
        'author': person(note.author),
        'can_edit': notes.can_edit(viewer, note),  # author or admin (M76, M77)
        'created_at': note.created_at,
        'updated_at': note.updated_at,
    }


ACTOR_WORDS = {'client': 'The client', 'claude': 'Claude', 'system': 'System'}


def activity_feed(deal):
    """The deal's feed, newest first: no downloads or views (§3.8), and `changes` left in the database (O.3.2)."""
    return (
        deal.activity.exclude(action__in=activity.ACCESS)
        .defer('changes')
        .select_related('actor', 'reverted_by')
        .order_by('-updated_at', '-id')
    )


def activity_row(row):
    return {
        'id': row.id,
        'at': row.updated_at,
        'actor': person(row.actor)['name'] if row.actor else ACTOR_WORDS.get(row.actor_kind, 'System'),
        'actor_kind': row.actor_kind,
        'area': row.area,
        'action': row.action,
        'summary': row.summary,
        'count': row.count,
        'document_id': row.document_id,
        'can_revert': activity.can_revert(row),
        'reverts_id': row.reverts_id,
        'reverted': {'at': row.reverted_at, 'by': person(row.reverted_by)} if row.reverted_at else None,
    }


def agency():
    settings = AgencySettings.get()
    return {
        'name': settings.name,
        'address': settings.address,
        'city_state_zip': settings.city_state_zip,
        'phone': settings.phone,
        'email': settings.email,
        'brand_color': settings.brand_color,
        'has_logo': bool(settings.logo),
        'time_zone': django_settings.AGENCY_TIME_ZONE,
    }
