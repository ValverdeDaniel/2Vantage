"""One door from a questionnaire to its PDF (plan.md §9.12; G56, G57, G59, G61, G62). Reads; never writes.

`render(found)` picks the exporter by what the carrier bundled: an AcroForm is filled (Warner, the SIIA disclosure),
a flat blank with a stamp layout is stamped (Florida Blue). The download, the filed signed copy (G135), the check and
the RFP packet (slice 46) all come through here, so two copies of the dispatch never drift.

- `printed_of(deal, form_key, row=None, facts=None)`: what the form prints right now (`printed.printed`);
- `build(deal, form_key, ...)`: its bytes;
- `file_name(deal, form_key)`: `<client slug>-<export_slug>.pdf`, the name the browser keeps (G62);
- `blank(form_key)`: the bundled blank's path and its name `<form slug>-blank.pdf` (G61).
"""

from django.utils.text import slugify

from .. import forms
from ..forms import fl_blue_51_layout
from ..models import Questionnaire
from ..selectors import context
from . import acroform, printed, stamp_draw

LAYOUTS = {'fl_blue_51': fl_blue_51_layout}  # the forms whose flat blank is stamped, by key


class BuildError(Exception):
    """No exporter for this form."""


def layout_of(form_key):
    return LAYOUTS.get(form_key)


def render(found):
    form = found.form
    if form.get('acroform'):
        return acroform.fill(form, found)
    layout = layout_of(form['key'])
    if layout is not None:
        return stamp_draw.stamp(form, layout, found)
    raise BuildError(f'No PDF exporter for "{form["key"]}".')


def printed_of(deal, form_key, row=None, facts=None):
    """The printed answers of one form on a deal; `row` and `facts` when the caller holds them (a signature)."""
    if row is None:
        row = Questionnaire.objects.filter(deal_id=deal.id, form=form_key).first()
    view = context.form_view(form_key, row, facts or context.prefill_facts(deal))
    return printed.printed(view, row, deal.client.name)


def build(deal, form_key, row=None, facts=None):
    return render(printed_of(deal, form_key, row, facts))


def file_name(deal, form_key):
    return f'{slugify(deal.client.name) or "deal"}-{forms.FORMS[form_key]["export_slug"]}.pdf'


def blank(form_key):
    """(path or None, file name) of the form's bundled blank."""
    form = forms.FORMS[form_key]
    return forms.asset_path(form.get('blank_pdf')), f'{slugify(forms.label(form_key)) or "questionnaire"}-blank.pdf'
