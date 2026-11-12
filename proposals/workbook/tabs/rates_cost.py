"""The premium block of a rates tab (plan.md §9.4; J147; old `presentation_workbook._TierSheet._premium` at 891f1b3):
"Monthly Premiums*", the tier counts and rates, the employer contributions kept, the carrier-stated premium, the
monthly and annual totals, and with exactly one current plan its changes, the package rows (never the stated premium,
D-026) and, when a quote carries a first-year credit, the credit and the net.

Every total is a live formula from `formulas.py`, stored with quotes' figure (rule 5): the plan's monthly and annual
from its priced result, each change from `quotes.math.change`, the net from `quotes.math.pricing.net_after_credit`.
"""

from quotes import fields
from quotes import math as m
from quotes.math import TIERS, pricing

from .. import cells, formulas, values
from .. import styles as s
from ..model import column_letter
from . import common
from .all_plans import fraction

CONTRIB_KEYS = fields.CONTRIB_KEYS
RATE_KEYS = dict(zip(TIERS, fields.TIER_RATE_KEYS, strict=True))
WHITE = {'fill': s.FILL_WHITE, 'border': s.THIN}


def _people(plan):
    used = plan.result.get('enrollment_used')
    return {tier: used.get(tier) or 0 for tier in TIERS} if used else None


def _same(a, b):
    return a is not None and b is not None and all(m.decimal(a[t]) == m.decimal(b[t]) for t in TIERS)


def _package_monthly(plan):
    """The package slot: the plan's own total, never the carrier-stated premium (D-026)."""
    return None if plan.result.get('quoted') else plan.result.get('monthly')


class _Block:
    def __init__(self, sheet, line, geometry):
        self.sheet, self.line, self.g = sheet, line, geometry
        self.rows, self.cols = geometry['rows'], geometry['cols']
        self.plans = line.presented
        self.current = geometry['current']
        self.base = self.plans[self.current['k']] if self.current else None
        self.base_people = _people(self.base) if self.base else None
        self.cn = column_letter(self.current['count']) if self.current else None
        self.cv = column_letter(self.current['rate']) if self.current else None

    def is_current(self, col):
        return self.current is not None and col['k'] == self.current['k']

    def counts(self, row, tier, col, plan):
        """A tier count: the single current plan's are inputs; a plan carrying the same people links to them; any
        other plan's are its own inputs (blank when quotes priced it with nobody)."""
        own = _people(plan)
        look = {'border': s.THIN, 'align': s.CENTER}
        if self.base_people is not None and not self.is_current(col) and _same(own, self.base_people):
            template = f'=${self.cn}{row}'
            cells.formula(
                self.sheet, row, col['count'], template, self.base_people[tier], s.COUNT, fill=s.FILL_WHITE, **look
            )
            return
        value = own[tier] if own is not None else None
        cells.number(self.sheet, row, col['count'], value, s.COUNT, font=s.INPUT, fill=s.FILL_INPUT, **look)
        cells.unlock(self.sheet, row, col['count'])

    def rate_row(self, row, label, key, tier=None):
        common.label(self.sheet, row, label)
        for col, plan in zip(self.cols, self.plans, strict=True):
            if tier is None:
                cells.blank(self.sheet, row, col['count'], **WHITE)
            else:
                self.counts(row, tier, col, plan)
            raw = plan.values.get(key)
            cells.number(
                self.sheet, row, col['rate'], values.number(raw), values.rate_format(raw, key), align=s.CENTER, **WHITE
            )
        self.sheet.heights[row] = s.ROW_H

    def stated_row(self, row):
        common.label(self.sheet, row, 'Carrier-stated monthly premium')
        for col, plan in zip(self.cols, self.plans, strict=True):
            cells.blank(self.sheet, row, col['count'], **WHITE)
            stated = m.round_decimal(values.number(plan.values.get('group_premium_monthly')))
            cells.number(self.sheet, row, col['rate'], stated, s.MONEY_WHOLE, align=s.CENTER, **WHITE)
        self.sheet.heights[row] = s.ROW_H

    def calc_row(self, row, label, num, made, *, total=False):
        """A row of formulas in the rate columns: `made(col, plan, v)` → (template, result), or None (empty)."""
        border = s.TOTAL if total else s.THIN
        look = {'font': s.BOLD if total else s.BODY, 'fill': s.FILL_WHITE, 'border': border, 'align': s.CENTER}
        common.label(self.sheet, row, label, bold=total, border=border)
        for col, plan in zip(self.cols, self.plans, strict=True):
            cells.blank(self.sheet, row, col['count'], fill=s.FILL_WHITE, border=border)
            found = made(col, plan, column_letter(col['rate']))
            if found is None:
                cells.blank(self.sheet, row, col['rate'], num=num, **look)
            else:
                cells.formula(self.sheet, row, col['rate'], found[0], found[1], num, **look)
        self.sheet.heights[row] = s.ROW_H

    def change(self, make, value, base):
        """A change cell for every plan but the current one (the base): (template, result)."""
        return lambda col, plan, v: None if self.is_current(col) else (make(v), value(plan, base))


