"""The board's tools (plan.md §7.8; F14–F17, F28): the finder's index and the saved setups. Thin: parse → selector or
service → respond.

- GET `deals/{id}/plans/find/` → {plans: [{id, line, current, carrier, texts}]}: every line's plans in one query;
  the browser's finder matches the words, so typing never waits on the server (F15).
- GET `saved-views/?view=quotes&line=medical` → [setup]: mine and the shared ones, offered on that line;
  POST {name, description?, view?, line?, shared?, config} → 201 setup.
- GET/PATCH/DELETE `saved-views/{id}/`: another person's private setup answers 404; Update and Delete are for its
  owner or an admin (403 with the sentence otherwise).
"""

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from deals.models import Deal

from .selectors import find_index
from .selectors import saved_views as saved
from .services import saved_views


class FindView(APIView):
    def get(self, request, pk):
        return Response({'plans': find_index(get_object_or_404(Deal, pk=pk))})


class SavedViewsView(APIView):
    def get(self, request):
        rows = saved.visible(request.user, request.query_params.get('view'), request.query_params.get('line'))
        return Response([saved.payload(row, request.user) for row in rows])

    def post(self, request):
        row = saved_views.create(request.user, request.data)
        return Response(saved.payload(row, request.user), status=status.HTTP_201_CREATED)


class SavedViewView(APIView):
    def get(self, request, view_id):
        row = saved.visible(request.user).filter(pk=view_id).first()
        if row is None:
            raise NotFound(saved_views.NOT_FOUND)
        return Response(saved.payload(row, request.user))

    def patch(self, request, view_id):
        row, entry = saved_views.update(request.user, view_id, request.data)
        return Response({**saved.payload(row, request.user), 'activity_id': entry.id if entry else None})

    def delete(self, request, view_id):
        saved_views.delete(request.user, view_id)
        return Response(status=status.HTTP_204_NO_CONTENT)
