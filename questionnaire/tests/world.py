"""A synthetic deal for the questionnaire's tests: intake answers, a primary contact and current medical plans, built
through each owner's services. Every name and number is invented."""

from conftest import make_deal

ANSWERS = {
    'legal_name': 'Example Fabrication LLC',
    'address_physical': '12 Sample Road, Orlando, FL 32801',
    'fein': '00-7654321',
    'sic_code': '3441 — Fabricated Structural Metal',
    'atne': '58',
    'employee_count': '62',
    'enrolled_count': '60',
    'years_in_business': '9',
    'waiting_period': '1st of the month following 30 days',
}
RATES = {'rate_ee': '612.50', 'rate_es': '1300.00', 'rate_ec': '1100.00', 'rate_fam': '1800.00'}


def make_world(user, *, enrolled='60', lines=('medical',), plans=1, contact=True, answers=None):
    from deals.services.contacts import create_contact
    from intake.services import update_answers
    from quotes.services.plans import create_plan

    deal = make_deal(user, requested_lines=lines, name='Example Fabrication (synthetic)')
    update_answers(user, deal.id, {**ANSWERS, 'enrolled_count': enrolled, **(answers or {})})
    if contact:
        create_contact(
            user, deal.client_id, role='hr_admin', name='Pat Sample', title='HR Lead', phone='555-0199', is_primary=True
        )
    for number in range(plans):
        create_plan(
            user, deal, line='medical', role='current', carrier='Florida Blue', name=f'BlueOptions {number + 1}',
            values={'funding': 'fully_insured', **RATES},
        )  # fmt: skip
    deal.refresh_from_db()
    return deal


def set_enrolled(user, deal, count):
    from intake.services import update_answers

    update_answers(user, deal.id, {'enrolled_count': str(count)})
