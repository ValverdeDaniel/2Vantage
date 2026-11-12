"""Reading ids and lines from a request (plan.md §3.6): a bad one answers 400 with a sentence, never 500."""

from rest_framework.exceptions import ValidationError

from deals import lines


def plan_id(raw, name='plan_id'):
    if isinstance(raw, bool):
        raise ValidationError({name: ['Give a plan id.']})
    try:
        return int(raw)
    except (TypeError, ValueError) as exc:
        raise ValidationError({name: ['Give a plan id.']}) from exc


def optional_id(raw, name):
    return None if raw in (None, '') else plan_id(raw, name)


def plan_ids(raw, name='plan_ids'):
    if not isinstance(raw, list):
        raise ValidationError({name: ['Give a list of plan ids.']})
    return [plan_id(item, name) for item in raw]


def line(request, required=True):
    key = request.query_params.get('line') or request.data.get('line')
    if required and key not in lines.BY_KEY:
        raise ValidationError({'line': ['Give a line of coverage.']})
    return key
