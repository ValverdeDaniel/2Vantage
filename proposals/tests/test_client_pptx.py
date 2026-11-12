"""The client PowerPoint of GD1 (plan.md §13.8 row 31, "done when": the .pptx opens with the old master, native charts
and notes, slide for slide like the PDF; J141, J142; J.6.10: each pptx text box equals its recorded frame and fits by
the same measure; Q.8 client canaries in pptx shapes, notes, layouts and charts)."""

import io

import pytest
from pptx import Presentation
from pptx.enum.chart import XL_CHART_TYPE
from pptx.enum.dml import MSO_FILL
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.oxml.ns import qn
from pypdf import PdfReader

from deals.downloads import safe_filename
from deals.models import Activity
from proposals.layout import items, tokens
from proposals.layout import text as measure
from proposals.paint import pdf, pptx
from proposals.story import build
from quotes import services as plans

pytestmark = pytest.mark.django_db

LAYOUTS = ['Proposal dark page', 'Proposal plain page', 'Proposal photo page', 'Proposal content']


@pytest.fixture(scope='module')
def built(gd1, django_db_blocker):
    """GD1's recorded pages and its PowerPoint, built once for the module (read-only)."""
    with django_db_blocker.unblock():
        found = build.deck(gd1.deal)
    data = pptx.draw(found['pages'], found['title'], found['sources'])
    return found, Presentation(io.BytesIO(data)), data


def _download(api, deal):
    response = api.get(f'/api/deals/{deal.id}/proposal/files/pptx/')
    assert response.status_code == 200
    assert response['Content-Type'] == 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
    name = safe_filename(f'{deal.client.name} - Proposal.pptx')
    assert response['Content-Disposition'] == f'attachment; filename="{name}"'
    return Presentation(io.BytesIO(b''.join(response.streaming_content)))


def _pt(value):
    return value / 12700


def _close(one, other, tolerance=0.01):
    return abs(one - other) <= tolerance


def _recorded_text(it):
    return '\n'.join(''.join(run['text'] for run in para['runs']) for para in it['paragraphs'])


def _text_frames(page):
    """(title frame, [the other text frames in paint order]) as the page recorded them."""
    if page['kind'] == 'full':
        texts = [it for it in page['frames'] if it['t'] == 'text']
        title = next((it for it in texts if it.get('title')), None)
        return title, [it for it in texts if it is not title]
    title = next(it for it in page['chrome'] if it['t'] == 'text' and it.get('title'))
    number = next(it for it in page['chrome'] if it['t'] == 'text' and items.plain(it) == str(page['n']))
    return title, [number] + [it for it in page['frames'] if it['t'] == 'text']


def _runs_back(text_frame):
    """The words a text frame holds, as layout runs: one line break between PowerPoint paragraphs."""
    runs = []
    for number, paragraph in enumerate(text_frame.paragraphs):
        if number and runs:
            runs[-1] = dict(runs[-1], text=runs[-1]['text'] + '\n')
        for run in paragraph.runs:
            font = run.font
            assert font.name == tokens.FONTS['family']  # J142: Arial, Helvetica's metrics
            assert run._r.rPr.get('kern') == '0'  # measured unkerned, written unkerned
            runs.append(measure.run(run.text, font.size.pt, '#000000', bool(font.bold), bool(font.italic)))
    return runs


def _same_lines(it, text_frame, room):
    """The words read back break, at the recorded width, into the recorded lines; at the box's room, into as many."""
    if not it.get('wrap', True):
        return
    runs = _runs_back(text_frame)
    recorded = [[''.join(seg['text'] for seg in line) for line in para['lines']] for para in it['paragraphs']]
    again = [''.join(seg['text'] for seg in line) for line in measure.lines_of(runs, it['w'])]
    assert again == [line for lines in recorded for line in lines]
    assert len(measure.lines_of(runs, room)) == len(again)


def _box_is_frame(shape, it):
    """A text box is its recorded frame: its top and height, the edge its words hang from, and at most TEXT_SLACK
    wider, only when it wraps."""
    left, width = _pt(shape.left), _pt(shape.width)
    assert _close(_pt(shape.top), it['y']) and _close(_pt(shape.height), it['h'])
    aligns = {para['align'] for para in it['paragraphs']}
    if aligns == {'l'}:
        assert _close(left, it['x'])
    elif aligns == {'r'}:
        assert _close(left + width, it['x'] + it['w'])
    else:
        assert _close(left + width / 2, it['x'] + it['w'] / 2)
    assert it['w'] - 0.01 <= width <= it['w'] + (1.01 if it.get('wrap', True) else 0.01)
    assert shape.text_frame.text == _recorded_text(it)
    _same_lines(it, shape.text_frame, width)