def _delta(value, base):
    found = m.change(value, base) if value is not None and base is not None else None
    return '' if found is None else found['delta']


def _pct(value, base):
    found = m.change(value, base) if value is not None and base is not None else None
    result = fraction(found)
    return '' if result is None else result


def _net(line, plan):
    """The package's annual less its first-year credit, as the net formula reads its cells."""
    year = m.annual(_package_monthly(plan))
    credit = (plan.result.get('credit') or {}).get('annual')
    if year is None:
        return None
    if credit is None:
        return year
    return pricing.net_after_credit(line.data.by_id[plan.id].credit, _package_monthly(plan), year, None)['net_annual']


def write(sheet, line, geometry):
    """Draw the block; return the single current plan's counts as written (None without one)."""
    rows = geometry['rows']
    if rows['band'] is None:
        return None
    block = _Block(sheet, line, geometry)
    cells.band(sheet, rows['band'], geometry['last_col'], 'Monthly Premiums*')
    cells.blank(sheet, rows['sub'], 1, fill=s.FILL_SUBHEAD, border=s.THIN)
    for col in geometry['cols']:
        for key, word in (('count', '#'), ('rate', 'Rate')):
            cells.text(
                sheet, rows['sub'], col[key], word, font=s.BOLD, fill=s.FILL_SUBHEAD, border=s.THIN, align=s.CENTER
            )
    sheet.heights[rows['sub']] = s.ROW_H
    for tier, row in zip(TIERS, rows['tiers'], strict=True):
        block.rate_row(row, common.TIER_LABEL[tier], RATE_KEYS[tier], tier)
    for tier, row in rows['contrib'].items():
        block.rate_row(row, f'Employer Contribution — {common.TIER_LABEL[tier]}', CONTRIB_KEYS[TIERS.index(tier)])
    if rows['g'] is not None:
        block.stated_row(rows['g'])
    cells.spacer(sheet, rows['tm'] - 1)
    tiers, tm, ta = rows['tiers'], rows['tm'], rows['ta']
    block.calc_row(
        tm,
        'Monthly Total by Product',
        s.MONEY_WHOLE,
        lambda col, plan, v: (
            formulas.total(column_letter(col['count']), v, tiers, rows['g']),
            plan.result.get('monthly'),
        ),
        total=True,
    )
    cells.spacer(sheet, tm + 1)
    block.calc_row(
        ta,
        'Annual Total by Product',
        s.MONEY_WHOLE,
        lambda col, plan, v: (formulas.annual(v, tm), plan.result.get('annual')),
        total=True,
    )
    if geometry['flags']['has_base']:
        _packages(block, line, rows)
    return block.base_people


