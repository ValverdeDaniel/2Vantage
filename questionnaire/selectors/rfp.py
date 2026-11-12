"""What the RFP reads of the questionnaire (plan.md §9.11; G110–G113; slice 46 mounts it). Reads; never writes.

- `rfp_files(deal, carriers=(), lines=(), funding=())`: one card per form the deal uses, its copy decided by
  `rfp_rules.copy_to_send` (the signed copy, else an accepted paper copy, else the DRAFT with a warning), its default
  tick by who is asked (`takes`) and what is asked (`disclosure_needed`), with the reason a tick is off; the paper
  copies of the form's kind that are not marked wrong ride along by id.
- `sent_with(deal, form_key)`: what the RFP stores when it sends the form — the signed copy's id, else a hash of the
  printed values — and `changed_since(deal, form_key, sent)` compares it with now (G113).
"""

import hashlib
import json

from documents.models import Document

from .. import forms, rfp_rules
from ..models import Questionnaire
from ..pdf import build
from . import context

NOT_TAKEN = 'None of the carriers you picked take this form'
NOT_ASKED = 'This request asks for no level-funded, self-funded or stop-loss quotes'
KIND_LABELS = {'medical': 'Medical questionnaire', 'stop_loss': 'Stop-loss disclosure'}
DOCUMENT_KINDS = {'medical': 'questionnaire', 'stop_loss': 'stop_loss'}


def printed_hash(deal, form_key, row=None, facts=None):
    """A hash of what the form prints now: every printed answer and both signatures."""
    found = build.printed_of(deal, form_key, row, facts)
    signers = [{'name': s['name'], 'date': s['date']} if s else None for s in (found.officer, found.agent)]
    body = {'scalars': found.scalars, 'rows': found.rows, 'signers': signers}
    return hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode('utf-8')).hexdigest()[:16]


def _signed_document(row):
    return row.signed_document_id if row is not None and row.locked else None


def sent_with(deal, form_key, row=None, facts=None):
    if row is None:
        row = Questionnaire.objects.filter(deal_id=deal.id, form=form_key).first()
    document = _signed_document(row)
    if document:
        return {'form': form_key, 'document': document}
    return {'form': form_key, 'hash': printed_hash(deal, form_key, row, facts)}


def changed_since(deal, form_key, sent):
    return rfp_rules.changed_since(sent, sent_with(deal, form_key))


def _paper(deal):
    """{document kind: [{id, review_state}]} of the deal's paper copies, newest first; a wrong one never goes."""
    found = {}
    rows = Document.objects.filter(deal_id=deal.id, kind__in=DOCUMENT_KINDS.values(), protected=False)
    for doc in rows.exclude(review_state='wrong').order_by('-uploaded_at', '-id').values('id', 'kind', 'review_state'):
        found.setdefault(doc['kind'], []).append(doc)
    return found


def _tick(form, carriers, lines, funding):
    """(default tick, reason when it is off)."""
    if form['kind'] == 'stop_loss':
        needed = rfp_rules.disclosure_needed(lines, funding)
        return needed, '' if needed else NOT_ASKED
    if not carriers:
        return True, ''  # nobody picked yet: it rides along
    taken = any(rfp_rules.takes(form, carrier) for carrier in carriers)
    return taken, '' if taken else NOT_TAKEN


def rfp_files(deal, carriers=(), lines=(), funding=()):
    ctx = context.deal_context(deal)
    paper = _paper(deal)
    out = []
    for resolved in ctx.resolved.values():
        key = resolved['form']
        if not key:
            continue
        form, row = forms.FORMS[key], ctx.stored.get(key)
        papers = paper.get(DOCUMENT_KINDS[form['kind']], [])
        include, reason = _tick(form, carriers, lines, funding)
        out.append(
            {
                'key': f'questionnaire:{key}',
                'form': key,
                'item': resolved['item'],
                'label': f'{KIND_LABELS[form["kind"]]} — {form["carrier"]}',
                'signed': bool(row and row.locked),
                **rfp_rules.copy_to_send(_signed_document(row), papers),
                'include': include,
                'applicable': include,
                'reason': reason,
                'filename': build.file_name(deal, key),
                'paper': [doc['id'] for doc in papers],
            }
        )
    return out
