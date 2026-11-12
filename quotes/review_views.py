"""The review station's plan values and their marks (plan.md §7.8, §10.7; E.6, E34, E48, E52–E58, E85–E89, F63–F67):

- `GET deals/{id}/plans/sources/?documents=1,2&bucket=&page=` → the List's rows, worst first, with the bucket counts,
  the strip's warning counts and the quality headline (`selectors/review.py`). Reads only.
- `POST deals/{id}/plans/marks/` `{action, refs | plan_ids | document_ids}` → what changed: each value's new marks and
  compact cell flags, each plan's open-warning count, and the Activity row Undo reverts (`services/review.py`).
  Past `VALUES_CAP` values the answer says `truncated` and lists none: the screen refetches instead (E53).
Bad ids, lines or actions answer 400 with a sentence; a refusal 409.
"""

from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from deals.models import Deal
from documents import review_rules

from . import facts
from .selectors.plans import mark_word
from .selectors.review import source_rows
from .services import review

VALUES_CAP = 2000


def _id_list(raw, name):
    parts = [part.strip() for part in str(raw or '').split(',') if part.strip()]
    if not parts or not all(part.isdigit() and int(part) <= 2**63 - 1 for part in parts):
        raise ValidationError({name: ['Give a list of ids.']})
    return [int(part) for part in parts]


def _page(raw):
    if raw in (None, ''):
        return 1
    if not str(raw).isdigit() or not 1 <= int(raw) <= 100000:
        raise ValidationError({'page': ['Give a page number.']})
    return int(raw)


class SourcesView(APIView):
    def get(self, request, pk):
        deal = get_object_or_404(Deal, pk=pk)
        params = request.query_params
        documents = _id_list(params['documents'], 'documents') if params.get('documents') else None
        bucket = params.get('bucket') or ''
        if bucket and bucket not in review_rules.BUCKET_KEYS:
            raise ValidationError({'bucket': ['Give one of the List’s buckets.']})
        return Response(source_rows(deal, documents, bucket, _page(params.get('page'))))


def _stamp(entry, key):
    stamp = (entry or {}).get(key)
    return {'by': stamp.get('by'), 'at': stamp.get('at'), 'state': stamp.get('state')} if stamp else None


def _value(plan, key, status):
    entry = plan.sources.get(key)
    cell = {}
    if status.get(key):
        cell['s'] = status[key]
    if mark_word(entry):
        cell['m'] = mark_word(entry)
    return {
        'ref': f'plan:{plan.id}:{key}',
        'plan_id': plan.id,
        'key': key,
        'cell': cell,
        'mark': _stamp(entry, 'mark'),
        'confirmed': _stamp(entry, 'confirmed'),
        'open': review_rules.open_warning(entry),
        'potential': review_rules.potential_error(entry),
        'dealt': review_rules.is_dealt(entry),
        'bucket': review_rules.review_bucket(entry),
    }


class MarksView(APIView):
    def post(self, request, pk):
        deal = get_object_or_404(Deal, pk=pk)
        data = request.data if isinstance(request.data, dict) else {}
        result = review.mark_values(
            request.user,
            deal,
            data.get('action'),
            refs=data.get('refs'),
            plan_ids=data.get('plan_ids'),
            document_ids=data.get('document_ids'),
        )
        statuses = {plan.id: facts.statuses(plan.line, plan.values, plan.sources) for plan in result.plans}
        truncated = len(result.values) > VALUES_CAP
        return Response(
            {
                'action': result.action,
                'changed': len(result.values),
                'activity_id': getattr(result.row, 'id', None),
                'truncated': truncated,
                'values': [] if truncated else [_value(plan, key, statuses[plan.id]) for plan, key in result.values],
                'plans': [
                    {
                        'id': plan.id,
                        'flags': plan.flags,
                        'incomplete': facts.plan_facts(plan.line, plan.values, statuses[plan.id])['incomplete'],
                    }
                    for plan in result.plans
                ],
            }
        )
