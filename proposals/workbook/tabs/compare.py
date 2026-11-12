"""`Dynamic <Line> Compare`: five, ten or sixteen plan slots, each a drop-down over the All Plans list with every row
looked up from it (plan.md §9.4; J148; old `presentation_bank._CompareSheet` at 891f1b3, Bryke's "Dynamic Single SBS
Comp" look). The client's counts and the employer's contribution are inputs in column B; the base-plan box names the
Current and Renewal plans the two % rows compare against; the file opens here. 9 pt type on 15 pt rows at 110%, five
slots a printed page with the break between two slots.

This module draws the top, the box and the header; `slots.SlotSheet` the slots' design rows and SBC link;
`compare_cost.CostRows` the rates, totals, changes, contribution and notes. Every formula's stored result is the All
Plans cell it finds, or quotes' figure for the pick at the shared counts (`all_plans.listed`), so a viewer that does
not calculate shows the app's.
"""

import math

from .. import bank as listing
from .. import cells, formulas, layout
from .. import print_plan as pp
from .. import styles as s
from ..model import column_letter
from . import bank_map
from .common import long_date
from .compare_cost import C
from .slots import SlotSheet

RENEWAL_WORD, CURRENT_WORD = 'RENEWAL', 'CURRENT'
PICK_PROMPT = (
    'Click, then start typing any part of a carrier or plan name to search, or open the list. Every row of this column '
    'follows your pick.'
)
CURRENT_PROMPT = 'Choose the plan "% Difference from Current" compares against.'
RENEWAL_PROMPT = 'Choose the renewal: "% Difference from Renewal" compares against it, and its column reads RENEWAL.'


def write(sheet, ctx, line):
    found = ctx.banks[line.key]
    items = listing.items(line, found['plan_ids'])
    cost = layout.part(line, 'cost')
    cmap = bank_map.compare_map(found, items, cost, table_notes=bank_map.notes_count(line))
    CompareSheet(sheet, ctx, line, found, items, cmap).write()


