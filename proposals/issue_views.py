"""Issue to client and the issued versions (plan.md §7.12 "Issuing"; J96, J102, J103, J104; J.6.6; slice 32).

- `POST deals/{id}/proposal/issue/` → 202 issue (the `issue` job queued; 200 with the version already building) ·
  409 {detail, blockers}: our recommendation missing on a line, a line past 16 plans, nothing on the proposal.
- `GET deals/{id}/proposal/issues/` → [issue], newest first (`issues.selectors`; the builder payload carries the same).
- `POST deals/{id}/proposal/issues/{v}/retry/` → 202 issue · 409 for an issued version or when the gate refuses.
- `GET deals/{id}/proposal/issues/{v}/{pdf,pptx,xlsx}/` → the stored bytes as issued, never rebuilt; `…/letter/` →
  the stored PDF on US Letter (`paint.paper.letter`, J114, made on each download from the stored bytes); `…/packet/`
  (`?include=pdf,pptx,xlsx`) → the ticked stored files in one zip. Each writes only its `downloaded` row, naming the
  file and the version (§3.8). 404 for a version that is not issued.
"""

import io

from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from deals import activity
from deals.downloads import file_response
from deals.models import Deal

from .issues import packet, selectors, start
from .issues.catalog import LETTER
from .paint import paper
from .services import AREA

PACKET = 'packet'
# What a `downloaded` row names, as the drafts' rows do ("Downloaded the client PDF (draft)"), with the version.
WORDS = {
    'pdf': 'the client PDF',
    'pptx': 'the client PowerPoint',
    'xlsx': 'the client spreadsheet',
    LETTER: 'the client Letter PDF',
    PACKET: 'the proposal packet',
}


def _answer(row, created=True):
    body = {**selectors.payload(row), 'job_id': row.job_id}
    return Response(body, status=status.HTTP_202_ACCEPTED if created else status.HTTP_200_OK)


class IssueView(APIView):
    def post(self, request, pk):
        deal = get_object_or_404(Deal, pk=pk)
        row, created = start.issue(request.user, deal)
        return _answer(row, created)


class IssuesView(APIView):
    def get(self, request, pk):
        return Response(selectors.issues(get_object_or_404(Deal, pk=pk)))


class RetryView(APIView):
    def post(self, request, pk, version):
        deal = get_object_or_404(Deal, pk=pk)
        return _answer(start.retry(request.user, deal, version))


def _read(document):
    try:
        with document.file.open('rb') as handle:
            return handle.read()
    except (FileNotFoundError, OSError, ValueError) as exc:
        raise Http404('This file is missing from storage.') from exc


class IssuedFileView(APIView):
    """One stored file of an issued version (`file`: pdf, pptx, xlsx, letter or packet, from the route)."""

    def get(self, request, pk, version, file):
        deal = get_object_or_404(Deal.objects.select_related('client'), pk=pk)
        row = selectors.issued(deal, version)
        if row is None:
            raise Http404(f'This deal has no issued proposal v{version}.')
        if file == PACKET:
            try:
                include = packet.parse_include(request.query_params.get('include'))
            except packet.Refused as refusal:
                return Response({'detail': str(refusal)}, status=status.HTTP_409_CONFLICT)
            data, name, document_id = packet.build(row, include), packet.zip_name(deal), row.pdf_id
        elif file == LETTER:
            data, document_id = paper.letter(_read(row.pdf)), row.pdf_id
            name = f'{row.pdf.original_name.removesuffix(".pdf")} (Letter).pdf'
        else:
            document = getattr(row, file)
            data, name, document_id = _read(document), document.original_name, document.id
        what = f'{WORDS[file]} (v{row.version})'
        activity.log_access(deal, request.user, 'downloaded', what, document_id, area=AREA)
        return file_response(io.BytesIO(data), name)
