"""Writing values that live in JSON on their row, with one `sources` entry each (plan.md §3.7).

Rules:
- writing a value equal to the stored one (after cleaning) changes nothing — not the value, not its source;
- writing a changed value replaces its whole source entry;
- clearing a value removes the value and its source.
Callers load the row with `select_for_update()` inside their transaction (`locked`), so two saves to different
keys of one row never erase each other.
"""

from django.db import transaction

from . import clock


def locked(model, pk):
    """The row, locked for the rest of the current transaction."""
    if not transaction.get_connection().in_atomic_block:
        raise RuntimeError('locked() must run inside transaction.atomic()')
    return model.objects.select_for_update().get(pk=pk)


def source(origin, user=None, **extra):
    entry = {'origin': origin, 'by': getattr(user, 'id', None), 'at': clock.now().isoformat()}
    entry.update({key: value for key, value in extra.items() if value is not None})
    return entry


def apply(values, sources, changes, make_source):
    """Apply {key: cleaned value or ''} to the two dicts in place. Returns the keys that actually changed.

    `make_source(key)` builds the source entry for a changed key.
    """
    changed = []
    for key, value in changes.items():
        if value in ('', None):
            if key in values:
                values.pop(key, None)
                sources.pop(key, None)
                changed.append(key)
            continue
        if values.get(key) == value:
            continue
        values[key] = value
        sources[key] = make_source(key)
        changed.append(key)
    return changed
