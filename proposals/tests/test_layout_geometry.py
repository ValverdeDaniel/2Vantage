"""Where the layout puts words and rows, as the old files put them (plan.md §9.5, §12.7; J122, J133, J136, J140; the
Fidelity lane's ±0.5 pt): reportlab's Paragraph and Table placed the old client PDF and PowerPoint, so the layout keeps
their geometry. A paragraph's later lines sit one leading under its first, whatever their type; a header row the page
sizes leads at 1.25 ×; an empty cell is a 12 pt line; a cell spanning rows shares what it needs beyond them; space
before overlaps the space after. Pure: no database."""

import io

import pytest
from pptx import Presentation
from pypdf import PdfReader
from reportlab.platypus import Spacer

from proposals.layout import fit, flowables, furniture, grid, record, tokens
from proposals.layout import table as tb
from proposals.layout import text as words
from proposals.paint import pdf, pptx
from proposals.story import exhibit, look

COLOURS = furniture.palette(None)
CHROME = {'stamp': '', 'note': '', 'firm': '', 'logo': None, 'draft': False, 'colours': COLOURS}
INK = COLOURS['ink']


def _baselines(pages):
    """{text: baseline y, from the page's top} of every string the PDF's first page draws."""
    found = {}

    def seen(text, cm, tm, _font, _size):
        if text.strip():
            found.setdefault(text.strip(), tokens.PAGE_H - tm[5])

    PdfReader(io.BytesIO(pdf.draw(pages))).pages[0].extract_text(visitor_text=seen)
    return found


def _frames(story):
    return record.lay_out([story], CHROME)[0]['frames']


def test_J122_a_paragraphs_later_lines_sit_one_leading_under_its_first_whatever_their_type():
    runs = [words.run('Carrier heading', 12, INK, True), words.run('\nsmaller plan name', 10, INK)]
    pages = record.lay_out([[flowables.Title('Sample'), flowables.Text(runs, leading=15)]], CHROME)
    lines = _baselines(pages)
    assert lines['Carrier heading'] == tokens.BODY_TOP + 12  # one size of the first line below the top
    assert lines['smaller plan name'] == lines['Carrier heading'] + 15  # one leading, not its own 10 pt


def test_J133_J140_a_header_row_the_page_sizes_leads_at_one_and_a_quarter():
    sized = look.grid([look.heads(['Coverage', 'Today'], COLOURS, 11)], [200, 200], COLOURS, pad=3.5)
    plain = look.grid([look.heads(['Coverage', 'Today'], COLOURS)], [200, 200], COLOURS, pad=3.5)
    assert sized.wrap(400, 1000)[1] == round(11 * 1.25, 2) + 7  # old `_heads(..., size)`
    assert plain.wrap(400, 1000)[1] == pytest.approx(14.4 + 7)  # old `cellHead`: 12 pt at 1.2


def _plan(pid, current=False, option=None):
    return {'id': pid, 'current': current, 'option': option, 'carrier': 'Aetna', 'priced_label': '', 'name': 'PPO 1500'}


def test_J133_a_plan_columns_heading_leads_at_one_and_a_quarter_its_type():
    plans = [_plan(1, current=True), {**_plan(2, option=1), 'sbc': ''}]
    plans[0]['sbc'] = ''
    entries = [('row', {'indent': 1}, ['Deductible', '$1,000', '$1,500'])]
    table = exhibit.build(entries, plans, {2}, COLOURS, 12, 3.5)
    table.wrap(tokens.BODY_W, 10**6)
    heights = table.heights()
    assert heights[0] == pytest.approx(3 * 15 + 7)  # carrier, plan name, RECOMMENDED at 15 pt (old `_plan_cell`)
    assert heights[1] == pytest.approx(14.4 + 7)


def test_J133_an_empty_cell_and_a_band_row_are_never_shorter_than_a_12_pt_line():
    band = {'kind': 'band', 'cells': [tb.cell('Rates', 9, INK, True, span=2)], 'blanks': True}
    blank = {'kind': 'plain', 'cells': [tb.cell('Total', 8, INK, True), tb.blank()]}
    table = tb.Table([band, blank], [200, 200], COLOURS, head=0, pad=2)
    table.wrap(400, 1000)
    assert table.heights() == [grid.EMPTY_LINE + 4, grid.EMPTY_LINE + 4]  # not 9 × 1.2 or 8 × 1.2


