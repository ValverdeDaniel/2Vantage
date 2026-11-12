"""Values that live in JSON on their row, with one `sources` entry per key (plan.md §3.7, O.3.1).

`apply()` is the only writer of a row's values and sources. Its rules (A31–A33, E66, F141):
- a value equal to the stored one (after cleaning) changes nothing: not the value, not its source;
- a changed value gets a new source entry, so a review `mark` or a `confirmed` never outlives its value;
- a typed value over a read one keeps `doc`, `page`, `cell`, `line` and `read_value` (the ↗ still opens the file)
  and drops `low` and `loc`;
- '' clears the value and its source entry; None puts back the value that was read (`read_value`).
Callers load the row with `locked()` inside their transaction, so two saves to different keys of one row never
erase each other, and record the returned before/after in Activity.
"""

from django.db import transaction

from . import clock

ORIGINS = ('typed', 'relay', 'client', 'ai', 'import', 'prefill', 'sale', 'in_force', 'agency')
ENTRY_KEYS = ('doc', 'page', 'cell', 'line', 'link', 'low', 'loc', 'mark', 'confirmed', 'read_value')
KEPT_UNDER_TYPED = ('doc', 'page', 'cell', 'line', 'read_value')
LINE_LIMIT = 300
READ_ORIGIN = 'ai'  # read_value is kept only on plans the reader made (F141)


def locked(model, pk):
    """The row, locked for the rest of the current transaction."""
    if not transaction.get_connection().in_atomic_block:
        raise RuntimeError('locked() must run inside transaction.atomic()')
    return model.objects.select_for_update().get(pk=pk)


def source(origin, user=None, **extra):
    """One source entry: {origin, by, at} plus any of ENTRY_KEYS that are not None."""
    if origin not in ORIGINS:
        raise ValueError(f'Unknown origin: {origin}')
    unknown = set(extra) - set(ENTRY_KEYS)
    if unknown:
        raise ValueError(f'Not a source key: {", ".join(sorted(unknown))}')
    entry = {'origin': origin, 'by': getattr(user, 'id', None), 'at': clock.now().isoformat()}
    entry.update({key: value for key, value in extra.items() if value is not None})
    if 'line' in entry:
        entry['line'] = str(entry['line'])[:LINE_LIMIT]
    return entry


def _new_entry(make_source, key, old):
    entry = dict(make_source(key) if callable(make_source) else make_source)
    if entry.get('origin') == 'typed':
        for name in KEPT_UNDER_TYPED:
            if name in old and name not in entry:
                entry[name] = old[name]
    return entry


def _read_back(old):
    """The entry for a value put back to what was read: the read's origin, with the file it came from."""
    entry = source(READ_ORIGIN)
    entry.update({name: old[name] for name in KEPT_UNDER_TYPED if name in old})
    return entry


def apply(values, sources, changes, make_source):
    """Apply {key: cleaned value | '' | None} to the two dicts in place.

    `make_source` is a source entry, or a function key -> entry, for the keys that change. Returns
    {key: [before, after]} for the keys that actually changed; None stands for "no value".
    """
    changed = {}
    for key, value in changes.items():
        before = values.get(key)
        old = sources.get(key) or {}
        if value is None:
            value = old.get('read_value')
            if value in (None, '') or value == before:
                continue
            entry = _read_back(old)
        elif value == '':
            if key not in values:
                continue
            values.pop(key)
            sources.pop(key, None)
            changed[key] = [before, None]
            continue
        elif value == before:
            continue
        else:
            entry = _new_entry(make_source, key, old)
        values[key] = value
        sources[key] = entry
        changed[key] = [before, value]
    return changed
