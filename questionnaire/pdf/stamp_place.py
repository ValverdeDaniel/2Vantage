"""Where each answer goes on Florida Blue's flat form, decided once (G57; G64's clipped and attachment codes). Pure:
measurements only (reportlab's `stringWidth` in the stamping face), no drawing, no database.

The printed form is smaller than the data: one plan row, one condition row, and follow-up answers that Acrobat shows
by inserting a line and reflowing the page, which a flat page cannot do. `placement` decides what the two pages carry:
- an answer with no box of its own rides the box of the answer that reveals it when both fit (question 12's
  explanation beside its reason, `OFF_FORM_FIELDS`);
- a condition's narrative wraps into the paper beside the cancer counts (`NARRATIVE_AREA`), the comments into their
  box (`TEXT_AREAS`);
- an answer too long for its box even at the smallest legible size prints "See attachment" there and whole on the
  attachment page; for a row, the whole row goes with it.
The drawing (`stamp_draw`), the attachment (`attachment`) and the check (`clip_report`) all read this one decision,
so whatever the pages do not draw is exactly what the attachment prints. The rows printed on the page are the first
rows holding an answer (B1's fix), and every row keeps its number on our form.
Ported from old Vantage 891f1b3 (`questionnaire_stamp._placement`, `clip_report`, `_needs_attachment`).
"""

from reportlab.pdfbase.pdfmetrics import stringWidth

from ..engine.options import active_effects
from ..engine.spec import field_spec, get_block
from ..engine.walk import visible_fields
from . import display, fonts
from .printed import filled, text

SEE_ATTACHMENT = 'See attachment'
JOINER = ' — '


def face(layout):
    return fonts.register(layout.FONT_NAME, layout.FONT_FILE)


def fit(value, width, size, min_size, font):
    """Shrink to fit the box, then clip: (text, size), measured in the face it is drawn in."""
    while size > min_size and stringWidth(value, font, size) > width:
        size -= 0.25
    while value and stringWidth(value, font, size) > width:
        value = value[:-1]
    return value, size


def fits(value, width, layout):
    """Does `value` fit a box `width` wide at or above the smallest legible size?"""
    return fit(value, width - 5, layout.FONT_SIZE, layout.MIN_FONT_SIZE, layout.FONT_NAME)[0] == value


def wrap_lines(value, width, size, font):
    """Greedy wrap into lines that fit `width`: the fit test and the drawing share it."""
    lines, line = [], ''
    for word in (value or '').split():
        trial = f'{line} {word}'.strip()
        if stringWidth(trial, font, size) > width and line:
            lines.append(line)
            line = word
        else:
            line = trial
    if line:
        lines.append(line)
    return lines


