"""Warner's large-group form and the SIIA disclosure: the carrier's own fillable fields, filled (G59).

The bundled blank is a real AcroForm, so the export is the original form with the answers written into its fields:
no coordinates. Each spec's `acroform` names every field it writes (spec key → the PDF's own field name, a Yes/No pair
as two boxes, Warner's grids row by row). A mapped name missing from the bundled PDF fails loudly (`AcroFormError`):
a re-issued carrier form needs a new map, not a blind, half-filled send.

The signature slots are /Sig fields, which hold no text: each typed name is drawn inside its widget's rectangle, read
from the PDF at run time; a paired Date box fills like any field. The DRAFT line, then the e-signature caption, sit on
the signature page (G53). Answers the page has no field for (`attachment_fields`, Warner's detail lines) print on an
attachment page; filled rows past the paper's last row print nowhere, and the check says so (`unprinted`). Rows print
in order of the rows holding answers, so a blank first row leaves no gap. Ported from old Vantage 891f1b3
(`questionnaire_acroform.py`).
"""

from io import BytesIO

from pypdf import PdfReader, PdfWriter
from reportlab.lib import colors
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas as pdfcanvas

from .. import forms
from ..engine.spec import field_spec, get_block
from . import attachment, display, fonts
from .printed import filled, text

SIGN_MAX, SIGN_MIN = 11.0, 6.0


class AcroFormError(Exception):
    """The AcroForm cannot be filled: no bundle, or field names that drifted from the map."""


def _flat(value):
    return list(value.values()) if isinstance(value, dict) else [value]


def paper_rows(form, block, cfg):
    """{paper row (1-based): {spec key: field name}} for one block: Warner names each row outright (its grids are
    numbered column-major), the SIIA grid by a `{n}` pattern."""
    if cfg.get('rows'):
        return cfg['rows']
    start, columns = cfg.get('start', 1), cfg.get('columns') or {}
    count = (get_block(form, block) or {}).get('max_rows', 1)
    return {k: {key: pattern.format(n=start + k - 1) for key, pattern in columns.items()} for k in range(1, count + 1)}


def mapped_names(form, spec):
    """Every field name the map can ever write, for every row and both signatures: the drift check covers it all."""
    names = [name for value in (spec.get('scalars') or {}).values() for name in _flat(value)]
    for block, cfg in (spec.get('blocks') or {}).items():
        for columns in paper_rows(form, block, cfg).values():
            names += [name for value in columns.values() for name in _flat(value)]
    for entry in (spec.get('signatures') or {}).values():
        names += [entry['sig']] + ([entry['date']] if entry.get('date') else [])
    return names


def on_state(fields, name):
    """The 'on' appearance state of a check box ('/On', '/1', …)."""
    for state in (fields.get(name) or {}).get('/_States_') or []:
        if state != '/Off':
            return state
    return '/Yes'


def sig_rects(reader):
    """{field name: (page index, (x0, y0, x1, y1))} for every /Sig widget."""
    out = {}
    for index, page in enumerate(reader.pages):
        annots = page.get('/Annots')
        for annot in annots.get_object() if annots is not None else []:
            widget = annot.get_object()
            rect = [float(v) for v in widget.get('/Rect') or []]
            if widget.get('/FT') == '/Sig' and widget.get('/T') and len(rect) == 4:
                out[str(widget['/T'])] = (index, tuple(rect))
    return out


