"""The ai API (plan.md §7.5; D.6). Slice 16: the state the browser polls, "Check this file", one job, and Stop.
Slice 18: the one read door (`deals/{id}/ai/reads/`, D39) and Discard on a waiting change set (D28, D74).
Slice 19: using a read (`ai/jobs/{id}/apply/`, D72) and ↶ Undo this run (`ai/jobs/{id}/undo/`, D73).
Slice 20: attaching files to Claude (`deals/{id}/ai/sends/`, D16, D17) and ↻ Try again (`ai/jobs/{id}/retry/`, D76);
the read door's `review` (the Re-read panel's reads always wait, E75).
Slice 22: ✦ Ask Claude to re-check (`deals/{id}/ai/recheck/`, D40, D93); its change set uses apply/undo/discard.

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
    """GET the deal's AI state: jobs queued, running and just finished; lock, spend, permissions. Writes nothing.
    PATCH {locked?, budget_usd?}: the table lock and the deal's budget (admins only), then the state (slice 24)."""

    def get(self, request, pk):
        return Response(selectors.deal_state(_deal(pk), request.user))

    def patch(self, request, pk):
        from .chat_views import patch_settings

        return patch_settings(request, _deal(pk))


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


def _model(data):
    model = data.get('model') or ''
    if not isinstance(model, str):
        raise ValidationError({'model': ['Name a model.']})
    return model


class ReadsView(APIView):
    """POST {document_ids, target?, pages?, model?, budget_override?, review?}: read these files with Claude (D39) →
    201 the job, or 200 the same read already going. 409 without a key; 400 for files this reader does not read.
    `review: true` makes the read wait for review whoever starts it (E75)."""

    def post(self, request, pk):
        deal = _deal(pk)
        ids = _ids(request.data.get('document_ids'))
        target = request.data.get('target') or 'quotes'
        if not isinstance(target, str):
            raise ValidationError({'target': ['Name a reader.']})
        job, created = services.start_read(
            request.user,
            deal,
            ids,
            target=target,
            pages=_pages(request.data.get('pages')),
            model=_model(request.data),
            budget_override=request.data.get('budget_override') is True,
            review=request.data.get('review') is True,
        )
        job = _job(job.id)
        return Response(selectors.job_payload(job), status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


def _refs(raw):
    if raw is None:
        return None
    if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
        raise ValidationError({'refs': ['Name the values as a list of refs.']})
    return raw


class RecheckView(APIView):
    """POST {refs? | plan_ids? | document_ids?, scanned?, model?}: ✦ Ask Claude to re-check (D40, D93, E77; slice 22)
    → 201 the job, or 200 the same re-check already going. Its change set waits for a person. `scanned: true` is the
    Overview's Double-check with AI (M92; slice 64): the values read from files that no person approved. 409 without a
    key, with nothing flagged (or scanned) there or too many values; 400 for ids or refs that are not the deal's."""

    def post(self, request, pk):
        deal = _deal(pk)
        plan_ids, document_ids = request.data.get('plan_ids'), request.data.get('document_ids')
        job, created = services.start_recheck(
            request.user,
            deal,
            refs=_refs(request.data.get('refs')),
            plan_ids=_ids(plan_ids, 'plan_ids') if plan_ids is not None else None,
            document_ids=_ids(document_ids) if document_ids is not None else None,
            model=_model(request.data),
            scanned=request.data.get('scanned') is True,
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


class SendsView(APIView):
    """POST {document_ids, model?, budget_override?, tab?}: files just attached in Work with Claude, read by the reader
    of their kind (D16, D17) → 201 {jobs: [job, in the order they run], not_read: [ids no reader reads]}, or 200 when
    every read was already going (or none was started). 409 without a key. `tab`: the deal tab the drawer is open on
    (intake reads only from Intake's, slice 51)."""

    def post(self, request, pk):
        deal = _deal(pk)
        tab = request.data.get('tab')
        started, not_read = services.start_send(
            request.user,
            deal,
            _ids(request.data.get('document_ids')),
            model=_model(request.data),
            budget_override=request.data.get('budget_override') is True,
            tab=tab if isinstance(tab, str) else '',
        )
        created = any(made for _job, made in started)
        body = {'jobs': [selectors.job_payload(_job(job.id)) for job, _made in started], 'not_read': not_read}
        return Response(body, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class RetryView(APIView):
    """POST {model?, force?, budget_override?}: ↻ Try again (D76) → 201 the new read. A used read is undone first (409
    with `can_force` as Undo; `force` is Undo anyway); one waiting is discarded. 409 while it runs, for a job that is
    not a read, or Opus or Run anyway for a producer."""

    def post(self, request, job_id):
        job, created = services.retry(
            request.user,
            _job(job_id).id,
            model=_model(request.data),
            force=request.data.get('force') is True,
            budget_override=request.data.get('budget_override') is True,
        )
        job = _job(job.id)
        return Response(selectors.job_payload(job), status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
