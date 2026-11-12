"""The Q.3 contracts for the questionnaire (plan.md §12.3): the write path, GETs write nothing, the permission matrix,
ids past bigint, the answers as the API speaks them, and two writers at once (Q.3 #8)."""

import threading

import pytest
from django.db import connection

from conftest import check_permissions, sweep_gets, write_path_contract
from questionnaire import services
from questionnaire.models import Questionnaire

from .world import make_world

pytestmark = pytest.mark.django_db
FL = 'fl_blue_51'
BASE = 'api/deals/<int:pk>/questionnaires/'


@pytest.fixture
def world(user):
    deal = make_world(user)
    services.set_answers(user, deal.id, FL, {'txtAdd2': 'Suite 1'})
    services.add_row(user, deal.id, FL, 'conditions')
    return deal


def samples(deal):
    one = {'pk': deal.id, 'form': FL}
    row = Questionnaire.objects.get(deal=deal, form=FL).rows['conditions'][0]['id']
    return {
        'api/meta/questionnaires/<slug:form>/': {'form': FL},
        BASE: {'pk': deal.id},
        BASE + 'choice/': {'pk': deal.id},
        BASE + '<slug:form>/': one,
        BASE + '<slug:form>/answers/': one,
        BASE + '<slug:form>/rows/<slug:block>/': {**one, 'block': 'conditions'},
        BASE + '<slug:form>/rows/<slug:block>/<int:row_id>/': {**one, 'block': 'conditions', 'row_id': row},
        BASE + '<slug:form>/sign/': one,
        BASE + '<slug:form>/reopen/': one,
        BASE + '<slug:form>/sources/': one,
        BASE + '<slug:form>/marks/': one,
    }


ALL = {'signed_out': 401, 'producer': 200, 'admin': 200}
MADE = {**ALL, 'producer': 201, 'admin': 201}
NOT_SIGNED = {**ALL, 'producer': 409, 'admin': 409}  # nothing to reopen: the form is not signed
MATRIX = [
    ('GET', 'api/meta/questionnaires/<slug:form>/', ALL),
    ('GET', BASE, ALL),
    ('PATCH', BASE + 'choice/', ALL, {'item': 'stop_loss_disclosure', 'choice': 'stop_loss_siia'}),
    ('GET', BASE + '<slug:form>/', ALL),
    ('PATCH', BASE + '<slug:form>/answers/', ALL, {'answers': {'txtAdd2': 'Suite 2'}}),
    ('POST', BASE + '<slug:form>/rows/<slug:block>/', MADE),
    ('DELETE', BASE + '<slug:form>/rows/<slug:block>/<int:row_id>/', ALL),
    ('GET', BASE + '<slug:form>/sources/', ALL),
    ('POST', BASE + '<slug:form>/marks/', ALL, {'action': 'check', 'refs': [f'questionnaire:{FL}:txtAdd2']}),
    ('POST', BASE + '<slug:form>/sign/', ALL, {'who': 'agent', 'name': 'Dana Agent'}),
    ('POST', BASE + '<slug:form>/reopen/', NOT_SIGNED, {'reason': 'Typo'}),
]


def test_Q3_questionnaire_gets_write_nothing(admin_api, world):
    sweep_gets(admin_api, ('questionnaire',), samples(world))


def test_Q3_questionnaire_permission_matrix(actors, no_csrf_api, world):
    check_permissions(actors, ('questionnaire',), MATRIX, samples(world), no_csrf_api)


def test_Q3_ids_past_bigint_and_unknown_forms_answer_404(api, world):
    assert api.get(f'/api/deals/{2**64}/questionnaires/').status_code == 404
    assert api.get(f'/api/deals/{world.id}/questionnaires/nope/').status_code == 404
    assert api.get('/api/meta/questionnaires/nope/').status_code == 404
    gone = api.delete(f'/api/deals/{world.id}/questionnaires/{FL}/rows/conditions/{2**64}/')
    assert gone.status_code == 404


def test_Q3_answers_write_path(user, world):
    row = Questionnaire.objects.get(deal=world, form=FL)
    write_path_contract(
        user,
        row,
        lambda: services.set_answers(user, world.id, FL, {'txtRsnBid': 'Renewal Increase', 'txtAdd2': 'Suite 3'}),
        lambda r: (r.answers, r.cleared),
        lambda: services.set_answers(user, world.id, FL, {'txtRsnBid': 'Healthcare Reform'}),
    )


