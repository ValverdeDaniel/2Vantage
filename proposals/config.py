"""The proposal configuration by path (plan.md §6.11, §7.12; J.6.2, J.6.3, J19, J20). Pure.

A write is `{path: value}`: "title", "reasons.medical", "lines.dental.rows", "output.pages.team", "summary.blocks",
"markets.lines.medical.notes.cigna". Each path is cleaned on its own (`clean`, with `cleaners`), merged into the
stored config (`merge`) so two people writing different paths never undo each other, and owned by one builder card
(`card_of`), whose completed mark the write clears (J19). Ported from old Vantage 891f1b3 `pipeline/composition.py`
(`clean_composition`, `merge_config`): the old one-key-at-a-time merge becomes a merge by path.

A path not listed here is not a setting yet: it answers 400 until the slice that owns its card adds it (the cover,
pictures and team, slice 34; `lines.<line>.merged`, slice 33). Values left at their default are removed from the
stored config, so "unset" and "default" never differ.
"""

import copy

from deals import lines

from . import catalog, pages
from . import cleaners as c
from .cleaners import Invalid

TEXT_LIMITS = {'title': catalog.MAX_TITLE, 'intro': catalog.MAX_TEXT, 'recommendation': catalog.MAX_TEXT}
UNKNOWN = '"{path}" is not a proposal setting.'
EVERY_LINE = '*'  # card_of's line for a deal-wide switch on a line card (Markets checked's Show it)


def _unknown(path):
    return Invalid(path, UNKNOWN.format(path=path))


def _output(path, rest, value):
    if rest == ['layout']:
        if value not in pages.LAYOUTS:
            raise Invalid(path, f'The layout is one of: {", ".join(pages.LAYOUTS)}.')
        return value
    if len(rest) == 1 and rest[0] in catalog.OUTPUT_SWITCHES:
        return c.switch(path, value)
    if rest == ['compare_slots']:
        return c.compare_slots(path, value)
    if len(rest) == 2 and rest[0] == 'pages' and rest[1] in catalog.PAGE_KEYS:
        return c.switch(path, value)
    raise _unknown(path)


def _markets(path, rest, value):
    if rest == ['on']:
        return c.market_switch(path, value)
    if len(rest) >= 3 and rest[0] == 'lines':
        c.line(path, rest[1])
        if rest[2:] == ['hidden']:
            return c.hidden_carriers(path, value)
        if len(rest) == 4 and rest[2] == 'notes':
            c.carrier_id(path, rest[3])
            return c.text(path, value, catalog.MAX_MARKET_NOTE)
    raise _unknown(path)


def _line_setting(path, line, rest, value):
    name = rest[0]
    if name == 'parts' and len(rest) == 2 and rest[1] in catalog.PART_KEYS:
        return c.switch(path, value)
    if len(rest) != 1:
        raise _unknown(path)
    if name == 'rows':
        return c.field_keys(path, value, catalog.MAX_ROWS, set(catalog.client_keys(line)))
    if name == 'card_stats':
        stats = c.field_keys(path, value, catalog.MAX_CARD_STATS, set(catalog.client_keys(line)))
        return stats or None  # an empty pick is the standard set again
    if name == 'table_note':
        return c.table_note(c.text(path, value, catalog.TABLE_NOTE_MAX * 2))
    raise _unknown(path)


def clean(path, value):
    """(the stored path, the cleaned value) for one write; `Invalid` with a sentence otherwise. A cleaned value equal
    to the default removes the path."""
    parts = path.split('.')
    head, rest = parts[0], parts[1:]
    if head in TEXT_LIMITS and not rest:
        return path, c.text(path, value, TEXT_LIMITS[head])
    if head == 'reasons' and len(rest) == 1:
        c.line(path, rest[0])
        return path, c.text(path, value, catalog.MAX_TEXT)
    if path == 'order':
        return path, c.order(path, value)
    if path == 'next_steps':
        return path, c.next_steps(path, value)
    if path == 'experience.summary':
        return path, c.text(path, value, catalog.MAX_TEXT)
    if path == 'experience.rows':
        return path, c.experience_rows(path, value)
    if path == 'summary.on':
        return path, c.switch(path, value)
    if path == 'summary.blocks':
        return path, c.summary_blocks(path, value)
    if head == 'output' and rest:
        return path, _output(path, rest, value)
    if head == 'markets' and rest:
        return path, _markets(path, rest, value)
    if head == 'lines' and len(rest) >= 2:
        return path, _line_setting(path, c.line(path, rest[0]), rest[1:], value)
    raise _unknown(path)


def default(path):
    """What an unset path reads as."""
    parts = path.split('.')
    if path in ('order', 'next_steps', 'experience.rows', 'summary.blocks'):
        return []
    if path == 'summary.on' or (parts[0] == 'output' and (parts[-1] in catalog.OUTPUT_SWITCHES or len(parts) == 3)):
        return True
    if parts[0] == 'lines' and len(parts) == 4 and parts[2] == 'parts':
        return True
    if parts[0] == 'lines' and parts[-1] in ('rows', 'card_stats'):
        return None
    if path == 'output.layout':
        return pages.DEFAULT_LAYOUT
    if path == 'output.compare_slots':
        return catalog.DEFAULT_COMPARE_SLOTS
    if path == 'markets.on':
        return None
    if parts[0] == 'markets' and parts[-1] == 'hidden':
        return []
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


CARD_BY_HEAD = {
    'title': 'cover',
    'intro': 'cover',
    'recommendation': 'summary',  # the deal-wide words print in the glance notes (J57)
    'next_steps': 'next_steps',
    'summary': 'summary',
    'experience': 'pages',
}


def card_of(path):
    """(card, line or None) owning a path, or None when no card does (the line order). Markets checked's Show it is
    deal-wide on a line card: it answers EVERY_LINE, and the write takes the card's mark off every line."""
    parts = path.split('.')
    head = parts[0]
    if head in CARD_BY_HEAD:
        return CARD_BY_HEAD[head], None
    if head == 'reasons':
        return 'quotes', parts[1]
    if head == 'lines':
        return 'rows', parts[1]
    if head == 'output':
        return ('pages' if parts[1:2] == ['pages'] else 'output'), None
    if head == 'markets':
        return 'markets', parts[2] if parts[1:2] == ['lines'] else EVERY_LINE
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


def output(stored):
    """The output settings with their defaults filled in: what How the documents look and the page switches show."""
    return {
        'layout': get(stored, 'output.layout'),
        **{key: get(stored, f'output.{key}') for key in catalog.OUTPUT_SWITCHES},
        'compare_slots': get(stored, 'output.compare_slots'),
        'pages': {key: get(stored, f'output.pages.{key}') for key in catalog.PAGE_KEYS},
    }


def experience(stored):
    return {'summary': get(stored, 'experience.summary'), 'rows': get(stored, 'experience.rows')}
