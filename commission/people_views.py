"""Producers & partners and Settings, the /commissions page's two tabs built in slice 48 (plan.md §7.10, §8.18;
H95–H101). The roster needs a commission tier (own sees the roster only); every write, and Settings, is the all
tier's (H97, H100, H102). The Book, By person and the tiles join with slice 49.
"""

from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.access import HasCommissions, commission_tier

from . import parties, selectors, services
from .models import Party
from .views import MAX_ID, body

ALL_ONLY = 'Only someone with all commission access can change this.'


class AllTier(BasePermission):
    message = ALL_ONLY

    def has_permission(self, request, view):
        return commission_tier(request.user) == 'all'


def _roster(request):
    inactive = request.query_params.get('inactive') in ('1', 'true')
    return parties.roster(commission_tier(request.user), inactive=inactive)


def _party_or_404(pk):
    if pk > MAX_ID:
        raise Http404
    return get_object_or_404(Party, pk=pk)


class PartiesView(APIView):
    """GET commissions/parties/?inactive=1 → {producers: [entry], partners: [entry], full} (own tier: no percentages
    and no access badges). POST {kind, name, email?, phone?, npn?, appointed?, default_split?, first_year_pct?,
    renewal_pct?, user?} → 201 {party: entry, activity_id, …roster} (all tier)."""

    def get_permissions(self):
        if self.request.method == 'GET':
            return [IsAuthenticated(), HasCommissions()]
        return [IsAuthenticated(), AllTier()]

    def get(self, request):
        return Response(_roster(request))

    def post(self, request):
        written = services.create_party(request.user, body(request))
        answer = {'party': parties.party_entry(written.row), 'activity_id': written.activity.id, **_roster(request)}
        return Response(answer, status=201)


class PartyView(APIView):
    """PATCH commissions/parties/{id}/ {any party field; active: false deactivates} → {party, activity_id, …roster}
    (all tier)."""

    permission_classes = [IsAuthenticated, AllTier]

    def patch(self, request, pk):
        _party_or_404(pk)
        written = services.save_party(request.user, pk, body(request))
        activity_id = written.activity.id if written.activity else None
        return Response({'party': parties.party_entry(written.row), 'activity_id': activity_id, **_roster(request)})


class SettingsView(APIView):
    """GET commissions/settings/ → {first_year_pct, renewal_pct, first_year_house_pct, renewal_house_pct, confirmed,
    confirmed_by, confirmed_at, default_commission, default_commission_label}. PATCH {first_year_pct?, renewal_pct?,
    default_commission?, confirm?} → {activity_id, …settings} (all tier, H100)."""

    permission_classes = [IsAuthenticated, AllTier]

    def get(self, request):
        return Response(selectors.settings_payload())

    def patch(self, request):
        written = services.save_settings(request.user, body(request))
        activity_id = written.activity.id if written.activity else None
        return Response({'activity_id': activity_id, **selectors.settings_payload()})
