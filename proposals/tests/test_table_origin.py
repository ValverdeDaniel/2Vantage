"""A table's words drawn as reportlab's Table drew them (plan.md §9.5, §12.7; J122, J133; slice 33's Fidelity fix for
GD5's stop-loss page): through the table's translation, then each cell's, so the device position of a glyph is the
same sum of floats as in the old file, and one on a pixel's edge rounds the same way. Pure: no database."""

import io
import re

from pypdf import PdfReader

from proposals.layout import furniture, grid, record
from proposals.layout import table as tb
from proposals.paint import pdf

COLOURS = furniture.palette(None)
CHROME = {'stamp': '', 'note': '', 'firm': '', 'logo': None, 'draft': False, 'colours': COLOURS}


def _table():
    rows = [
        {
            'kind': 'row',
            'cells': [
                tb.cell('Specific Deductible (per person)', 11.5, COLOURS['ink']),
                tb.cell('$50,000', 11.5, COLOURS['ink'], align='c'),
            ],
        },
        {
            'kind': 'row',
            'cells': [
                tb.cell('Aggregate Premium PEPM', 11.5, COLOURS['ink']),
                tb.cell('$12.10', 11.5, COLOURS['ink'], align='c'),
            ],
        },
    ]
    return tb.Table(rows, [165.6, 200], COLOURS, head=0)


def test_J122_row_positions_are_reportlabs_compensated_sums():
    heights = [15.4, 29.2, 15.4]
    positions = grid.row_positions(heights)
    assert positions[-1] == 0 and len(positions) == len(heights) + 1
    assert positions[0] == positions[1] + heights[0] and positions[2] == heights[2]
    rowheight = positions[1] - positions[2]  # the middle row, as reportlab's `_drawCell` reads it
    assert grid.origin(0, positions, 1, 1, (6, 6, 3.5, 3.5), 27.6) == [6, positions[2] + (rowheight + 27.6) / 2.0]


def test_J122_a_tables_words_are_drawn_through_its_translation_then_each_cells():
    pages = record.lay_out([[_table()]], CHROME)
    frame = next(item for item in pages[0]['frames'] if item['t'] == 'table')
    origin = frame['origin']
    assert frame['x'] == origin[0], 'the table sits where reportlab translated it'
    assert all(cell['text']['at'][0] == cell['x'] - frame['x'] + 6 for cell in frame['cells'])
    content = PdfReader(io.BytesIO(pdf.draw(pages))).pages[0].get_contents().get_data().decode('latin-1')
    label = content.index('(Specific Deductible')
    before = content[:label]
    table_cm = f'1 0 0 1 {origin[0]:g} '
    assert table_cm in before, 'the table translation comes first'
    cell = r'1 0 0 1 6 [\d.]+ cm(?:(?!cm).)*?BT 1 0 0 1 0 [\d.]+ Tm'  # no other translation in between
    assert re.search(cell, before[before.rindex(table_cm) :], re.S), "a left cell's words start at its own origin"
