"""`<Line> All Plans`: every quoted plan the client may see, the list the Compare tab's drop-downs read (plan.md §9.4;
J149, J150, J154; old `presentation_bank._BankSheet` at 891f1b3). A navy header with an AutoFilter, the plan labels
on light blue, the design values as text, the rates as numbers with their stored decimals, and Monthly, Annual and %
from current as live formulas over the Compare tab's counts, each stored with quotes' figure at those counts.

`listed` is what the tab prints for each plan; the Compare and Composite Rates tabs store a looked-up cell's result
from it, so a lookup's result is exactly the cell it finds.
"""

import math
from decimal import Decimal

from quotes import fields
from quotes import math as m
from quotes.math import TIERS

from .. import bank as listing
from .. import cells, design, formulas, values
from .. import print_plan as pp
from .. import styles as s
from ..grammar import sheet_ref
from ..model import column_letter
from . import bank_map
from .common import TIER_LABEL, subtitle

NOTE = (
    'Every plan quoted for this line. ★ marks the plans in this proposal. Pick any of them in the drop-downs on the '
    "'{tab}' tab; the totals follow that tab's counts."
)
NOTE_UNSTARRED = (
    "Every plan quoted for this line: the current plan first, then the quotes in the proposal's order. Use the filter "
    "arrows in the header to narrow the list, and pick any plan in the drop-downs on the '{tab}' tab; the totals "
    "follow that tab's counts."
)
WIDTHS = {'label': 46, 'status': 16, 'carrier': 22, 'design': 22, 'sbc': 40, 'rate': 15, 'money': 16, 'pct': 12}
LABEL_CHARS = 42
TIER_RATE = dict(zip(TIERS, fields.TIER_RATE_KEYS, strict=True))


def fraction(change):
    """quotes' one-decimal percentage as the fraction a percent-formatted cell holds (20.0 → 0.2), or None."""
    if not change or change.get('pct') is None:
        return None
    return Decimal(str(change['pct'])) / 100


def listed(line, bank, items, counts):
    """{plan id: what its All Plans row holds}: status, carrier, design texts by item id, the SBC link, the rates, the
    stated premium, and Monthly / Annual / % from current at the shared `counts` (quotes' math)."""
    by_id = {plan.id: plan for plan in line.plans}
    enrollment = bank_map.enrollment(counts)
    out = {}
    for entry in bank['entries']:
        if entry['kind'] != 'plan':
            continue
        plan = by_id[entry['id']]
        stated = values.number(plan.values.get('group_premium_monthly'))
        monthly = m.monthly_premium(line.data.by_id[plan.id], line.data, enrollment)[0]
        out[plan.id] = {
            'label': entry['label'],
            'status': entry['status'],
            'carrier': entry['carrier'],
            'design': {item['id']: design.text(item, plan) for item in items if item['kind'] == 'row'},
            'sbc': values.sbc_link(plan.values.get(values.SBC_KEY)),
            'rates': {tier: values.number(plan.values.get(TIER_RATE[tier])) for tier in TIERS},
            'raw': {tier: plan.values.get(TIER_RATE[tier]) for tier in TIERS},
            'stated': m.round_decimal(stated) if stated is not None else None,
            'monthly': monthly,
            'annual': m.annual(monthly),
        }
    base = out.get(bank['current_ids'][0]) if len(bank['current_ids']) == 1 else None
    for pid, row in out.items():
        is_base = base is not None and pid == bank['current_ids'][0]
        row['pct'] = None if base is None or is_base else fraction(m.change(row['monthly'], base['monthly']))
    return out


def write(sheet, ctx, line):
    found = ctx.banks[line.key]
    items = listing.items(line, found['plan_ids'])
    amap = bank_map.all_plans_map(line, found, items)
    cost = bool(amap['cols']['monthly'])
    cmap = bank_map.compare_map(found, items, cost, table_notes=bank_map.notes_count(line))
    shared = bank_map.shared(ctx, line)
    rows_out = listed(line, found, items, shared['counts'])
    _Sheet(sheet, ctx, line, found, amap, cmap, rows_out).write()


