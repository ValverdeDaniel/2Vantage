"""The RFP's files (plan.md §7.11, §9.8; K.6 endpoints; K82, K113). Slice 45 serves the census files of the one key
space: `census-warner`, `census-aetna`, `census-angle`, `census-angle-csv`, `census-uhc`; the packet, the forms, the
cover and the drafts join with slice 46 (with the check's `?ack=`).

- `GET deals/{id}/rfp/files/{key}/`: the file, built from the deal and never stored, named `<Client> - <Carrier>
  census.xlsx` (no person's name), through `file_response` (no-store). It carries member data, so every download writes
  one `downloaded` row naming the kind of file (§3.8, K113).
- `GET deals/{id}/rfp/files/{key}/look/?sheet=&start=`: "Check the real file" (K82): the file built exactly as the
  download builds it, answered as windows of the sheet with Excel's look (`documents.sheets.window`, the document
  viewer's shape) and the file's warnings; it opens on the roster sheet; logged as a `viewed` row.
An unknown key answers 400 naming the valid ones; a deal with nobody on its census 409 ("No census yet", K41).
"""

import io

from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from deals import activity
from deals.downloads import file_response
from documents import sheets

from .formats import fill, scope
from .views import _deal

NO_CENSUS = 'No census yet — there is nobody on this deal’s census to put in the file.'
PREFIX = 'census-'


def _file_key(key):
    """The census file key (`warner`, `angle-csv`, …) for a key of the one key space; 400 otherwise."""
    if key not in scope.keys():
        raise ValidationError({'key': [f'"{key}" is not one of this RFP’s files: {", ".join(scope.keys())}.']})
    return key.removeprefix(PREFIX)


def _start(raw):
    if raw in (None, ''):
        return None
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise ValidationError({'start': ['Send a row number.']}) from None
    if value < 0:
        raise ValidationError({'start': ['Send a row number.']})
    return value


def _built(deal, key):
    try:
        return fill.build(deal, _file_key(key))
    except fill.NoCensus:
        return None


def _what(key):
    found, kind = fill.resolve(key.removeprefix(PREFIX))
    return f'the {found["carrier"]} census file' + (' (CSV)' if kind == 'csv' else '')


class FileView(APIView):
    """GET deals/{id}/rfp/files/{key}/ → the file (attachment); 400 unknown key; 409 no census."""

    def get(self, request, pk, key):
        deal = _deal(pk)
        built = _built(deal, key)
        if built is None:
            return Response({'detail': NO_CENSUS}, status=409)
        activity.log_access(deal, request.user, 'downloaded', _what(key), None, area='rfp')
        return file_response(io.BytesIO(built.content), built.filename)


class LookView(APIView):
    """GET deals/{id}/rfp/files/{key}/look/?sheet=&start= → {file, warnings, sheets, sheet, start, window, total_rows,
    cols, col_letters, rows, match, format}; 400 unknown key or start; 409 no census."""

    def get(self, request, pk, key):
        deal = _deal(pk)
        start = _start(request.query_params.get('start'))
        built = _built(deal, key)
        if built is None:
            return Response({'detail': NO_CENSUS}, status=409)
        found, kind = fill.resolve(key.removeprefix(PREFIX))
        sheet = request.query_params.get('sheet') or (found['sheet'] if kind == 'xlsx' else None)
        window = sheets.window(f'file.{kind}', built.content, sheet=sheet, start=start, look=True)
        activity.log_access(deal, request.user, 'viewed', _what(key), None, area='rfp')
        return Response({'file': key, 'warnings': built.warnings, **window})
