"""The RFP's files (plan.md §7.11, §9.8–§9.11; K.6 endpoints; K50, K51, K55, K63, K70, K82, K113). One door for
every file of the one key space, the packet and each draft; nothing is stored.

- `GET deals/{id}/rfp/files/{key}/?ack=`: a row's file (`census-…`, `form-census-<variant>`, `form`, `cover`,
  `questionnaire-<form>`, `disclosure-<form>`, `proposal`, `doc-<id>`), `packet` (the zip, §9.10) or `draft-<key>` (the
  `.eml`, §9.11), built from one request and served through `file_response` (no-store, streamed). With `ack`, a check
  that changed since the modal read it answers 409 `{detail, report}` with the fresh report (K70). A file that
  carries member data writes one `downloaded` row naming its kind (and the document, for a file from Documents), never
  a person (§3.8; K113); so does a packet or a draft carrying one. 400: a key the deal does not have, or a packet with
  nothing ticked; 409: no census yet, or a row that cannot be built — named by its label only (K55, bug 36).
- `GET …/files/{key}/look/?sheet=&start=`: "Check the real file" for a census file (K82): its sheet windows
  (`documents.sheets.window`) and warnings, logged `viewed`.
"""

import io

from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from deals import activity, clock
from deals.downloads import file_response
from documents import sheets

from . import drafts, eml, members
from . import packet as zipped
from .cards import packet
from .check import report
from .context import Request
from .formats import fill, scope
from .views import _deal

NO_CENSUS = 'No census yet — there is nobody on this deal’s census to put in the file.'
STALE = 'Something changed since you checked this file. Here is the check as it stands now.'
PREFIX = 'census-'
DRAFT = report.DRAFT


def _unknown(key):
    return ValidationError({'key': [f'“{key}” is not one of this RFP’s files.']})


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


def _what(row):
    if row['section'] == 'census':
        return _what_census(row['key'])
    return f'the {row["title"]}' if row['section'] != 'attachments' else f'a {row["title"]} file'


def _log(deal, user, found, what):
    """One `downloaded` row when a file carries member data (§3.8)."""
    if any(member.phi for member in found):
        document = found[0].document if len(found) == 1 else None
        activity.log_access(deal, user, 'downloaded', what, document, area='rfp')


def _file(ctx, rows, key):
    """(bytes, file name, members) for the key. Raises ValidationError, members.NotBuilt or packet.Nothing."""
    if key == report.PACKET:
        content, name, found = zipped.build(ctx, rows, clock.today())
        return content, name, found, 'the RFP packet'
    if key.startswith(DRAFT):
        by_key = {row['key']: row for row in rows}
        draft = next((d for d in drafts.drafts(ctx, packet.in_packet(rows)) if d['key'] == key[len(DRAFT) :]), None)
        if draft is None:
            raise _unknown(key)
        found = members.members(ctx, [by_key[name] for name in draft['attachment_keys']])
        return eml.build(draft, found), eml.filename(ctx, draft), found, f'the {draft["name"]} email draft'
    row = next((found for found in rows if found['key'] == key), None)
    if row is None:
        raise _unknown(key)
    if not row['available']:
        raise NoCensus() if row['section'] in ('census', 'census_forms') else members.NotBuilt(row['title'])
    found = members.member(ctx, row)
    return found.data, found.name, [found], _what(row)


class NoCensus(Exception):
    pass


class FileView(APIView):
    """GET deals/{id}/rfp/files/{key}/?ack= → the file (attachment); 400 unknown key or nothing ticked; 409 no census,
    a row that cannot be built, or a stale `ack` ({detail, report})."""

    def get(self, request, pk, key):
        deal = _deal(pk)
        ctx = Request(deal)
        rows = packet.rows(ctx)
        ack = str(request.query_params.get('ack') or '')[:64]
        try:
            fresh = report.stale(ctx, key, ack, rows)
        except report.Unknown:
            raise _unknown(key) from None
        if fresh is not None:
            return Response({'detail': STALE, 'report': fresh}, status=409)
        try:
            content, name, found, what = _file(ctx, rows, key)
        except NoCensus:
            return Response({'detail': NO_CENSUS}, status=409)
        except zipped.Nothing as error:
            raise ValidationError({'key': [str(error)]}) from None
        except members.NotBuilt as error:
            return Response({'detail': error.sentence}, status=409)
        _log(deal, request.user, found, what)
        return file_response(io.BytesIO(content), name)


def _census_key(key):
    if key not in scope.keys():
        raise ValidationError({'key': [f'"{key}" is not one of this RFP’s files: {", ".join(scope.keys())}.']})
    return key.removeprefix(PREFIX)


def _what_census(key):
    found, kind = fill.resolve(key.removeprefix(PREFIX))
    return f'the {found["carrier"]} census file' + (' (CSV)' if kind == 'csv' else '')


class LookView(APIView):
    """GET deals/{id}/rfp/files/{key}/look/?sheet=&start= → {file, warnings, sheets, sheet, start, window, total_rows,
    cols, col_letters, rows, match, format}; 400 unknown key or start; 409 no census."""

    def get(self, request, pk, key):
        deal = _deal(pk)
        start = _start(request.query_params.get('start'))
        try:
            built = fill.build(deal, _census_key(key))
        except fill.NoCensus:
            return Response({'detail': NO_CENSUS}, status=409)
        found, kind = fill.resolve(key.removeprefix(PREFIX))
        sheet = request.query_params.get('sheet') or (found['sheet'] if kind == 'xlsx' else None)
        window = sheets.window(f'file.{kind}', built.content, sheet=sheet, start=start, look=True)
        activity.log_access(deal, request.user, 'viewed', _what_census(key), None, area='rfp')
        return Response({'file': key, 'warnings': built.warnings, **window})
