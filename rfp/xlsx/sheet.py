"""One worksheet's XML, patched in place (old `xlsx_fill._Sheet` 891f1b3, unchanged in behaviour; K90).

- **A cell keeps its own style.** A new `<c>` inherits, in order: an explicit style, the nearest row in the same column
  that HAS the cell (searching below the style-source row first: the first data row lacks the top rule the header
  draws), the row's `s` when the row is `customFormat="1"`, then the covering `<col style>` (without that last step
  column X of the Warner census loses its border on every row written).
- **The style decides the type.** A number written into a Text-formatted cell (`numFmtId` 49 / `@`) is stored as text,
  because that is what Excel stores when a person types there (Aetna's ZIP, UHC's ZIP and SIC). A number elsewhere is
  a number, a date a serial. Callers pass typed values; this never guesses a type from a string.
- **A formula is never overwritten**: a stray write is reported as a warning and the formula stays.
- **Clearing never creates.** Blanking a cell with no explicit style drops the element, as Excel does.
- **Strings are written inline** (`t="inlineStr"`), so `sharedStrings.xml` is copied through unchanged, and an inline
  string is inert: typed text starting with `=` lands as typed (K107). Row start tags are kept verbatim apart from
  `spans`, a hint Excel recomputes.
"""

import re
from datetime import date, datetime

from .refs import FillError, col_index, col_letters, escape, split_ref, unescape

# Excel's 1900 date system with its leap-year bug: 1899-12-30 is serial 0 (none of the bundled workbooks uses 1904).
EPOCH = date(1899, 12, 30)
TEXT_NUMFMT = 49  # the builtin Text format; a custom format whose code is "@" counts too

_ROW_RE = re.compile(r'<row\b[^>]*?(?:/>|>.*?</row>)', re.S)
_CELL_RE = re.compile(r'<c\b[^>]*?(?:/>|>.*?</c>)', re.S)
_ROW_NUM_RE = re.compile(r'\br="(\d+)"')
_CELL_REF_RE = re.compile(r'\br="([A-Z]+)(\d+)"')
_STYLE_RE = re.compile(r'\bs="(\d+)"')
_SPANS_RE = re.compile(r'\s+spans="[^"]*"')
_COL_RE = re.compile(r'<col\b[^>]*/>')
_COL_STYLE_RE = re.compile(r'\bstyle="(\d+)"')  # a column carries its default in style=, a cell and a row in s=
XF_RE = re.compile(r'<xf\b[^>]*?(?:/>|>.*?</xf>)', re.S)


def serial(value):
    if isinstance(value, datetime):
        whole = (value.date() - EPOCH).days
        return whole + (value.hour * 3600 + value.minute * 60 + value.second) / 86400
    return (value - EPOCH).days


def number_text(value):
    """What Excel would store as the text of a typed number."""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def cell_xml(ref, value, style, *, text_style=False):
    """One `<c>` element. None or '' clears the value and keeps the style; `text_style` stores a number or a date as
    the text a person typing it would leave."""
    attrs = f' s="{style}"' if style is not None else ''
    if value is None or value == '':
        return f'<c r="{ref}"{attrs}/>'
    if isinstance(value, bool):  # before int: bools are ints in Python
        return f'<c r="{ref}"{attrs} t="b"><v>{1 if value else 0}</v></c>'
    if isinstance(value, datetime | date):
        if not text_style:
            return f'<c r="{ref}"{attrs}><v>{serial(value)}</v></c>'
        value = value.strftime('%m/%d/%Y')
    elif isinstance(value, int | float):
        if not text_style:
            return f'<c r="{ref}"{attrs}><v>{value}</v></c>'
        value = number_text(value)
    text = escape(str(value))
    return f'<c r="{ref}"{attrs} t="inlineStr"><is><t xml:space="preserve">{text}</t></is></c>'


