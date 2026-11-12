"""Clients and deals API (plan.md §7.3). Thin: parse → service or selector → respond."""

from django.contrib.auth import get_user_model
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from . import activity, lifecycle, selectors, services
from .downloads import file_response
from .models import Activity, AgencySettings, Client, Deal
from .services.facts import clean_agent, clean_deal_size
from .services.lines import refuse_lines

MAX_ID = 2**63 - 1  # a bigger id is not a row: 404, never a database error


class Pages(PageNumberPagination):
    page_size = 25


def _date(value, field):
    if value in (None, ''):
        return None
    parsed = parse_date(str(value))
    if not parsed:
        raise ValidationError({field: ['Use the date format YYYY-MM-DD.']})
    return parsed


def _flag(value, field):
    """A JSON true or false; anything else is a 400."""
    if not isinstance(value, bool):
        raise ValidationError({field: ['Send true or false.']})
    return value


def header_deals():
    """Deals with what the header reads, in one query."""
    return Deal.objects.select_related('client', 'client__archived_by', 'owner')


def _user(value, field):
    if value in (None, ''):
        return None
    user = get_user_model().objects.filter(pk=value, is_active=True).first()
    if not user:
        raise ValidationError({field: ['Unknown user.']})
    return user


class ClientListView(APIView):
    def get(self, request):
        params = request.query_params
        owner = request.user if params.get('owner') == 'me' else _user(params.get('owner'), 'owner')
        rows = selectors.client_rows(
            q=params.get('q', ''),
            relationship=params.get('relationship', ''),
            stage=params.get('stage', ''),
            owner=owner,
            ordering=params.get('ordering', '-last_activity'),
        )
        pager = Pages()
        page = pager.paginate_queryset(rows, request, view=self)
        return pager.get_paginated_response([selectors.client_row(deal) for deal in page])

    def post(self, request):
        data = request.data
        if 'requested_lines' in data:  # the lines to quote have one writer, intake's intent door (B17; slice 11)
            refuse_lines(None)
        client, deal = services.create_client(
            request.user,
            name=data.get('name', ''),
            relationship=data.get('relationship') or lifecycle.PROSPECT,
            effective_date=_date(data.get('effective_date'), 'effective_date'),
            owner=_user(data.get('owner_id'), 'owner_id'),
        )
        return Response(
            {'client': selectors.client_detail(client), 'deal': selectors.deal_header(deal)},
            status=status.HTTP_201_CREATED,
        )


