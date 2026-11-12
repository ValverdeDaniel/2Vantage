"""`<Line> Composite Rates`: every listed plan as a card, four across a printed page, pages stacked down the sheet with
a manual row break after each (plan.md §9.4; J150; old `presentation_bank._CompositeSheet` at 891f1b3, Bryke's
"Composite Rates"). Written whenever the list holds plans the rates tab does not show.

A card is a Compare column whose pick is fixed (`slots.SlotSheet`): the same lookups and formulas, its counts and
contribution inputs in B links to the Compare tab's, its % rows reading that tab's base pickers, so the file keeps one
set of inputs and a card always equals the Compare column for the same plan.
"""

from quotes.math import TIERS

from .. import bank as listing
from .. import cells, formulas, layout
from .. import print_plan as pp
from .. import styles as s
from ..grammar import sheet_ref
from ..model import column_letter
from . import bank_map
from .common import long_date
from .compare_cost import C
from .slots import SlotSheet

NOTE = (
    "Every plan on the '{bank}' tab as a card, four to a page. The counts, the base plans and the employer "
    "contribution are the '{compare}' tab's: change them there and every card follows."
)


def write(sheet, ctx, line):
    found = ctx.banks[line.key]
    items = listing.items(line, found['plan_ids'])
    cost = layout.part(line, 'cost')
    cmap = bank_map.compare_map(found, items, cost, table_notes=bank_map.notes_count(line))
    CompositeSheet(sheet, ctx, line, found, items, cmap, cost).write()


