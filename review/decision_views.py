"""The review queues and their decisions, staff side (plan.md §7.13; L.6 endpoints; slice 55). Thin: parse → selector or
service → answer. Ids come from the path as integers (B4); a bad query or body answers 400, never 500.

- GET  deals/{id}/review/queue/?surface=intake|census|questionnaire&phase=to_review|in_progress|going_back&group=
  &page= → the queue (selectors/queue.py). Writes nothing; `private, no-store` (member data rides it).
- POST deals/{id}/review/approve/ {refs: [ref]} | {surface, ready_only?, include_idle?} → {approved: [ref],
  activity_ids: [id]}.
- POST deals/{id}/review/reject/ {refs} → {rejected: [ref], activity_ids} ("Keep ours").
- POST deals/{id}/review/undo/ {refs} → {undone: [ref], activity_ids}: approvals taken back; 409 {detail, keys} when an
  answer changed since it was approved.
A ref is `intake:<key>`, `intake:block:<block>`, `census:<member id>:<column>`, `census:<member id>:*` (a person a
client added) or `q:<form>:<slot>` (a questionnaire answer, slice 58); 400 {refs: [the refused ones]}.
"""

from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .rules import items as item_rules
from .selectors import queue as queue_selector
from .services import decisions
from .views import _body, _deal

GROUP_LIMIT = 200


def _page(raw):
    if raw in (None, ''):
        return 1
    if not str(raw).isdigit() or len(str(raw)) > 6:
        raise ValidationError({'page': ['Send the page as a number.']})
    return int(raw)


class QueueView(APIView):
    def get(self, request, pk):
        deal = _deal(pk)
        query = request.query_params
        surface = query.get('surface') or 'census'
        if surface not in queue_selector.SURFACES:
            raise ValidationError({'surface': [decisions.NO_SURFACE]})
        phase = query.get('phase') or item_rules.TO_REVIEW
        if phase not in item_rules.PHASES:
            raise ValidationError({'phase': [f'One of {", ".join(item_rules.PHASES)}.']})
        group = (query.get('group') or '')[:GROUP_LIMIT]
        found = queue_selector.queue(deal, surface, phase=phase, group=group, page=_page(query.get('page')))
        response = Response(found)
        response['Cache-Control'] = 'private, no-store'
        return response


def _ids(decided):
    return [row.id for row in decided.activity]


class ApproveView(APIView):
    def post(self, request, pk):
        deal = _deal(pk)
        data = _body(request)
        surface = data.get('surface')
        if surface is not None:
            for flag in ('ready_only', 'include_idle'):
                if flag in data and not isinstance(data[flag], bool):
                    raise ValidationError({flag: ['Send true or false.']})
            decided = decisions.approve(
                request.user,
                deal.id,
                refs=data.get('refs'),
                surface=surface,
                ready_only=data.get('ready_only', True),
                include_idle=data.get('include_idle', False),
            )
        else:
            decided = decisions.approve(request.user, deal.id, refs=data.get('refs'))
        return Response({'approved': decided.refs, 'activity_ids': _ids(decided)})


class RejectView(APIView):
    def post(self, request, pk):
        deal = _deal(pk)
        decided = decisions.reject(request.user, deal.id, _body(request).get('refs'))
        return Response({'rejected': decided.refs, 'activity_ids': _ids(decided)})


class UndoView(APIView):
    def post(self, request, pk):
        deal = _deal(pk)
        decided = decisions.undo(request.user, deal.id, _body(request).get('refs'))
        return Response({'undone': decided.refs, 'activity_ids': _ids(decided)})
