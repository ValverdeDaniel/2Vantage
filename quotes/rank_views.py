"""⚖ Rank plans' door (plan.md §7.5; D6, D96, F111, OQ44; slice 37). quotes serves it: Rank reads intake's guidance
and the line's plans, both right of ai in the chain."""

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from ai import selectors as ai_selectors
from ai.models import Job
from deals.models import Deal

from . import parse
from .rank.start import start_rank


class RankView(APIView):
    def post(self, request, pk):
        """{line, plan_ids?, model?}: rank one line's quoted plans against the client guidance (`plan_ids`: only the
        plans a filtered board shows, OQ44) → 201 the `rank` job, or 200 the same rank already going. 409 with the
        sentence: no Claude, no guidance ("Add client guidance first…"), the table locked, Opus for a producer, no
        quoted plan; 400 a bad line or ids."""
        deal = get_object_or_404(Deal, pk=pk)
        raw = request.data.get('plan_ids')
        model = request.data.get('model')
        job, created = start_rank(
            request.user,
            deal,
            parse.line(request),
            plan_ids=None if raw is None else parse.plan_ids(raw),
            model=model if isinstance(model, str) else '',
        )
        job = Job.objects.select_related('created_by').get(pk=job.pk)
        return Response(
            ai_selectors.job_payload(job), status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )
