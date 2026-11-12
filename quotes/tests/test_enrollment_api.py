"""The typed-enrollment door and the headcount (plan.md §5.5, §5.7, §7.8; F85, F88, F90–F92; OQ18, OQ21; Q.3 #1;
Q.9 row 13): the line's whole typed set, an unchanged save writing nothing, Keep, the switch, census plan names,
Revert, the refusals, and the headcount's order with its cross-check."""

import pytest

from conftest import make_deal
from contract_helpers import write_path_contract
from deals import activity
from deals.models import Activity
from intake import providers as intake_providers
from intake.services import update_answers
from quotes import facts, services
from quotes.models import LineEnrollment, Plan

pytestmark = pytest.mark.django_db

RATES = {'rate_ee': '500', 'rate_es': '1000', 'rate_ec': '900', 'rate_fam': '1500'}
FIGURE = {'EE': 20, 'ES': 5, 'EC': 3, 'FAM': 2}


def add(user, deal, role='alternate', name='HMO 1500', line='medical', **kw):
    values = kw.pop('values', RATES)
    return services.create_plan(user, deal, line=line, role=role, carrier='Aetna', name=name, values=values, **kw)


def post(api, deal, body):
    return api.post(f'/api/deals/{deal.id}/plans/enrollment/', {'line': 'medical', **body}, format='json')


def board(api, deal, line='medical'):
    return api.get(f'/api/deals/{deal.id}/plans/', {'line': line}).json()


def test_F88_the_line_figure_prices_a_quote_first_line_and_says_so(api, user, deal):
    quote = add(user, deal)
    response = post(api, deal, {'whole_line': FIGURE})
    assert response.status_code == 200
    assert response.json()['line_enrollment']['figure'] == FIGURE
    body = board(api, deal)
    (row,) = body['plans']
    assert (row['id'], row['premium']['monthly'], row['enrollment_source']) == (
        quote.id,
        20700,
        'line',
    )  # 20×500 + 5×1000 + 3×900 + 2×1500
    assert body['enrollment']['figure'] == FIGURE and body['enrollment']['offers_figure'] is True
    assert Activity.objects.get(pk=response.json()['activity_id']).summary == 'Edited enrollment on Medical'


def test_Q3_1_line_figure_write_path(user, deal):
    add(user, deal)
    services.set_enrollment(user, deal, 'medical', whole_line=FIGURE)
    row = LineEnrollment.objects.get(deal=deal, line='medical')

    def figure(ee):
        return lambda: services.set_enrollment(user, deal, 'medical', whole_line={**FIGURE, 'EE': ee})

    write_path_contract(user, row, call=figure(25), read=lambda r: r.enrollment, later=figure(26))


def test_Q9_13_an_unchanged_save_writes_nothing(user, deal):
    plan = add(user, deal, role='current')
    first = services.set_enrollment(user, deal, 'medical', plans=[{'id': plan.id, 'enrollment': FIGURE}], whole_line={})
    stamped = LineEnrollment.objects.get(deal=deal, line='medical').typed_at
    count = Activity.objects.count()
    again = services.set_enrollment(user, deal, 'medical', plans=[{'id': plan.id, 'enrollment': FIGURE}], whole_line={})
    assert first.activity and again == (([], None, None))
    assert Activity.objects.count() == count
    assert LineEnrollment.objects.get(deal=deal, line='medical').typed_at == stamped


def test_F85_the_whole_set_clears_a_plan_it_leaves_out(user, deal):
    a, b = add(user, deal, role='current'), add(user, deal, role='current', name='PPO 2500')
    services.set_enrollment(
        user, deal, 'medical', plans=[{'id': a.id, 'enrollment': FIGURE}, {'id': b.id, 'enrollment': FIGURE}]
    )
    services.set_enrollment(user, deal, 'medical', plans=[{'id': a.id, 'enrollment': FIGURE}])
    assert Plan.objects.get(pk=b.pk).enrollment == {}


def test_F88_the_switch_prices_without_typed_counts_and_keeps_them(api, user, deal):
    add(user, deal)
    services.set_enrollment(user, deal, 'medical', whole_line=FIGURE)
    stamped = LineEnrollment.objects.get(deal=deal, line='medical').typed_at
    response = post(api, deal, {'on': False})
    assert Activity.objects.get(pk=response.json()['activity_id']).summary == 'Switched typed counts off on Medical'
    row = board(api, deal)
    assert row['plans'][0]['premium']['reason'] == 'no_enrollment' and row['enrollment']['figure'] == FIGURE
    assert LineEnrollment.objects.get(deal=deal, line='medical').typed_at == stamped  # a switch is not typing


