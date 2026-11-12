"""The stop-loss workbook's Binding Notes (plan.md §9.13; F106, G117; the old pipeline/workbooks._sl_binding_rows at
891f1b3): the binding and disclosure checklist, with a live status where the deal knows the answer and an open
working-paper row everywhere else.

The SIIA disclosure's state comes from the questionnaire through quotes' provider slot `disclosure_state` (G117,
O.6 #47), in the old app's own words (`providers.DISCLOSURE_WORDS`); quotes never imports questionnaire. The plan
document, the claims experience and the roster are read from documents and the census, both left of quotes. Counts
and words only: no member, no file name (rule 10).
"""

from census import facts as census_facts
from documents.models import Document

from .. import providers

ITEMS = [
    'Disclosure: claimants at or above 50% of spec (paid + pending)',
    'Disclosure: transplant / oncology / dialysis / NICU / specialty Rx',
    'Disabled / COBRA / retirees on census',
    'Incumbent large-claim notices filed',
    'Plan document / SPD matches quoted design',
    'Final census (DOB, gender, tier, ZIP) attached',
    '24 months paid claims + large-claim listing',
    'First month premium / deposit instructions',
    'No-new-laser request at renewal',
    'Rate cap requested?',
    'Preferred proposal selected on Option Comparison',
]
FOOTER = (
    'Stop-loss reimburses the plan sponsor, not employees. Lasers, rates, run-in, and contract basis are not bound '
    'until the carrier issues a policy or written binder. Compare laser liability, not premium alone.'
)
PLAN_DOCUMENT_KINDS = {'plan_doc', 'sbc'}
CLAIMS_KINDS = {'claims'}


def binding_notes(deal):
    """[(item, status)] in the old order; a status only where the deal can state it."""
    words = providers.DISCLOSURE_WORDS
    disclosure = words.get(providers.disclosure_state(deal.id), words[providers.NOT_STARTED])
    kinds = set(Document.objects.filter(deal_id=deal.id).values_list('kind', flat=True))
    employees = census_facts.stored(deal.id)['employees']
    status = {
        ITEMS[0]: disclosure,
        ITEMS[1]: disclosure,
        ITEMS[4]: 'Plan document on file' if PLAN_DOCUMENT_KINDS & kinds else 'No plan document on file',
        ITEMS[5]: f'{employees} employees on the roster' if employees else 'No census rows yet',
        ITEMS[6]: 'Claims experience on file' if CLAIMS_KINDS & kinds else 'No claims document on file',
    }
    return [(item, status.get(item, '')) for item in ITEMS]