def test_S31_J141_GD1_the_pptx_is_the_pdf_slide_for_slide(built):
    found, deck, _data = built
    pages = found['pages']
    reader = PdfReader(io.BytesIO(pdf.draw(pages, found['title'], found['sources'])))
    assert len(deck.slides) == len(pages) == len(reader.pages)
    assert (_pt(deck.slide_width), _pt(deck.slide_height)) == tokens.DECK_SIZE
    assert deck.core_properties.title == found['title'] and deck.core_properties.author == ''
    assert [layout.name for layout in deck.slide_layouts] == LAYOUTS
    for page, slide, sheet in zip(pages, deck.slides, reader.pages, strict=True):
        assert slide.shapes.title is not None and slide.shapes.title.text_frame.text  # every slide titled
        assert slide.shapes.title.text_frame.text == page['title']
        assert slide.shapes.title.text_frame.text.split('\n')[0] in sheet.extract_text().replace('\n', ' ')
        expected = 'Proposal content' if page['kind'] == 'content' else 'Proposal photo page'  # GD1's have pictures
        assert slide.slide_layout.name == expected


def test_S31_J141_J139_the_master_wears_the_chrome_once(built):
    _found, deck, _data = built
    master = deck.slide_master
    on_master = ' '.join(shape.text_frame.text for shape in master.shapes if shape.has_text_frame)
    for words in ('Golden Manufacturing (synthetic) · Prepared', tokens.DISCLAIMER, 'VANTAGE RISK SOLUTIONS'):
        assert words in on_master
    assert 'Draft for review, not for clients' in on_master  # OQ35: every page of a draft
    layouts = {layout.name: layout for layout in deck.slide_layouts}
    assert layouts['Proposal content']._element.get('showMasterSp') in (None, '1')
    for name in ('Proposal dark page', 'Proposal plain page', 'Proposal photo page'):
        assert layouts[name]._element.get('showMasterSp') == '0'
    ground = [shape.shape_type for shape in layouts['Proposal photo page'].shapes if not shape.is_placeholder]
    assert ground == [MSO_SHAPE_TYPE.AUTO_SHAPE]  # the gradient, lifted once: no slide repeats it
    for slide in deck.slides:
        own = [shape.text_frame.text for shape in slide.shapes if shape.has_text_frame]
        assert tokens.DISCLAIMER not in own and 'VANTAGE RISK SOLUTIONS' not in own  # the chrome's lines
        assert all(holder.text_frame.text for holder in slide.placeholders)
        shapes = [shape for shape in slide.shapes if shape.shape_type == MSO_SHAPE_TYPE.AUTO_SHAPE]
        assert MSO_FILL.GRADIENT not in [shape.fill.type for shape in shapes]  # the ground: on its layout only


def test_S31_J141_page_numbers_are_live_fields_without_of_M(built):
    found, deck, _data = built
    for number, (page, slide) in enumerate(zip(found['pages'], deck.slides, strict=True), start=1):
        fields = [f for shape in slide.shapes for f in shape._element.iter(qn('a:fld'))]
        if page['kind'] == 'full':
            assert fields == []
            continue
        assert [(f.get('type'), f.find(qn('a:t')).text) for f in fields] == [('slidenum', str(number))]


def test_S31_J141_J128_the_premium_chart_is_native_and_the_notes_are_the_pages(built):
    found, deck, _data = built
    charts = 0
    for page, slide in zip(found['pages'], deck.slides, strict=True):
        notes = slide.notes_slide.notes_text_frame.text if slide.has_notes_slide else ''
        assert notes == '\n\n'.join(page['notes'])
        recorded = [it for it in page['frames'] if it['t'] == 'bars']
        drawn = [shape.chart for shape in slide.shapes if shape.has_chart]
        assert len(drawn) == len(recorded)
        for it, chart in zip(recorded, drawn, strict=True):
            charts += 1
            assert chart.chart_type == XL_CHART_TYPE.COLUMN_CLUSTERED and len(it['categories']) >= 2
            assert list(chart.plots[0].categories) == it['categories']
            assert [(s.name, list(s.values)) for s in chart.plots[0].series] == [
                (entry['name'], [float(v) for v in entry['values']]) for entry in it['series']
            ]
    assert charts == 1  # GD1's "What you pay today and what we recommend"
    assert any(page['notes'] for page in found['pages'])


