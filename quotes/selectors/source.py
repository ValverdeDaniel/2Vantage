"""One plan value's full source, for ↗ "open in file" (plan.md §7.8; E18, E31; F.6). Read only.

The comparison is compact and names only a cell's document (`d`); the station asks for the rest when a value opens:
the value as stored, where it was read (`page` or `cell`, the reader's `line`, the locator's `loc`), the words that
pick the plan's column in a file (`hint`: carrier and name) and the file bar's "Opened to show <row · plan>" (`what`).
"""

from .. import fields

ENTRY = ('origin', 'doc', 'page', 'cell', 'line', 'loc', 'low', 'mark', 'confirmed')


def value_source(plan, key):
    """{plan_id, key, label, value, hint, what, source}; `source` is None for a value with no entry."""
    entry = plan.sources.get(key) if isinstance(plan.sources.get(key), dict) else None
    label = fields.BY_KEY[key]['label']
    hint = ' '.join(part for part in (plan.carrier, plan.name) if part)
    return {
        'plan_id': plan.id,
        'key': key,
        'label': label,
        'value': plan.values.get(key, ''),
        'hint': hint,
        'what': f'{label} · {hint}',
        'source': {name: entry.get(name) for name in ENTRY} if entry else None,
    }