class _Sheet:
    def __init__(self, sheet, ctx, line, found, amap, cmap, rows_out):
        self.sheet, self.ctx, self.line, self.bank = sheet, ctx, line, found
        self.m, self.cmap, self.rows_out = amap, cmap, rows_out
        self.cols = amap['cols']
        self.compare = ctx.layout.compare[line.key]

    def write(self):
        sheet, m_ = self.sheet, self.m
        self._widths()
        cells.band(sheet, 1, m_['last_col'], f'{self.line.label} — All Quoted Plans', size=s.TITLE_SIZE, height=24)
        cells.band(sheet, 2, m_['last_col'], subtitle(self.ctx.facts), height=18)
        note = NOTE if self.bank['starred'] else NOTE_UNSTARRED
        _note(sheet, 3, 1, m_['last_col'], note.format(tab=self.compare), font=s.ITALIC, chars=150)
        self._header()
        current = self.bank['current_ids']
        base_row = m_['row_of'].get(current[0]) if len(current) == 1 else None
        for entry, row in zip(self.bank['entries'], range(m_['first'], m_['last'] + 1), strict=True):
            if entry['kind'] == 'section':
                self._section(row, entry['label'])
            else:
                self._plan(row, entry, base_row)
        self._notes()
        sheet.freeze = (m_['first'], 2)
        sheet.autofilter = (m_['first'] - 1, 1, m_['last'], m_['last_col'])
        header = m_['first'] - 1
        pp.fitted(
            sheet,
            m_['last_col'],
            m_['last_row'],
            draft=self.ctx.draft,
            fit_wide=max(1, math.ceil(m_['last_col'] / 10)),
            title_cols=(1, 1),
            title_rows=(header, header),
        )

    def _widths(self):
        widths, cols = self.sheet.widths, self.cols
        for name in ('label', 'status', 'carrier'):
            widths[cols[name]] = WIDTHS[name]
        for column in cols['design']:
            widths[column['col']] = WIDTHS['design']
        if cols['sbc']:
            widths[cols['sbc']] = WIDTHS['sbc']
        for col in cols['rates'].values():
            widths[col] = WIDTHS['rate']
        for name in ('stated', 'monthly', 'annual'):
            if cols[name]:
                widths[cols[name]] = WIDTHS['money']
        if cols['pct']:
            widths[cols['pct']] = WIDTHS['pct']

    def _header(self):
        cols, row = self.cols, self.m['first'] - 1
        headers = [(cols['label'], 'Plan'), (cols['status'], 'Status'), (cols['carrier'], 'Carrier')]
        headers += [(column['col'], column['header']) for column in cols['design']]
        if cols['sbc']:
            headers.append((cols['sbc'], 'Summary of Benefits (SBC) link'))
        headers += [(col, TIER_LABEL[tier]) for tier, col in cols['rates'].items()]
        for name, word in (
            ('stated', 'Carrier-stated monthly premium'),
            ('monthly', 'Monthly Total'),
            ('annual', 'Annual Total'),
            ('pct', '% from Current'),
        ):
            if cols[name]:
                headers.append((cols[name], word))
        for col, word in headers:
            cells.text(self.sheet, row, col, word, font=s.WHITE_BOLD, fill=s.FILL_NAVY, border=s.THIN, align=s.CENTER)
        self.sheet.heights[row] = cells.row_height([(word, 18) for _col, word in headers], minimum=30)

    def _section(self, row, label):
        for col in range(2, self.m['last_col'] + 1):
            cells.blank(self.sheet, row, col, fill=s.FILL_NAVY, font=s.WHITE_BOLD)
        cells.text(self.sheet, row, 1, label, font=s.WHITE_BOLD, fill=s.FILL_NAVY, align=s.label_align(0))
        self.sheet.heights[row] = s.ROW_H

    def _plan(self, row, entry, base_row):
        sheet, cols, out = self.sheet, self.cols, self.rows_out[entry['id']]
        cell = {'fill': s.FILL_WHITE, 'border': s.THIN}
        look = s.BOLD if entry['status'] else s.BODY
        cells.text(
            sheet,
            row,
            cols['label'],
            entry['label'],
            font=look,
            fill=s.FILL_LABEL,
            border=s.THIN,
            align=s.label_align(),
        )
        cells.text(sheet, row, cols['status'], entry['status'], font=s.RECOMMENDED, align=s.CENTER, **cell)
        cells.text(sheet, row, cols['carrier'], entry['carrier'], align=s.CENTER, **cell)
        shown = [(entry['label'], LABEL_CHARS)]
        for column in cols['design']:
            text = out['design'][column['item']['id']]
            cells.text(sheet, row, column['col'], text, align=s.CENTER, **cell)
            shown.append((text, 26))
        if cols['sbc']:
            cells.text(sheet, row, cols['sbc'], out['sbc'], align=s.LEFT, **cell)
        rate_refs = []
        for tier, col in cols['rates'].items():
            fmt = values.rate_format(out['raw'][tier], TIER_RATE[tier])
            cells.number(sheet, row, col, out['rates'][tier], fmt, align=s.CENTER, **cell)
            rate_refs.append(f'{column_letter(col)}{row}')
        stated = None
        if cols['stated']:
            cells.number(sheet, row, cols['stated'], out['stated'], s.MONEY_WHOLE, align=s.CENTER, **cell)
            stated = f'{column_letter(cols["stated"])}{row}'
        if cols['monthly']:
            self._totals(row, rate_refs, stated, base_row, out, cell)
        sheet.heights[row] = cells.row_height(shown)

    def _totals(self, row, rate_refs, stated, base_row, out, cell):
        sheet, cols, sheets = self.sheet, self.cols, self.ctx.sheets
        prefix = sheet_ref(self.compare)
        counts = [f'{prefix}$B${tier_row}' for tier_row in self.cmap['rows']['tiers']]
        monthly = column_letter(cols['monthly'])
        cells.formula(
            sheet,
            row,
            cols['monthly'],
            formulas.total_over(counts, rate_refs, stated),
            out['monthly'],
            s.MONEY_WHOLE,
            sheets=sheets,
            font=s.BOLD,
            align=s.CENTER,
            **cell,
        )
        cells.formula(
            sheet,
            row,
            cols['annual'],
            formulas.annual(monthly, row),
            out['annual'],
            s.MONEY_WHOLE,
            sheets=sheets,
            align=s.CENTER,
            **cell,
        )
        if not cols['pct']:
            return
        if base_row is None or row == base_row:
            cells.blank(sheet, row, cols['pct'], num=s.CHANGE, **cell)
        else:
            cells.formula(
                sheet,
                row,
                cols['pct'],
                formulas.pct(monthly, row, monthly, base_row),
                out['pct'],
                s.CHANGE,
                sheets=sheets,
                align=s.CENTER,
                **cell,
            )

    def _notes(self):
        if self.m['notes'] is None:
            return
        left_out, found = self.bank['left_out'], []
        if left_out['no_rate']:
            count = left_out['no_rate']
            found.append(
                f'{count} quoted plan{"s" if count != 1 else ""} without rates {"are" if count != 1 else "is"} '
                'not listed.'
            )
        if left_out['hidden']:
            count = left_out['hidden']
            found.append(
                f'{count} quoted plan{"s" if count != 1 else ""} from '
                f'{"carriers" if count != 1 else "a carrier"} hidden on Markets checked '
                f'{"are" if count != 1 else "is"} not listed.'
            )
        if left_out['cap']:
            found.append(
                f'{left_out["cap"]} more quoted plans are not listed: the list holds {listing.MAX_BANK_PLANS}.'
            )
        first = self.m['notes'][0]
        cells.spacer(self.sheet, first - 1)
        for row, text in enumerate(found, first):
            _note(self.sheet, row, 1, min(self.m['last_col'], 3), text)


def _note(sheet, row, first_col, last_col, text, *, font=None, chars=120, minimum=s.ROW_H, line_pt=s.LINE_PT):
    """A note row merged across `first_col`..`last_col`, tall enough for its words."""
    cells.text(sheet, row, first_col, text, font=font or s.BODY, align=s.LEFT)
    if last_col > first_col:
        cells.merge_pair(sheet, row, first_col, last_col)
    sheet.heights[row] = cells.row_height([(text, chars)], minimum=minimum, line_pt=line_pt)
