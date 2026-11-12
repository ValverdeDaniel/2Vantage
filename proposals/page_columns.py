"""What each column of "What the client will see" says and offers (plan.md §5.4, §8.14; F37–F39, F45, F52, J5, J8,
J10–J13; ported from old Vantage at 7385bb3, `ProposalPages.jsx` and `PlanPicker.jsx`). Pure.

The facts and words the old screen worked out in the browser are worked out here once (J.5 B6): the column's kind
and title ("Today", "Option n" in reading order, a priced version's label), its chips, "Replacing:", the arrows'
ends among the plans shown, what ✕ does (and the sentence when it cannot, J.5 B5), the premium and the change vs
current (quotes' math only), and the picker's greyed reasons that do not depend on the spot. Stop-loss is a line like
every other (OQ13): its names take picks and its quotes take arrows and links.
"""

from deals import carriers
from quotes import math as m
from quotes import presented

from . import formatting as fmt
from . import pages as splitter

UNKNOWN_CARRIER = 'Unknown carrier'
CURRENT_WHY = 'Current plans lead each page'
VERSION_WHY = 'Moves with its plan'
MINUS = '−'


def words(row):
    """How a client document names a plan: its carrier and its "Name on client documents" or name."""
    return ' '.join(part for part in (row.carrier, row.client_name or row.name) if part).strip() or f'Plan {row.id}'


def group_of(plan, data):
    """The current plan a plan sits with on the pages and in the order (`order.layout`'s group), or None."""
    root = data.root(plan)
    if root.role == 'current':
        return root.id
    bases = data.base_ids(root)
    return bases[0] if bases else None


def links_of(plan, data):
    """The current plans a plan is linked to (a renewal's plan, an alternate's `replaces`), its root's for a version."""
    root = data.root(plan)
    if root.role == 'current':
        return []
    current = {p.id for p in data.current}
    if root.role == 'renewal':
        return [root.renews] if root.renews in current else []
    return data.base_ids(root) if root.replaces else []


def column(plan, data):
    """The splitter's view of a presented plan (`pages.Column`)."""
    root = data.root(plan)
    current = plan.role == 'current'
    return splitter.Column(
        id=plan.id,
        current=current,
        lead=current or root.role == 'current',
        carrier=carriers.identity(plan.carrier) or f'plan:{plan.id}',
        carrier_name=carriers.display_name(plan.carrier) or plan.carrier or UNKNOWN_CARRIER,
        group=None if current else group_of(plan, data),
        renews=root.renews if root.role == 'renewal' and root.renews in data.by_id else None,
        version=root.id != plan.id,
    )


def kind_of(plan, data):
    if plan.role == 'current':
        return 'current'
    if data.root(plan).id != plan.id:
        return 'priced'
    if plan.role == 'renewal' and plan.renews in {p.id for p in data.current}:
        return 'renewal'
    return 'option'


def arrows(shown, data):
    """{plan id: {first, last}} for the plans that take ‹ ›: a current plan beside another, moving among the current
    plans; a quote inside its group, among the quotes shown. A priced version rides behind its plan (no arrows)."""
    out = {}
    currents = [p for p in shown if p.role == 'current']
    if len(currents) >= 2:
        for i, plan in enumerate(currents):
            out[plan.id] = {'first': i == 0, 'last': i == len(currents) - 1}
    groups = {}
    for plan in shown:
        if plan.role != 'current' and data.root(plan).id == plan.id:
            groups.setdefault(group_of(plan, data), []).append(plan.id)
    for ids in groups.values():
        for i, pid in enumerate(ids):
            out[pid] = {'first': i == 0, 'last': i == len(ids) - 1}
    return out


def option_numbers(pages, data):
    """{plan id: n}: "Option n" as Issue will stamp it, in the order the client first meets the plans; renewals are
    numbered, current plans and priced versions are not (§5.4, J159)."""
    out = {}
    for pid in splitter.reading_order(pages):
        plan = data.by_id[pid]
        if plan.role != 'current' and data.root(plan).id == plan.id:
            out[pid] = len(out) + 1
    return out


def premium(plan, results):
    result = results[plan.id]
    note = m.REASON_WORDS.get(result['reason'], '') if result['monthly'] is None else ''
    return fmt.money(result['monthly']), note


def _signed(number, text):
    return ('+' if number > 0 else MINUS if number < 0 else '') + text


def change(plan, results):
    """{text, pct, up} against what the plan replaces, only where quotes' math gives a change (the same people), or
    None: "+$1,200/mo · +4.5%", as the old screen wrote it (a minus sign, never a hyphen)."""
    result = results[plan.id]
    if plan.role == 'current' or not result['change']:
        return None
    pct = result['change']['pct']
    monthly = m.monthly_change(result['monthly'], [results[pid]['monthly'] for pid in result['base_ids']])
    delta = monthly['delta'] if monthly else None
    dollars = _signed(delta, f'{fmt.money(abs(delta))}/mo') if delta is not None else ''
    percent = _signed(pct, f'{abs(pct):.1f}%') if pct is not None else ''
    lead = pct if pct is not None else delta
    return {
        'text': ' · '.join(part for part in (dollars, percent) if part),
        'pct': percent,
        'up': bool(lead and lead > 0),
    }


