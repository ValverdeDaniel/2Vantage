"""`quotes.facts.group_facts` (plan.md §5.7; K101, G28): the group's facts the carrier forms print, read once."""

import pytest

from conftest import make_deal
from quotes import facts

pytestmark = pytest.mark.django_db


def test_G28_split_address_reads_street_city_state_and_zip_or_leaves_them_blank():
    assert facts.split_address('12 Sample Road, Orlando, fl 32801') == (
        '12 Sample Road',
        'Orlando',
        'FL',
        '32801',
        'Orlando, fl 32801',
    )
    assert facts.split_address('Somewhere near the river') == ('Somewhere near the river', '', '', '', '')
    assert facts.split_address('') == ('', '', '', '', '')


def test_K101_G28_group_facts_read_intake_the_primary_contact_the_incumbent_and_the_agency(user):
    from deals.services.contacts import create_contact
    from intake.services import create_coverage, update_answers
    from quotes.services.plans import create_plan

    deal = make_deal(user, requested_lines=('medical', 'dental'), name='Example Facts (synthetic)')
    found = facts.group_facts(deal)
    assert found['group.legal_name'] == 'Example Facts (synthetic)' and found['group.current_carrier'] == ''
    assert found['group.address_state'] == '' and not found['broker.is_bor']
    update_answers(user, deal.id, {'legal_name': 'Example Facts LLC', 'address_physical': '1 Main St, Tampa, FL 33602',
                                   'atne': '55', 'employee_count': '58', 'enrolled_count': '52'})  # fmt: skip
    create_contact(user, deal.client_id, role='prior_broker', name='Old Broker')
    create_contact(user, deal.client_id, role='billing', name='Lee Sample', title='Controller', phone='555-0101')
    create_coverage(user, deal.id, {'line': 'dental', 'carrier': 'Dental Co'})
    found = facts.group_facts(deal)
    assert (found['group.legal_name'], found['group.address_city'], found['group.zip']) == (
        'Example Facts LLC',
        'Tampa',
        '33602',
    )
    assert found['group.atne'] == '55' and found['group.eligible'] == '58' and found['group.enrolled'] == '52'
    assert (found['group.contact_name'], found['group.contact_first'], found['group.contact_last']) == (
        'Lee Sample',
        'Lee',
        'Sample',
    )  # never the prior broker
    assert found['group.current_carrier'] == ''  # a dental incumbent is not the medical one (N1)
    create_plan(user, deal, line='medical', role='current', carrier='Florida Blue', name='PPO')
    assert facts.group_facts(deal)['group.current_carrier'] == 'Florida Blue'
