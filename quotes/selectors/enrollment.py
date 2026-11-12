"""The comparison's `enrollment` block: what the Advisor's counts card, the census notice and the split read (plan.md
§5.5, §8.14; F85, F88–F91, OQ18, OQ20).

    keys            the line's basis keys (EE…FAM, volume or lives)
    on              the line's one switch for its typed counts
    figure          the figure typed for the whole line, or None; `offers_figure`: the card offers it (the line has no
                    current plan, or a figure is stored so it keeps applying, F88)
    typed_at        when the line's typed counts were saved; `stale`: before the latest census import
    typed_plans     how many plans carry their own typed counts
    census          {figures, source, imported_at} for the line, or None; `texts`: the census plan texts with
                    enrolled employees, each with its counts and the current plan it is matched to (by hand, name or
                    number) or None, on medical, dental and vision (F90)
    census_now      plans priced from the census because their typed counts were saved before the import (F91)
    split           when two or more current plans stop the line's pricing (F88): `lost`, the plans with no price;
                    `unlinked`, the alternates that replace no current plan yet (they ask what they replace, OQ20);
                    `figure`, the line figure to split; else None
    medical         {figures, source}: medical's people, on a line that borrows them (worksite, stop-loss)
"""

from .. import math as m
from ..math import by_plan
from ..math import enrollment as counts


def _plain(figures):
    return None if not figures else {key: m.plain(m.decimal(value)) for key, value in figures.items()}


def _stamp(at):
    return at.isoformat() if at else None


def _census(data):
    census = data.people.census
    if not census:
        return None
    keys = m.enrollment_keys(data.rate_basis)
    figures = {key: m.plain(m.decimal(census.get(key)) or 0) for key in keys}
    source = counts.PROXY if census.get('source') == 'borrowed' else counts.CENSUS
    return {'figures': figures, 'source': source, 'imported_at': _stamp(data.people.imported_at)}


def _split(data, results):
    lost = [p.id for p in data.plans if results[p.id]['reason'] == 'per_plan_counts_needed']
    if not lost:
        return None
    unlinked = [p.id for p in data.plans if p.role == 'alternate' and not data.base_ids(p) and p.id in lost]
    figure = counts.figures_of(data.people.figure, m.enrollment_keys(data.rate_basis))
    return {'lost': lost, 'unlinked': unlinked, 'figure': _plain(figure)}


def line_block(data, results):
    people = data.people
    keys = m.enrollment_keys(data.rate_basis)
    figure = counts.figures_of(people.figure, keys)
    medical = people.medical
    return {
        'keys': keys,
        'on': people.on,
        'figure': _plain(figure),
        'offers_figure': not data.current or figure is not None,
        'typed_at': _stamp(people.typed_at),
        'stale': people.stale and bool(people.typed_at or figure or any(p.enrollment for p in data.plans)),
        'typed_plans': sum(1 for p in data.plans if m.typed(p, keys)),
        'census': _census(data),
        'texts': by_plan.matched(data),
        'census_now': [p.id for p in data.plans if m.gave_way(p, data)],
        'split': _split(data, results),
        'medical': {'figures': _plain(medical[0]), 'source': medical[1]} if medical else None,
    }
