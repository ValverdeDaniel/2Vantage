"""Which plans a proposal presents, and in what column order (plan.md §8.12, §9.4)."""


def default_ids(plans):
    """Every current plan, its renewal, the recommended plans, and the starred alternates (all if none starred)."""
    alternates = [p for p in plans if p.role == 'alternate']
    starred = [p for p in alternates if p.starred]
    chosen = [p for p in plans if p.role in ('current', 'renewal') or p.recommended]
    chosen += starred or alternates
    return {p.id for p in chosen}


def forced_ids(plans):
    """Current and recommended plans are always presented."""
    return {p.id for p in plans if p.role == 'current' or p.recommended}


def ordered(plans, presented_ids, alternate_order=None):
    """Columns: each current plan then its renewal (Advisor order); then alternates — in the member's order when
    given, otherwise grouped by carrier in order of first appearance."""
    presented = [p for p in plans if p.id in presented_ids]
    columns = []
    for current in [p for p in presented if p.role == 'current']:
        columns.append(current)
        columns += [p for p in presented if p.role == 'renewal' and p.renews_id == current.id]
    columns += [p for p in presented if p.role == 'renewal' and p not in columns]
    alternates = [p for p in presented if p.role == 'alternate']
    if alternate_order:
        rank = {pid: i for i, pid in enumerate(alternate_order)}
        alternates.sort(key=lambda p: rank.get(p.id, len(rank)))
    else:
        carriers = list(dict.fromkeys(p.carrier for p in alternates))
        alternates.sort(key=lambda p: carriers.index(p.carrier))
    return columns + alternates


def presented_for(config_lines, line, plans):
    """(ordered plans, is_default) for a line."""
    stored = config_lines.get(line)
    if not stored:
        return ordered(plans, default_ids(plans)), True
    known = {p.id for p in plans}
    ids = {pid for pid in stored if pid in known} | forced_ids(plans)
    return ordered(plans, ids, [pid for pid in stored if pid in known]), False
