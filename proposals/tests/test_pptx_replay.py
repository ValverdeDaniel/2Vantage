"""The PowerPoint's replay on a small synthetic deck (plan.md §9.6; J141, J142). Pure: no database. The deck is laid out
the way the story lays it out (`layout.record.lay_out`), then painted twice; what GD1 does not show is pinned here: the
dark layout with the mark, a brand of another firm and its uploaded logo on the master, a section divider's title in
its placeholder, a long paragraph re-measured at its box, and the guard against a frame the PowerPoint cannot
replay."""

import io

import pytest
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.oxml.ns import qn

from proposals.layout import flowables, furniture, record, tokens
from proposals.layout import text as words
from proposals.paint import pptx
from proposals.paint.pptx import frames
from synthetic_files import png

BRAND = '#7a1f3d'  # another firm's colour: the master, the title and the ground follow it
COLOURS = furniture.palette(BRAND)
CHROME = {
    'stamp': 'Sample Co (synthetic) · Prepared November 12, 2026',
    'note': tokens.DISCLAIMER,
    'firm': 'Sample Agency',
    'logo': 'logo:agency',  # the firm's upload, by the name the frames use
    'draft': False,
    'colours': COLOURS,
}
LONG = 'Each carrier quoted the plans on the census it was given, and the rates hold until the effective date. ' * 6


def _story():
    cover = furniture.cover_items({'client': 'Sample Co (synthetic)', 'kind': '2027 Benefits Proposal'}, COLOURS)
    divider = furniture.section_items(2, 'Medical', 'What we found', COLOURS)
    body = [
        flowables.Title('What we found'),
        flowables.Text([words.run(LONG, 13, COLOURS['ink'])], leading=19),
        flowables.Note('Say the renewal first.'),
    ]
    return [
        [flowables.FullPage(cover, ground=furniture.dark_ground(COLOURS), title='Sample Co (synthetic)')],
        [flowables.FullPage(divider, ground=furniture.dark_ground(COLOURS), title='Medical')],
        body,
    ]


def _deck():
    pages = record.lay_out(_story(), CHROME)
    data = pptx.draw(pages, 'Sample Co (synthetic) — Proposal', {'logo:agency': png()})
    return pages, Presentation(io.BytesIO(data))


def test_S31_J141_a_dark_page_stands_on_the_dark_layout_its_ground_lifted_once():
    pages, deck = _deck()
    assert [slide.slide_layout.name for slide in deck.slides] == [
        'Proposal dark page',
        'Proposal dark page',
        'Proposal content',
    ]
    dark = next(layout for layout in deck.slide_layouts if layout.name == 'Proposal dark page')
    ground = [shape.shape_type for shape in dark.shapes if not shape.is_placeholder]
    assert ground == [MSO_SHAPE_TYPE.AUTO_SHAPE, MSO_SHAPE_TYPE.PICTURE]  # the lift and the mark
    stops = dark.shapes[0]._element.findall('.//' + qn('a:gs'))
    assert [stop.find(qn('a:srgbClr')).get('val') for stop in stops] == [
        COLOURS['navy_dark'].lstrip('#').upper(),
        BRAND.lstrip('#').upper(),
    ]
    mark = furniture.dark_ground(COLOURS)[1]
    for slide in list(deck.slides)[:2]:  # a slide may hold a logo, never the mark again
        sizes = [round(s.width / 12700) for s in slide.shapes if s.shape_type == MSO_SHAPE_TYPE.PICTURE]
        assert round(mark['w']) not in sizes
    assert [slide.shapes.title.text_frame.text for slide in deck.slides] == [p['title'] for p in pages]


def test_S31_J141_J139_the_master_takes_the_brand_and_the_draftless_chrome():
    _pages, deck = _deck()
    master = deck.slide_master
    style = master._element.find(qn('p:txStyles')).find(qn('p:titleStyle')).find(qn('a:lvl1pPr'))
    defaults = style.find(qn('a:defRPr'))
    assert defaults.get('sz') == '2600' and defaults.get('b') == '1'
    assert defaults.find('.//' + qn('a:srgbClr')).get('val') == BRAND.lstrip('#').upper()
    on_master = ' '.join(shape.text_frame.text for shape in master.shapes if shape.has_text_frame)
    assert 'SAMPLE AGENCY' in on_master and 'Draft' not in on_master  # an issued file wears no Draft (OQ35)
    logos = [shape for shape in master.shapes if shape.shape_type == MSO_SHAPE_TYPE.PICTURE]
    assert len(logos) == 1 and logos[0].image.blob == png()  # lifted with its picture, once for every slide
    for slide in deck.slides:
        assert not [shape for shape in slide.shapes if getattr(shape, 'image', None) and shape.image.blob == png()]


def test_S31_J142_a_long_paragraph_breaks_where_the_layout_broke_it():
    pages, deck = _deck()
    recorded = next(it for it in pages[2]['frames'] if it['t'] == 'text')
    box = next(
        s for s in deck.slides[2].shapes if s.shape_type == MSO_SHAPE_TYPE.TEXT_BOX and len(s.text_frame.text) > 50
    )
    runs = [words.run(r.text, r.font.size.pt, '#000', bool(r.font.bold)) for r in box.text_frame.paragraphs[0].runs]
    assert len(recorded['paragraphs'][0]['lines']) > 3
    assert len(words.lines_of(runs, box.width / 12700)) == len(recorded['paragraphs'][0]['lines'])
    assert box.text_frame.paragraphs[0].line_spacing.pt == 19
    assert deck.slides[2].notes_slide.notes_text_frame.text == 'Say the renewal first.'


def test_S31_J141_a_frame_the_powerpoint_cannot_replay_stops_the_file():
    deck = Presentation()
    slide = deck.slides.add_slide(deck.slide_layouts[6])
    with pytest.raises(frames.DeckError):
        frames.paint(slide, {'t': 'pie'}, None)