def test_J136_a_cell_spanning_rows_shares_what_it_needs_beyond_them_and_centres_its_words():
    paras = [{'runs': [words.run('WE RECOMMEND', 11, INK, True)], 'leading': 100, 'align': 'l'}]
    plate = {'runs': [], 'paras': paras, 'rowspan': 3, 'pad': (20, 16, 16, 16), 'fill': COLOURS['navy']}
    rows = [{'kind': 'plain', 'cells': ([plate] if n == 0 else []) + [tb.cell(f'Fact {n}', 12, INK, leading=16)]}
            for n in range(3)]  # fmt: skip
    table = tb.Table(rows, [300, 300], COLOURS, head=0, zebra=False, rule={'color': '#e6e8ec', 'lw': 0.5, 'col': 1})
    table.wrap(600, 1000)
    assert table.heights() == [44.0, 44.0, 44.0]  # 100 + 32 needed, 3 × 23 held: 21 more each
    frame = _frames([table])[0]
    spanned = next(cell for cell in frame['cells'] if cell.get('rowspan'))
    assert (spanned['col'], spanned['h'], spanned['text']['y'] - spanned['y']) == (0, 132.0, 16.0)
    facts = [cell for cell in frame['cells'] if cell['col'] == 1]
    assert [cell['row'] for cell in facts] == [0, 1, 2]
    assert all(rule['x1'] == 300 + tokens.BODY_X for rule in frame['rules'])  # the hairlines start at the figures


def test_J136_J141_a_cell_spanning_rows_replays_as_one_merged_powerpoint_cell():
    plate = {'runs': [words.run('WE RECOMMEND', 11, INK, True)], 'rowspan': 2, 'fill': COLOURS['navy']}
    rows = [
        {'kind': 'plain', 'cells': [plate, tb.cell('Deductible', 12, INK)]},
        {'kind': 'plain', 'cells': [tb.cell('Family rate', 12, INK)]},
    ]
    table = tb.Table(rows, [300, 300], COLOURS, head=0, zebra=False, rule={'color': '#e6e8ec', 'lw': 0.5, 'col': 1})
    pages = record.lay_out([[flowables.Title('Dental — our recommendation'), table]], CHROME)
    slide = Presentation(io.BytesIO(pptx.draw(pages))).slides[0]
    drawn = next(shape for shape in slide.shapes if shape.has_table).table
    assert drawn.cell(0, 0).span_height == 2 and drawn.cell(0, 0).text_frame.text == 'WE RECOMMEND'
    assert [drawn.cell(row, 1).text_frame.text for row in (0, 1)] == ['Deductible', 'Family rate']


def test_J122_space_before_overlaps_the_space_after_and_a_note_leaves_none():
    def text(before=0.0, after=0.0):
        return flowables.Text([words.run('Words', 12, INK)], leading=15, space_before=before, space_after=after)

    def tops(story):
        return [frame['y'] for frame in _frames([flowables.Title('Sample'), *story])]

    first, second = tops([text(after=6), text(before=8)])
    assert second - first == 15 + 8  # the larger of the two, as reportlab's frame overlaps them
    first, second = tops([text(), Spacer(1, 12), text(before=8)])
    assert second - first == 15 + 12 + 8
    first, second = tops([text(after=6), flowables.Note('Say it.'), text(before=8)])
    assert second - first == 15 + 6 + 8  # a zero-size note between leaves no space of its own to overlap


def test_J140_the_fit_log_counts_the_notes_under_a_plan_sets_table():
    def build(size, pad):
        rows = [look.heads(['Benefit', 'Plan'], COLOURS, size), look.row(['Deductible', '$1,000'], COLOURS, size)]
        return look.grid(rows, [200, 200], COLOURS, pad=pad)

    _table, found = fit.exhibit(build, 0, notes=2)  # the old fit report's `notes`: long values moved under the table
    assert found['notes'] == 2 and found['outcome'] == 'fits'