def text_styles(styles_xml):
    """The cellXfs indexes whose number format is Text."""
    customs = set()
    block = re.search(r'<numFmts[^>]*>(.*?)</numFmts>', styles_xml, re.S)
    if block:
        for tag in re.findall(r'<numFmt\b[^>]*/>', block.group(1)):
            fmt_id = re.search(r'\bnumFmtId="(\d+)"', tag)
            code = re.search(r'\bformatCode="([^"]*)"', tag)
            if fmt_id and code and unescape(code.group(1)).strip() == '@':
                customs.add(int(fmt_id.group(1)))
    xfs = re.search(r'<cellXfs[^>]*>(.*?)</cellXfs>', styles_xml, re.S)
    if not xfs:
        return frozenset()
    out = set()
    for index, xf in enumerate(XF_RE.findall(xfs.group(1))):
        found = re.search(r'\bnumFmtId="(\d+)"', xf)
        fmt_id = int(found.group(1)) if found else 0
        if fmt_id == TEXT_NUMFMT or fmt_id in customs:
            out.add(index)
    return frozenset(out)


def _explicit_style(cell):
    found = _STYLE_RE.search(cell.split('>', 1)[0])
    return int(found.group(1)) if found else None


class Sheet:
    """One worksheet's XML. `write` patches a cell; `render` returns the sheet with its sheetData and dimension
    rewritten and every other byte as it was."""

    def __init__(self, xml, text_xfs=frozenset()):
        self.xml = xml
        body = re.search(r'<sheetData\s*/>|<sheetData>(.*?)</sheetData>', xml, re.S)
        if not body:
            raise FillError('Worksheet has no sheetData')
        self.body_span = body.span()
        self.rows = {}  # row number -> raw <row> xml
        self.order = []
        for match in _ROW_RE.finditer(body.group(1) or ''):
            num = int(_ROW_NUM_RE.search(match.group(0)).group(1))
            self.rows[num] = match.group(0)
            self.order.append(num)
        self.col_styles = self._col_styles()
        self.text_xfs = text_xfs
        self.warnings = []
        self.written = set()  # (col index, row) of every written cell
        self._nearest = {}  # (letters, source row) -> style or None

    def _col_styles(self):
        """Column-level default styles, which new cells must inherit."""
        styles = {}
        cols = re.search(r'<cols>(.*?)</cols>', self.xml, re.S)
        if not cols:
            return styles
        for col in _COL_RE.finditer(cols.group(1)):
            tag = col.group(0)
            style = _COL_STYLE_RE.search(tag)
            if not style:
                continue
            lo = int(re.search(r'\bmin="(\d+)"', tag).group(1))
            hi = int(re.search(r'\bmax="(\d+)"', tag).group(1))
            for index in range(lo, min(hi, 16384) + 1):
                styles[index] = int(style.group(1))
        return styles

    def cells(self, row_num):
        row = self.rows.get(row_num)
        if not row:
            return {}
        out = {}
        for match in _CELL_RE.finditer(row):
            ref = _CELL_REF_RE.search(match.group(0))
            if ref:
                out[ref.group(1)] = match.group(0)
        return out

    def style_of(self, ref):
        """The cell's own xf index, or None."""
        letters, num = split_ref(ref)
        cell = self.cells(num).get(letters)
        return _explicit_style(cell) if cell else None

    def text_at(self, ref, shared):
        """The displayed text of a cell: what the drift guard reads."""
        letters, num = split_ref(ref)
        cell = self.cells(num).get(letters)
        if not cell:
            return ''
        if ' t="s"' in cell:
            index = re.search(r'<v>(\d+)</v>', cell)
            return shared[int(index.group(1))] if index else ''
        if ' t="inlineStr"' in cell:
            found = re.search(r'<t[^>]*>(.*?)</t>', cell, re.S)
            return unescape(found.group(1)) if found else ''
        found = re.search(r'<v>(.*?)</v>', cell, re.S)
        return found.group(1) if found else ''

    def holds_formula(self, ref):
        letters, num = split_ref(ref)
        return '<f' in self.cells(num).get(letters, '')

    def _row_style(self, row_num):
        row = self.rows.get(row_num)
        if not row or 'customFormat="1"' not in row:
            return None
        style = _STYLE_RE.search(row.split('>', 1)[0])
        return int(style.group(1)) if style else None

    def _nearest_style(self, letters, source_row):
        """The style of the nearest row below `source_row` that has this cell, else the source row's own. Cached per
        column: column X of the Warner census has no cell on ~590 rows, and re-parsing every row on every write would
        make a 500-member roster crawl."""
        key = (letters, source_row)
        if key in self._nearest:
            return self._nearest[key]
        style = None
        for row_num in [r for r in self.order if r > source_row] + [source_row]:
            cell = self.cells(row_num).get(letters)
            if cell:
                style = _explicit_style(cell)
                if style is not None:
                    break
        self._nearest[key] = style
        return style

    def write(self, ref, value, style=None, *, style_source_row=None):
        letters, num = split_ref(ref)
        existing = self.cells(num).get(letters)
        if existing is not None and '<f' in existing:
            self.warnings.append(f'{ref} holds a formula — left as the template had it.')
            return
        clearing = value is None or value == ''
        if clearing:
            if existing is None:
                return  # never create a cell just to leave it empty
            if _explicit_style(existing) is None:
                self._remove(num, existing)
                return
        if style is None and existing is not None:
            style = _explicit_style(existing)
        if style is None and style_source_row is not None:
            style = self._nearest_style(letters, style_source_row)
        if style is None:
            style = self._row_style(num)
        if style is None:
            style = self.col_styles.get(col_index(letters))
        xml = cell_xml(ref, value, style, text_style=style in self.text_xfs)
        if not clearing:
            self.written.add((col_index(letters), num))
        self._place(num, letters, existing, xml)

    def _place(self, num, letters, existing, xml):
        row = self.rows.get(num)
        if row is None:
            self.rows[num] = f'<row r="{num}">{xml}</row>'
            self.order = sorted(self.rows)
            return
        row = _SPANS_RE.sub('', row, count=1)
        if row.endswith('/>'):  # an empty row element
            self.rows[num] = f'{row[:-2]}>{xml}</row>'
            return
        if existing is not None:
            self.rows[num] = row.replace(existing, xml, 1)
            return
        target = col_index(letters)  # insert in column order
        out, pos, inserted = [], 0, False
        for match in _CELL_RE.finditer(row):
            ref_match = _CELL_REF_RE.search(match.group(0))
            index = col_index(ref_match.group(1)) if ref_match else 0
            if not inserted and index > target:
                out.append(row[pos : match.start()])
                out.append(xml)
                pos = match.start()
                inserted = True
        out.append(row[pos:])
        row = ''.join(out)
        if not inserted:
            row = row.replace('</row>', f'{xml}</row>', 1)
        self.rows[num] = row

    def _remove(self, num, existing):
        row = _SPANS_RE.sub('', self.rows[num], count=1).replace(existing, '', 1)
        if row.endswith('></row>'):
            row = f'{row[: -len("></row>")]}/>'
        self.rows[num] = row

    def set_row_height(self, row_num, points):
        row = self.rows.get(row_num)
        if row is None:
            self.rows[row_num] = f'<row r="{row_num}" ht="{points}" customHeight="1"/>'
            self.order = sorted(self.rows)
            return
        head_end = row.index('>') if not row.endswith('/>') else len(row) - 2
        head, tail = row[:head_end], row[head_end:]
        head = re.sub(r'\s+ht="[^"]*"', '', head)
        head = re.sub(r'\s+customHeight="[^"]*"', '', head)
        self.rows[row_num] = f'{head} ht="{points}" customHeight="1"{tail}'

    def render(self):
        rows = ''.join(self.rows[num] for num in sorted(self.rows))
        start, end = self.body_span
        return self._grow_dimension(f'{self.xml[:start]}<sheetData>{rows}</sheetData>{self.xml[end:]}')

    def _grow_dimension(self, xml):
        """Excel keeps `<dimension>` at the used range; a roster written past it would leave the hint short."""
        if not self.written:
            return xml
        found = re.search(r'<dimension ref="([^"]*)"', xml)
        if not found:
            return xml
        ref = found.group(1)
        first, _, last = ref.partition(':')
        c1, r1 = split_ref(first)
        c2, r2 = split_ref(last) if last else (c1, r1)
        lo_c, hi_c, lo_r, hi_r = col_index(c1), col_index(c2), r1, r2
        for col, row in self.written:
            lo_c, hi_c = min(lo_c, col), max(hi_c, col)
            lo_r, hi_r = min(lo_r, row), max(hi_r, row)
        grown = f'{col_letters(lo_c)}{lo_r}:{col_letters(hi_c)}{hi_r}'
        if grown == ref or (lo_c == hi_c and lo_r == hi_r):
            return xml
        return xml[: found.start(1)] + grown + xml[found.end(1) :]
