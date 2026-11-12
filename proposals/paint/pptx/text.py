"""Recorded text frames as PowerPoint text (plan.md §9.6; J141, J142; J.6.10). Ported from old Vantage 891f1b3
`pipeline/proposal_deck.py` (`_write_run`, `_write_paragraph`, `_rich_text`).

A text frame's measured paragraphs are written back as their runs, one PowerPoint paragraph per typed line break,
adjoining runs of one style merged, so PowerPoint wraps them itself (Arial has Helvetica's metrics, J142) and an edit
re-flows the way a reader expects. Each text box is its recorded frame (plan.md §9.6), unkerned as the layout
measured it, so the same measure at the same width breaks the same lines; a wrapping box only gains `TEXT_SLACK` on the
side its words never reach, for a renderer's rounding. A frame marked `title` fills the slide's title placeholder, in
place, so the outline and the navigator read; the page number is a live field, without "of M".
"""

from pptx.enum.text import PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Pt

from ...layout import tokens
from .units import FAMILY, bare, emu, rgb, slack_sides, unkerned

ALIGN = {'l': PP_ALIGN.LEFT, 'c': PP_ALIGN.CENTER, 'r': PP_ALIGN.RIGHT}
SLIDE_NUMBER_FIELD = '{B6F15528-21DE-4FAA-801E-634DDDAF4B2B}'
STYLE = ('size', 'color', 'bold', 'italic', 'link')


def pieces(para):
    """A recorded paragraph's runs split at its typed line breaks: [[run]], adjoining runs of one style merged."""
    out = [[]]
    for run in para['runs']:
        for number, text in enumerate(str(run['text']).split('\n')):
            if number:
                out.append([])
            if not text:
                continue
            last = out[-1][-1] if out[-1] else None
            if last and all(last.get(key) == run.get(key) for key in STYLE):
                last['text'] += text
            else:
                out[-1].append(dict(run, text=text))
    return out


def _run(paragraph, run, inherit=False, field=False):
    piece = paragraph.add_run()
    piece.text = run['text']
    unkerned(piece._r.get_or_add_rPr())
    font = piece.font
    if not inherit:
        font.name = FAMILY
        font.size = Pt(run['size'])
        font.bold = bool(run['bold'])
        font.italic = bool(run['italic'])
        font.color.rgb = rgb(run['color'])
    if run.get('link'):
        piece.hyperlink.address = run['link']
    if field:
        element = piece._r
        element.tag = qn('a:fld')
        element.set('id', SLIDE_NUMBER_FIELD)
        element.set('type', 'slidenum')
    return piece


def _paragraph(paragraph, para, runs, inherit=False, field=False):
    if not inherit:
        paragraph.alignment = ALIGN.get(para['align'], PP_ALIGN.LEFT)
        paragraph.line_spacing = Pt(para['leading'])
    paragraph.space_before = Pt(0)
    paragraph.space_after = Pt(0)
    for run in runs:
        _run(paragraph, run, inherit=inherit, field=field)
    # An empty paragraph is otherwise 18 points tall, which would grow its box or its row.
    paragraph._p.get_or_add_endParaRPr().set('sz', str(int(round(para['size'] * 100))))


def write(text_frame, paragraphs, field=False):
    """A frame's measured paragraphs into `text_frame` (its first paragraph reused)."""
    first = True
    for para in paragraphs:
        for runs in pieces(para):
            paragraph = text_frame.paragraphs[0] if first else text_frame.add_paragraph()
            first = False
            _paragraph(paragraph, para, runs, field=field)


def box_of(it):
    """(x, y, w, h) of a text frame's box: the recorded frame; a wrapping one with its slack on the free side."""
    x, w = it['x'], it['w']
    if it.get('wrap', True):
        left, right = slack_sides(it['paragraphs'])
        x, w = x - left, w + left + right
    return x, it['y'], w, it['h']


def place(shape, it):
    x, y, w, h = box_of(it)
    shape.left, shape.top, shape.width, shape.height = emu(x), emu(y), emu(w), emu(h)


def text_box(slide, it, _pictures=None, field=False):
    x, y, w, h = box_of(it)
    box = slide.shapes.add_textbox(emu(x), emu(y), emu(w), emu(h))
    frame = box.text_frame
    bare(frame)
    frame.word_wrap = bool(it.get('wrap', True))
    write(frame, it['paragraphs'], field=field)
    return box


def number_box(slide, it):
    """The page number where the chrome put it, as a field that follows the slide's own place in the deck."""
    return text_box(slide, it, field=True)


def content_title(slide, it):
    """A content page's title in its placeholder, which keeps the master's place and type (26 pt, bold, the brand's
    navy, J139): only a title the layout stepped down to fit one line carries its own size."""
    holder = slide.shapes.title
    frame = holder.text_frame
    largest = tokens.TITLE_TYPE[0]
    first = True
    for para in it['paragraphs']:
        for runs in pieces(para):
            paragraph = frame.paragraphs[0] if first else frame.add_paragraph()
            first = False
            _paragraph(paragraph, para, runs, inherit=True)
            for run, written in zip(runs, paragraph.runs, strict=True):
                if run['size'] != largest:
                    written.font.size = Pt(run['size'])
    return holder


def page_title(slide, it):
    """A whole page's title (the cover's client, the agenda, a divider, Thank you) in the placeholder, moved to its
    recorded frame and written as recorded; it rises to where the frame was recorded, above what came before."""
    holder = slide.shapes.title
    place(holder, it)
    frame = holder.text_frame
    bare(frame)
    frame.word_wrap = bool(it.get('wrap', True))
    write(frame, it['paragraphs'])
    tree = slide.shapes._spTree
    tree.remove(holder._element)
    tree.append(holder._element)
    return holder
