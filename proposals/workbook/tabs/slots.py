"""A sheet of plan slots looked up from a line's All Plans list: what the Compare tab and each Composite Rates card
share (plan.md §9.4; J148, J150; old `presentation_bank._CompareSheet` at 891f1b3). Each slot is two columns whose
rows look the slot's pick up (INDEX and MATCH over All Plans); `pid` and `found_value` say what a slot's lookup finds,
which is each formula's stored result (the All Plans cell itself), so the stored results equal the recalculation.
The design rows and the Summary of Benefits link are drawn here; the rates and contribution in `compare_cost`.
"""

from .. import bank as listing
from .. import cells, formulas
from .. import styles as s
from ..model import column_letter
from . import all_plans, bank_map
from .compare_cost import C, CostRows

PROMPT_CURRENT = 'Select the current plan ▾'
PROMPT_RENEWAL = 'Select the renewal plan ▾'


class SlotSheet(CostRows):
    # A half holds "EE Only: -15.7%" in bold 9 pt; the label column the longest contribution label on one line.
    LABEL_W, INPUT_W, HALF_W = 35, 11, 15
    LABEL_CHARS, WIDE_CHARS, SLOT_CHARS = 40, 54, 30

    def __init__(self, sheet, ctx, line, found, items, cmap):
        self.sheet, self.ctx, self.line, self.bank, self.items = sheet, ctx, line, found, items
        self.m, self.rows, self.box = cmap, cmap['rows'], cmap['box']
        self.amap = bank_map.all_plans_map(line, found, items)
        self.first, self.last = self.amap['first'], self.amap['last']
        self.titles = {
            'line': ctx.layout.line_tab.get(line.key),
            'compare': ctx.layout.compare[line.key],
            'bank': ctx.layout.bank[line.key],
        }
        self.shared = bank_map.shared(ctx, line)
        self.listed = all_plans.listed(line, found, items, self.shared['counts'])
        self.pid_of = {label.lower(): pid for pid, label in found['label_of'].items()}
        prefill = found['prefill']
        self.picks = [prefill[k] if k < len(prefill) else listing.SELECT for k in range(len(cmap['slots']))]
        self.base_values = {
            'current': found['base'] or PROMPT_CURRENT,
            'renewal': PROMPT_RENEWAL,
        }

    # -- what a slot holds (for the stored results) ------------------------------------------------------------------
    def pid(self, slot):
        return self.pid_of.get(str(self.picks[slot['k']]).lower())

    def found_value(self, slot, key, sub=None):
        """The All Plans cell a slot's lookup finds: its value, or '' (no pick, or an empty cell)."""
        row = self.listed.get(self.pid(slot))
        if row is None:
            return ''
        value = row[key] if sub is None else row[key].get(sub)
        return '' if value is None else value

    # -- helpers -----------------------------------------------------------------------------------------------------
    def _found(self, bank_col, key):
        return formulas.lookup(self.titles['bank'], column_letter(bank_col), self.first, self.last, key)

    def _pick(self, slot):
        return f'{column_letter(slot["col"])}${self.rows["plan"]}'

    def _base(self, row):
        """The absolute reference of a base picker (the box's G2 or G3)."""
        return f'${column_letter(self.box["pick"])}${row}'

    @staticmethod
    def _height(pairs, minimum=s.COMPACT_ROW_H):
        return cells.row_height(pairs, minimum=minimum, line_pt=s.COMPACT_LINE_PT)

    def _label(self, row, text, *, bold=False, indent=1, fill=s.FILL_LABEL, merge=False):
        """A row label on light blue (or `fill`), B in the same fill; with `merge` (nothing in B) the two merged."""
        look = C['bold'] if bold else C['body']
        cells.text(self.sheet, row, 1, text, font=look, fill=fill, border=s.THIN, align=s.label_align(indent))
        cells.blank(self.sheet, row, 2, fill=fill, border=s.THIN)
        if merge:
            cells.merge_pair(self.sheet, row, 1, 2)

    def _navy_label(self, row, text):
        cells.text(self.sheet, row, 1, text, font=C['white'], fill=s.FILL_NAVY, border=s.THIN, align=s.label_align())
        cells.blank(self.sheet, row, 2, fill=s.FILL_NAVY, border=s.THIN)

    def _slot(self, row, slot, template, value, num, *, fill, font=None):
        """One slot's formula on one row, its two columns merged."""
        cells.formula(
            self.sheet,
            row,
            slot['col'],
            template,
            value,
            num,
            sheets=self.ctx.sheets,
            font=font or C['body'],
            fill=fill,
            border=s.THIN,
            align=s.CENTER,
        )
        cells.blank(self.sheet, row, slot['right'], fill=fill, border=s.THIN)
        cells.merge_pair(self.sheet, row, slot['col'], slot['right'])

    def _picker(self, row, col, value, *, last_col, fill=s.FILL_WHITE):
        """An input that names a plan: bold blue, editable under protection, merged across to `last_col`."""
        cells.text(self.sheet, row, col, value, font=C['pick'], fill=fill, border=s.THIN, align=s.CENTER)
        for partner in range(col + 1, last_col + 1):
            cells.blank(self.sheet, row, partner, fill=fill, border=s.THIN)
        cells.unlock(self.sheet, row, col)
        cells.merge_pair(self.sheet, row, col, last_col)

    def _dropdown(self, cells_range, prompt):
        cells.dropdown(self.sheet, cells_range, self.titles['bank'], 'A', self.first, self.last, prompt=prompt)

    # -- the design rows and the SBC link ----------------------------------------------------------------------------
    def _design(self):
        sheet, rows = self.sheet, self.rows
        columns = {column['item']['id']: column['col'] for column in self.amap['cols']['design']}
        shade = False
        for item in self.items:
            row = rows['design'][item['id']]
            if item['kind'] == 'band':
                cells.band(sheet, row, self.m['last_col'], item['label'], size=s.COMPACT_SIZE, height=s.COMPACT_ROW_H)
                shade = False
                continue
            self._label(row, item['label'], indent=item['indent'], merge=True)
            fill = s.FILL_GREY if shade else s.FILL_WHITE
            shade = not shade
            for slot in self.m['slots']:
                template = formulas.looked_up(self._found(columns[item['id']], self._pick(slot)))
                self._slot(row, slot, template, self.found_value(slot, 'design', item['id']), s.GENERAL, fill=fill)
            sheet.heights[row] = self._height([(item['label'], self.WIDE_CHARS)])

    def _sbc(self):
        """Summary of Benefits: "See SBC" in each column whose plan has a public link; the words sit in B, so the
        formula holds no string."""
        sheet, row = self.sheet, self.rows['sbc']
        self._label(row, 'Summary of Benefits')
        cells.text(sheet, row, 2, 'See SBC', font=C['italic'], fill=s.FILL_LABEL, border=s.THIN, align=s.CENTER)
        column = self.amap['cols']['sbc']
        for slot in self.m['slots']:
            found = self._found(column, self._pick(slot))
            template = f'=IFERROR(IF({found}="","",HYPERLINK({found},$B${row})),"")'
            value = 'See SBC' if self.found_value(slot, 'sbc') else ''
            self._slot(row, slot, template, value, s.GENERAL, fill=s.FILL_WHITE, font=C['link'])
        sheet.heights[row] = s.COMPACT_ROW_H