def line_capacity(drop, leading):
    """Baselines that fit: the first, plus what the room below it allows."""
    return 1 + max(int(drop // leading), 0)


def boxed(form, block, key, vals):
    return display.boxed(field_spec(form, block, key), vals.get(key))


def first_row(found, block):
    """(number, values) of the block's first row holding an answer, or (None, {})."""
    rows = filled(found, block)
    return rows[0] if rows else (None, {})


def host_of(form, key):
    """The answer whose box an off-form answer rides: the one its `visible_if` names."""
    return ((field_spec(form, '', key) or {}).get('visible_if') or {}).get('field', '')


def caption(form, block, key):
    return (field_spec(form, block, key) or {}).get('label', '')


def effect_block(form, layout):
    return next((b for b in layout.BLOCK_BOXES if (get_block(form, b) or {}).get('effect_drivers')), '')


def effect_lines(form, layout, vals):
    """(repaint, [(caption, value)]): the follow-up lines a row shows in place of the printed cancer-count pair. The
    carrier's own change scripts swap them for a category's surgery or transplant counts, or nothing."""
    block = effect_block(form, layout)
    effects = active_effects(form, block, vals)
    if effects.get(layout.PRINTED_EFFECT):
        return False, []
    lines = []
    for flag, keys in layout.EFFECT_LINES.items():
        if effects.get(flag):
            lines.extend((caption(form, block, key), text(vals, key)) for key in keys)
    return True, lines


def _hosts(form, layout, scalars, overflow):
    out = {}
    for key in layout.OFF_FORM_FIELDS:
        host = host_of(form, key)
        reason, explanation = boxed(form, '', host, scalars), text(scalars, key)
        out[host] = reason
        if explanation:
            joined = f'{reason}{JOINER}{explanation}' if reason else explanation
            width = layout.FIELD_BOXES[host][3]
            if fit(joined, width - 5, layout.FONT_SIZE, layout.MIN_COMBINED_FONT_SIZE, layout.FONT_NAME)[0] == joined:
                out[host] = joined
            else:
                overflow.add(key)
    return out


def _narrative(form, layout, found, overflow):
    """Row 1's narrative, pre-wrapped, when it fits the paper beside the counts; re-checked against the filtered row,
    so an answer its gate now hides never prints."""
    for block, keys in layout.OFF_FORM_BLOCK_FIELDS.items():
        _number, vals = first_row(found, block)
        for key in keys:
            body = text(vals, key) if key in visible_fields(form, block, vals) else ''
            if not body:
                continue
            _page, _x, _top, width, drop = layout.NARRATIVE_AREA
            heading = wrap_lines(caption(form, block, key), width, layout.FONT_SIZE, layout.FONT_NAME)
            lines = wrap_lines(body, width, layout.FONT_SIZE, layout.FONT_NAME)
            if len(lines) <= line_capacity(drop, layout.LEADING) - len(heading):
                return {'heading': heading, 'lines': lines}
            overflow.add(key)
    return None


def placement(form, layout, found):
    """{hosts: {key: text}, narrative: {heading, lines}|None, comments: {key: [line]}, overflow: {key},
    row_overflow: {block}}."""
    face(layout)
    scalars, overflow = found.scalars, set()
    hosts = _hosts(form, layout, scalars, overflow)
    narrative = _narrative(form, layout, found, overflow)
    comments = {}
    for key, (_page, _x, _top, width, drop) in layout.TEXT_AREAS.items():
        lines = wrap_lines(text(scalars, key), width, layout.FONT_SIZE, layout.FONT_NAME)
        if len(lines) > line_capacity(drop, layout.LEADING):
            overflow.add(key)  # half a comment and no sign of the rest is worse than a pointer to the attachment
            lines = []
        comments[key] = lines
    for key, box in layout.FIELD_BOXES.items():
        if key not in hosts and too_long(form, layout, '', key, scalars, box):
            overflow.add(key)
    row_overflow = set()
    for block, boxes in layout.BLOCK_BOXES.items():
        _number, vals = first_row(found, block)
        if any(too_long(form, layout, block, key, vals, box) for key, box in boxes.items()):
            row_overflow.add(block)
    return {
        'hosts': hosts,
        'narrative': narrative,
        'comments': comments,
        'overflow': overflow,
        'row_overflow': row_overflow,
    }


def too_long(form, layout, block, key, vals, box):
    """An answer that does not fit its box even at the smallest legible size."""
    value = boxed(form, block, key, vals)
    return bool(value) and not fits(value, box[3], layout)


def more_rows(layout, found):
    """{block: n} rows holding answers past the ones the printed form shows."""
    out = {}
    for block, shown in layout.PRINTED_ROWS.items():
        extra = len(filled(found, block)) - shown
        if extra > 0:
            out[block] = extra
    return out


def chunks(form, layout, found, place):
    """{block: [(number, values)]} the attachment continues: rows the page has no room for, and the printed row
    itself when one of its answers went to the attachment."""
    out = {}
    for block in form.get('blocks') or {}:
        rows, shown = filled(found, block), layout.PRINTED_ROWS.get(block, 0)
        moved = any(key in place['overflow'] for key in layout.OFF_FORM_BLOCK_FIELDS.get(block, ()))
        chosen = rows[:shown] if rows and (moved or block in place['row_overflow']) else []
        chosen += rows[shown:]
        if chosen:
            out[block] = chosen
    return out


def needs_attachment(layout, found, place):
    return bool(place['overflow'] or place['row_overflow'] or more_rows(layout, found))


def clip_report(form, layout, found):
    """What the pages print and what they cannot (the check, G64): {attached: [(block, number, key)], rows: {block:
    n}, clipped: [(block, number, key)]}. An attached answer prints whole on the attachment, as do `rows` more rows; a
    clipped one is cut short in an inline box the carrier inserts beside a picker, with nowhere else to go."""
    place = placement(form, layout, found)
    attached = [('', 0, key) for key in sorted(place['overflow']) if field_spec(form, '', key)]
    for block, keys in layout.OFF_FORM_BLOCK_FIELDS.items():
        attached += [(block, first_row(found, block)[0], key) for key in keys if key in place['overflow']]
    for block in sorted(place['row_overflow']):
        number, vals = first_row(found, block)
        boxes = layout.BLOCK_BOXES[block].items()
        attached += [(block, number, key) for key, box in boxes if too_long(form, layout, block, key, vals, box)]
    boxes = layout.INLINE_BOXES.items()
    clipped = [('', 0, key) for key, box in boxes if too_long(form, layout, '', key, found.scalars, box)]
    for block, inline in layout.INLINE_BLOCK_BOXES.items():
        number, vals = first_row(found, block)
        clipped += [(block, number, k) for k, box in inline.items() if too_long(form, layout, block, k, vals, box)]
    return {'attached': attached, 'rows': more_rows(layout, found), 'clipped': clipped}
