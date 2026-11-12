"""One workbook cell reduced to what Q.5 compares: its value or formula, number format, font, fill and border, each
in a form both writers agree on (old Vantage wrote the file with openpyxl, 2Vantage with XlsxWriter).

Colours read as RRGGBB; an automatic, default-indexed or theme-1 colour (the text colour) reads "auto", and so does
explicit black on a font. A missing cell is the default cell: blank, General, Calibri 11, no fill, no border.
"""

from . import mask, refs

DEFAULT = {
    'value': None,
    'format': 'General',
    'font': ('Calibri', 11.0, False, False, None, False, 'auto'),
    'fill': 'none',
    'border': ('none',) * 4,
}
SIDES = ('left', 'right', 'top', 'bottom')
FONT_FIELDS = ('name', 'size', 'bold', 'italic', 'underline', 'strike', 'colour')


def colour(value, *, text=False):
    if value is None:
        return 'auto'
    kind = getattr(value, 'type', None)
    if kind == 'rgb' and isinstance(value.rgb, str):
        rgb = value.rgb[-6:].upper()
        return 'auto' if text and rgb == '000000' else rgb
    if kind == 'theme':
        tint = round(float(value.tint or 0), 3)
        if value.theme == 1 and not tint:
            return 'auto'
        return f'theme{value.theme}{"+" + str(tint) if tint else ""}'
    if kind == 'indexed':
        return 'auto' if value.indexed in (64, 8) else f'indexed{value.indexed}'
    return 'auto'


def font(cell):
    f = cell.font
    underline = f.u if f.u not in (None, 'none') else None
    return (f.name, float(f.sz or 11), bool(f.b), bool(f.i), underline, bool(f.strike), colour(f.color, text=True))


def fill(cell):
    pattern = cell.fill.fill_type if cell.fill is not None else None
    if not pattern:
        return 'none'
    if pattern == 'solid':
        return colour(cell.fill.fgColor)
    return f'{pattern}:{colour(cell.fill.fgColor)}:{colour(cell.fill.bgColor)}'


def border(cell):
    out = []
    for side in SIDES:
        edge = getattr(cell.border, side, None)
        style = getattr(edge, 'style', None)
        out.append(f'{style}:{colour(edge.color)}' if style else 'none')
    return tuple(out)


def value(cell, here=None, maps=None):
    """('formula', text moved through `maps`) or ('value', masked value)."""
    raw = cell.value
    if cell.data_type == 'f' and isinstance(raw, str):
        text = raw if maps is None else refs.translate(raw, here, maps)
        return ('formula', text)
    if hasattr(raw, 'text'):  # an ArrayFormula or rich text
        raw = str(raw.text)
    if isinstance(raw, bool):
        return ('value', raw)
    if isinstance(raw, int | float):
        return ('value', float(raw))
    if isinstance(raw, str):
        return ('value', mask.text(raw.replace('\r\n', '\n')) or None)
    return ('value', raw if raw is None else str(raw))


def read(cell, here=None, maps=None):
    if cell is None:
        return dict(DEFAULT)
    found = value(cell, here, maps)
    return {
        'value': None if found == ('value', None) else found,
        'format': cell.number_format or 'General',
        'font': font(cell),
        'fill': fill(cell),
        'border': border(cell),
    }


def differences(old, new, *, both=True):
    """[(kind, old, new)] where two read cells differ. The number format and the font are held to each other where
    a value is shown, or where both files style the cell (an empty input keeps its blue for the value typed later);
    a cell one writer leaves out and the other writes empty with Calibri is no difference a person sees."""
    out = []
    if old['value'] != new['value']:
        kind = 'formula' if 'formula' in (_kind(old['value']), _kind(new['value'])) else 'value'
        out.append((kind, _shown(old['value']), _shown(new['value'])))
    shows = both or old['value'] is not None or new['value'] is not None
    if old['format'] != new['format'] and shows:
        out.append(('number-format', old['format'], new['format']))
    if old['font'] != new['font'] and shows:
        changed = [
            f'{name} {a!r}→{b!r}' for name, a, b in zip(FONT_FIELDS, old['font'], new['font'], strict=True) if a != b
        ]
        out.append(('font', ', '.join(changed), ''))
    if old['fill'] != new['fill']:
        out.append(('fill', old['fill'], new['fill']))
    if old['border'] != new['border']:
        changed = [f'{s} {a}→{b}' for s, a, b in zip(SIDES, old['border'], new['border'], strict=True) if a != b]
        out.append(('border', ', '.join(changed), ''))
    return out


def _kind(found):
    return found[0] if isinstance(found, tuple) else None


def _shown(found):
    if not isinstance(found, tuple):
        return found
    kind, raw = found
    if kind == 'value' and isinstance(raw, float) and raw.is_integer():
        return int(raw)
    return raw
