"""The Export viewer's Excel view: the client spreadsheet as Excel will show it, one tab a request (plan.md §7.12,
§8.14, §9.4; J107, J116–J118; old `workbook_preview.py` at 891f1b3, D-194).

`preview(deal, tab)` builds the download's own sheet model (`workbook.build`), never a file kept anywhere, and answers
the tab list (each tab's check counts, for its dot) with one tab worked into the grid's shape:
- its look is `look(write(model))`: what documents' look reader (the Documents viewer's, for an uploaded workbook)
  reads from the tab as the download's writer writes it (fills, fonts, borders, merges, widths, heights), worked out
  from the model by `viewer.look` without the round trip, and held to it by the tests, so the screen is the file;
- each value is the model's (a formula's stored result: quotes' math, no evaluator, J119), drawn through its number
  format (`workbook.text`), folded into the look with the format's colour, the conditional fills that hold now and
  Excel's alignment for numbers;
- frozen panes, zoom, gridlines, drop-downs (prompt and list, read-only), the Cover's pictures, the printed pages
  (`workbook_pages`) and the checks (`workbook_checks`).
It writes nothing (Q.3 #2): the option numbers it prints are predicted, as the download's are. Pure but for the read.
"""

import base64
import io
import re

from PIL import Image

from deals import clock

from ..workbook import build, facts, write
from ..workbook import text as t
from . import fills, workbook_pages
from .look import model_look
from .workbook_checks import ERROR, LOGICAL, NUMBER, TabCells, value_of

FILE = 'workbook'
MAX_PREVIEW_ROWS = 2500  # a tab ships at most this many rows; past it the tab says how many the download has
MAX_LIST = 2000  # a drop-down's list, as shown
PROMPT_TITLE = write.PROMPT_TITLE
_SOURCE = re.compile(r"'((?:[^']|'')+)'!\$([A-Z]{1,3})\$([0-9]+):\$([A-Z]{1,3})\$([0-9]+)")


def _col_number(letters):
    number = 0
    for ch in letters:
        number = number * 26 + ord(ch) - 64
    return number


def _drop_list(book, source):
    """The texts a drop-down offers: the column of the tab its source names, as the cells show them."""
    match = _SOURCE.fullmatch(source)
    sheet = book.by_title(match.group(1).replace("''", "'")) if match else None
    if sheet is None:
        return []
    col, first, last = _col_number(match.group(2)), int(match.group(3)), int(match.group(5))
    out = []
    for row in range(first, last + 1):
        cell = sheet.get(row, col)
        shown = t.display(value_of(cell), (cell.style or {}).get('num_format') if cell else None)[0]
        if shown:
            out.append(shown)
        if len(out) >= MAX_LIST:
            break
    return out


def _dropdowns(book, sheet):
    return [
        {
            'cells': [[rule['cells'][0] - 1, rule['cells'][1] - 1, rule['cells'][2] - 1, rule['cells'][3] - 1]],
            'title': PROMPT_TITLE if rule['prompt'] else '',
            'prompt': rule['prompt'],
            'list': _drop_list(book, rule['source']),
        }
        for rule in sheet.validations
    ]


def _images(sheet):
    out = []
    for image in sheet.images:
        data = image['data']
        try:
            width, height = Image.open(io.BytesIO(data)).size
        except Exception:  # noqa: BLE001 - a picture we cannot read is left off, never an error
            continue
        kind = 'jpeg' if data[:3] == b'\xff\xd8\xff' else 'png'
        out.append(
            {
                'r': image['row'] - 1,
                'c': image['col'] - 1,
                'w': round(width * image.get('x_scale', 1)),
                'h': round(height * image.get('y_scale', 1)),
                'src': f'data:image/{kind};base64,' + base64.b64encode(data).decode('ascii'),
            }
        )
    return out


def _folded(found, cells, colours, sheet, shown):
    """(styles, looks): the look's per-cell styles with what the value adds, each distinct style once."""
    lit = fills.conditional_fills(sheet)
    flags = {(item[0], item[1]): item[3] for item in cells}
    styles, index, looks = [{}], {(): 0}, []
    for r in range(shown):
        ids = []
        for c, base_id in enumerate(found['cells'][r] if r < len(found['cells']) else []):
            style = dict(found['styles'][base_id])
            if (r + 1, c + 1) in lit:
                style['bg'] = lit[(r + 1, c + 1)]
            if (r, c) in colours:
                style['fg'] = colours[(r, c)]
            flag = flags.get((r, c), 0)
            if flag & (ERROR | LOGICAL):
                style.setdefault('ha', 'center')
            elif flag & NUMBER:
                style.setdefault('ha', 'right')
            key = tuple(sorted(style.items()))
            if key not in index:
                index[key] = len(styles)
                styles.append(style)
            ids.append(index[key])
        looks.append(ids)
    return styles, looks


def tab_payload(book, sheet, worked=None):
    """One tab in the grid's shape (the module docstring)."""
    worked = worked or TabCells(sheet, MAX_PREVIEW_ROWS)
    cells, checks, counts, _unknown = worked.run()
    rows, cols, shown = worked.rows, worked.cols, worked.shown
    found = model_look(sheet, shown, cols)
    styles, looks = _folded(found, cells, worked.colours, sheet, shown)
    freeze = {'rows': sheet.freeze[0] - 1, 'cols': sheet.freeze[1] - 1} if sheet.freeze else None
    return {
        'title': sheet.title,
        'rows': shown,
        'cols': cols,
        'col_px': found['col_px'],
        'row_px': [px if px is not None else found['default_row_px'] for px in found['row_px']],
        'merges': found['merges'],
        'freeze': freeze,
        'zoom': int(sheet.zoom or 100),
        'gridlines': not sheet.print,
        'styles': styles,
        'looks': looks,
        'cells': cells,
        'dropdowns': _dropdowns(book, sheet),
        'images': _images(sheet),
        'checks': checks,
        'counts': counts,
        'print': workbook_pages.print_summary(sheet),
        'cut': None if shown == rows else {'shown': shown, 'total': rows},
    }


def from_book(book, tab=None, *, draft=False):
    """The preview of a built sheet model: every tab's title and check counts, and `tab` (else the tab the file opens
    on) worked out in full."""
    titles = book.titles()
    opens_on = titles[book.opens_on] if titles else ''
    wanted = tab if tab in titles else opens_on
    tabs, chosen = [], None
    for sheet in book.sheets:
        worked = TabCells(sheet, MAX_PREVIEW_ROWS)
        counts = worked.run()[2]
        tabs.append({'title': sheet.title, 'counts': counts, 'capped': worked.rows > MAX_PREVIEW_ROWS})
        if sheet.title == wanted:
            chosen = (sheet, worked)
    return {
        'file': FILE,
        'built_at': clock.now().isoformat(),
        'draft': bool(draft),
        'opens_on': opens_on,
        'tabs': tabs,
        'tab': tab_payload(book, *chosen) if chosen else None,
    }


def preview(deal, tab=None):
    """The Excel view of `deal`'s client spreadsheet as it would download now. Raises `build.NothingToPresent` with
    the download's own sentence when no line has a tab."""
    found = facts.read_deal(deal)
    return from_book(build.from_facts(found), tab, draft=bool(found.draft))
