"""Attach SBC… (plan.md §7.8, §10.4; D38, D47, OQ33; slice 22; the old AttachSbcView and `attachSbc`, 891f1b3): one
plan's Summary of Benefits and Coverage, filed on the deal as an SBC and read into that plan's design.

The read always waits for a person's review (OQ33: even a direct person's), so the toast's "review it before it
changes the plan" is true; it lands through the SBC reader (`reader/sbc.py`). The file is a new upload, filed as kind
`sbc` with the plan's carrier, its role and the medical line, or an SBC already on the deal (`document_id`). Refused in
words before anything is stored: without Claude (409), on a plan of another line (an SBC is a medical plan's), and on
a priced version or a copy, which take their design from the plan they were made from (the old menu's rule).
"""

from rest_framework.exceptions import ValidationError

from ai import client
from ai import services as ai
from deals.activity import Refused
from documents import services as documents
from documents.models import Document

from ..models import Plan

ROLE_OF_PLAN = {'current': 'current', 'renewal': 'renewal', 'alternate': 'alternates'}
NOT_MEDICAL = 'An SBC describes a medical plan, so it attaches to medical plans only.'
DERIVED = '{name} takes its design from the plan it was made from: attach the SBC to that plan.'
NO_FILE = 'Choose the SBC to attach: a file, or one already on the deal.'
NOT_SBC = 'That file is not filed as an SBC: set its type to SBC, or upload it here.'
NOT_THIS_DEAL = 'That file is not on this deal.'


def attach(user, plan_id, *, upload=None, document_id=None, model=''):
    """(job, created): the SBC read for `plan_id`, waiting for review once it ends."""
    plan = Plan.objects.select_related('deal').get(pk=plan_id)
    if not client.available():
        raise Refused(client.NoKey.sentence)
    if plan.line != 'medical':
        raise Refused(NOT_MEDICAL)
    if plan.derived_from_id:
        raise Refused(DERIVED.format(name=f'{plan.carrier} {plan.name}'))
    deal = plan.deal
    if upload is not None:
        document = documents.upload(
            user,
            deal,
            upload,
            {
                'kind': 'sbc',
                'role': ROLE_OF_PLAN.get(plan.role, ''),
                'carrier': plan.carrier,
                'lines': ['medical'],
            },
        )
    elif document_id is not None:
        document = Document.objects.filter(deal=deal, pk=document_id).first()
        if document is None:
            raise ValidationError({'document_id': [NOT_THIS_DEAL]})
        if document.kind != 'sbc':
            raise ValidationError({'document_id': [NOT_SBC]})
    else:
        raise ValidationError({'file': [NO_FILE]})
    return ai.start_read(user, deal, [document.id], target='sbc', model=model, plan=plan.id)
