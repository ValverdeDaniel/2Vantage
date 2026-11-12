"""What the board says about one plan, worked out on the server (plan.md §5.4; F62, F122, D-051). Pure.

- `statuses`: per field, `missing` (required and blank) or `to_check` (an open warning); blank and ok keys are left
  out. A plan with a quoted premium and no tier rate at all is not missing its tier rates (age-banded medical, §5.5).
- `open_warning`: the one rule until `documents.review_rules.open_warning` (slice 17, OQ28): a value marked
  ⚑ Needs checking, or one Claude read that nobody has approved or ignored.
- `plan_facts`: `incomplete` (no total, a key field of the line blank, or a key field to check: what "Hide incomplete
  data" hides), `flags` (open warnings on the plan) and `compliance` (the tests the carrier says it fails: minimum
  value and Medicare Part D; a blank answer is not a failure).
`facts.incumbent` (F144) arrives with intake in slice 11.
"""

from functools import cache

from deals import lines

from . import fields

# The fields that make a plan complete, per field set (the old Advisor's KEY_FIELDS_BY_SET).
KEY_FIELDS = {
    'medical': ['deductible_single', 'oop_max_single', 'network', 'plan_type'],
    'dental': ['den_annual_max', 'den_deductible', 'network', 'plan_type'],
    'vision': ['vis_exam_copay', 'vis_frame_allowance', 'network', 'plan_type'],
    'life': ['life_schedule', 'life_guarantee_issue', 'unit_rate'],
    'disability': ['dis_elimination', 'dis_benefit_pct', 'dis_max_benefit', 'unit_rate'],
    'generic': ['benefit_summary', 'plan_type', 'unit_rate'],
    'stop_loss': ['sl_spec_deductible', 'sl_spec_rate', 'sl_agg_factor', 'sl_agg_corridor'],
}
COMPLIANCE = ('minimum_value', 'part_d_creditable')


@cache
def _line_keys(line_key):
    return tuple(fields.keys_for(line_key))


@cache
def _key_fields(line_key):
    has = set(_line_keys(line_key))
    return tuple(
        key for key in KEY_FIELDS.get(lines.BY_KEY[line_key]['field_set'], KEY_FIELDS['generic']) if key in has
    )


def open_warning(entry):
    mark = ((entry or {}).get('mark') or {}).get('state')
    if mark == 'check':
        return True
    return (entry or {}).get('origin') == 'ai' and not entry.get('confirmed') and mark != 'ignored'


def statuses(line_key, values, sources):
    quoted_only = values.get('group_premium_monthly') and not any(values.get(k) for k in fields.TIER_RATE_KEYS)
    status = {}
    for key in _line_keys(line_key):
        if values.get(key) in (None, ''):
            exempt = quoted_only and key in fields.TIER_RATE_KEYS
            if fields.BY_KEY[key]['required'] and not exempt:
                status[key] = 'missing'
        elif open_warning(sources.get(key)):
            status[key] = 'to_check'
    return status


def plan_facts(line_key, values, status, monthly):
    """Judged against the fields the line has: a dental plan has no deductible and out-of-pocket max to miss."""
    keys = _key_fields(line_key)
    blank = any(values.get(key) in (None, '') for key in keys)
    doubtful = any(status.get(key) == 'to_check' for key in keys)
    return {
        'incomplete': monthly is None or blank or doubtful,
        'flags': sum(1 for state in status.values() if state == 'to_check'),
        'compliance': [key for key in COMPLIANCE if str(values.get(key) or '').strip().lower() == 'no'],
    }