class CompositeSheet(SlotSheet):
    def __init__(self, sheet, ctx, line, found, items, cmap, cost):
        super().__init__(sheet, ctx, line, found, items, cmap)
        self.titles['composite'] = ctx.layout.composite[line.key]
        self.cost = cost
        self.compare_rows, self.compare_box = cmap['rows'], cmap['box']
        self.box = None  # a card page has no base box of its own

    def _remote(self, ref):
        return f'{sheet_ref(self.titles["compare"])}{ref}'

    def _base(self, row):
        """The Compare tab's base picker (its G2 or G3)."""
        return self._remote(f'${column_letter(self.compare_box["pick"])}${row}')

    def _link(self, row, source_row, num, value):
        """B on this row: the Compare tab's B on `source_row`, blank while that is blank (`formulas.linked`)."""
        template = formulas.linked(self._remote(f'$B${source_row}'))
        cells.formula(
            self.sheet,
            row,
            2,
            template,
            value,
            num,
            sheets=self.ctx.sheets,
            font=C['body'],
            fill=s.FILL_LABEL,
            border=s.THIN,
            align=s.CENTER,
        )

    def _count(self, row, tier):
        self._link(row, self.compare_rows['tiers'][TIERS.index(tier)], s.COUNT, self.shared['counts'].get(tier))

    def _input(self, row, name, value, num):
        source = self.compare_rows[name[0]][name[1]] if isinstance(name, tuple) else self.compare_rows[name]
        self._link(row, source, num, value)

    # -- the sheet ---------------------------------------------------------------------------------------------------
    def write(self):
        sheet = self.sheet
        sheet.widths[1], sheet.widths[2] = self.LABEL_W, self.INPUT_W
        for k in range(2 * bank_map.CARDS_PER_PAGE):
            sheet.widths[3 + k] = self.HALF_W
        last_col = 2 + 2 * bank_map.CARDS_PER_PAGE
        self._title(last_col)
        pages = bank_map.composite_pages(self.bank, self.items, self.cost)
        breaks, heights, last_row = [], [], 4
        for index, (top, page, chunk) in enumerate(pages):
            self.m, self.rows = page, page['rows']
            self.picks = [entry['label'] for entry in chunk]
            first_row = 1 if index == 0 else top  # page one prints the title rows above its cards
            self._card_header(chunk, index, len(pages))
            self._design()
            if self.rows['sbc']:
                self._sbc()
            if self.rows['tiers']:
                self._premium()
                self._changes()
                self._contribution()
            last_row = bank_map.card_page_last(page)
            heights.append(
                sum(float(sheet.heights.get(row) or s.DEFAULT_ROW_PT) for row in range(first_row, last_row + 1))
            )
            if index < len(pages) - 1:
                breaks.append(last_row + 1)  # the spacer row ends the page
        sheet.freeze = (1, 3)
        widths = [self.LABEL_W, self.INPUT_W] + [self.HALF_W] * (2 * bank_map.CARDS_PER_PAGE)
        scale = pp.card_print_scale(widths, max(heights or [s.DEFAULT_ROW_PT]))
        pp.card_pages(sheet, last_col, last_row, breaks, scale, draft=self.ctx.draft)
        sheet.zoom = s.COMPARE_ZOOM

    def _title(self, last_col):
        """Rows 1 to 4: the client, the line, what the tab is, a navy rule."""
        sheet, facts = self.sheet, self.ctx.facts
        effective = long_date(facts.effective)
        heading = f'{self.line.label} — Every Quoted Plan'
        cells.text(sheet, 1, 1, facts.client, font=C['title'], align=s.PLAIN_LEFT)
        cells.text(
            sheet,
            2,
            1,
            f'{heading} · Effective {effective}' if effective else heading,
            font=C['bold'],
            align=s.PLAIN_LEFT,
        )
        note = NOTE.format(bank=self.titles['bank'], compare=self.titles['compare'])
        cells.text(sheet, 3, 1, note, font=C['italic'], align=s.LEFT)
        cells.merge_pair(sheet, 3, 1, last_col)
        sheet.heights[3] = cells.row_height([(note, 150)], minimum=s.COMPACT_ROW_H, line_pt=s.COMPACT_LINE_PT)
        sheet.heights[1], sheet.heights[2] = 18, 15
        for col in range(1, last_col + 1):
            cells.blank(sheet, 4, col, fill=s.FILL_NAVY)
        sheet.heights[4] = 3

    def _card_header(self, chunk, index, count):
        """A page's status words, carriers and plan names. The plan name is the card's fixed pick, written as text,
        which the rows below look up exactly as a Compare column looks up its pick."""
        sheet, rows = self.sheet, self.rows
        cells.text(sheet, rows['marker'], 1, f'Page {index + 1} of {count}', font=C['bold'], align=s.label_align(0))
        for col in (1, 2):
            cells.blank(sheet, rows['carrier'], col, fill=s.FILL_NAVY, border=s.THIN)
        cells.merge_pair(sheet, rows['carrier'], 1, 2)
        self._label(rows['plan'], 'Plan Name', bold=True, merge=True)
        status, carrier = self.amap['cols']['status'], self.amap['cols']['carrier']
        for slot, entry in zip(self.m['slots'], chunk, strict=True):
            pick = self._pick(slot)
            self._slot(
                rows['marker'],
                slot,
                formulas.looked_up(self._found(status, pick)),
                self.found_value(slot, 'status'),
                s.GENERAL,
                fill=s.FILL_WHITE,
                font=C['navy'],
            )
            self._slot(
                rows['carrier'],
                slot,
                formulas.looked_up(self._found(carrier, pick)),
                self.found_value(slot, 'carrier'),
                s.GENERAL,
                fill=s.FILL_NAVY,
                font=C['white'],
            )
            cells.text(
                sheet,
                rows['plan'],
                slot['col'],
                entry['label'],
                font=C['bold'],
                fill=s.FILL_WHITE,
                border=s.THIN,
                align=s.CENTER,
            )
            cells.blank(sheet, rows['plan'], slot['right'], fill=s.FILL_WHITE, border=s.THIN)
            cells.merge_pair(sheet, rows['plan'], slot['col'], slot['right'])
        sheet.heights[rows['marker']] = sheet.heights[rows['carrier']] = 16
        sheet.heights[rows['plan']] = self._height([(entry['label'], self.SLOT_CHARS) for entry in chunk], minimum=24)
