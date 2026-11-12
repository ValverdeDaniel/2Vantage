"""A recorded plan table as a native PowerPoint table (plan.md §9.6; J133, J141). Ported from old Vantage 891f1b3
`pipeline/proposal_deck.py` (`_rich_table`, `_set_edges`), reading `layout/table.py`'s frame instead of reportlab's
internals (J.5 B14).

The grid is the recorded one: its column widths, its row heights, each cell's fill, span and words, its side padding
(less `TEXT_SLACK` on the side its words never reach, as a text box gains it) and the padding above and below that
centred the tallest cell; the rules become the cells' top and bottom edges. The
"No Style, No Grid" table style lets nothing of PowerPoint's own blue show through, and a row the producer adds looks
like these.
"""

from lxml import etree
from pptx.enum.text import MSO_ANCHOR
from pptx.oxml.ns import qn
from pptx.util import Pt

from . import text as text_
from .units import EMU_PER_POINT, emu, hex_value, rgb, slack_sides

NO_TABLE_STYLE = '{2D5ABB26-0587-4C30-8999-92F81FD0307C}'


def _edges(it):
    """{row boundary: (colour, width)}: boundary k lies above row k. A rule over a row (drawn after the hairline under
    the row before it) is the deliberate one, so it wins."""
    tops = [0.0]
    for height in it['row_h']:
        tops.append(tops[-1] + height)
    out = {}
    for rule in it['rules']:
        at = rule['y1'] - it['y']
        boundary = min(range(len(tops)), key=lambda k: abs(tops[k] - at))
        if abs(tops[boundary] - at) < 0.5:
            out[boundary] = (rule['color'], rule['lw'])
    return out


def _set_edges(cell, top, bottom):
    """The cell's four borders: `top` and `bottom` are (colour, width) or None; DrawingML wants them before the fill."""
    tc_pr = cell._tc.get_or_add_tcPr()
    for tag, edge in (('a:lnL', None), ('a:lnR', None), ('a:lnT', top), ('a:lnB', bottom)):
        for old in tc_pr.findall(qn(tag)):
            tc_pr.remove(old)
        if edge:
            ln = etree.SubElement(tc_pr, qn(tag), w=str(int(edge[1] * EMU_PER_POINT)), cap='flat', cmpd='sng')
            fill = etree.SubElement(ln, qn('a:solidFill'))
            etree.SubElement(fill, qn('a:srgbClr'), val=hex_value(edge[0]))
            etree.SubElement(ln, qn('a:prstDash'), val='solid')
        else:
            ln = etree.SubElement(tc_pr, qn(tag), w='0')
            etree.SubElement(ln, qn('a:noFill'))
    for tag in ('a:solidFill', 'a:noFill'):
        fill = tc_pr.find(qn(tag))
        if fill is not None:
            tc_pr.remove(fill)
            tc_pr.append(fill)


def _pads(it):
    """Each row's padding above and below: half of what its height holds beyond its tallest cell's words."""
    tallest = {}
    for cell in it['cells']:
        tallest[cell['row']] = max(tallest.get(cell['row'], 0.0), cell['text']['h'])
    return [max(0.0, (height - tallest.get(row, 0.0)) / 2) for row, height in enumerate(it['row_h'])]


def _cell(table, data, pad, edges):
    cell = table.cell(data['row'], data['col'])
    if data.get('fill'):
        cell.fill.solid()
        cell.fill.fore_color.rgb = rgb(data['fill'])
    else:
        cell.fill.background()
    words = data['text']
    left = words['x'] - data['x']
    right = data['w'] - words['w'] - left
    more_left, more_right = slack_sides(words['paragraphs'])
    cell.margin_left = Pt(max(0.0, left - more_left))
    cell.margin_right = Pt(max(0.0, right - more_right))
    cell.margin_top = cell.margin_bottom = Pt(pad)
    cell.vertical_anchor = MSO_ANCHOR.MIDDLE
    frame = cell.text_frame
    frame.word_wrap = True
    text_.write(frame, words['paragraphs'])
    for col in range(data['col'], data['col'] + (data.get('span') or 1)):
        _set_edges(table.cell(data['row'], col), edges.get(data['row']), edges.get(data['row'] + 1))


def table(slide, it, _pictures=None):
    cols, heights = it['cols'], it['row_h']
    frame = slide.shapes.add_table(
        len(heights), len(cols), emu(it['x']), emu(it['y']), emu(sum(cols)), emu(sum(heights))
    )
    grid = frame.table
    grid.first_row = False
    grid.horz_banding = False
    grid._tbl.tblPr.find(qn('a:tableStyleId')).text = NO_TABLE_STYLE
    for number, width in enumerate(cols):
        grid.columns[number].width = emu(width)
    for number, height in enumerate(heights):
        grid.rows[number].height = emu(height)
    edges, pads = _edges(it), _pads(it)
    covered = set()
    for data in it['cells']:
        span = data.get('span') or 1
        if span > 1:
            grid.cell(data['row'], data['col']).merge(grid.cell(data['row'], data['col'] + span - 1))
        covered.update((data['row'], col) for col in range(data['col'], data['col'] + span))
    for data in it['cells']:
        _cell(grid, data, pads[data['row']], edges)
    for row in range(len(heights)):
        for col in range(len(cols)):
            if (row, col) not in covered:
                grid.cell(row, col).fill.background()
                _set_edges(grid.cell(row, col), edges.get(row), edges.get(row + 1))
    return frame