class CompareSheet(SlotSheet):
    """The Compare tab: the slots under its top rows, base box and drop-down header."""

    # -- the sheet ---------------------------------------------------------------------------------------------------
    def write(self):
        sheet, rows = self.sheet, self.rows
        sheet.widths[1], sheet.widths[2] = self.LABEL_W, self.INPUT_W
        for slot in self.m['slots']:
            sheet.widths[slot['col']] = sheet.widths[slot['right']] = self.HALF_W
        self._top()
        self._header()
        self._design()
        if rows['sbc']:
            self._sbc()
        if rows['tiers']:
            self._premium()
            self._changes()
            self._contribution()
        self._notes()
        sheet.freeze = (rows['plan'] + 1, 3)
        self._print_setup()

    def _print_setup(self):
        """Five slots a printed page, A:B and the header rows on every page, at a computed scale; then Bryke's zoom."""
        sheet, rows = self.sheet, self.rows
        page = [self.LABEL_W, self.INPUT_W] + [self.HALF_W] * (2 * bank_map.PER_PAGE)
        pages = math.ceil(len(self.m['slots']) / bank_map.PER_PAGE)
        plan = {
            'breaks': [2 + 2 * bank_map.PER_PAGE * n for n in range(1, pages)],
            'scale': pp.columns_print_scale(page, cells.sheet_height_pt(sheet, self.m['last_row'])),
            'title_cols': (1, 2),
            'title_rows': (rows['marker'], rows['plan']),
        }
        pp.with_breaks(sheet, self.m['last_col'], self.m['last_row'], plan, draft=self.ctx.draft)
        sheet.zoom = s.COMPARE_ZOOM

    # -- rows 1 to 4: who it is for, the base box, the rule ----------------------------------------------------------
    def _top(self):
        sheet, facts = self.sheet, self.ctx.facts
        prepared = ' · '.join(part for part in (facts.agency['name'], facts.agency['producer']) if part)
        effective = long_date(facts.effective)
        label = self.line.label
        top = (
            (facts.client, C['title'], 18),
            (f'Prepared by {prepared}' if prepared else '', C['body'], 15),
            (f'{label} · Effective {effective}' if effective else label, C['body'], 15),
        )
        for row, (value, look, height) in enumerate(top, 1):
            cells.text(sheet, row, 1, value, font=look, align=s.PLAIN_LEFT)
            sheet.heights[row] = height
        if self.box:
            self._box()
        for col in range(1, self.m['last_col'] + 1):
            cells.blank(sheet, self.rows['rule'], col, fill=s.FILL_NAVY)
        sheet.heights[self.rows['rule']] = 3

    def _box(self):
        """ "% Difference Base Plans": the Current base (prefilled with the current plan) and the Renewal base (a prompt
        until picked). Each word cell is what a column whose pick is that base reads in its status."""
        sheet, box, rows = self.sheet, self.box, self.rows
        cells.text(
            sheet,
            1,
            box['first'],
            '% Difference Base Plans',
            font=C['white'],
            fill=s.FILL_NAVY,
            border=s.THIN,
            align=s.CENTER,
        )
        for col in range(box['first'] + 1, box['last'] + 1):
            cells.blank(sheet, 1, col, fill=s.FILL_NAVY, border=s.THIN)
        cells.merge_pair(sheet, 1, box['first'], box['last'])
        for row, word, value, fill, prompt in (
            (rows['base_current'], CURRENT_WORD, self.base_values['current'], s.FILL_LABEL, CURRENT_PROMPT),
            (rows['base_renewal'], RENEWAL_WORD, self.base_values['renewal'], s.FILL_GREEN, RENEWAL_PROMPT),
        ):
            cells.text(sheet, row, box['word'], word, font=C['bold'], fill=s.FILL_WHITE, border=s.THIN, align=s.CENTER)
            cells.text(
                sheet, row, box['arrow'], 'Based On ➡', font=C['bold'], fill=s.FILL_WHITE, border=s.THIN, align=s.CENTER
            )
            self._picker(row, box['pick'], value, last_col=box['last'], fill=fill)
            self._dropdown((row, box['pick'], row, box['pick']), prompt)

    # -- rows 5 to 7: status words, Carrier, Plan Name ---------------------------------------------------------------
    def _status_template(self, slot):
        pick = self._pick(slot)
        found = self._found(self.amap['cols']['status'], pick)
        if not self.box:
            return formulas.looked_up(found)
        renewal = self._base(self.rows['base_renewal'])
        word = f'${column_letter(self.box["word"])}${self.rows["base_renewal"]}'
        return f'=IFERROR(IF(AND({pick}={renewal},{renewal}<>""),{word},IF({found}="","",{found})),"")'

    def _header(self):
        sheet, rows = self.sheet, self.rows
        cells.text(
            sheet,
            rows['marker'],
            1,
            f'Dynamic {self.line.label} Compare — pick any plan',
            font=C['bold'],
            align=s.label_align(0),
        )
        for col in (1, 2):
            cells.blank(sheet, rows['carrier'], col, fill=s.FILL_NAVY, border=s.THIN)
        cells.merge_pair(sheet, rows['carrier'], 1, 2)
        self._label(rows['plan'], 'Plan Name ▾', bold=True, merge=True)
        carrier = self.amap['cols']['carrier']
        for slot in self.m['slots']:
            self._slot(
                rows['marker'],
                slot,
                self._status_template(slot),
                self.found_value(slot, 'status'),
                s.GENERAL,
                fill=s.FILL_WHITE,
                font=C['navy'],
            )
            self._slot(
                rows['carrier'],
                slot,
                formulas.looked_up(self._found(carrier, self._pick(slot))),
                self.found_value(slot, 'carrier'),
                s.GENERAL,
                fill=s.FILL_NAVY,
                font=C['white'],
            )
            self._picker(rows['plan'], slot['col'], self.picks[slot['k']], last_col=slot['right'])
        first, last = self.m['slots'][0], self.m['slots'][-1]
        span = (rows['marker'], first['col'], rows['marker'], last['right'])
        if self.box:
            # The column whose pick is a base lights up: amber for the renewal, green for the current.
            head = f'{column_letter(first["col"])}${rows["plan"]}'
            renewal, current = self._base(rows['base_renewal']), self._base(rows['base_current'])
            cells.highlight(sheet, span, f'AND({head}={renewal},{renewal}<>"")', s.HIGHLIGHT_RENEWAL)
            cells.highlight(sheet, span, f'AND({head}={current},{current}<>"")', s.HIGHLIGHT_CURRENT)
        self._dropdown((rows['plan'], first['col'], rows['plan'], last['right']), PICK_PROMPT)
        sheet.heights[rows['marker']] = sheet.heights[rows['carrier']] = 16
        shown = [(value, self.SLOT_CHARS) for value in self.bank['prefill']] or [('', self.SLOT_CHARS)]
        sheet.heights[rows['plan']] = self._height(shown, minimum=24)