def test_Q3_a_medical_answer_is_a_key_only_change(user, world):
    row = Questionnaire.objects.get(deal=world, form=FL)
    write_path_contract(
        user,
        row,
        lambda: services.set_answers(user, world.id, FL, {'chkMedCon': 'Yes'}),
        lambda r: r.answers,
        lambda: None,
        keys_only=True,
    )


def test_G18_the_api_answers_the_form_with_what_changed_and_what_dropped(api, world):
    url = f'/api/deals/{world.id}/questionnaires/{FL}/answers/'
    answer = api.patch(url, {'answers': {'txtRsnBid': 'Renewal Increase', 'numTAP': 'x'}}, format='json')
    body = answer.json()
    assert answer.status_code == 200 and body['changed'] == ['txtRsnBid'] and body['activity_id']
    assert body['dropped'] == [{'slot': 'numTAP', 'reason': 'not_number'}]
    assert body['values']['txtRsnBid'] == 'Renewal Increase' and 'progress' in body and 'order' in body
    assert api.patch(url, {'answers': 'nope'}, format='json').status_code == 400
    assert api.patch(url, {'answers': {}, 'relay': 'yes'}, format='json').status_code == 400


def test_G51_the_api_names_the_blanks_and_the_authorization(api, world):
    url = f'/api/deals/{world.id}/questionnaires/{FL}/sign/'
    refused = api.post(url, {'who': 'officer', 'name': 'Pat Sample'}, format='json')
    assert refused.status_code == 400 and refused.json()['code'] == 'authorization_required'
    held = api.post(url, {'who': 'officer', 'name': 'Pat Sample', 'authorized': True}, format='json')
    assert held.status_code == 409 and held.json()['incomplete']['total'] > held.json()['incomplete']['filled']
    signed = api.post(url, {'who': 'officer', 'name': 'Pat Sample', 'authorized': True, 'sign_anyway': True},
                      format='json')  # fmt: skip
    assert signed.status_code == 200 and signed.json()['locked']
    locked = api.patch(f'/api/deals/{world.id}/questionnaires/{FL}/answers/', {'answers': {'txtAdd2': 'x'}},
                       format='json')  # fmt: skip
    assert locked.status_code == 409


def test_G35_the_spec_is_cached_and_carries_no_answers(api, world):
    answer = api.get(f'/api/meta/questionnaires/{FL}/')
    assert answer['Cache-Control'] == 'private, max-age=3600'
    assert 'Example Fabrication' not in answer.content.decode()


@pytest.mark.django_db(transaction=True)
def test_Q3_two_writes_to_different_slots_at_once_both_survive(user):
    deal = make_world(user)
    services.set_answers(user, deal.id, FL, {'txtAdd2': 'Suite 1'})
    errors = []

    def write(answers):
        try:
            services.set_answers(user, deal.id, FL, answers)
        except Exception as error:  # pragma: no cover - reported below
            errors.append(error)
        finally:
            connection.close()

    threads = [threading.Thread(target=write, args=(a,)) for a in ({'txtRsnBid': 'Other'}, {'chkFBPrior': 'No'})]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    row = Questionnaire.objects.get(deal=deal, form=FL)
    assert not errors and row.answers['txtRsnBid'] == 'Other' and row.answers['chkFBPrior'] == 'No'


@pytest.mark.django_db(transaction=True)
def test_Q3_two_first_writes_at_once_make_one_row(user):
    deal = make_world(user)
    errors = []

    def write(answers):
        try:
            services.set_answers(user, deal.id, FL, answers)
        except Exception as error:  # pragma: no cover - reported below
            errors.append(error)
        finally:
            connection.close()

    threads = [threading.Thread(target=write, args=(a,)) for a in ({'txtRsnBid': 'Other'}, {'chkFBPrior': 'No'})]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    rows = list(Questionnaire.objects.filter(deal=deal, form=FL))
    assert not errors and len(rows) == 1 and set(rows[0].answers) == {'txtRsnBid', 'chkFBPrior'}
