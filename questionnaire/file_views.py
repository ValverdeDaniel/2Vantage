"""The questionnaire's files and their check (plan.md §7.9, §9.12; G56, G61–G67, G135).

- `GET …/{form}/check/` → `{form, label, ok, problems, ack}`; writes nothing.
- `GET …/{form}/pdf/?ack=&inline=1` → the filled form, or the filed signed copy once the officer has signed. A stale
  `ack` answers 409 with the fresh report (G66). The file carries medical history, so every download writes one
  `downloaded` row and every preview (`inline=1`, the "Check the form ▸" pane) a `viewed` row, naming the form, never
  a person (G63, §3.8).
- `GET …/{form}/blank/` → the carrier's bundled blank, nothing filled (G61); no member data, so not logged.
File names come from the server and the browser keeps them (G62).
"""

import io

from django.http import Http404
from rest_framework.response import Response
from rest_framework.views import APIView

from deals import activity
from deals.downloads import file_response

from . import forms
from .check import report
from .pdf import acroform, build, fonts, stamp_draw
from .selectors import files
from .services.common import AREA, form_or_404
from .views import _deal

STALE = 'Something changed since you checked this form. Here is the check as it stands now.'
NOT_BUILT = (acroform.AcroFormError, stamp_draw.StampError, build.BuildError, fonts.FontMissing)


class CheckView(APIView):
    def get(self, request, pk, form):
        form_or_404(form)
        return Response(report.report(_deal(pk), form))


class PdfView(APIView):
    def get(self, request, pk, form):
        form_or_404(form)
        deal = _deal(pk)
        ack = str(request.query_params.get('ack') or '')[:64]
        fresh = report.stale(deal, form, ack)
        if fresh is not None:
            return Response({'detail': STALE, 'report': fresh}, status=409)
        try:
            copy = files.download(deal, form)
        except NOT_BUILT as error:
            raise activity.Refused(f'The {forms.label(form)} PDF could not be built: {error}') from error
        inline = request.query_params.get('inline') == '1'
        what = f'the {forms.label(form)} PDF' + ('' if copy.signed else ' (draft)')
        document_id = copy.document.id if copy.document else None
        activity.log_access(deal, request.user, 'viewed' if inline else 'downloaded', what, document_id, area=AREA)
        return file_response(io.BytesIO(copy.data), copy.name, inline=inline)


class BlankView(APIView):
    def get(self, request, pk, form):
        form_or_404(form)
        _deal(pk)
        path, name = build.blank(form)
        if path is None:
            raise Http404('No blank form is available.')
        return file_response(path.open('rb'), name)
