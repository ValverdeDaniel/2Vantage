"""One census value's full source, for ↗ and the Documents station (plan.md §7.7, §10.7; E18, E43; slice 65). Read
only.

The station asks a value's owner where it was read (O.3.1, `useValueSource`): a cell the census import read opens at
its own cell of the file ("Census!C7"), a typed one on the file it kept (E66). The value is the one the roster shows
(an SSN masked to its last four, OQ16), and `what`, the file bar's "Opened to show …", names the column only, never
the person (rule 10; the old station labelled census rows by position, never by name).
"""

from .. import fields
from .roster import shown_values

ENTRY = ('origin', 'doc', 'page', 'cell', 'line', 'loc', 'low', 'mark', 'confirmed')


def value_source(member, key):
    """{member_id, key, label, value, hint, what, source}; `source` is None for a value with no entry."""
    entry = member.sources.get(key) if isinstance(member.sources.get(key), dict) else None
    label = fields.BY_KEY[key]['label']
    return {
        'member_id': member.id,
        'key': key,
        'label': label,
        'value': shown_values({key: member.values.get(key, '')})[key],
        'hint': '',
        'what': label,
        'source': {name: entry.get(name) for name in ENTRY} if entry else None,
    }
