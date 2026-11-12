"""Staff answers, rows and the first write (G18, G27, G33, G43, G123, G133, G134, G136)."""

import pytest
from django.http import Http404
from rest_framework.exceptions import ValidationError

from deals import activity
from deals.models import Activity
from intake.models import Intake
from questionnaire import services
from questionnaire.models import Questionnaire
from questionnaire.selectors import payload

from .world import make_world

pytestmark = pytest.mark.django_db
FL = 'fl_blue_51'


@pytest.fixture
def world(user):
    return make_world(user, plans=2)


def test_G26_a_read_never_makes_the_row(world):
    shown = payload.form_payload(world, FL)
    assert not Questionnaire.objects.exists() and not shown['started']
    assert [r['plan'] for r in shown['rows']['plans']] and shown['values']['txtCoName'] == 'Example Fabrication LLC'


def test_G133_G134_the_first_write_makes_the_row_with_a_plan_row_per_current_plan_and_freezes_the_band(user, world):
    shown = payload.form_payload(world, FL)
    first = shown['rows']['plans'][0]['id']
    answered = services.set_answers(user, world.id, FL, {f'plans.{first}.numCurrRatePrem': '25000'})
    row = Questionnaire.objects.get(deal=world, form=FL)
    assert [r.get('plan') for r in row.rows['plans']] == [r['plan'] for r in shown['rows']['plans']]
    assert row.answers == {f'plans.{first}.numCurrRatePrem': '25000'} and answered.activity
    entry = Intake.objects.get(deal=world).checklist['medical_questionnaire']
    assert (entry['form_key'], entry['form_source']) == (FL, 'band')
    after = payload.form_payload(world, FL)
    assert after['values'][f'plans.{first}.txtCurrPlanName'] == 'BlueOptions 1'  # unwritten slots follow the plan


def test_G18_dropped_answers_come_back_and_an_unchanged_value_writes_nothing(user, world):
    first = services.set_answers(user, world.id, FL, {'txtRsnBid': 'Renewal Increase', 'numTAP': 'lots'})
    assert first.dropped == [{'slot': 'numTAP', 'reason': 'not_number'}]
    count = Activity.objects.count()
    again = services.set_answers(user, world.id, FL, {'txtRsnBid': 'Renewal Increase'})
    assert again.changed == {} and again.activity is None and Activity.objects.count() == count


def test_G33_emptying_a_prefilled_box_hides_only_the_prefill_and_typing_brings_it_back(user, world):
    services.set_answers(user, world.id, FL, {'txtCoName': ''})
    row = Questionnaire.objects.get(deal=world, form=FL)
    assert row.cleared == ['txtCoName'] and 'txtCoName' not in row.answers
    assert 'txtCoName' not in payload.form_payload(world, FL)['values']
    services.set_answers(user, world.id, FL, {'txtCoName': 'Typed Co'})
    row.refresh_from_db()
    assert row.cleared == [] and row.answers['txtCoName'] == 'Typed Co'
    services.set_answers(user, world.id, FL, {'txtCoName': ''})
    row.refresh_from_db()
    assert row.cleared == ['txtCoName'] and 'txtCoName' not in row.answers


def test_G23_a_medical_answer_reaches_activity_as_its_key_only(user, world):
    services.set_answers(user, world.id, FL, {'chkMedCon': 'Yes', 'txtRsnBid': 'Renewal Increase'})
    rows = list(Activity.objects.filter(area='questionnaire').order_by('id'))
    texts = [str(r.changes) + r.summary for r in rows]
    assert any(isinstance(e['k'], list) and e['k'] == ['chkMedCon'] for r in rows for e in r.changes)
    assert not any("'Yes'" in t for t in texts)


def test_G123_revert_restores_live_prefill_and_refuses_after_a_later_write(user, world):
    services.set_answers(user, world.id, FL, {'txtCoName': 'Typed Co'})
    row = Activity.objects.filter(area='questionnaire').latest('id')
    activity.revert(row.id, user)
    assert payload.form_payload(world, FL)['values']['txtCoName'] == 'Example Fabrication LLC'
    services.set_answers(user, world.id, FL, {'txtAdd2': 'Suite 4'})
    burst = Activity.objects.filter(area='questionnaire', reverted_at__isnull=True).latest('id')
    from contract_helpers import later_clock

    with later_clock():
        services.set_answers(user, world.id, FL, {'txtAdd2': 'Suite 5'})
    with pytest.raises(activity.Refused) as refused:
        activity.revert(burst.id, user)
    assert refused.value.keys == ['txtAdd2']


def test_G43_rows_keep_their_ids_and_hold_their_limits(user, world):
    added = services.add_row(user, world.id, FL, 'conditions')
    second = services.add_row(user, world.id, FL, 'conditions')
    services.set_answers(user, world.id, FL, {'chkMedCon': 'Yes', f'conditions.{second.row_id}.drpMedCat': 'Diabetes'})
    services.remove_row(user, world.id, FL, 'conditions', added.row_id)
    row = Questionnaire.objects.get(deal=world, form=FL)
    assert [r['id'] for r in row.rows['conditions']] == [second.row_id]
    assert row.answers[f'conditions.{second.row_id}.drpMedCat'] == 'Diabetes'
    with pytest.raises(Http404):
        services.remove_row(user, world.id, FL, 'conditions', added.row_id)
    plans = [r['id'] for r in row.rows['plans']]
    services.remove_row(user, world.id, FL, 'plans', plans[0])
    with pytest.raises(ValidationError):
        services.remove_row(user, world.id, FL, 'plans', plans[1])  # at least one plan row
    for _ in range(11):
        services.add_row(user, world.id, FL, 'plans')
    with pytest.raises(ValidationError):
        services.add_row(user, world.id, FL, 'plans')  # at most twelve
    with pytest.raises(Http404):
        services.add_row(user, world.id, FL, 'nope')


def test_G43_a_removed_row_comes_back_with_its_answers_on_revert(user, world):
    services.set_answers(user, world.id, FL, {'plans.2.numRenPrem': '27000'})
    services.remove_row(user, world.id, FL, 'plans', 2)
    removal = Activity.objects.filter(area='questionnaire', action='rows').latest('id')
    activity.revert(removal.id, user)
    row = Questionnaire.objects.get(deal=world, form=FL)
    assert [r['id'] for r in row.rows['plans']] == [1, 2] and row.answers['plans.2.numRenPrem'] == '27000'


def test_G7_a_form_the_deal_does_not_use_is_refused(user, world):
    with pytest.raises(activity.Refused):
        services.set_answers(user, world.id, 'stop_loss_siia', {'plan_sponsor': 'Example'})
    assert not Questionnaire.objects.exists()


def test_Q3_the_first_write_locks_the_deal_then_intake_then_the_form(user, world):
    from django.db import connection
    from django.test.utils import CaptureQueriesContext

    with CaptureQueriesContext(connection) as queries:
        services.set_answers(user, world.id, FL, {'txtAdd2': 'Suite 4'})
    locks = [q['sql'] for q in queries.captured_queries if 'FOR UPDATE' in q['sql']]
    tables = [
        next(t for t in ('deals_deal', 'intake_intake', 'questionnaire_questionnaire') if t in sql) for sql in locks
    ]
    assert tables[0] == 'deals_deal' and tables[-1] == 'questionnaire_questionnaire'
    assert tables.index('intake_intake') < tables.index('questionnaire_questionnaire')
