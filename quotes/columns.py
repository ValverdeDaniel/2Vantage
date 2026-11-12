"""A plan's own columns as Activity keys (plan.md §3.7, O.3.2): "plan.<name>" beside its value keys.

The services record each changed column's before and after under these keys, and `revert.py` writes the "before"
back through `write`. Values are kept plain for JSON: dates as ISO text, links and package memberships as sorted id
lists (`REPLACES` and `PACKAGES` are many-to-many sets, written by their callers).
"""

from datetime import datetime

# Activity key → model attribute.
COLUMNS = {
    'plan.carrier': 'carrier',
    'plan.name': 'name',
    'plan.plan_number': 'plan_number',
    'plan.client_name': 'client_name',
    'plan.notes': 'notes',
    'plan.role': 'role',
    'plan.renews_id': 'renews_id',
    'plan.starred': 'starred',
    'plan.star_reason': 'star_reason',
    'plan.starred_by': 'starred_by_id',
    'plan.starred_at': 'starred_at',
    'plan.recommended': 'recommended',
    'plan.sold': 'sold',
    'plan.sold_at': 'sold_at',
    'plan.sort_order': 'sort_order',
    'plan.line': 'line',
    'plan.removed_at': 'removed_at',
    'plan.codes': 'codes',
    'plan.source_document': 'source_document_id',
    'plan.derived': 'derived',  # a priced version's record, re-priced by ✎ (F82; slice 35)
    'plan.bundling': 'bundling',  # the quote's rates already include the bundle (F78; slice 35)
    'plan.option_number': 'option_number',  # "Option n", cleared by a move to another line (J159; slice 25)
    'plan.pair_of': 'pair_of_id',  # the first half of a pair printed as one column (D-219, J15; slice 33)
}
REPLACES = 'plan.replaces_ids'
PACKAGES = 'plan.package_ids'
DATES = {'plan.starred_at', 'plan.sold_at', 'plan.removed_at'}
STAR = ('plan.starred', 'plan.star_reason', 'plan.starred_by', 'plan.starred_at')
LINKS = ('plan.role', 'plan.renews_id', REPLACES)


def read(plan, key, replaces=None):
    """The column's value as Activity keeps it. `replaces` is the plan's replaced ids when `key` is REPLACES."""
    if key == REPLACES:
        return sorted(replaces or [])
    if key == PACKAGES:
        return sorted(plan.package_ids)
    value = getattr(plan, COLUMNS[key])
    return value.isoformat() if isinstance(value, datetime) else value


def write(plan, key, value):
    """Set a column from its Activity value (REPLACES and PACKAGES are the caller's: they are many-to-many sets)."""
    if key in DATES and value is not None:
        value = datetime.fromisoformat(value)
    setattr(plan, COLUMNS[key], value)


def snapshot(plan, keys, replaces=None):
    return {key: read(plan, key, replaces) for key in keys}


def diff(before, after):
    """{key: [before, after]} for the keys that changed."""
    return {key: [before[key], after[key]] for key in before if before[key] != after[key]}


def fields_of(keys):
    """The model fields a save of these keys writes."""
    return sorted({COLUMNS[key].removesuffix('_id') for key in keys if key in COLUMNS})
