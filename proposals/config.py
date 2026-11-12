"""The proposal configuration by path (plan.md §6.11, §7.12; J.6.2, J.6.3, J19, J20). Pure.

A write is `{path: value}`: "title", "reasons.medical", "lines.dental.rows", "lines.medical.parts.cost",
"output.layout". Each path is cleaned on its own (`clean`), merged into the stored config (`merge`) so two people
writing different paths never undo each other, and owned by one builder card (`card_of`), whose completed mark the
write clears (J19). Ported from old Vantage 891f1b3 `pipeline/composition.py` (`clean_composition`,
`clean_table_note`, `merge_config`): the old one-key-at-a-time merge becomes a merge by path.

A path not listed here is not a setting yet: it answers 400 until the slice that owns its card adds it (the summary,
markets, experience, team and the rest of `output`, slices 26 and 34; `lines.<line>.merged`, slice 33).
Values left at their default are removed from the stored config, so "unset" and "default" never differ.
"""

import copy
import re

from deals import lines

from . import catalog, pages

TEXT_LIMITS = {'title': catalog.MAX_TITLE, 'intro': catalog.MAX_TEXT, 'recommendation': catalog.MAX_TEXT}
LINE_KEYS = ('parts', 'rows', 'card_stats', 'table_note')
UNKNOWN = '"{path}" is not a proposal setting.'


class Invalid(ValueError):
    """A value or path refused; the message is shown as is (400)."""

    def __init__(self, path, message):
        self.path, self.message = path, message
        super().__init__(message)


def _line(path, key):
    if key not in lines.BY_KEY:
        raise Invalid(path, f'"{key}" is not a line of coverage.')
    return key


def _text(path, value, limit):
    if value is None:
        return ''
    if not isinstance(value, str):
        raise Invalid(path, 'Send text.')
    return value.strip()[:limit]


def table_note(value):
    """Spaces collapsed within each line, blank lines dropped, ≤4 lines and ≤600 characters ('' is no note)."""
    rows = [' '.join(part.split()) for part in value.replace('\r\n', '\n').split('\n')]
    rows = [row for row in rows if row][: catalog.TABLE_NOTE_LINES]
    return '\n'.join(rows)[: catalog.TABLE_NOTE_MAX].strip()


def _keys(path, value, line, limit, allowed):
    """A de-duplicated list of the line's field keys (an unknown one is dropped, as the old cleaner did), or None."""
    if value is None:
        return None
    if not isinstance(value, list):
        raise Invalid(path, 'Send a list of field keys, or null.')
    out = []
    for item in value:
        key = str(item or '').strip()
        if key in allowed and key not in out:
            out.append(key)
    return out[:limit]


def _order(path, value):
    if value is None:
        return []
    if not isinstance(value, list):
        raise Invalid(path, 'Send the lines in order.')
    out = []
    for key in value:
        if _line(path, str(key)) not in out:
            out.append(str(key))
    return out


def _next_steps(path, value):
    if value is None:
        return []
    if not isinstance(value, list):
        raise Invalid(path, 'Send the next steps as a list of {date, text}.')
    steps = []
    for item in value[: catalog.MAX_NEXT_STEPS]:
        if not isinstance(item, dict):
            raise Invalid(path, 'Each next step is {date, text}.')
        text = str(item.get('text') or '').strip()[: catalog.MAX_STEP_TEXT]
        when = str(item.get('date') or '').strip()
        if when and not re.fullmatch(r'\d{4}-\d{2}-\d{2}', when):
            raise Invalid(path, f'"{when}" is not a date (YYYY-MM-DD).')
        if text:
            steps.append({'date': when, 'text': text})
    return steps


def clean(path, value):
    """(the stored path, the cleaned value) for one write; `Invalid` with a sentence otherwise. A cleaned value equal
    to the default (DEFAULTS) removes the path."""
    parts = path.split('.')
    head = parts[0]
    if head in TEXT_LIMITS and len(parts) == 1:
        return path, _text(path, value, TEXT_LIMITS[head])
    if head == 'reasons' and len(parts) == 2:
        _line(path, parts[1])
        return path, _text(path, value, catalog.MAX_TEXT)
    if path == 'order':
        return path, _order(path, value)
    if path == 'next_steps':
        return path, _next_steps(path, value)
    if path == 'output.layout':
        if value not in pages.LAYOUTS:
            raise Invalid(path, f'The layout is one of: {", ".join(pages.LAYOUTS)}.')
        return path, value
    if head == 'lines' and len(parts) >= 3:
        return path, _line_setting(path, _line(path, parts[1]), parts[2:], value)
    raise Invalid(path, UNKNOWN.format(path=path))