class ClientDetailView(APIView):
    def get(self, request, pk):
        return Response(selectors.client_detail(get_object_or_404(Client, pk=pk)))

    def patch(self, request, pk):
        get_object_or_404(Client, pk=pk)
        if 'relationship' in request.data:  # the status has its own door (§7.3)
            raise ValidationError({'relationship': [f'Change the status through clients/{pk}/status/.']})
        changes = {key: request.data[key] for key in ('name', 'notes') if key in request.data}
        if 'owner_id' in request.data:
            changes['owner'] = _user(request.data['owner_id'], 'owner_id')
        client = services.update_client(request.user, pk, **changes)
        return Response(selectors.client_detail(client))

    def delete(self, request, pk):
        """Clients are archived, never deleted (M104, OQ47): POST clients/{id}/archive/."""
        return Response({'detail': 'Clients are archived, never deleted.'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)


class ClientArchiveView(APIView):
    """POST clients/{id}/archive/ {archived: true|false}: Archive or Restore (M6, M7, M103). Answers the archive block,
    {client_id, archived: {at, by} | null}."""

    def post(self, request, pk):
        if pk > MAX_ID:
            raise Http404
        get_object_or_404(Client, pk=pk)
        archived = _flag(request.data.get('archived'), 'archived')
        client, _changed = services.set_archived(request.user, pk, archived)
        return Response({'client_id': client.id, 'archived': selectors.archived_block(client)})


class ArchivedView(APIView):
    """GET archived/: archived clients, each with its status and its deal's stage (M105)."""

    def get(self, request):
        return Response(selectors.archived_clients())


class ClientStatusView(APIView):
    """POST clients/{id}/status/ {to}: Convert to client, Back to prospect, or a classification fix (§5.1, §7.3).
    Answers the client detail; a refused move is a 409 with its sentence."""

    def post(self, request, pk):
        if pk > MAX_ID:
            raise Http404
        get_object_or_404(Client, pk=pk)
        to = request.data.get('to')
        if not isinstance(to, str) or not to:
            raise ValidationError({'to': ['Choose the status to move to.']})
        services.set_status(request.user, pk, to)
        return Response(selectors.client_detail(Client.objects.select_related('owner').get(pk=pk)))


class DealView(APIView):
    def get(self, request, pk):
        return Response(selectors.deal_header(get_object_or_404(header_deals(), pk=pk)))

    def patch(self, request, pk):
        get_object_or_404(Deal, pk=pk)
        data = request.data
        if 'requested_lines' in data:  # the lines to quote have one writer, intake's intent door (B17; slice 11)
            refuse_lines(pk)
        changes = {}
        if 'effective_date' in data:
            changes['effective_date'] = _date(data['effective_date'], 'effective_date')
        if 'owner_id' in data:
            changes['owner'] = _user(data['owner_id'], 'owner_id')
        if 'stage' in data:
            changes['stage'] = data['stage']
        if 'deal_size' in data:
            changes['deal_size'] = clean_deal_size(data['deal_size'])
        if 'agent_of_record' in data:
            changes['agent_of_record'] = clean_agent(data['agent_of_record'])
        services.update_deal(request.user, pk, **changes)
        return Response(selectors.deal_header(header_deals().get(pk=pk)))


class DealLostView(APIView):
    """POST deals/{id}/lost/ {reason?}: the reason is optional (OQ48); a sold or lost deal answers 409 (M3)."""

    def post(self, request, pk):
        get_object_or_404(Deal, pk=pk)
        services.mark_lost(request.user, pk, request.data.get('reason', ''))
        return Response(selectors.deal_header(header_deals().get(pk=pk)))


class DealReopenView(APIView):
    def post(self, request, pk):
        get_object_or_404(Deal, pk=pk)
        services.reopen(request.user, pk)
        return Response(selectors.deal_header(header_deals().get(pk=pk)))


class DealActivityView(APIView):
    def get(self, request, pk):
        deal = get_object_or_404(Deal, pk=pk)
        pager = Pages()
        page = pager.paginate_queryset(selectors.activity_feed(deal), request, view=self)
        return pager.get_paginated_response([selectors.activity_row(row) for row in page])


class ActivityRevertView(APIView):
    """POST activity/{id}/revert/: puts back the row's earlier values, once (§3.7, O.3.2). Refusals answer 409."""

    def post(self, request, pk):
        if pk > MAX_ID:
            raise Http404
        try:
            row = activity.revert(pk, request.user)
        except Activity.DoesNotExist as exc:
            raise Http404 from exc
        return Response(
            {
                'activity_id': row.id,
                'reverted_id': row.reverts_id,
                'deal_id': row.deal_id,
                'summary': row.summary,
                'changes': row.changes,
            }
        )


class UserListView(APIView):
    """Active users, for owner pickers."""

    def get(self, request):
        users = get_user_model().objects.filter(is_active=True).order_by('first_name', 'last_name', 'username')
        return Response([selectors.person(user) for user in users])


class AgencyView(APIView):
    def get(self, request):
        return Response(selectors.agency())


class AgencyLogoView(APIView):
    def get(self, request):
        agency = AgencySettings.get()
        if not agency.logo:
            return Response({'detail': 'No logo.'}, status=status.HTTP_404_NOT_FOUND)
        return file_response(agency.logo.open('rb'), 'logo.png', inline=True)
