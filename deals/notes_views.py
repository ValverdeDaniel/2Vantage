"""The deal's notes over HTTP (plan.md §7.3; A37, M73–M77). Thin: parse → service or selector → respond."""

from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from . import selectors, services
from .models import Deal, Note
from .services.notes import clean_body, clean_kind
from .views import MAX_ID


def _pinned(value):
    if not isinstance(value, bool):
        raise ValidationError({'pinned': ['Send true or false.']})
    return value


def _changes(data):
    changes = {}
    if 'body' in data:
        changes['body'] = clean_body(data['body'])
    if 'kind' in data:
        changes['kind'] = clean_kind(data['kind'])
    if 'pinned' in data:
        changes['pinned'] = _pinned(data['pinned'])
    return changes


class DealNotesView(APIView):
    """GET deals/{id}/notes/ (pinned first, newest first) · POST {body, kind?, pinned?} → 201 note."""

    def get(self, request, pk):
        if pk > MAX_ID:
            raise Http404
        return Response(selectors.note_rows(get_object_or_404(Deal, pk=pk), request.user))

    def post(self, request, pk):
        if pk > MAX_ID:
            raise Http404
        get_object_or_404(Deal, pk=pk)
        data = request.data
        note = services.add_note(
            request.user,
            pk,
            body=data.get('body'),
            kind=data.get('kind', 'note'),
            pinned=_pinned(data.get('pinned', False)),
        )
        return Response(selectors.note_row(note, request.user), status=status.HTTP_201_CREATED)


class NoteView(APIView):
    """PATCH notes/{id}/ {body, kind, pinned} → note · DELETE → {activity_id}: a soft delete whose Revert is the Undo
    (M77). Only the author or an admin (403 otherwise); a deleted note is a 404."""

    def _live(self, pk):
        if pk > MAX_ID or not Note.objects.filter(pk=pk).exists():
            raise Http404
        return pk

    def patch(self, request, pk):
        note, _changed = services.update_note(request.user, self._live(pk), **_changes(request.data))
        return Response(selectors.note_row(note, request.user))

    def delete(self, request, pk):
        row = services.delete_note(request.user, self._live(pk))
        return Response({'id': pk, 'activity_id': row.id})
