"""The one layout pass (plan.md §9.5; J122, J139, J140, J142; Q.9 row 29: layout cases, type floors). Pure: no
database. Tables are built here the way the story builds them, then fitted, laid out and drawn."""

import io
import json

from pypdf import PdfReader

from proposals.layout import chrome, fit, flowables, furniture, items, record, tokens
from proposals.layout import table as tb
from proposals.layout import text as words
from proposals.paint import pdf

COLOURS = furniture.palette(None)
CHROME = {
    'stamp': 'Sample Co (synthetic) · Prepared November 12, 2026',
    'note': tokens.DISCLAIMER,
    'firm': 'Sample Agency',
    'logo': None,
    'draft': True,
    'colours': COLOURS,
}


def _table(rows, label='Benefit', cols=4, value='$1,000', long_label=''):
    def build(size, pad):
        head = {
            'kind': 'head',
            'cells': [tb.cell('', size, '#fff')] + [tb.cell(f'Plan {n}', size, '#fff', True, 'c') for n in range(cols)],
        }
        body = [
            {
                'kind': 'row',
                'cells': [tb.cell(long_label or f'{label} {n}', size, COLOURS['ink2'])]
                + [tb.cell(value, size, COLOURS['ink'], align='c') for _ in range(cols)],
            }
            for n in range(rows)
        ]
        return tb.Table([head, *body], [tokens.LABEL_W] + [150] * cols, COLOURS, pad=pad)

    return build


def _sizes(page):
    """Every type size a page's frames print, chrome included."""
    found = []

    def walk(item):
        if item['t'] == 'text':
            found.extend(seg['size'] for para in item['paragraphs'] for line in para['lines'] for seg in line)
        elif item['t'] == 'table':
            for cell in item['cells']:
                walk(cell['text'])

    for item in page['frames'] + page['chrome']:
        walk(item)
    return found


def test_J140_a_table_that_fits_takes_the_largest_type():
    table, size, pad = fit.fitted(_table(8), tokens.BODY_H)
    assert size == tokens.TABLE_TYPE['cell']
    assert pad == tokens.PADS[0]


def test_J140_type_steps_down_to_the_floor_and_never_below():
    found = fit.fitted(_table(26), tokens.BODY_H)
    assert found is not None
    assert tokens.TABLE_TYPE['floor'] <= found[1] < tokens.TABLE_TYPE['cell']
    assert fit.fitted(_table(120), tokens.BODY_H) is None
    table, outcome = fit.exhibit(_table(120), 0)
    assert outcome['outcome'] == 'runs_on'
    assert outcome['size'] == tokens.TABLE_TYPE['floor']


def test_J140_notes_follow_when_the_table_and_its_notes_cannot_share_a_page():
    build = _table(20)
    _table_, alone = fit.exhibit(build, 0)
    assert alone['outcome'] == 'fits'
    floor = build(tokens.TABLE_TYPE['floor'], tokens.TIGHTEST_PAD).wrap(tokens.BODY_W, 10**6)[1]
    _table_, crowded = fit.exhibit(build, tokens.BODY_H - floor + 10)
    assert crowded['outcome'] == 'notes_follow'
    assert crowded['size'] == alone['size']  # the table stays whole and as large; its notes go on


def test_J140_benefit_rows_keep_to_two_lines_where_smaller_type_helps():
    label = 'Diagnostic tests, x-ray and blood work at a free-standing facility'
    build = _table(4, long_label=label, cols=2)
    table, size, _pad = fit.fitted(build, tokens.BODY_H, short_rows=True)
    assert table.rows_over() == 0
    assert build(tokens.TABLE_TYPE['cell'], 3.5).rows_over() > 0
    assert size < tokens.TABLE_TYPE['cell']


def test_J140_long_values_move_to_numbered_notes_one_note_per_sentence():
    shared = {}
    sentence = 'Covered in full after the deductible when the member uses a designated facility in the network area.'
    assert fit.noted(sentence, 'Imaging', 'Aetna', shared) == 'See note 1'
    assert fit.noted(sentence, 'Imaging', 'Cigna', shared) == 'See note 1'
    assert fit.noted('$250', 'Imaging', 'Cigna', shared) == '$250'
    assert fit.notes_of(shared) == [f'1. Aetna, Cigna, Imaging: {sentence}']


def test_J140_a_table_too_long_runs_on_continued_with_its_header_repeated():
    table, outcome = fit.exhibit(_table(90), 0)
    story = [[flowables.Title('Medical — plan comparison', line='medical', fit=outcome), table]]
    pages = record.lay_out(story, CHROME)
    assert len(pages) >= 2
    assert pages[0]['title'] == 'Medical — plan comparison' and not pages[0]['continued']
    for page in pages[1:]:
        assert page['title'] == 'Medical — plan comparison (continued)'
        assert page['continued'] and page['line'] == 'medical'
        frame = next(item for item in page['frames'] if item['t'] == 'table')
        assert frame['cells'][0]['kind'] == 'head'
    rows = sum(
        max(cell['row'] for cell in item['cells']) for p in pages for item in p['frames'] if item['t'] == 'table'
    )
    assert rows == 90  # every benefit row printed once, the header again on every page
    assert min(_sizes(pages[1])) >= 6.5  # the footer's rates note is the chrome's own small print
    table_sizes = [
        seg['size']
        for p in pages
        for item in p['frames']
        if item['t'] == 'table'
        for cell in item['cells']
        for para in cell['text']['paragraphs']
        for line in para['lines']
        for seg in line
    ]
    assert min(table_sizes) == tokens.TABLE_TYPE['floor']


