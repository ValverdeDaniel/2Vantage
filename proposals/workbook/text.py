"""What a cell of the client spreadsheet shows, and whether it fits (plan.md §9.4; J116, J118; old `workbook_text.py` at
891f1b3, D-194).

Excel draws a stored number through its number format: 0.0417 under `CHANGE_EE_ONLY` reads "EE Only: +4.2%" in red.
The Export viewer shows the file before it is downloaded, so it applies the formats itself. The set is closed:
`styles.NUMBER_FORMATS` is every format a cell of the file may carry, and `display` renders each as Excel does. A
format outside the set reads as General and is counted by the caller, never an error.

What fits: Excel shows "####" for a number wider than its cell, and cuts off text that cannot run on or wrap. The file
is Arial throughout, and Arial's letters are as wide as Helvetica's, so reportlab's Helvetica metrics measure it with no
font file. Widths are screen pixels at 100%: Excel draws text at a whole-pixel size, each letter rounded to a whole
pixel. Pure: values and strings in, strings and numbers out.
"""

import math
import re
from decimal import ROUND_HALF_UP, Context, Decimal
from functools import lru_cache

from reportlab.pdfbase.pdfmetrics import stringWidth

from .styles import NUMBER_FORMATS as KNOWN_FORMATS  # noqa: F401  (the closed set, for the viewer's count)

# Excel's error values: a formula's stored result that is one of these shows as an error, not a value.
ERRORS = frozenset({'#DIV/0!', '#N/A', '#NAME?', '#NULL!', '#NUM!', '#REF!', '#VALUE!'})
# The colour words and [ColorN] a format may name (Excel's 56-colour palette: Color10 is the dark green `CHANGE`
# uses for a decrease).
NAMED_COLOURS = {
    'black': '#000000',
    'white': '#FFFFFF',
    'red': '#FF0000',
    'green': '#00FF00',
    'blue': '#0000FF',
    'yellow': '#FFFF00',
    'magenta': '#FF00FF',
    'cyan': '#00FFFF',
}
# Excel lays text out in screen pixels, so whether a line fits depends a little on the screen's scaling: at 125% a
# column is about 3% wider against its text than at 100%. Measured 2026-11-05 against Excel's own AutoFit (D-194): with
# SURE's slack and no padding the preview cut exactly the cells Excel cut. A check is "sure" when the text fails even
# so, and "tight" when it fails only under STRICT (100%, with Excel's padding).
SURE = (1.03, 0)  # (width factor, padding in pixels)
STRICT = (1.0, 2)
INDENT_PX = 9  # one indent level
GENERAL_CHARS = 11  # General shows at most this many characters

_SECTION_SPLIT = re.compile(r'"[^"]*"|\[[^\]]*\]|\\.|;|[^";\[\\]+')
_COLOUR = re.compile(r'^\[(?:(black|white|red|green|blue|yellow|magenta|cyan)|color(\d{1,2}))\]', re.IGNORECASE)


def _palette(n):
    from openpyxl.styles.colors import COLOR_INDEX

    index = int(n) + 7
    return '#' + COLOR_INDEX[index][-6:] if 8 <= index < 64 else None


def _sections(fmt):
    """The format's sections (split on ";" outside quotes and brackets)."""
    parts, current = [], ''
    for match in _SECTION_SPLIT.finditer(fmt):
        token = match.group()
        if token == ';':
            parts.append(current)
            current = ''
        else:
            current += token
    parts.append(current)
    return parts


class _Section:
    """One section of a number format: its colour, the literal text before and after the number, the pad widths and
    the number's shape."""

    def __init__(self, text):
        self.colour = None
        while (match := _COLOUR.match(text)) is not None:
            word, number = match.groups()
            self.colour = NAMED_COLOURS[word.lower()] if word else _palette(number)
            text = text[match.end() :]
        self.before, self.after, self.pad = '', '', ''
        self.int_zeros = self.min_dec = self.max_dec = self.percent = 0
        self.thousands = self.has_number = self.text_only = False
        side, i = 'before', 0
        while i < len(text):
            ch = text[i]
            if ch == '"':
                end = text.index('"', i + 1)
                setattr(self, side, getattr(self, side) + text[i + 1 : end])
                i = end + 1
            elif ch == '\\' and i + 1 < len(text):
                setattr(self, side, getattr(self, side) + text[i + 1])
                i += 2
            elif ch == '_' and i + 1 < len(text):
                self.pad += text[i + 1]
                i += 2
            elif ch == '@':
                self.text_only = True
                i += 1
            elif ch in '0#?,.':
                j = i
                while j < len(text) and text[j] in '0#?,.':
                    j += 1
                self._shape(text[i:j])
                self.has_number, side, i = True, 'after', j
            else:
                self.percent += ch == '%'
                setattr(self, side, getattr(self, side) + ch)
                i += 1

    def _shape(self, spec):
        whole, _, decimals = spec.partition('.')
        self.thousands = ',' in whole
        self.int_zeros = whole.count('0')
        self.min_dec = decimals.count('0')
        self.max_dec = sum(1 for ch in decimals if ch in '0#?')

    def number(self, value):
        """The number's digits for this section (no sign: the caller's)."""
        exact = Decimal(format(abs(value) * (100**self.percent), '.15g'))
        rounded = exact.quantize(Decimal(1).scaleb(-self.max_dec), rounding=ROUND_HALF_UP, context=Context(prec=60))
        whole, _, frac = format(rounded, 'f').partition('.')
        frac = frac[: self.max_dec]
        while len(frac) > self.min_dec and frac.endswith('0'):
            frac = frac[:-1]
        whole = whole.lstrip('0')
        if len(whole) < self.int_zeros:
            whole = whole.rjust(self.int_zeros, '0')
        if self.thousands and whole:
            whole = f'{int(whole):,}'
        return whole + ('.' + frac if frac or (self.max_dec and self.min_dec) else '')

    def is_zero(self, value):
        return self.number(value).strip('0.,') == ''