def replacing(plan, kind, data, numbers, results, rows):
    """ "Replacing:" under a column: {ids, editable, text}. On a line with two or more current plans an option picks
    what it replaces (one plan, or "Several…", a consolidation; F52); a renewal and a priced version only say it."""
    if kind == 'current':
        return {'ids': [], 'editable': False, 'text': 'What they have today'}
    ids = links_of(plan, data)
    several = len(data.current) >= 2
    if several and kind == 'option':
        return {'ids': ids, 'editable': True, 'text': ''}
    root = data.root(plan)
    bases = [root.id] if root.role == 'current' else ids or ([data.current[0].id] if len(data.current) == 1 else [])
    if not bases:
        return {'ids': [], 'editable': False, 'text': ''}
    names = [f'Current {numbers[pid]}' if several else words(rows[pid]) for pid in bases]
    money = fmt.money(results[bases[0]]['monthly']) if len(bases) == 1 else ''
    text = f'Replacing: {" + ".join(names)}' + (f' · {money}' if money else '')
    return {'ids': ids, 'editable': False, 'text': text}


def take_off(plan, data, label, row):
    """What ✕ does (J13): {unstar, unrecommend, star: [ids], why}. On a starred line it unstars the plan (and drops its
    recommendation, after a confirm); on a line with nothing starred it stars every other quote, which past the line's
    room it cannot: `why` says so and names the fix (J.5 B5, F.5 #4)."""
    out = {'unstar': plan.starred, 'unrecommend': plan.recommended, 'star': [], 'why': None}
    if presented.has_stars(data):
        return out
    others = [p.id for p in data.plans if p.role != 'current' and p.id != plan.id and not p.recommended]
    if len(others) > presented.room(data):
        out['why'] = (
            f'Nothing on {label} is starred, so every quote prints. Taking {words(row)} off would star the other '
            f'{len(others)}, and the proposal holds {presented.MAX_COLUMNS} plans: star the plans to show instead.'
        )
        return out
    return {**out, 'star': others}


def stays(plan, kind, data, numbers):
    """A renewal stays beside the plan it renews: (that plan's id, the picker's words) or (None, '')."""
    if kind != 'renewal' or len(data.current) < 2:
        return None, ''
    return plan.renews, f'Renews Current {numbers[plan.renews]}: it stays beside that plan'


def chips(plan, kind, numbers, data, row):
    several = len(data.current) >= 2
    out = []
    if kind == 'current':
        out.append({'key': 'current', 'text': f'CURRENT {numbers[plan.id]}' if several else 'CURRENT', 'title': ''})
    elif kind == 'renewal':
        renews = data.by_id[plan.renews]
        out.append(
            {
                'key': 'renewal',
                'text': 'RENEWAL',
                'of': numbers[renews.id] if several else None,  # the picker says "RENEWAL of 2"
                'title': f"The carrier's renewal of {renews.name}",
            }
        )
    elif kind == 'priced':
        derived = row.derived or {}
        out.append({'key': 'priced', 'text': 'PRICED', 'title': derived.get('note') or derived.get('label') or ''})
    return out


def facts(plan, data, results, rows, ctx):
    """Everything one plan's column (or picker row) says. `ctx`: {numbers (current slots), options, first_page,
    arrows, label, on}."""
    row = rows[plan.id]
    kind = kind_of(plan, data)
    numbers = ctx['numbers']
    monthly, note = premium(plan, results)
    stays_with, stays_words = stays(plan, kind, data, numbers)
    option = ctx['options'].get(plan.id)
    title = {'current': 'Today', 'priced': (row.derived or {}).get('label') or 'Priced version'}.get(kind)
    return {
        'plan_id': plan.id,
        'kind': kind,
        'number': numbers.get(plan.id),
        'title': title or (f'Option {option}' if option else ''),
        'option': option,
        'predicted': option is not None,  # until Issue stamps the numbers (§5.4, J102)
        'carrier': row.carrier,
        'name': row.client_name or row.name,
        'words': words(row),
        'chips': chips(plan, kind, numbers, data, row),
        'pickable': kind in ('option', 'renewal'),
        'arrows': ctx['arrows'].get(plan.id),
        'remove': None if kind == 'current' else take_off(plan, data, ctx['label'], row),
        'replacing': replacing(plan, kind, data, numbers, results, rows),
        'links': links_of(plan, data),
        'group': None if kind == 'current' else group_of(plan, data),
        'stays_with': stays_with,
        'stays_words': stays_words,
        'why_not': CURRENT_WHY if kind == 'current' else VERSION_WHY if kind == 'priced' else None,
        'on': plan.id in ctx['on'],
        'starred': plan.starred,
        'recommended': plan.recommended,
        'monthly': monthly,
        'monthly_note': note,
        'change': change(plan, results),
        'page': ctx['first_page'].get(plan.id),
    }