def test_J140_a_table_never_runs_past_the_body():
    table, outcome = fit.exhibit(_table(90), 0)
    pages = record.lay_out([[flowables.Title('Dental'), table]], CHROME)
    for page in pages:
        for item in page['frames']:
            assert item['y'] >= tokens.BODY_TOP - 0.01
            assert item['y'] + item['h'] <= tokens.BODY_TOP + tokens.BODY_H + 0.01


def test_J139_a_title_steps_down_from_26_to_16_points_and_no_further():
    short = chrome.title_item('Next steps', COLOURS)
    assert short['paragraphs'][0]['size'] == 26
    long = chrome.title_item('Medical — Replacing: ' + 'Aetna Open Access HDHP 3300 Choice POS II PPO ' * 3, COLOURS)
    assert long['paragraphs'][0]['size'] == 16
    middle = chrome.title_item('Medical — Replacing: Aetna Open Access HDHP 3300 and Choice POS II PPO 1500', COLOURS)
    assert 16 <= middle['paragraphs'][0]['size'] < 26


def test_J139_content_pages_wear_the_chrome_and_full_pages_none():
    cover = flowables.FullPage(furniture.cover_items({'client': 'Sample Co', 'kind': '', 'lines': []}, COLOURS))
    pages = record.lay_out([[cover], [flowables.Title('Next steps'), flowables.Block([], 20)]], CHROME)
    assert pages[0]['kind'] == 'full' and pages[0]['chrome'] == []
    texts = [items.plain(item) for item in pages[1]['chrome'] if item['t'] == 'text']
    assert 'Next steps' in texts
    assert CHROME['stamp'] in texts and tokens.DISCLAIMER in texts and 'SAMPLE AGENCY' in texts
    assert '2' in texts  # the page number, no "of M"
    assert furniture.DRAFT_MARK in texts


def test_J122_words_wrap_by_the_one_measure():
    para = words.paragraph([words.run('one two three four five six seven eight nine ten', 12, '#000')], 80)
    assert len(para['lines']) > 1
    assert all(words.line_width(line) <= 80.01 for line in para['lines'])
    broken = words.paragraph([words.run('Superlongcarriercodewithoutanyspaces', 12, '#000')], 60)
    assert all(words.line_width(line) <= 60.01 for line in broken['lines'])
    typed = words.paragraph([words.run('first\nsecond', 12, '#000')], 400)
    assert [line[0]['text'] for line in typed['lines']] == ['first', 'second']
    marked = words.paragraph([words.run('R&D <b>not bold</b>', 12, '#000')], 400)
    assert marked['lines'][0][0]['text'] == 'R&D <b>not bold</b>'


def test_J122_recorded_pages_are_plain_data_for_the_powerpoint_to_replay():
    table, outcome = fit.exhibit(_table(10), 0)
    pages = record.lay_out([[flowables.Title('Vision'), table, flowables.Note('We recommend VSP.')]], CHROME)
    assert json.loads(json.dumps(pages)) == pages
    assert pages[0]['notes'] == ['We recommend VSP.']


def test_J142_every_word_is_helvetica():
    table, _outcome = fit.exhibit(_table(10), 0)
    pages = record.lay_out([[flowables.Title('Vision'), table]], CHROME)
    fonts = set()
    for item in pages[0]['frames'] + pages[0]['chrome']:
        paras = [c['text'] for c in item['cells']] if item['t'] == 'table' else [item] if item['t'] == 'text' else []
        for frame in paras:
            fonts |= {seg['font'] for para in frame['paragraphs'] for line in para['lines'] for seg in line}
    assert fonts and fonts <= {'Helvetica', 'Helvetica-Bold', 'Helvetica-Oblique'}
    assert tokens.FONTS['family'] == 'Arial'


def test_J122_the_pdf_draws_the_recorded_pages_at_sixteen_by_nine():
    table, outcome = fit.exhibit(_table(90), 0)
    pages = record.lay_out([[flowables.Title('Medical — plan comparison'), table]], CHROME)
    reader = PdfReader(io.BytesIO(pdf.draw(pages, 'Sample')))
    assert len(reader.pages) == len(pages)
    box = reader.pages[0].mediabox
    assert (float(box.width), float(box.height)) == tokens.DECK_SIZE
    assert 'Medical — plan comparison (continued)' in reader.pages[1].extract_text()
    assert reader.metadata.title == 'Sample'
