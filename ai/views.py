"""The ai API (plan.md §7.5; D.6). Slice 16: the state the browser polls, "Check this file", one job, and Stop.
Slice 18: the one read door (`deals/{id}/ai/reads/`, D39) and Discard on a waiting change set (D28, D74).
Slice 19: using a read (`ai/jobs/{id}/apply/`, D72) and ↶ Undo this run (`ai/jobs/{id}/undo/`, D73).

The two GETs a browser polls (`deals/{id}/ai/` and `ai/jobs/{id}/`) use the `ai_poll` throttle alone, so polling
every 2 s on two tabs never uses up the user rate (§3.5, E.6). Any signed-in person may start or stop a job on any
deal (OQ3).
"""

from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.http import quote_etag
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from deals.models import Deal

from . import selectors, services
from .models import Job

MAX_ID = 2**63 - 1  # a bigger id is not a row: 404, never a database error


def _deal(pk):
    if pk > MAX_ID:
        raise Http404
    return get_object_or_404(Deal, pk=pk)


def _job(job_id):
    if job_id > MAX_ID:
        raise Http404
    return get_object_or_404(Job.objects.select_related('created_by'), pk=job_id)


def _ids(raw, name='document_ids'):
    if not isinstance(raw, list) or any(isinstance(item, bool) for item in raw):
        raise ValidationError({name: ['Give a list of document ids.']})
    try:
        ids = [int(item) for item in raw]
    except (TypeError, ValueError) as exc:
        raise ValidationError({name: ['Give a list of document ids.']}) from exc
    if any(not 0 < item <= MAX_ID for item in ids):
        raise ValidationError({name: ['Give a list of document ids.']})
    return ids


class Polled(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'ai_poll'


class DealAiView(Polled):
    """GET the deal's AI state: jobs queued, running and just finished; lock, spend, permissions. Writes nothing."""

    def get(self, request, pk):
        return Response(selectors.deal_state(_deal(pk), request.user))


class LocateView(APIView):
    """POST {document_ids, recheck?}: "Check this file" (E59) → 201 the new job, or 200 the same one already going."""

    def post(self, request, pk):
        deal = _deal(pk)
        ids = _ids(request.data.get('document_ids'))
        job, created = services.start_locate(request.user, deal, ids, bool(request.data.get('recheck')))
        job = _job(job.id)
        return Response(selectors.job_payload(job), status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class JobView(Polled):
    """GET one job and its result, with an ETag: an unchanged job answers 304."""

    def get(self, request, job_id):
        job = _job(job_id)
        etag = quote_etag(f'job-{job.id}-{job.updated_at.timestamp():.6f}')
        if request.headers.get('If-None-Match') == etag:
            return Response(status=status.HTTP_304_NOT_MODIFIED, headers={'ETag': etag})
        return Response(selectors.job_payload(job), headers={'ETag': etag})


class CancelView(APIView):
    """POST: Stop. A queued job ends at once; a running one at its next step, keeping what it finished."""

    def post(self, request, job_id):
        job, _changed = services.cancel(request.user, _job(job_id).id)
        return Response(selectors.job_payload(_job(job.id)))


def _pages(raw):
    if raw in (None, ''):
        return None
    if not isinstance(raw, list) or any(isinstance(item, bool) for item in raw):
        raise ValidationError({'pages': ['Give a list of page numbers.']})
    try:
        pages = [int(item) for item in raw]
    except (TypeError, ValueError) as exc:
        raise ValidationError({'pages': ['Give a list of page numbers.']}) from exc
    if any(not 0 < page <= 100_000 for page in pages):
        raise ValidationError({'pages': ['Give a list of page numbers.']})
    return pages


class ReadsView(APIView):
    """POST {document_ids, target?, pages?, model?, budget_override?}: read these files with Claude (D39) → 201 the job,
    or 200 the same read already going. 409 without a key; 400 for files this reader does not read."""

    def post(self, request, pk):
        deal = _deal(pk)
        ids = _ids(request.data.get('document_ids'))
        target = request.data.get('target') or 'quotes'
        if not isinstance(target, str):
            raise ValidationError({'target': ['Name a reader.']})
        model = request.data.get('model') or ''
        if not isinstance(model, str):
            raise ValidationError({'model': ['Name a model.']})
        job, created = services.start_read(
            request.user,
            deal,
            ids,
            target=target,
            pages=_pages(request.data.get('pages')),
            model=model,
            budget_override=request.data.get('budget_override') is True,
        )
        job = _job(job.id)
        return Response(selectors.job_payload(job), status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class DiscardView(APIView):
    """POST: drop a waiting change set (D74). Nothing on the deal changes."""

    def post(self, request, job_id):
        job, _changed = services.discard(request.user, _job(job_id).id)
        return Response(selectors.job_payload(_job(job.id)))


class ApplyView(APIView):
    """POST {select?, picks?}: use a waiting read (D72) → {job, landed}. No `select` is "Use this scan" (the read as
    proposed); `select` is "Apply N selected" (item ids, "<item>:<key>" for a value that arrived unticked);
    `picks` {item id: plan id | "new" | "alternate"} places a "Which current plan?" item (D117). 409 when the read is
    not waiting or was used; 400 for an unknown item or pick."""

    def post(self, request, job_id):
        select = request.data.get('select')
        picks = request.data.get('picks')
        job, landed = services.apply(request.user, _job(job_id).id, select=select, picks=picks)
        return Response({'job': selectors.job_payload(_job(job.id)), 'landed': landed})


class UndoView(APIView):
    """POST {force?}: ↶ Undo this run (D73) → {job, undone}. 409 with `can_force` when something changed since."""

    def post(self, request, job_id):
        job, _changed = services.undo(request.user, _job(job_id).id, force=request.data.get('force') is True)
        job = _job(job.id)
        return Response({'job': selectors.job_payload(job), 'undone': (job.result.get('landed') or {}).get('undone')})
