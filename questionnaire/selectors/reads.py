"""A staged read as the drawer's card shows it (plan.md §7.9, §10.5; G99, G100; slice 52). Never writes.

`read_payload(deal, read_id)`: `GET deals/{id}/questionnaires/reads/{read_id}/` — the read's entries against the form
as it stands (`reader.review`): each answer old → new with its page and Claude's doubt, each row with where it goes
(a new row, or the form's row N), the conflicts with why, and whether the form is signed (then nothing can be used,
G99). A used, discarded or undone read answers its status and no entries: its values are gone (D74).
"""

from django.http import Http404

from .. import forms
from ..models import StagedRead
from ..reader import review
from . import context

ENTRY_KEYS = ('ref', 'kind', 'label', 'new', 'old', 'page', 'low', 'sensitive', 'state', 'tick', 'why')
ROW_KEYS = ('block', 'block_label', 'number', 'target_number', 'values')


def _entry(entry):
    shown = {key: entry.get(key) for key in ENTRY_KEYS}
    if entry['kind'] == 'row':
        shown.update({key: entry.get(key) for key in ROW_KEYS})
    if entry.get('opens'):
        shown['opens'] = entry['opens']
    return shown


def read_payload(deal, read_id):
    staged = StagedRead.objects.filter(pk=read_id, deal_id=deal.id).first()
    if staged is None:
        raise Http404('That read is not on this deal.')
    ctx = context.deal_context(deal)
    row = ctx.stored.get(staged.form)
    out = {
        'id': staged.id,
        'form': staged.form,
        'label': forms.label(staged.form),
        'job': staged.job_id,
        'document': staged.document_id,
        'status': staged.status,
        'signed': bool(row and row.locked),
        'entries': [],
        'counts': {},
    }
    if staged.status != StagedRead.WAITING:
        return out
    view = context.form_view(staged.form, row, context.prefill_facts(deal))
    listed, counts = review.entries(view, staged.read, staged.document_id)
    out.update(entries=[_entry(entry) for entry in listed], counts=counts)
    return out