def general(value, chars=GENERAL_CHARS):
    """A number as Excel's General shows it in a wide enough column: up to `chars` characters, fewer decimals first,
    scientific only for the very large or very small."""
    if isinstance(value, bool):
        return 'TRUE' if value else 'FALSE'
    if isinstance(value, int) and abs(value) < 10**chars:
        return str(value)
    if value == 0:
        return '0'
    if 1e-9 <= abs(value) < 10 ** (chars - (1 if value < 0 else 0)):
        for places in range(chars, -1, -1):
            exact = Decimal(format(value, '.15g'))
            text = format(exact.quantize(Decimal(1).scaleb(-places), ROUND_HALF_UP, Context(prec=60)), 'f')
            if '.' in text:
                text = text.rstrip('0').rstrip('.')
            if len(text) <= chars:
                return text
    for places in range(5, -1, -1):
        mantissa, _, exponent = f'{value:.{places}E}'.partition('E')
        if '.' in mantissa:
            mantissa = mantissa.rstrip('0').rstrip('.')
        sign = '-' if exponent.startswith('-') else '+'
        text = f'{mantissa}E{sign}{exponent.lstrip("+-").zfill(2)}'
        if len(text) <= chars:
            return text
    return f'{value:.0E}'


def display(value, fmt):
    """(text, colour, pad) for a cell holding `value` under number format `fmt`, as Excel shows it with room enough:
    text is what the cell reads ('' for an empty cell or a formula's ""), colour '#RRGGBB' when the format colours this
    value, pad the characters whose width Excel keeps clear after the text (`_)`)."""
    if value is None:
        return '', None, ''
    if isinstance(value, bool):
        return ('TRUE' if value else 'FALSE'), None, ''
    if isinstance(value, str):
        return value, None, ''
    if not isinstance(value, int | float | Decimal) or not math.isfinite(value):
        return str(value), None, ''
    value = float(value) if isinstance(value, Decimal) else value
    fmt = fmt or 'General'
    if fmt in ('General', '@'):
        return general(value), None, ''
    numeric = [section for section in (_Section(text) for text in _sections(fmt)) if not section.text_only]
    if not numeric:
        return general(value), None, ''
    if len(numeric) == 1:
        section, sign = numeric[0], '-' if value < 0 and not numeric[0].is_zero(value) else ''
    elif len(numeric) == 2:
        section, sign = (numeric[0] if value >= 0 else numeric[1]), ''
    else:
        section, sign = (numeric[0] if value > 0 else numeric[1] if value < 0 else numeric[2]), ''
    digits = section.number(value) if section.has_number else ''
    return sign + section.before + digits + section.after, section.colour, section.pad


# --- Widths --------------------------------------------------------------------------------------------------------
def ppem(size_pt):
    """The whole-pixel size Excel draws `size_pt` type at, at 100%."""
    return max(1, round(float(size_pt or 11) * 96 / 72))


@lru_cache(maxsize=4096)
def _advance(ch, font, size):
    """One letter's advance in whole pixels at `size` pixels an em."""
    try:
        em = stringWidth(ch, font, 1000) / 1000
    except Exception:  # noqa: BLE001 - a glyph reportlab cannot size reads as a wide letter
        em = 0.8
    return round(em * size)


def text_px(text, size_pt=11, bold=False):
    """The width Excel gives `text` in Arial at `size_pt`, in screen pixels."""
    size, font = ppem(size_pt), 'Helvetica-Bold' if bold else 'Helvetica'
    return sum(_advance(ch, font, size) for ch in text or '')


def room(px, geometry=SURE):
    """The pixels a line of text may use in a `px`-wide cell."""
    scale, pad = geometry
    return px * scale - pad


def hashes(px, size_pt=11, bold=False):
    """The "####" Excel fills a `px`-wide cell with when a number will not fit."""
    each = max(1, text_px('#', size_pt, bold))
    return '#' * max(1, int(room(px, STRICT) // each))


def number_fits(text, pad, px, size_pt=11, bold=False, geometry=SURE):
    """Whether a number's text (and its pad) fits a `px`-wide cell."""
    return text_px(text + pad, size_pt, bold) <= room(px, geometry)


def line_pt(size_pt):
    """The height of one line of Arial at `size_pt`, as Excel fits a row to it (11 pt reads 14.25): whole pixels."""
    return math.ceil(float(size_pt or 11) * 96 / 72 * 1.15 + 1.6 * 4 / 3) * 0.75


def wrapped_lines(text, px, size_pt=11, bold=False, geometry=SURE):
    """How many lines Excel wraps `text` into in a `px`-wide cell: at spaces, a word longer than the line broken where
    it runs out, a newline always."""
    room_px = max(1, room(px, geometry))
    space = text_px(' ', size_pt, bold)
    count = 0
    for paragraph in str(text).replace('\r\n', '\n').replace('\r', '\n').split('\n'):
        count += 1
        width = 0
        for word in paragraph.split(' '):
            word_px = text_px(word, size_pt, bold)
            if width and width + space + word_px > room_px:
                count += 1
                width = 0
            elif width:
                width += space
            while word_px > room_px:
                count += 1
                word_px -= room_px
            width += word_px
    return count
