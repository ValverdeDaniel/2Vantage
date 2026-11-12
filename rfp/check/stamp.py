"""`checks_stamp` (K.6; K52): a short hash of everything the check reads, so the page asks for the pills again only when
it moves. It covers the census (its people's last change and number, its stored counts), the questionnaires, intake's
answers and coverage rows, the deal's documents, what the deal prints (effective date, lines, owner, agent), the
headcount the band uses, and the request's funding, carriers, other carriers, route, form and ticks, and what the
registered providers' lines read (`providers.stamps`; slice 55). Marks, sends, notes and the due date do not change
it. Reads only, in a fixed number of queries.
"""

import hashlib
import json

from django.db.models import Count, Max

from census.models import CensusFacts, Member
from documents.models import Document
from intake.models import CurrentCoverage, Intake
from questionnaire.models import Questionnaire

from . import providers

PARTS = ('funding', 'carriers', 'other_carriers', 'route', 'form', 'include')


def _first(queryset, *fields):
    return list(queryset.values_list(*fields).first() or ())


def stamp(ctx):
    deal = ctx.deal
    members = Member.all_objects.filter(deal_id=deal.id).aggregate(at=Max('updated_at'), n=Count('id'))
    documents = Document.all_objects.filter(deal_id=deal.id).values_list('id', 'kind', 'role', 'review_state',
                                                                        'archived_at', 'lines')  # fmt: skip
    found = {
        'members': [members['at'], members['n']],
        'facts': _first(CensusFacts.objects.filter(deal_id=deal.id), 'updated_at'),
        'forms': Questionnaire.objects.filter(deal_id=deal.id).aggregate(at=Max('updated_at'), n=Count('id')),
        'intake': _first(Intake.objects.filter(deal_id=deal.id), 'updated_at'),
        'coverage': list(
            CurrentCoverage.objects.filter(deal_id=deal.id).values_list('line', 'in_force', 'carrier', 'funding')
        ),  # fmt: skip
        'documents': sorted(documents),
        'deal': [deal.effective_date, sorted(deal.requested_lines or []), deal.owner_id, deal.agent_of_record],
        'count': [ctx.count, bool(ctx.check.get('differ'))],
        'request': [ctx.stored[key] for key in PARTS],
        'providers': providers.stamps(deal),  # what the registered lines read (L120; slice 55)
    }
    text = json.dumps(found, sort_keys=True, default=str)
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]
