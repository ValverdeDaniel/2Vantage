"""The census format lens (plan.md §7.11; K79–K88): `GET deals/{id}/rfp/formats/` (the Export readiness cards and
the lens chips) and `GET deals/{id}/rfp/formats/{key}/?rows=` (one format, its first `rows` rows, 1–200, default 50).
Reads only. No query parameter is named `format` (K.6)."""

from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .formats import lens
from .views import _deal


def _rows(raw):
    if raw in (None, ''):
        return 50
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise ValidationError({'rows': ['Send a number of rows from 1 to 200.']}) from None
    if not 1 <= value <= lens.MAX_ROWS:
        raise ValidationError({'rows': ['Send a number of rows from 1 to 200.']})
    return value


class FormatsView(APIView):
    """GET → {formats: [{key, kind, label, carrier, file_formats, rows, columns, gaps, max_rows, capped, in_packet,
    required_by, to_fix}], default_key}."""

    def get(self, request, pk):
        return Response(lens.formats(_deal(pk)))


class FormatView(APIView):
    """GET → one format (rfp/formats/lens.py `detail`); 400 an unknown key (with the valid ones) or a bad `rows`."""

    def get(self, request, pk, key):
        deal = _deal(pk)
        limit = _rows(request.query_params.get('rows'))
        try:
            return Response(lens.detail(deal, key, limit))
        except lens.UnknownFormat as exc:
            raise ValidationError({'key': [f'"{key}" is not a census format.'], 'valid': exc.valid}) from None
