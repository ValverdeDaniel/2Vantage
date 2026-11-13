"""The reads behind Card 1, Get to Market (plan.md §8.6; M42–M61, M67, M108–M111; slice 63). Reads only, inside the
payload's batch scope: intake's payload (the gate, its checklist in full and the coverage intent, as the Intake tab
reads them), the census's stored counts, the questionnaire items with their progress and the forms' names, the one
headcount and the enrollment check (`quotes.facts.enrollment_check`, shared with the RFP). `gtm.card` does the rest.

`get_to_market(deal, pending, refusal, quotes)` → (card, check, intake): the card, the enrollment check (its own block
too) and intake's payload for the blocks that read it as well (Coverage notes, M80). `pending` is review's client
answers waiting; slice 58 adds `questionnaire` to them (read as 0 while absent).
"""

from census import facts as census_facts
from intake import providers as intake_providers
from intake import selectors as intake_selectors
from questionnaire import forms as questionnaire_forms
from quotes import facts as quote_facts

from . import gtm

CHECK_KEYS = ('intake', 'census', 'advisor', 'differ', 'warning')


def enrollment(deal):
    """(check, headcount): `enrollment_check`'s three answers and warning (M67), and the headcount the band uses."""
    found = quote_facts.enrollment_check(deal)
    return {key: found[key] for key in CHECK_KEYS}, found['used']


def get_to_market(deal, pending, refusal, quotes):
    intake = {**intake_selectors.intake_payload(deal), 'requested_lines': list(deal.requested_lines or [])}
    forms = intake_providers.questionnaire_items(deal.id)
    labels = {found['form']: questionnaire_forms.label(found['form']) for found in forms.values() if found.get('form')}
    check, headcount = enrollment(deal)
    facts = gtm.Facts(
        intake=intake,
        census=census_facts.stored(deal.id),
        pending=pending or {},
        forms=forms,
        form_labels=labels,
        headcount=headcount,
        check=check,
        quotes=(quotes or {}).get('quotes', 0),
        refusal=refusal,
    )
    return gtm.card(facts), check, intake
