"""Before and after of a row's fields, for Activity's `changes` (plan.md §3.7). Owners are user ids, dates ISO text."""


def _plain(value):
    return value.isoformat() if hasattr(value, 'isoformat') else value


def snapshot(row, fields):
    return {field.removesuffix('_id'): _plain(getattr(row, field)) for field in fields}


def diff(before, after):
    """{key: [before, after]} for the keys that changed."""
    return {key: [before[key], after[key]] for key in before if before[key] != after[key]}
