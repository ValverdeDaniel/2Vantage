"""A spreadsheet's window and the cell a value was read from (plan.md §7.4; E27–E29).

GET `documents/{id}/sheet/?sheet=&start=&cell=&look=1` answers one window (sheets.window); it is a view of the file,
so a file with member data writes its `viewed` row (E99). POST `documents/{id}/sheet/find/` takes `{value, line,
hint}` in its body, never in the URL (E28), and answers `{sheet, cell, state}`.
"""

from django.http import Http404
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .sheet_find import find_value
from .sheets import MAX_ROWS, SheetError, window
from .views import document_or_404

TEXT_LIMIT = 300


def _bytes(document):
    try:
        with document.file.open('rb') as handle:
            return handle.read()
    except (FileNotFoundError, OSError, ValueError) as exc:
        raise Http404('This file is missing from storage.') from exc


def _start(raw):
    if raw in (None, ''):
        return None
    try:
        start = int(raw)
    except (TypeError, ValueError) as exc:
        raise ValidationError({'start': ['Start must be a row number.']}) from exc
    if not 0 <= start <= MAX_ROWS:
        raise ValidationError({'start': ['Start must be a row number.']})
    return start


def _text(data, key):
    value = data.get(key) or ''
    if not isinstance(value, str | int | float):
        raise ValidationError({key: ['Must be text.']})
    return str(value)[:TEXT_LIMIT]


class SheetView(APIView):
    def get(self, request, document_id):
        document = document_or_404(document_id)
        query = request.query_params
        try:
            payload = window(
                document.original_name,
                _bytes(document),
                sheet=query.get('sheet') or None,
                start=_start(query.get('start')),
                cell=query.get('cell') or None,
                look=query.get('look') == '1',
            )
        except SheetError as exc:
            raise ValidationError({'detail': str(exc)}) from exc
        services.record_access(request.user, document, inline=True)
        return Response(payload)


class SheetFindView(APIView):
    def post(self, request, document_id):
        document = document_or_404(document_id)
        if not isinstance(request.data, dict):
            raise ValidationError({'non_field_errors': ['Send {value, line, hint}.']})
        value, line, hint = (_text(request.data, key) for key in ('value', 'line', 'hint'))
        if not (value or line):
            raise ValidationError({'value': ['Say what to find.']})
        try:
            return Response(find_value(document.original_name, _bytes(document), value, line, hint))
        except SheetError as exc:
            raise ValidationError({'detail': str(exc)}) from exc
