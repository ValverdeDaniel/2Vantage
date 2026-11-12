"""Which form a filled file is read into (plan.md §10.4; G101, G102; the old `pages.SCAN_KIND_DOC_TYPES['qform']`).

A file's kind says which kind of form it is (old Vantage: "a qform read's type follows its form"): a medical
questionnaire's file goes to the deal's medical form (Florida Blue 51+ or Warner 51+), a stop-loss disclosure's to its
disclosure. The form is the one the checklist arms for that item, else — a form swapped away from after it was started
— the one most recently worked on. The drawer's "Reading" picker on the Questionnaire tab names these forms (G102).
"""

from .. import forms
from ..selectors import context

KIND_OF_FILE = {file_kind: kind for kind, file_kind in forms.FILE_KIND.items()}
WHAT = {forms.MEDICAL: 'medical questionnaire', forms.STOP_LOSS_KIND: 'stop-loss disclosure'}
NO_FORM = 'This deal has no fillable {what} to read the file into. Choose one on the marketing checklist first.'
SIGNED = '{label} is signed, so Claude reads nothing into it. Reopen the form to read a filled copy into it.'


def form_for(ctx, file_kind):
    """The form key a file of `file_kind` is read into on the deal of `ctx` (selectors.context), or ''."""
    kind = KIND_OF_FILE.get(file_kind)
    if kind is None:
        return ''
    armed = ctx.resolved[forms.ITEM_OF_KIND[kind]]['form']
    if armed:
        return armed
    started = sorted(
        (row for key, row in ctx.stored.items() if forms.FORMS[key]['kind'] == kind and context.started(row)),
        key=lambda row: (row.updated_at, row.id),
        reverse=True,
    )
    return started[0].form if started else ''


def refusal(ctx, file_kind):
    """Why a file of this kind cannot be read on this deal ('' when it can): no form for it, or its form is signed."""
    key = form_for(ctx, file_kind)
    if not key:
        return NO_FORM.format(what=WHAT.get(KIND_OF_FILE.get(file_kind), 'form'))
    row = ctx.stored.get(key)
    if row is not None and row.locked:
        return SIGNED.format(label=forms.label(key))
    return ''


def forms_of(deal_id, files):
    """{file id: form key} for the files of one read (one deal)."""
    from deals.models import Deal

    if not files:
        return {}
    ctx = context.deal_context(Deal.objects.get(pk=deal_id))
    return {file.id: form_for(ctx, file.kind) for file in files}
