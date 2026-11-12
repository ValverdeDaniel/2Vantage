"""POST plans/{id}/sbc/ — Attach SBC… (plan.md §7.8; D38, D47; slice 22): a staged read of the plan's design.

Multipart with one `file` (a new SBC, filed on the deal) or JSON `{document_id}` (an SBC already there), and `model?`
→ 201 the read job (ai's job payload), or 200 the same read already going. 409 without Claude, on a plan of another
line or a priced version or copy; 400 for a missing file, a file that is not the deal's or not an SBC, or a bad id;
404 for a plan that is not there (a removed plan too).
"""

from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from ai.selectors import job_payload

from .models import Plan
from .services import sbc

MAX_ID = 2**63 - 1


def _document_id(raw):
    if raw in (None, ''):
        return None
    if isinstance(raw, bool):
        raise ValidationError({'document_id': ['Give a document id.']})
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise ValidationError({'document_id': ['Give a document id.']}) from exc
    if not 0 < value <= MAX_ID:
        raise ValidationError({'document_id': ['Give a document id.']})
    return value


class AttachSbcView(APIView):
    def post(self, request, plan_id):
        if plan_id > MAX_ID:
            raise Http404
        plan = get_object_or_404(Plan, pk=plan_id)
        model = request.data.get('model') or ''
        if not isinstance(model, str):
            raise ValidationError({'model': ['Name a model.']})
        job, created = sbc.attach(
            request.user,
            plan.id,
            upload=request.FILES.get('file'),
            document_id=_document_id(request.data.get('document_id')),
            model=model,
        )
        job.refresh_from_db()
        return Response(job_payload(job), status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
