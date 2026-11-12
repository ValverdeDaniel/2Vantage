"""Every value a read proposes, found in its own file before it waits for review (plan.md §10.7; E79, E81, D95).

The read's values are looked for exactly as "Check this file" looks for a landed value (`locate_hooks.query_for`, the
same rules), in the bytes the read already holds: each value's change-set entry gets its `loc` (found, derived,
weak, absent or "check by eye") and, when the file does not print it, `low` says so (D95). Nothing is stored on a
plan: the answers ride in the change set and land with it (slice 19).
"""

from types import SimpleNamespace

from deals import clock
from documents import locate

from ..locate_hooks import query_for

NOT_IN_FILE = 'Not found in the file.'
LOOSE = 'Found only loosely in the file: check it by eye.'


def locate_items(items, files):
    by_doc = {}
    for item in items:
        plan = SimpleNamespace(carrier=item.get('carrier', ''), name=item.get('name', ''))
        for value in item.get('values') or []:
            entry = {'page': value.get('page'), 'line': value.get('line')}
            by_doc.setdefault(value.get('doc'), []).append((value, query_for(plan, value['key'], value['new'], entry)))
    stamp = {'v': locate.VERSION, 'at': clock.now().isoformat()}
    for file in files:
        asked = by_doc.get(file.id)
        if not asked:
            continue
        index, why = locate.open_index(f'file{file.extension}', file.raw, file.page_count)
        results = locate.locate_all(index, why, [query for _value, query in asked])
        for (value, _query), result in zip(asked, results, strict=True):
            value['loc'] = {**result.as_dict(), **stamp}
            if not value.get('low'):
                if result.state == locate.ABSENT:
                    value['low'] = NOT_IN_FILE
                elif result.state == locate.WEAK:
                    value['low'] = LOOSE