def test_S31_J_6_10_each_text_box_equals_its_recorded_frame_and_fits_by_the_same_measure(built):
    found, deck, _data = built
    for page, slide in zip(found['pages'], deck.slides, strict=True):
        title, texts = _text_frames(page)
        holder = slide.shapes.title
        assert holder.text_frame.text == _recorded_text(title)
        if page['kind'] == 'full':
            _box_is_frame(holder, title)
        else:  # the master's title zone, which centres the recorded line
            assert _close(_pt(holder.left), title['x'])
            assert _close(_pt(holder.top) + _pt(holder.height) / 2, title['y'] + title['h'] / 2)
            size = title['paragraphs'][0]['runs'][0]['size']
            written = holder.text_frame.paragraphs[0].runs[0].font.size
            assert (written.pt if written else tokens.TITLE_TYPE[0]) == size
        boxes = [shape for shape in slide.shapes if shape.shape_type == MSO_SHAPE_TYPE.TEXT_BOX]
        assert len(boxes) == len(texts)
        for shape, it in zip(boxes, texts, strict=True):
            _box_is_frame(shape, it)


def test_S31_J133_J141_each_table_is_its_recorded_grid(built):
    found, deck, _data = built
    tables = 0
    for page, slide in zip(found['pages'], deck.slides, strict=True):
        recorded = [it for it in page['frames'] if it['t'] == 'table']
        drawn = [shape for shape in slide.shapes if shape.has_table]
        assert len(drawn) == len(recorded)
        for it, shape in zip(recorded, drawn, strict=True):
            tables += 1
            grid = shape.table
            assert _close(_pt(shape.left), it['x']) and _close(_pt(shape.top), it['y'])
            assert all(_close(_pt(c.width), w) for c, w in zip(grid.columns, it['cols'], strict=True))
            assert all(_close(_pt(r.height), h) for r, h in zip(grid.rows, it['row_h'], strict=True))
            for cell in it['cells']:
                written = grid.cell(cell['row'], cell['col'])
                span = cell.get('span') or 1
                assert written.span_width == span
                assert written.text_frame.text == _recorded_text(cell['text'])
                room = sum(it['cols'][cell['col'] : cell['col'] + span])
                room -= _pt(written.margin_left) + _pt(written.margin_right)
                _same_lines(cell['text'], written.text_frame, room)
    assert tables >= 10


def test_Q3_S31_the_download_writes_only_its_downloaded_row(api, gd1):
    before = set(Activity.objects.filter(deal=gd1.deal).values_list('id', flat=True))
    deck = _download(api, gd1.deal)
    assert len(deck.slides) == len(build.deck(gd1.deal)['pages'])
    added = Activity.objects.filter(deal=gd1.deal).exclude(id__in=before)
    assert [(row.action, row.summary, row.area) for row in added] == [
        ('downloaded', 'Downloaded the client PowerPoint (draft)', 'proposal')
    ]


def _every_word(deck):
    """Every word a client could find in the file: shapes (tables included), notes, the master, its layouts, charts,
    the properties."""
    words = [deck.core_properties.title or '', deck.core_properties.subject or '', deck.core_properties.keywords or '']
    owners = [deck.slide_master, *deck.slide_layouts, *deck.slides]
    for owner in owners:
        for shape in owner.shapes:
            if shape.has_text_frame:
                words.append(shape.text_frame.text)
            if getattr(shape, 'has_table', False) and shape.has_table:
                words += [cell.text_frame.text for row in shape.table.rows for cell in row.cells]
            if getattr(shape, 'has_chart', False) and shape.has_chart:
                plot = shape.chart.plots[0]
                words += [str(c) for c in plot.categories] + [s.name for s in plot.series]
    for slide in deck.slides:
        if slide.has_notes_slide:
            words.append(slide.notes_slide.notes_text_frame.text)
    return ' '.join(words)


def test_Q9_S31_client_canaries_never_reach_the_pptx(api, gd1, user):
    plans.update_plan(user, gd1.refs['A'], {'notes': 'Zqcanarynote', 'values': {'network': 'Zqclientnetwork'}})
    plans.update_plan(user, gd1.refs['CG1'], {'values': {'mental_health_outpatient': 'Zqcanarymental'}})
    plans.star(user, gd1.deal, [gd1.refs['CG2']], True, reason='Zqcanarystar')
    words = _every_word(_download(api, gd1.deal))
    assert 'Zqclientnetwork' in words  # a client field prints
    assert 'Medical — Replacing: Aetna Open Access HDHP 3300 (continued)' in words  # J140, a slide of its own
    for canary in ('Zqcanarynote', 'Zqcanarymental', 'Zqcanarystar'):
        assert canary not in words