def _packages(block, line, rows):
    """Change against the current plan, the package slot, its change against the current package, and with a credit
    the credit and the net."""
    cv, base = block.cv, block.base
    ta, pm, pa = rows['ta'], rows['pm'], rows['pa']
    year, package_year = base.result.get('annual'), m.annual(_package_monthly(base))
    annual = lambda plan, b: plan.result.get('annual')  # noqa: E731
    block.calc_row(
        rows['dp'],
        '$ Change from Current',
        s.CHANGE_MONEY,
        block.change(lambda v: formulas.delta(v, ta, cv, ta), lambda plan, b: _delta(annual(plan, b), year), None),
    )
    block.calc_row(
        rows['pp'],
        '% Change from Current',
        s.CHANGE,
        block.change(lambda v: formulas.pct(v, ta, cv, ta), lambda plan, b: _pct(annual(plan, b), year), None),
    )
    cells.spacer(block.sheet, pm - 1)
    block.calc_row(
        pm,
        'Monthly Total (package)',
        s.MONEY_WHOLE,
        lambda col, plan, v: (formulas.total(column_letter(col['count']), v, rows['tiers']), _package_monthly(plan)),
        total=True,
    )
    block.calc_row(
        pa,
        'Annual Total (package)',
        s.MONEY_WHOLE,
        lambda col, plan, v: (formulas.annual(v, pm), m.annual(_package_monthly(plan))),
        total=True,
    )
    package = lambda plan, b: m.annual(_package_monthly(plan))  # noqa: E731
    block.calc_row(
        rows['dk'],
        '$ Change from Current Package',
        s.CHANGE_MONEY,
        block.change(
            lambda v: formulas.delta(v, pa, cv, pa), lambda plan, b: _delta(package(plan, b), package_year), None
        ),
    )
    block.calc_row(
        rows['pk'],
        '% Change from Current Package',
        s.CHANGE,
        block.change(lambda v: formulas.pct(v, pa, cv, pa), lambda plan, b: _pct(package(plan, b), package_year), None),
    )
    if rows['cr'] is None:
        return
    cr, na = rows['cr'], rows['na']
    cells.spacer(block.sheet, cr - 1)
    common.label(block.sheet, cr, 'First-year premium credit')
    for col, plan in zip(block.cols, block.plans, strict=True):
        cells.blank(block.sheet, cr, col['count'], **WHITE)
        credit = None if block.is_current(col) else (plan.result.get('credit') or {}).get('annual')
        cells.number(block.sheet, cr, col['rate'], credit, s.MONEY_WHOLE, align=s.CENTER, **WHITE)
    block.sheet.heights[cr] = s.ROW_H
    block.calc_row(
        na,
        'Net annual premium (after credit)',
        s.MONEY_WHOLE,
        lambda col, plan, v: (formulas.net(v, pa, cr), _net(line, plan)),
        total=True,
    )
    net = lambda plan, b: _net(line, plan)  # noqa: E731
    block.calc_row(
        rows['nd'],
        'Net $ change from current',
        s.CHANGE_MONEY,
        block.change(lambda v: formulas.delta(v, na, cv, pa), lambda plan, b: _delta(net(plan, b), package_year), None),
    )
    block.calc_row(
        rows['np'],
        'Net % change from current',
        s.CHANGE,
        block.change(lambda v: formulas.pct(v, na, cv, pa), lambda plan, b: _pct(net(plan, b), package_year), None),
    )


def enrollment_note(line, geometry):
    """The last note: where the current plan's counts came from, or why the line asks for enrollment instead."""
    plans = line.presented
    typed = any(plan.result.get('enrollment_source') == 'typed' for plan in plans if plan.role != 'current')
    if geometry['current'] is not None:
        source = plans[geometry['current']['k']].result.get('enrollment_source') or 'none'
        note = common.ENROLL_NOTE.get(source) or common.ENROLL_NOTE['none']
    elif all(plan.result.get('monthly') is not None for plan in plans):
        note = common.PCT_NOTE
    else:
        sentence = common.SEVERAL_CURRENT if line.current_ids else common.NO_CURRENT
        note = f'{sentence}. {common.PCT_NOTE}'
    return f'{note} {common.TYPED_PLAN_NOTE}' if typed else note