def collect(form, spec, found, fields):
    """({field name: text}, [check boxes to tick]) from the printed answers. A pair ticks "yes" or "no"; a single box
    (decided by the PDF's own field type) ticks on Yes, its blank being the no."""
    out, ticks = {}, []

    def put(target, field, raw):
        value = display.handwritten(field, raw)
        if not value:
            return
        if isinstance(target, dict):
            if target.get(value.lower()):
                ticks.append(target[value.lower()])
        elif (fields.get(target) or {}).get('/FT') == '/Btn':
            if value == 'Yes':
                ticks.append(target)
        else:
            out[target] = value

    for key, target in (spec.get('scalars') or {}).items():
        put(target, field_spec(form, '', key), found.scalars.get(key))
    for block, cfg in (spec.get('blocks') or {}).items():
        paper = paper_rows(form, block, cfg)
        for slot, (_number, vals) in enumerate(filled(found, block), 1):
            for key, target in (paper.get(slot) or {}).items():  # past the paper's last row: nowhere (`unprinted`)
                put(target, field_spec(form, block, key), vals.get(key))
    return out, ticks


def unprinted(form, spec, found):
    """What the filled form cannot print (the check, G64): {attached: [key], dropped: {block: n}}."""
    attached = [key for key in spec.get('attachment_fields') or () if text(found.scalars, key)]
    dropped = {}
    for block, cfg in (spec.get('blocks') or {}).items():
        extra = len(filled(found, block)) - len(paper_rows(form, block, cfg))
        if extra > 0:
            dropped[block] = extra
    return {'attached': attached, 'dropped': dropped}


def _marks(writer, by_page, note_page, found):
    """One overlay per page that needs our ink: typed names inside their /Sig rectangles, and our note."""
    pages = dict(by_page)
    pages.setdefault(note_page, [])
    for index, marks in pages.items():
        page = writer.pages[index]
        buffer = BytesIO()
        canvas = pdfcanvas.Canvas(buffer, pagesize=(float(page.mediabox.width), float(page.mediabox.height)))
        canvas.setFillColor(colors.black)
        for (x0, y0, x1, _y1), name in marks:
            face, size = fonts.sign_font(name), SIGN_MAX
            while size > SIGN_MIN and stringWidth(name, face, size) > (x1 - x0 - 6):
                size -= 0.5
            canvas.setFont(face, size)
            canvas.drawString(x0 + 3, y0 + 4, name)
        if index == note_page:
            fonts.draw_notes(canvas, found)
        canvas.showPage()
        canvas.save()
        buffer.seek(0)
        page.merge_page(PdfReader(buffer).pages[0])


def fill(form, found):
    """The carrier's AcroForm with the answers in its fields, as bytes."""
    spec = form.get('acroform') or {}
    path = forms.asset_path(spec.get('pdf'))
    if not spec or path is None:
        raise AcroFormError('This form has no bundled AcroForm to fill.')
    reader = PdfReader(str(path))
    fields = reader.get_fields() or {}
    missing = [name for name in mapped_names(form, spec) if name not in fields]
    if missing:
        raise AcroFormError(
            f'The bundled form no longer matches the field map ({len(missing)} missing, first: {missing[0]!r}). '
            'A re-issued carrier form needs a new map, not a blind fill.'
        )
    values, ticks = collect(form, spec, found, fields)
    signers = {'officer': found.officer, 'agent': found.agent}
    for who, entry in (spec.get('signatures') or {}).items():
        if signers.get(who) and entry.get('date'):
            values[entry['date']] = signers[who]['date']
    values.update({name: on_state(fields, name) for name in ticks})
    writer = PdfWriter()
    writer.append(reader)
    for page in writer.pages:
        if page.get('/Annots'):  # only the form page carries widgets
            writer.update_page_form_field_values(page, values, auto_regenerate=False)
    writer.set_need_appearances_writer(True)
    rects, by_page = sig_rects(reader), {}
    for who, entry in (spec.get('signatures') or {}).items():
        placed = rects.get(entry['sig'])
        if signers.get(who) and placed:
            by_page.setdefault(placed[0], []).append((placed[1], signers[who]['name']))
    _marks(writer, by_page, next((index for index, _rect in rects.values()), 0), found)
    extra = attachment.detail_pages(form, found, set(unprinted(form, spec, found)['attached']))
    if extra is not None:
        for page in PdfReader(extra).pages:
            writer.add_page(page)
    out = BytesIO()
    writer.write(out)
    return out.getvalue()
