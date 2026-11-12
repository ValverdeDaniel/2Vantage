"""The quote list behind a composite line's Compare, Composite Rates and All Plans tabs (plan.md §9.4; J148–J150, J154;
old `presentation_bank._line_bank` at 891f1b3, D-083). Pure, over `facts.Line`.

Every quoted plan the client may see, one drop-down away: the current plans, then the starred plans (★, in the
proposal's order), then every other quote by carrier in the house order (`order.layout`). A line with no star lists
the current plans, then every quote by carrier, and marks none (★ means starred). Left out unless presented: a carrier
hidden on Markets checked (J154, OQ39) and a quote with no rate and no stated premium, each counted in a note; past
MAX_BANK_PLANS a note says how many more were left off. The Compare tab's columns open on the current plans, then the
recommended, then the starred ones (J149).
"""

from quotes import fields
from quotes.math import TIERS, contribution

from . import design, layout, rows, values
from .tabs.common import plan_label

MAX_BANK_PLANS = 2000  # a soft ceiling a line, said in a note row
LABEL_MAX = 120  # MATCH refuses a lookup value over 255 characters
SELECT = 'Select a plan ▾'
STATUS_SOLD, STATUS_CURRENT, STATUS_RECOMMENDED, STATUS_PRESENTED = 'SOLD', 'CURRENT PLAN', 'RECOMMENDED', '★ PROPOSED'
# Excel's MATCH reads * ? ~ as wildcards, so a label never holds them: each becomes a look-alike.
_WILDCARDS = str.maketrans({'*': '∗', '?': '？', '~': '∼'})
PRICE_KEYS = (*fields.TIER_RATE_KEYS, 'group_premium_monthly')


def label_text(text):
    """A drop-down label as the cell stores it: whitespace collapsed, wildcards swapped, never starting like a
    formula, at most LABEL_MAX characters."""
    found = ' '.join(values.clean(text).split()).translate(_WILDCARDS).lstrip('=+-@ ')
    if len(found) > LABEL_MAX:
        found = found[: LABEL_MAX - 1].rstrip() + '…'
    return found


class _Labels:
    """Unique labels for one line's list, case ignored (MATCH ignores case); the placeholder is reserved."""

    def __init__(self):
        self.taken = {SELECT.lower()}

    def __call__(self, text):
        base = label_text(text) or 'Plan'
        candidate, number = base, 1
        while candidate.lower() in self.taken:
            number += 1
            suffix = f' ({number})'
            candidate = base[: LABEL_MAX - len(suffix)].rstrip() + suffix
        self.taken.add(candidate.lower())
        return candidate


def has_price(plan):
    return any(values.number(plan.values.get(key)) is not None for key in PRICE_KEYS)


def _contribution(line, current):
    """The Compare tab's contribution inputs: the single current plan's own share, only while the builder keeps the
    contribution rows (quotes' `contribution.inputs`)."""
    if current is None or 'contrib_ee' not in line.picked:
        return {'ee_pct': None, 'dep_pct': None, 'tier': None}
    rates = {tier: current.values.get(key) for tier, key in zip(TIERS, fields.TIER_RATE_KEYS, strict=True)}
    paid = {tier: current.values.get(key) for tier, key in zip(TIERS, fields.CONTRIB_KEYS, strict=True)}
    return contribution.inputs(rates, paid, line.people or {})


def _status(line, plan, starred, presented):
    if plan.sold:
        return STATUS_SOLD
    if plan.role == 'current':
        return STATUS_CURRENT
    if layout.part(line, 'recommendation') and plan.recommended:
        return STATUS_RECOMMENDED
    return STATUS_PRESENTED if starred and plan.id in presented else ''


def _name(plan, picked):
    name = plan_label(plan, picked)
    if plan.priced:
        name = f'{name} ({plan.priced})' if name else plan.priced
    return name


