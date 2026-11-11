"""Reads and payloads for clients and deals (plan.md §7.3)."""

from django.conf import settings as django_settings
from django.db.models import F, OuterRef, Q, Subquery
from django.db.models.functions import Coalesce

from .models import Activity, AgencySettings, Deal


def person(user):
    if not user:
        return None
    return {'id': user.id, 'name': user.get_full_name() or user.username}


def deal_header(deal):
    return {
        'id': deal.id,
        'client': {'id': deal.client_id, 'name': deal.client.name, 'relationship': deal.client.relationship},
        'effective_date': deal.effective_date,
        'stage': deal.stage,
        'lost_reason': deal.lost_reason,
        'lost_at': deal.lost_at,
        'requested_lines': deal.requested_lines,
        'owner': person(deal.owner),
        'created_at': deal.created_at,
        'updated_at': deal.updated_at,
    }


def client_rows(*, q='', relationship='', stage='', owner=None, ordering='-last_activity'):
    """One row per client with its current deal (version 1: one deal per client)."""
    last_activity = Activity.objects.filter(deal=OuterRef('pk')).order_by('-updated_at').values('updated_at')[:1]
    deals = Deal.objects.select_related('client', 'owner').annotate(
        last_activity_at=Coalesce(Subquery(last_activity), F('created_at'))
    )
    if q:
        deals = deals.filter(client__name__icontains=q.strip())
    if relationship in ('new', 'existing'):
        deals = deals.filter(client__relationship=relationship)
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
        'owner': person(deal.owner or deal.client.owner),
        'deal': {'id': deal.id, 'stage': deal.stage, 'effective_date': deal.effective_date},
        'last_activity_at': deal.last_activity_at,
    }


def client_detail(client):
    return {
        'id': client.id,
        'name': client.name,
        'relationship': client.relationship,
        'owner': person(client.owner),
        'notes': client.notes,
        'deals': [{'id': d.id, 'effective_date': d.effective_date, 'stage': d.stage} for d in client.deals.all()],
    }


def activity_row(row):
    return {
        'id': row.id,
        'at': row.updated_at,
        'actor': person(row.actor)['name'] if row.actor else (row.actor_label or 'System'),
        'area': row.area,
        'action': row.action,
        'summary': row.summary,
        'count': row.count,
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
