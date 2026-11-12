"""Intake's facts for Agenda and the Overview (plan.md §5.10; B35): the ready state, its gaps and the journey's counts,
for many deals at once, counts and flags only."""

import pytest

from conftest import make_deal
from deals.services import create_contact
from intake import services, summary

pytestmark = pytest.mark.django_db


def test_B35_facts_say_what_stands_between_each_deal_and_the_market(user, deal):
    other = make_deal(user, name='Other Co.')
    services.update_answers(user, other.id, {'legal_name': 'Other Co. LLC'})
    create_contact(user, other.client_id, role='hr_admin', name='Riley Example', email='riley@example.test')
    services.sign_bor(user, other.id, 'Jordan Example')
    services.mark_marketed(user, other.id, override=True)
    found = summary.facts([deal.id, other.id, 10**9])
    assert set(found) == {deal.id, other.id}
    blocked, marketed = found[deal.id], found[other.id]
    assert blocked['ready_state'] == 'blocked' and blocked['marketed_at'] is None
    assert {'HR contact', 'Signed BOR', 'Census'} <= set(blocked['gaps'])
    assert blocked['answered'] == 0 and blocked['needed'] == len(blocked['missing'])
    assert marketed['ready_state'] == 'submitted' and marketed['marketed_at'] is not None
    assert (marketed['contacts_ok'], marketed['bor_on_file'], marketed['census_ok']) == (True, True, False)
    assert marketed['answered'] == 1 and 'Legal Company Name' not in marketed['missing']
    assert set(marketed['checklist']) == {'tier', 'required', 'done', 'missing', 'all_clear'}
