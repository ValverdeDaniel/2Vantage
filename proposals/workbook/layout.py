"""The client spreadsheet's tabs, in order (plan.md §9.4; J145–J151; old `presentation_layout` at 891f1b3). Pure.

Cover; Markets Checked when the proposal shows it; then, for each line the builder leaves something on, in its
order: a rates tab (a composite line) or a generic tab (one column a plan), a current-coverage tab for a line kept as
is, and after a composite line's own tab its 'Dynamic <Line> Compare', its '<Line> Composite Rates' when the list
holds plans the rates tab does not show, and its '<Line> All Plans'; Disclaimers last. Nothing is refused for size: a
composite line with more plans than its rates tab holds skips that tab and every plan rides its Compare, Composite
Rates and All Plans tabs (J3). Titles are curated or cleaned, then unique (case ignored, at most 31 characters).
"""

import re
from collections import namedtuple

from quotes import presented as room

Tab = namedtuple('Tab', 'kind title line')
Layout = namedtuple('Layout', 'tabs line_tab compare composite bank in_force bank_only')

COVER, MARKETS, DISCLAIMERS = 'Cover', 'Markets Checked', 'Disclaimers'
PARTS = ('comparison', 'cost', 'recommendation')
MAX_PLANS_PER_LINE = room.MAX_COLUMNS  # the most plans a rates tab lays side by side
COMPARE_PREFIX, COMPARE_SUFFIX = 'Dynamic ', ' Compare'
TAB_NAMES = {
    'medical': 'Medical',
    'dental': 'Dental',
    'vision': 'Vision',
    'basic_life_add': 'Basic Life',
    'voluntary_life': 'Voluntary Life',
    'std': 'Short-Term Disability',
    'ltd': 'Long-Term Disability',
    'voluntary_std': 'Voluntary STD',
    'voluntary_ltd': 'Voluntary LTD',
    'voluntary_worksite': 'Voluntary Worksite',
    'critical_illness': 'Critical Illness',
    'accident': 'Accident',
    'hospital': 'Hospital Indemnity',
    'gap': 'Gap',
    'individual_life': 'Individual Life',
    'stop_loss': 'Stop-Loss',
    'pbm': 'PBM',
}
_ILLEGAL = re.compile(r'[\[\]:*?/\\\x00-\x1f]')


def part(line, name):
    value = (line.parts or {}).get(name)
    return True if value is None else bool(value)


def gets_tab(line):
    """A line gets a tab when it presents a plan and the builder left one of its three parts on."""
    return bool(line.presented) and any(part(line, name) for name in PARTS)


def gets_in_force_tab(line):
    """A line kept as is (no plans, its in-force facts) gets a current-coverage tab while a part is on."""
    return line.kept is not None and not line.presented and any(part(line, name) for name in PARTS)


def _title(line):
    if line.key in TAB_NAMES:
        return TAB_NAMES[line.key]
    title = ' '.join(_ILLEGAL.sub('', line.label or line.key).split()).strip("'").strip()
    return title[:31].rstrip() or 'Sheet'


def unique(title, taken):
    """`title`, or with ' 2', ' 3', … when a tab has it (case ignored), within 31 characters; `taken` gains it."""
    base = title[:31].rstrip()
    candidate, number = base, 1
    while candidate.lower() in taken:
        number += 1
        suffix = f' {number}'
        candidate = base[: 31 - len(suffix)].rstrip() + suffix
    taken.add(candidate.lower())
    return candidate


def suffixed(title, suffix):
    return title[: 31 - len(suffix)].rstrip() + suffix


def dynamic(title):
    room_left = 31 - len(COMPARE_PREFIX) - len(COMPARE_SUFFIX)
    return COMPARE_PREFIX + title[:room_left].rstrip() + COMPARE_SUFFIX


def tabs(facts, banks, disclaimers):
    """The file's `Layout`. `banks` is {line: bank} (bank.py) for the composite lines that carry the Compare tabs."""
    taken = {COVER.lower(), MARKETS.lower()}
    if disclaimers:
        taken.add(DISCLAIMERS.lower())
    out = [Tab('cover', COVER, None)]
    if facts.markets['on'] and facts.markets['lines']:
        out.append(Tab('markets', MARKETS, None))
    line_tab, compare, composite, bank, in_force, bank_only = {}, {}, {}, {}, [], []
    for line in facts.lines:
        if gets_in_force_tab(line):
            title = unique(_title(line), taken)
            out.append(Tab('in_force', title, line.key))
            in_force.append(line.key)
            line_tab[line.key] = title
            continue
        if not gets_tab(line):
            continue
        listed = banks.get(line.key)
        stem = _title(line)
        if listed is not None and len(line.presented) > MAX_PLANS_PER_LINE:
            bank_only.append(line.key)
        else:
            stem = unique(stem, taken)
            out.append(Tab('rates' if line.composite else 'generic', stem, line.key))
            line_tab[line.key] = stem
        if listed is None:
            continue
        compare[line.key] = unique(dynamic(stem), taken)
        out.append(Tab('compare', compare[line.key], line.key))
        if line.key in bank_only or listed['composite']:
            composite[line.key] = unique(suffixed(stem, ' Composite Rates'), taken)
            out.append(Tab('composite', composite[line.key], line.key))
        bank[line.key] = unique(suffixed(stem, ' All Plans'), taken)
        out.append(Tab('bank', bank[line.key], line.key))
    if disclaimers:
        out.append(Tab('disclaimers', DISCLAIMERS, None))
    return Layout(out, line_tab, compare, composite, bank, in_force, bank_only)


def refusal(layout):
    """The sentence the producer reads when there is nothing to present, or None. Only an empty proposal refuses."""
    if not any(tab.kind not in ('cover', 'markets', 'disclaimers') for tab in layout.tabs):
        return 'No plans on this proposal yet — add or star the plans to present first.'
    return None