def line_bank(line, slots_on):
    """{entries: [{kind: section|plan, label, id?, status?, carrier?}], plan_ids (listed, in order), presented_ids,
    current_ids, starred, composite, base, slots, prefill, has_g, has_sbc, contrib, left_out}, or None when nothing is
    listed."""
    presented_ids = [plan.id for plan in line.presented]
    presented = set(presented_ids)
    by_id = {plan.id: plan for plan in line.plans}
    current_ids = [plan.id for plan in line.presented if plan.role == 'current']
    starred = any(plan.starred for plan in line.plans if plan.role != 'current')
    left_out = {'hidden': 0, 'no_rate': 0, 'cap': 0}
    rest = []
    for plan in line.plans:
        if plan.id in presented:
            continue
        if plan.identity in line.hidden:
            left_out['hidden'] += 1
        elif not has_price(plan):
            left_out['no_rate'] += 1
        else:
            rest.append(plan.id)
    room = max(0, MAX_BANK_PLANS - len(presented_ids))
    if len(rest) > room:
        left_out['cap'] = len(rest) - room
        rest = rest[:room]
    labels, entries, label_of = _Labels(), [], {}

    def section(text):
        entries.append({'kind': 'section', 'label': labels(f'— {text} —')})

    def add(pid, prefix):
        plan = by_id[pid]
        name = _name(plan, line.picked)
        label = labels(prefix + (f'{plan.carrier} — {name}' if name else plan.carrier))
        label_of[pid] = label
        entries.append(
            {
                'kind': 'plan',
                'id': pid,
                'label': label,
                'status': _status(line, plan, starred, presented),
                'carrier': plan.carrier,
                'current': plan.role == 'current',
            }
        )

    if current_ids:
        section('CURRENT PLAN' if len(current_ids) == 1 else 'CURRENT PLANS')
        for pid in current_ids:
            add(pid, 'Current · ')
    others = [pid for pid in presented_ids if pid not in current_ids]
    if starred and others:
        section(STATUS_PRESENTED)
        for pid in others:
            add(pid, '★ ')
    elif others:
        order = {plan.id: i for i, plan in enumerate(line.plans)}
        rest = sorted(set(others) | set(rest), key=lambda pid: order.get(pid, len(order)))
    run = None
    for pid in rest:
        identity = by_id[pid].identity
        if identity != run:
            section(by_id[pid].carrier)
            run = identity
        add(pid, '')
    listed = [entry['id'] for entry in entries if entry['kind'] == 'plan']
    if not listed:
        return None
    slots = list(current_ids)
    if layout.part(line, 'recommendation'):
        slots += [pid for pid in presented_ids if by_id[pid].recommended and pid not in slots]
    if starred:
        slots += [pid for pid in presented_ids if pid not in slots]
    else:
        slots += [pid for pid in listed if pid not in slots]
    over_cap = len(presented_ids) > layout.MAX_PLANS_PER_LINE
    single = by_id[current_ids[0]] if len(current_ids) == 1 else None
    return {
        'entries': entries,
        'plan_ids': listed,
        'presented_ids': presented_ids,
        'current_ids': current_ids,
        'starred': starred,
        'composite': over_cap or bool(set(listed) - presented),
        'base': label_of[current_ids[0]] if single else None,
        'slots': slots_on,
        'prefill': [label_of[pid] for pid in slots[:slots_on]],
        'label_of': label_of,
        'has_g': any(values.number(by_id[pid].values.get('group_premium_monthly')) is not None for pid in listed),
        'has_sbc': any(values.sbc_link(by_id[pid].values.get(values.SBC_KEY)) for pid in listed),
        'contrib': _contribution(line, single),
        'left_out': left_out,
    }


def items(line, listed_ids):
    """The design items the Compare, Composite Rates and All Plans tabs show for a line's listed plans (Bryke's rows on
    medical), or none with the comparison part off. With every row kept, an in/out box keeps its out-of-network side
    (N/A)."""
    if not layout.part(line, 'comparison'):
        return []
    house_map = rows.COMPARE_MEDICAL_ROWS if line.field_set == 'medical' else None
    picked = list(line.picked)
    if house_map is not None and line.picked_all:
        for row in rows.flat(house_map):
            if row.flag == 'inout' and row.keys[0] in picked and row.keys[1] not in picked:
                picked.append(row.keys[1])
    listed = set(listed_ids)
    return design.items(line.field_set, picked, [p for p in line.plans if p.id in listed], house_map=house_map)


def banks(facts):
    """{line: bank} for every composite line with a tab that keeps its comparison or cost part on, while the builder
    keeps the Compare tabs (J41 `output.compare_tabs`)."""
    if not facts.output.get('compare_tabs', True):
        return {}
    slots_on = facts.output.get('compare_slots') or 16
    out = {}
    for line in facts.lines:
        if not (line.composite and layout.gets_tab(line)):
            continue
        if not (layout.part(line, 'comparison') or layout.part(line, 'cost')):
            continue
        found = line_bank(line, slots_on)
        if found is not None:
            out[line.key] = found
    return out
