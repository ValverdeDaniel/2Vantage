"""Agenda over HTTP (plan.md §7.15; I.6 endpoints). Thin: parse → service or selector → respond. Every signed-in user
sees and plans every deal (OQ3, I110); deleting a task is for its creator or an admin (OQ93)."""

from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from deals import clock
from deals.models import Deal
from deals.selectors import note_row
from deals.views import MAX_ID

from . import payload, selectors, services, shell
from .models import Task
from .queue import feed, stats

STEP_KEY_MAX = 80


def _deal_id(pk):
    if pk > MAX_ID or not Deal.objects.filter(pk=pk).exists():
        raise Http404
    return pk


def _step_key(raw):
    key = str(raw if raw is not None else '').strip()
    if len(key) > STEP_KEY_MAX:
        raise ValidationError({'step_key': ['That is not a step.']})
    return key


def _task_answer(task, viewer):
    return payload.task_row(task, clock.today(), viewer)


class DealAgendaView(APIView):
    """GET deals/{id}/agenda/ → {today, deal_id, lost, finished, next_step, waiting, journey, progress, rows}."""

    def get(self, request, pk):
        deal = get_object_or_404(Deal, pk=_deal_id(pk))
        return Response(selectors.deal_agenda(deal, request.user))


class DealJourneyView(APIView):
    """GET deals/{id}/journey/ → the shell's one read: {deal_id, today, next_step, waiting, journey, progress, badges,
    meters, ready} (A21, A23, A24; slice 61)."""

    def get(self, request, pk):
        deal = get_object_or_404(Deal, pk=_deal_id(pk))
        return Response(shell.journey_read(deal))


class WorkQueueView(APIView):
    """GET work-queue/ ?include=closed → {today, rows, owners, client_names, cards} (I70–I86; slice 61). Finished
    and lost deals' rows come only with `include=closed` (I80); anything else is a 400."""

    def get(self, request):
        include = request.query_params.get('include', '')
        if include not in ('', 'closed'):
            raise ValidationError({'include': ['include must be "closed" or left out.']})
        return Response(feed.work_queue(include_closed=include == 'closed'))


class WorkQueueStatsView(APIView):
    """GET work-queue/stats/ → {actions_week, sales_month}, each {total, change_pct, series} (I83, I84, I127)."""

    def get(self, request):
        return Response(stats.stats())


class MarksView(APIView):
    """POST deals/{id}/agenda/marks/ {step_key, kind: later | done, until?, note?} → {step, next_step}; 400 or 409."""

    def post(self, request, pk):
        deal_id = _deal_id(pk)
        data = request.data
        key = _step_key(data.get('step_key'))
        kind = data.get('kind')
        if kind == 'later':
            found = services.set_later(request.user, deal_id, key, data.get('until'), data.get('note', ''))
        elif kind == 'done':
            found = services.set_done_anyway(request.user, deal_id, key, data.get('note', ''))
        else:
            raise ValidationError({'detail': 'kind must be "later" or "done".'})
        return Response(found)


class MarkView(APIView):
    """DELETE deals/{id}/agenda/marks/{step_key}/ → {step, next_step}: Bring back, or Undo; 409 with no mark."""

    def delete(self, request, pk, step_key):
        return Response(services.clear_mark(request.user, _deal_id(pk), _step_key(step_key)))


class FollowUpsView(APIView):
    """POST deals/{id}/agenda/follow-ups/ {step_key, kind: call | email, body} → {step, next_step, note}."""

    def post(self, request, pk):
        data = request.data
        found = services.log_follow_up(
            request.user, _deal_id(pk), _step_key(data.get('step_key')), data.get('kind'), data.get('body', '')
        )
        return Response({**found, 'note': note_row(found['note'], request.user)})


class DealTasksView(APIView):
    """POST deals/{id}/tasks/ {title, due, assigned_to?, note?, done?} → 201 task row."""

    def post(self, request, pk):
        data = request.data
        task = services.add_task(
            request.user,
            _deal_id(pk),
            title=data.get('title'),
            due=data.get('due'),
            note=data.get('note', ''),
            assigned_to=data.get('assigned_to'),
            done=data.get('done', False),
        )
        return Response(_task_answer(task, request.user), status=status.HTTP_201_CREATED)


class TaskView(APIView):
    """PATCH tasks/{id}/ any of {title, due, note, assigned_to, done, move_note} → task row · DELETE → 204, a soft
    delete (403 unless its creator or an admin). A deleted or unknown task is a 404."""

    FIELDS = ('title', 'due', 'note', 'assigned_to', 'done', 'move_note')

    def _live(self, pk):
        if pk > MAX_ID or not Task.objects.filter(pk=pk).exists():
            raise Http404
        return pk

    def patch(self, request, pk):
        changes = {key: request.data[key] for key in self.FIELDS if key in request.data}
        task, _changed = services.update_task(request.user, self._live(pk), **changes)
        return Response(_task_answer(task, request.user))

    def delete(self, request, pk):
        services.delete_task(request.user, self._live(pk))
        return Response(status=status.HTTP_204_NO_CONTENT)
