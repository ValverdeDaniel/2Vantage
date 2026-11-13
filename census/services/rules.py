"""The deal's own rule for a census column (plan.md §5.3.3, §6.6 `CensusSettings.rules`; C27, OQ17; old 891f1b3
`census_review.set_requirements`): Auto, Required or Waived. Written from Review & requests' Census board (slice 57),
its only writer (plan.md §7.7).

`set_rules(user, deal_id, changes)`: `changes` {column: 'auto' | 'required' | 'waived'}. Waived beats every other reason
a cell is required, carrier files included; Required beats them too; Auto lets §5.3.3's steps decide (`fields.
is_required`). Never SSN's Required (it is never asked of a client, OQ16) — Waived and Auto are fine. Lock order: the
Deal, then the CensusSettings row (created on this first write), then CensusFacts, rewritten in the same transaction
since what is required moves its counts. One Activity row (area census, action `rules`, target `census_rules:<deal>`,
before and after per column: a rule is not a value, so it is revertible, `revert`). An unchanged rule writes nothing.
"""

from django.db import transaction
from rest_framework.exceptions import ValidationError

from deals import activity

from .. import facts, fields
from ..models import CensusSettings
from . import rows

RULES = 'rules'
NOTHING = 'Send the rules as an object of census columns.'


def target(deal_id):
    return f'census_rules:{deal_id}'


def _clean(changes):
    if not isinstance(changes, dict) or not changes:
        raise ValidationError({'rules': [NOTHING]})
    allowed = [key for key, _label in fields.RULES]
    out, errors = {}, []
    for key, rule in changes.items():
        if key not in fields.BY_KEY:
            errors.append('Some of those are not census columns.')
        elif rule not in allowed:
            errors.append(f'Name the rule as one of: {", ".join(allowed)}.')
        elif key in fields.SSN_KEYS and rule == fields.REQUIRED:
            errors.append('SSN is never required: a client is never asked for it.')
        else:
            out[key] = rule
    if errors:
        raise ValidationError({'rules': list(dict.fromkeys(errors))})
    return out


def _locked(deal_id):
    CensusSettings.objects.get_or_create(deal_id=deal_id)
    return CensusSettings.objects.select_for_update().get(deal_id=deal_id)


def _put(row, diff):
    current = dict(row.rules or {})
    for key, (_before, after) in diff.items():
        if after == fields.AUTO:
            current.pop(key, None)
        else:
            current[key] = after
    row.rules = current
    row.save(update_fields=['rules', 'updated_at'])


@transaction.atomic
def set_rules(user, deal_id, changes):
    """({column: [before, after]} written, Activity row or None)."""
    wanted = _clean(changes)
    deal = rows.lock_deal(deal_id)
    row = _locked(deal_id)
    current = row.rules or {}
    diff = {key: [current.get(key, fields.AUTO), rule] for key, rule in wanted.items()}
    diff = {key: pair for key, pair in diff.items() if pair[0] != pair[1]}
    if not diff:
        return {}, None
    _put(row, diff)
    facts.refresh(deal_id)
    count = len(diff)
    summary = f'Changed what this deal needs on {count} census column{"" if count == 1 else "s"}'
    change = activity.change(target(deal_id), diff)
    return diff, activity.record(deal, user, rows.AREA, RULES, summary, changes=[change])


def revert(row, user):  # noqa: ARG001 (the reverters' signature)
    """Put a `rules` row's columns back (census/revert.py; the Deal is already locked). Refuses after a later change."""
    later = activity.later_keys(row)
    if later:
        keys = sorted(later)
        raise activity.changed_since([fields.label(key) for _target, key in keys], [key for _target, key in keys])
    settings = _locked(row.deal_id)
    written = []
    for entry in row.changes:
        diff = {key: [after, before] for key, (before, after) in entry['k'].items()}
        _put(settings, diff)
        written.append(activity.change(entry['t'], diff))
    facts.refresh(row.deal_id)
    return written
