"""The finder's index (plan.md §7.8 `plans/find/`; F14, F15, OQ14): every line's plans in one read, each with the texts
the finder searches and the carrier its name means, so the browser can fold "UHC" into UnitedHealthcare."""

import pytest

from conftest import make_deal
from quotes import services
from quotes.selectors import find_index

pytestmark = pytest.mark.django_db


def plan(user, deal, line='medical', role='alternate', carrier='Cigna', name='Open Access', **values):
    return services.create_plan(user, deal, line=line, role=role, carrier=carrier, name=name, values=values)


def test_F14_the_index_lists_every_line_with_the_texts_the_finder_searches(user):
    deal = make_deal(user)
    current = plan(user, deal, role='current', carrier='Aetna', name='HMO 1000', network='Aetna HMO', plan_type='HMO')
    quote = plan(user, deal, carrier='UHC Level-Funded', name='Choice Plus 1500', plan_type='PPO')
    services.update_plan(user, quote.id, {'plan_number': 'H1234-001'})
    dental = plan(user, deal, line='dental', carrier='Delta Dental', name='PPO 1500')
    by_id = {entry['id']: entry for entry in find_index(deal)}
    assert by_id[current.id] == {
        'id': current.id,
        'line': 'medical',
        'current': True,
        'carrier': 'aetna',
        'texts': ['HMO 1000', 'Aetna', 'Aetna HMO', 'HMO'],
    }
    assert by_id[quote.id]['carrier'] == 'unitedhealthcare'  # the one matcher, deals.carriers.match
    assert by_id[quote.id]['texts'] == ['Choice Plus 1500', 'H1234-001', 'UHC Level-Funded', 'PPO']
    assert by_id[dental.id]['line'] == 'dental' and by_id[dental.id]['carrier'] is None


def test_F14_codes_are_searched_and_removed_plans_are_not_listed(user):
    deal = make_deal(user)
    kept = plan(user, deal)
    gone = plan(user, deal, name='Gone')
    type(kept).objects.filter(pk=kept.id).update(codes=['5182', {'sbc': 'X-77'}, {'n': 3}])
    services.delete_plans(user, deal, [gone.id])
    (entry,) = find_index(deal)
    assert entry['id'] == kept.id and entry['texts'][-3:] == ['5182', 'X-77', '3']


def test_F15_the_endpoint_answers_every_line_at_once(api, user):
    deal = make_deal(user)
    plan(user, deal)
    plan(user, deal, line='vision', carrier='VSP', name='Choice 10/25')
    response = api.get(f'/api/deals/{deal.id}/plans/find/')
    assert response.status_code == 200
    assert {entry['line'] for entry in response.json()['plans']} == {'medical', 'vision'}
    assert api.get('/api/deals/999999/plans/find/').status_code == 404
