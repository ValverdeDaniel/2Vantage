"""The request, read once (plan.md §5.7; K.6 "built once per request"; K17, K101): what the cards, the drafts, the
forms, the cover, the packet and the check all read, so they cannot disagree about the group within one answer.

`Request(deal)` holds the stored settings with every default filled in — the band from the one headcount (K17), the
route (stored, else the band's), the funding asked (stored, else the medical incumbent's), the requested lines, the
carriers picked, the form variant — and reads the rest lazily, once each: the group facts (`quotes.facts.group_facts`),
the agency, the census counts and people, the questionnaire's RFP files (`questionnaire.selectors.rfp.rfp_files`), the
documents that can ride the packet and the latest issued proposal. Nothing here writes.

The returns inbox (OQ65 default): `AgencySettings.rfp_return_email`, else the deal owner's email.
"""

from functools import cached_property

from census import facts as census_facts
from commission import selectors as commission_selectors
from deals import carriers as identities
from deals import lines
from deals.models import AgencySettings
from documents.models import Document
from intake.models import CurrentCoverage
from questionnaire.selectors import rfp as questionnaire_rfp
from quotes import facts as quote_facts

from . import cleaners, printed, request
from .forms import maps
from .models import RfpRequest

# The documents the packet can carry (K49; plan.md §9.10): the client's own files and the paper copies of forms.
ATTACHMENT_KINDS = ('renewal', 'quote', 'claims', 'invoice', 'sbc', 'questionnaire', 'stop_loss')
ISSUED = 'proposal'
SELF_FUNDED = ('level_funded', 'self_funded')


class Request:
    def __init__(self, deal, row=None, *, loaded=False, stored=None):
        """`loaded`: `row` is the deal's RfpRequest (or None) already read; `stored`: the settings as a write is about
        to leave them (the service works the packet's defaults out against those)."""
        self.deal = deal
        self.row = row if loaded else RfpRequest.objects.filter(deal_id=deal.id).first()
        self.stored = stored if stored is not None else cleaners.stored(self.row)
        self.lines = [line for line in lines.LINE_KEYS if line in set(deal.requested_lines or [])]
        self.picked = [key for key in self.stored['carriers'] if key in identities.BY_KEY]
        self.variant = maps.variant_of(self.stored['form'])

    @cached_property
    def check(self):
        """The three enrolled counts and the one the band uses (K19)."""
        return quote_facts.enrollment_check(self.deal)

    @property
    def count(self):
        return self.check['used']['count']

    @property
    def band(self):
        return request.band(self.count)

    @property
    def route(self):
        return request.route(self.stored['route'], self.band)[0]

    @property
    def route_default(self):
        return request.route(self.stored['route'], self.band)[1]

    @cached_property
    def funding(self):
        stored = self.stored['funding']
        if stored is not None:
            return request.funding(stored, [])
        found = quote_facts.incumbent(self.deal, 'medical') or {}
        return request.funding(None, request.default_funding(found.get('funding')))

    @cached_property
    def chips(self):
        return request.chips(set(self.picked), self.band, self.lines, identities.CARRIERS)

    @cached_property
    def chip(self):
        return {row['key']: row for row in self.chips}

    @cached_property
    def agency(self):
        return AgencySettings.get()

    @cached_property
    def rates(self):
        """{line: {rate, source}}: each requested line's commission ask, the deal's agreed rate else the agency's."""
        return commission_selectors.requested_rates(self.deal)

    @cached_property
    def commission(self):
        """(the text the form prints, ['Medical: 5%', …]) (K29, K106), from commission's requested rates."""
        return request.commission_text(self.lines, {line: found['rate'] for line, found in self.rates.items()}, None)

    @cached_property
    def group(self):
        return quote_facts.group_facts(self.deal)

    @cached_property
    def census(self):
        return census_facts.stored(self.deal.id)

    @property
    def members(self):
        return self.census['employees'] + self.census['dependents']

    @cached_property
    def people(self):
        return census_facts.people(self.deal.id)

    @cached_property
    def fte(self):
        return printed.fte(self.deal, self.people)

    @cached_property
    def forms(self):
        """The questionnaire's cards for this request (G110–G113): its copy, default tick and reason."""
        return questionnaire_rfp.rfp_files(self.deal, self.picked, self.lines, self.funding)

    @cached_property
    def documents(self):
        """The live documents that can ride the packet, newest first; a file marked wrong never goes (G110)."""
        rows = Document.objects.filter(deal_id=self.deal.id, kind__in=ATTACHMENT_KINDS, protected=False)
        rows = rows.exclude(review_state='wrong').select_related('deal__client')
        return list(rows.order_by('-uploaded_at', '-id'))

    @cached_property
    def form_documents(self):
        """{id: Document} of the copies the questionnaire rows send (a filed signed copy, an accepted paper copy)."""
        ids = [entry['document'] for entry in self.forms if entry['document']]
        if not ids:
            return {}
        return {doc.id: doc for doc in Document.objects.filter(deal_id=self.deal.id, pk__in=ids)}

    @cached_property
    def self_funded(self):
        """A line in force is level- or self-funded (claims then ride the packet at any size, K49)."""
        return CurrentCoverage.objects.filter(deal_id=self.deal.id, in_force=True, funding__in=SELF_FUNDED).exists()

    @cached_property
    def issued(self):
        """The latest issued proposal (OQ68; J169), or None."""
        return Document.objects.filter(deal_id=self.deal.id, kind=ISSUED).order_by('-uploaded_at', '-id').first()

    @property
    def group_name(self):
        return self.group.get('group.legal_name') or self.deal.client.name

    @cached_property
    def return_to(self):
        """Where the carriers reply (OQ65): the agency's returns inbox, else the deal owner's email; '' when neither."""
        owner = self.deal.owner
        return (self.agency.rfp_return_email or '').strip() or ((owner.email or '').strip() if owner else '')

    @property
    def agent(self):
        return self.group.get('broker.agent') or ''

    def other_text(self):
        return (self.stored['other_carriers'] or '').strip()
