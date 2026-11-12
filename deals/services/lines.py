"""The lines to quote, `Deal.requested_lines` (plan.md §5.2, §7.3; B17, B32).

`set_lines` is the only writer of the field, and only intake's `set_intent` calls it, inside its own transaction, so
the shopping list and the coverage intent never disagree (the old app had three writers). It records no Activity of
its own: `set_intent` records one row holding this change beside the coverage rows it changed.
"""

from rest_framework.exceptions import ValidationError

from .. import lines
from ..models import Deal
from ..values import locked

DOOR = 'Change the lines to quote through deals/{id}/intake/intent/.'


def clean_lines(raw):
    """A list of line keys, in §4.1's order and de-duplicated. A bad list is a 400."""
    if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
        raise ValidationError({'requested_lines': ['Lines must be a list of line keys.']})
    unknown = [key for key in raw if key not in lines.BY_KEY]
    if unknown:
        raise ValidationError({'requested_lines': [f'Unknown line: {", ".join(unknown)}']})
    return [key for key in lines.LINE_KEYS if key in raw]


def set_lines(deal_id, keys):
    """Write the deal's lines to quote; returns {'requested_lines': [before, after]}, or {} when unchanged.

    Runs inside the caller's transaction and locks the Deal row (the caller has usually locked it already)."""
    deal = locked(Deal, deal_id)
    keys = clean_lines(list(keys))
    if keys == list(deal.requested_lines or []):
        return {}
    before = list(deal.requested_lines or [])
    deal.requested_lines = keys
    deal.save(update_fields=['requested_lines', 'updated_at'])
    return {'requested_lines': [before, keys]}


def refuse_lines(deal_id):
    """The 400 for a door that no longer takes `requested_lines` (POST clients/, PATCH deals/{id}/; slice 11)."""
    raise ValidationError({'requested_lines': [DOOR.replace('{id}', str(deal_id) if deal_id else '<id>')]})
