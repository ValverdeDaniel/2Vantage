"""Which forms a deal uses (plan.md §6.8, §8.11; G5–G7, G9, G11, G133). Pure.

`resolve(item, entry, count, requested_lines)` answers one checklist item — the medical questionnaire or the stop-loss
disclosure — from the item's stored checklist entry (`Intake.checklist[item]`: its `form_key` choice, the
`form_source` that set it, and a person's `requirement`), the one enrolled headcount and the requested lines:
1. a waiver drops it: the medical item applies only while medical is requested or no line is set, and an item a
   person marked "Not needed" asks for no form (G6);
2. then the choice: a form key is that form (chosen by a person, or frozen from the band by the first write, G133);
   `upload` is no fillable form, the item stays a document request (G4);
3. then the band: at 51 or more enrolled the medical item uses Florida Blue 51+; the stop-loss item is opt-in.

A choice the band froze remembers it (`source` band): when the band later says otherwise, `notice` offers Keep or
Switch on the checklist row and the tab, and nothing swaps silently (G133). `chips(...)` are the tab's form chips: the
armed forms, then any form already started, so a signed form always keeps a way in (G7).
"""

from intake.checklist import QUESTIONNAIRE, STOP_LOSS, WAIVED

from . import forms

ITEMS = (QUESTIONNAIRE, STOP_LOSS)
PRODUCER, BAND = 'producer', 'band'


def resolve(item, entry, count, requested_lines):
    """{item, choice, form, source, needed, applies, band, band_form, notice} for one item."""
    entry = entry or {}
    choice = forms.normal_choice(item, entry.get('form_key'))
    if choice not in forms.choices(item):
        choice = forms.AUTO if item == QUESTIONNAIRE else forms.NOT_NEEDED
    stored_source = entry.get('form_source') or ''
    band_name = forms.band(count)
    band_form = forms.band_default(item, count)
    requested = set(requested_lines or ())
    applies = item != QUESTIONNAIRE or 'medical' in requested or not requested
    waived = entry.get('requirement') == WAIVED
    out = {
        'item': item,
        'choice': choice,
        'form': '',
        'source': '',
        'needed': False,
        'applies': applies,
        'waived': waived,
        'band': band_name,
        'band_form': band_form,
        'notice': None,
    }
    if not applies or waived:
        return out
    if choice in forms.FORMS:
        source = BAND if stored_source == BAND else PRODUCER
        out.update(form=choice, source=source, needed=True)
        if source == BAND and band_form != choice:
            out['notice'] = notice(item, choice, band_name, band_form)
    elif choice == forms.UPLOAD:
        out.update(source=PRODUCER, needed=True)
    elif choice == forms.AUTO:
        out.update(form=band_form, source=BAND, needed=True)
    return out


def notice(item, kept, band_name, band_form):
    """The band notice (G133): "Group size now says ≤50 — Keep Florida Blue 51+ · Switch"."""
    switch_to = band_form or (forms.UPLOAD if item == QUESTIONNAIRE else forms.NOT_NEEDED)
    switch_label = forms.label(band_form) if band_form else forms.UPLOAD_LABELS[item][1]
    return {
        'band': band_name,
        'text': f'Group size now says {forms.BAND_WORDS[band_name]}',
        'keep': kept,
        'keep_label': f'Keep {forms.label(kept)}',
        'switch': switch_to,
        'switch_label': f'Switch to {switch_label}',
    }


def resolve_all(checklist, count, requested_lines):
    """{item: resolve(...)} for both items."""
    return {item: resolve(item, (checklist or {}).get(item), count, requested_lines) for item in ITEMS}


def chips(resolved, started):
    """The tab's forms, in checklist order: each item's armed form, then every form already started (a stored answer
    or a signature) that is not armed. `started` is {form key: True}. [] hides the tab (G7)."""
    out = [r['form'] for r in resolved.values() if r['form']]
    out += [key for key in forms.FORMS if started.get(key) and key not in out]
    return out
