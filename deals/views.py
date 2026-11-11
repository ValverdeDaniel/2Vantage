"""Clients and deals API (plan.md §7.3). Thin: parse → service or selector → respond."""

from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from . import selectors, services
from .downloads import file_response
from .models import AgencySettings, Client, Deal


class Pages(PageNumberPagination):
    page_size = 25


def _date(value, field):
    if value in (None, ''):
        return None
    parsed = parse_date(str(value))
    if not parsed:
        raise ValidationError({field: ['Use the date format YYYY-MM-DD.']})
    return parsed


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
        client, deal = services.create_client(
            request.user,
            name=data.get('name', ''),
            relationship=data.get('relationship') or 'new',
            effective_date=_date(data.get('effective_date'), 'effective_date'),
            requested_lines=data.get('requested_lines') or [],
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
        changes = {key: request.data[key] for key in ('name', 'relationship', 'notes') if key in request.data}
        if 'owner_id' in request.data:
            changes['owner'] = _user(request.data['owner_id'], 'owner_id')
        client = services.update_client(request.user, pk, **changes)
        return Response(selectors.client_detail(client))

    def delete(self, request, pk):
        if not request.user.is_staff:
            return Response({'detail': 'Only an admin can delete a client.'}, status=status.HTTP_403_FORBIDDEN)
        services.delete_client(request.user, pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


class DealView(APIView):
    def get(self, request, pk):
        return Response(selectors.deal_header(get_object_or_404(Deal.objects.select_related('client'), pk=pk)))

    def patch(self, request, pk):
        get_object_or_404(Deal, pk=pk)
        data = request.data
        changes = {}
        if 'effective_date' in data:
            changes['effective_date'] = _date(data['effective_date'], 'effective_date')
        if 'owner_id' in data:
            changes['owner'] = _user(data['owner_id'], 'owner_id')
        for key in ('stage', 'requested_lines'):
            if key in data:
                changes[key] = data[key]
        deal = services.update_deal(request.user, pk, **changes)
        return Response(selectors.deal_header(deal))


class DealLostView(APIView):
    def post(self, request, pk):
        get_object_or_404(Deal, pk=pk)
        deal = services.mark_lost(request.user, pk, request.data.get('reason', ''))
        if deal is None:
            return Response(
                {'detail': 'A sold deal cannot be marked lost. Un-sell it first.'}, status=status.HTTP_409_CONFLICT
            )
        return Response(selectors.deal_header(deal))


class DealReopenView(APIView):
    def post(self, request, pk):
        get_object_or_404(Deal, pk=pk)
        return Response(selectors.deal_header(services.reopen(request.user, pk)))


class DealActivityView(APIView):
    def get(self, request, pk):
        deal = get_object_or_404(Deal, pk=pk)
        pager = Pages()
        page = pager.paginate_queryset(deal.activity.select_related('actor').all(), request, view=self)
        return pager.get_paginated_response([selectors.activity_row(row) for row in page])


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