def _line_setting(path, line, rest, value):
    name = rest[0]
    if name == 'parts' and len(rest) == 2 and rest[1] in catalog.PART_KEYS:
        if not isinstance(value, bool):
            raise Invalid(path, 'Send true or false.')
        return value
    if len(rest) != 1:
        raise Invalid(path, UNKNOWN.format(path=path))
    if name == 'rows':
        allowed = set(catalog.client_keys(line))
        return _keys(path, value, line, catalog.MAX_ROWS, allowed)
    if name == 'card_stats':
        allowed = set(catalog.client_keys(line))
        stats = _keys(path, value, line, catalog.MAX_CARD_STATS, allowed)
        return stats or None  # an empty pick is the standard set again
    if name == 'table_note':
        return table_note(_text(path, value, catalog.TABLE_NOTE_MAX * 2))
    raise Invalid(path, UNKNOWN.format(path=path))


def default(path):
    """What an unset path reads as."""
    parts = path.split('.')
    if path in ('order', 'next_steps'):
        return []
    if parts[0] == 'lines' and len(parts) == 4 and parts[2] == 'parts':
        return True
    if parts[0] == 'lines' and parts[-1] in ('rows', 'card_stats'):
        return None
    if path == 'output.layout':
        return pages.DEFAULT_LAYOUT
    return ''


def get(stored, path):
    node = stored
    for part in path.split('.'):
        if not isinstance(node, dict) or part not in node:
            return default(path)
        node = node[part]
    return node


def place(stored, path, value):
    parts = path.split('.')
    node = stored
    for part in parts[:-1]:
        node = node.setdefault(part, {})
    node[parts[-1]] = value


def drop(stored, path):
    """Remove the path and every dict it leaves empty."""
    parts = path.split('.')
    trail, node = [], stored
    for part in parts[:-1]:
        if not isinstance(node.get(part), dict):
            return
        trail.append((node, part))
        node = node[part]
    node.pop(parts[-1], None)
    for parent, part in reversed(trail):
        if parent[part]:
            break
        parent.pop(part)


def put(stored, path, value):
    """`stored` with one path set (or removed when the value is its default), in place."""
    if value == default(path):
        drop(stored, path)
    else:
        place(stored, path, value)


def expand(changes):
    """A write's {path: value}, with "reasons" as a whole {line: text} spread into its paths."""
    if not isinstance(changes, dict) or not changes:
        raise Invalid('', 'Send the settings to change, {path: value}.')
    out = {}
    for path, value in changes.items():
        path = str(path)
        if path == 'reasons':
            if not isinstance(value, dict):
                raise Invalid(path, 'Send {line: text}.')
            out.update({f'reasons.{line}': text for line, text in value.items()})
        else:
            out[path] = value
    return out


def merge(stored, changes):
    """(the new config, {path: [before, after]} of the paths that change). `stored` is left as it was."""
    merged = copy.deepcopy(stored or {})
    diff = {}
    for path, raw in expand(changes).items():
        path, value = clean(path, raw)
        before = get(merged, path)
        if before == value:
            continue
        put(merged, path, value)
        diff[path] = [before, value]
    return merged, diff


def card_of(path):
    """(card, line or None) owning a path, or None when no card does (the line order)."""
    parts = path.split('.')
    head = parts[0]
    if head in ('title', 'intro'):
        return 'cover', None
    if head == 'recommendation':
        return 'summary', None  # the deal-wide words print in the glance notes (J57)
    if head == 'reasons':
        return 'quotes', parts[1]
    if head == 'lines':
        return 'rows', parts[1]
    if head == 'next_steps':
        return 'next_steps', None
    if head == 'output':
        return 'output', None
    return None


def line_spec(stored, line):
    """One line's resolved settings: parts, rows (None = every row with a value), card stats (None = the standard
    set), table note."""
    return {
        'parts': {key: get(stored, f'lines.{line}.parts.{key}') for key in catalog.PART_KEYS},
        'rows': get(stored, f'lines.{line}.rows'),
        'card_stats': get(stored, f'lines.{line}.card_stats'),
        'table_note': get(stored, f'lines.{line}.table_note'),
    }


def ordered(stored, keys):
    """`keys` (lines) in the producer's order; a line the order forgot keeps its place after, in §4.1 order."""
    order = get(stored, 'order')
    index = {key: i for i, key in enumerate(order)}
    return sorted(keys, key=lambda key: (index.get(key, len(order)), lines.LINE_KEYS.index(key)))
