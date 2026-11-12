"""One cell's look in Excel, as a small dict, for `sheet_look` (plan.md §3.1; E29, D-167). Ported from the old
docscan/sheet_format.py.

Keys: `bg` fill, `fg` font colour, `b` `i` `u` `x` bold, italic, underline, strike, `s` size in points, `ff` font
family, `sym` a picture font (Wingdings), `ha` `va` alignment, `wrap`, `ind` indent, and `bt` `br` `bb` `bl` borders
as CSS ("1px solid #000000"). Never a cell's value: number formats are not applied (D-167). Theme colours resolve
through the workbook's theme part; a workbook built in memory has none, so its theme colours read as automatic.
"""

import colorsys
import re

# Excel numbers its theme colours lt1, dk1, lt2, dk2, ...; the theme part lists them dk1, lt1, dk2, lt2, ...
THEME_ORDER = (
    'lt1', 'dk1', 'lt2', 'dk2', 'accent1', 'accent2', 'accent3', 'accent4', 'accent5', 'accent6', 'hlink', 'folHlink',
)  # fmt: skip
_DRAWING = '{http://schemas.openxmlformats.org/drawingml/2006/main}'
BORDERS = {
    'hair': '1px dotted',
    'dotted': '1px dotted',
    'dashed': '1px dashed',
    'dashDot': '1px dashed',
    'dashDotDot': '1px dashed',
    'thin': '1px solid',
    'mediumDashed': '2px dashed',
    'mediumDashDot': '2px dashed',
    'mediumDashDotDot': '2px dashed',
    'slantDashDot': '2px dashed',
    'medium': '2px solid',
    'thick': '3px solid',
    'double': '3px double',
}
H_ALIGN = {
    'left': 'left',
    'center': 'center',
    'centerContinuous': 'center',
    'right': 'right',
    'justify': 'justify',
    'distributed': 'justify',
    'fill': 'left',
}
V_ALIGN = {'top': 'top', 'center': 'middle', 'bottom': 'bottom', 'justify': 'middle', 'distributed': 'middle'}
# Fonts whose letters are pictures: the viewer maps the common ones (Wingdings "ü" is a tick).
SYMBOL_FONTS = {
    'wingdings': 'wingdings',
    'wingdings 2': 'wingdings2',
    'wingdings 3': 'wingdings3',
    'webdings': 'webdings',
    'symbol': 'symbol',
}
_FONT_NAME = re.compile(r'^[A-Za-z0-9 \-]{1,40}$')
_HEX = re.compile(r'^[0-9A-Fa-f]{6}$')


def theme_palette(book):
    """The workbook's twelve theme colours as RRGGBB, in Excel's index order (missing ones None)."""
    raw = getattr(book, 'loaded_theme', None)
    if not raw:
        return []
    from openpyxl.xml.functions import fromstring

    scheme = fromstring(raw).find(f'.//{_DRAWING}clrScheme')
    if scheme is None:
        return []
    found = {}
    for slot in scheme:
        name = slot.tag.replace(_DRAWING, '')
        for colour in slot:
            if colour.tag == f'{_DRAWING}srgbClr':
                found[name] = colour.get('val')
            elif colour.tag == f'{_DRAWING}sysClr':
                fallback = '000000' if colour.get('val') == 'windowText' else 'FFFFFF'
                found[name] = colour.get('lastClr') or fallback
    return [found.get(name) for name in THEME_ORDER]


def _tinted(hex6, tint):
    """Excel's tint: towards white when positive, towards black when not."""
    if not tint:
        return hex6
    r, g, b = (int(hex6[i : i + 2], 16) / 255 for i in (0, 2, 4))
    hue, light, sat = colorsys.rgb_to_hls(r, g, b)
    light = light * (1 + tint) if tint < 0 else light * (1 - tint) + tint
    r, g, b = colorsys.hls_to_rgb(hue, max(0.0, min(1.0, light)), sat)
    return ''.join(f'{round(v * 255):02X}' for v in (r, g, b))


def _indexed(index):
    from openpyxl.styles.colors import COLOR_INDEX

    if index == 64:
        return '000000'
    if index == 65:
        return 'FFFFFF'
    return COLOR_INDEX[index][-6:] if index is not None and 0 <= index < len(COLOR_INDEX) else ''


def colour(value, palette):
    """`#RRGGBB` for an openpyxl colour, or None (automatic, or unknown)."""
    if value is None:
        return None
    try:
        if value.type == 'rgb':
            hex6 = value.rgb[-6:] if isinstance(value.rgb, str) else ''
        elif value.type == 'theme':
            index = value.theme
            hex6 = palette[index] if index is not None and index < len(palette) else ''
        elif value.type == 'indexed':
            hex6 = _indexed(value.indexed)
        else:
            return None
        if not hex6 or not _HEX.match(hex6):
            return None
        return '#' + _tinted(hex6.upper(), value.tint or 0)
    except (AttributeError, IndexError, TypeError, ValueError):
        return None


def _font(font, palette, style):
    name = (font.name or '').strip()
    symbol = SYMBOL_FONTS.get(name.lower())
    if symbol:
        style['sym'] = symbol
    elif _FONT_NAME.match(name):
        style['ff'] = name
    for attribute, key in (('b', 'b'), ('i', 'i'), ('strike', 'x')):
        if getattr(font, attribute):
            style[key] = 1
    if font.u and font.u != 'none':
        style['u'] = 1
    if font.sz:
        style['s'] = round(float(font.sz), 1)
    fg = colour(font.color, palette)
    if fg:
        style['fg'] = fg


def _alignment(align, style):
    if H_ALIGN.get(align.horizontal):
        style['ha'] = H_ALIGN[align.horizontal]
    if V_ALIGN.get(align.vertical):
        style['va'] = V_ALIGN[align.vertical]
    if align.wrap_text:
        style['wrap'] = 1
    if align.indent:
        style['ind'] = int(align.indent)


def cell_style(cell, palette):
    """A cell's look (no value). Border sides are kept as stored; `sheet_look` settles them between neighbours."""
    style = {}
    fill = cell.fill
    if getattr(fill, 'fill_type', None) == 'solid':
        bg = colour(fill.fgColor, palette)
        if bg:
            style['bg'] = bg
    if cell.font is not None:
        _font(cell.font, palette, style)
    if cell.alignment is not None:
        _alignment(cell.alignment, style)
    border = cell.border
    if border is not None:
        for side, key in ((border.top, 'bt'), (border.right, 'br'), (border.bottom, 'bb'), (border.left, 'bl')):
            line = BORDERS.get(getattr(side, 'style', None))
            if line:
                style[key] = f'{line} {colour(side.color, palette) or "#000000"}'
    return style