def test_F90_a_census_text_given_to_one_plan_leaves_the_other(api, user, deal):
    a, b = add(user, deal, role='current'), add(user, deal, role='current', name='PPO 2500')
    services.set_enrollment(user, deal, 'medical', census_names={a.id: ['Aetna POS 2000', 'HMO 1500 (old)']})
    response = post(api, deal, {'census_names': {str(b.id): ['HMO 1500 (old)']}})
    assert response.status_code == 200
    assert Plan.objects.get(pk=a.pk).census_names == ['Aetna POS 2000']
    assert Plan.objects.get(pk=b.pk).census_names == ['HMO 1500 (old)']
    row = Activity.objects.get(pk=response.json()['activity_id'])
    assert row.summary == 'Matched census plan names on Medical'
    activity.revert(row.id, user)
    assert Plan.objects.get(pk=a.pk).census_names == ['Aetna POS 2000', 'HMO 1500 (old)']


def test_F91_keep_without_a_later_census_writes_nothing(user, deal):
    add(user, deal)
    services.set_enrollment(user, deal, 'medical', whole_line=FIGURE)
    assert services.set_enrollment(user, deal, 'medical', keep=True).activity is None


@pytest.mark.parametrize(
    'body, field',
    [
        ({'line': 'nope'}, 'line'),
        ({'plans': [{'id': 'x', 'enrollment': FIGURE}]}, 'plans'),
        ({'plans': [{'id': 999999, 'enrollment': FIGURE}]}, 'plans'),
        ({'whole_line': {'lives': 4}}, 'enrollment'),
        ({'whole_line': {'EE': 2.5}}, 'enrollment'),
        ({'whole_line': {'EE': -1}}, 'enrollment'),
        ({'on': 'yes'}, 'on'),
        ({'census_names': ['Aetna']}, 'census_names'),
    ],
)
def test_F85_a_bad_save_answers_400_naming_the_field(api, user, deal, body, field):
    add(user, deal)
    response = post(api, deal, body)
    assert response.status_code == 400 and field in response.json()


def test_F90_census_names_go_only_on_current_plans(api, user, deal):
    quote = add(user, deal)
    response = post(api, deal, {'census_names': {str(quote.id): ['HMO 1500']}})
    assert response.status_code == 400
    assert response.json()['census_names'] == [f'Plan {quote.id} is not a current plan on Medical.']


def test_A34_revert_of_counts_refuses_on_a_sold_plan(user, deal):
    plan = add(user, deal, role='current')
    saved = services.set_enrollment(user, deal, 'medical', plans=[{'id': plan.id, 'enrollment': FIGURE}])
    Plan.objects.filter(pk=plan.pk).update(sold=True)
    with pytest.raises(activity.Refused) as refused:
        activity.revert(saved.activity.id, user)
    assert 'marked sold' in refused.value.sentence


def test_F59_a_move_to_another_line_clears_a_current_plans_census_names_and_undo_restores_them(user, deal):
    plan = add(user, deal, role='current')
    services.set_enrollment(user, deal, 'medical', census_names={plan.id: ['HMO 1500 (old)']})
    _moved, row = services.move_line(user, deal, [plan.id], 'dental')
    assert Plan.objects.get(pk=plan.pk).census_names == []
    activity.revert(row.id, user)  # Undo of the move puts the plan, and its census plan names, back
    assert Plan.objects.get(pk=plan.pk).census_names == ['HMO 1500 (old)']


def test_5_7_OQ21_the_headcount_reads_the_advisor_then_intakes_enrolled_count_then_an_estimate(user):
    deal = make_deal(user, requested_lines=('medical',))
    update_answers(user, deal.id, {'employee_count': '61'})
    assert facts.enrolled_headcount(deal) == {
        'count': 61,
        'source': 'intake.employee_count',
        'estimate': True,
        'via': '',
    }
    update_answers(user, deal.id, {'enrolled_count': '44'})
    assert intake_providers.headcount(deal.id) == {'count': 44, 'source': 'intake.enrolled_count', 'estimate': False}
    add(user, deal)
    services.set_enrollment(user, deal, 'medical', whole_line=FIGURE)
    assert intake_providers.headcount(deal.id) == {'count': 30, 'source': 'advisor', 'estimate': False}
    check = facts.enrollment_check(deal)
    assert (check['intake'], check['census'], check['advisor'], check['differ']) == (44, None, 30, True)
    assert check['warning'] == 'Enrolled: intake 44 · census none · Advisor 30 — the band uses the Advisor, 30.'


def test_5_7_the_cross_check_says_when_the_band_uses_an_estimate(user):
    deal = make_deal(user, requested_lines=('medical',))
    update_answers(user, deal.id, {'employee_count': '61'})
    assert facts.enrollment_check(deal)['warning'] is None  # one answer known: nothing to cross-check
    assert facts.enrolled_headcount(deal)['estimate'] is True
