"""The answers PATCH and its service (plan.md §5.2, §7.6; B1, B3, B4, B.6; Q.9 row 39): all or nothing through the one
cleaner, unchanged writes nothing, a GET creates no row, the effective date's door, `expect`, relay and Revert."""

import datetime

import pytest

from deals import activity
from deals.models import Activity, Deal
from intake import form, services, values
from intake.models import Intake

pytestmark = pytest.mark.django_db


def _patch(api, deal, answers, **extra):
    return api.patch(f'/api/deals/{deal.id}/intake/', {'answers': answers, **extra}, format='json')


def test_B4_a_get_creates_no_row_and_reads_empty(api, deal):
    body = api.get(f'/api/deals/{deal.id}/intake/').json()
    assert not Intake.objects.filter(deal=deal).exists()
    assert body['answers'] == {} and body['sources'] == {}
    assert body['needed'] == values.needed_keys({})
    assert all(body['status'][key] == 'missing' for key in body['needed'])
    assert body['readiness'] == {'needed': 8, 'answered': 0, 'pct': 0}
    assert body['issues'] == {} and body['notes'] == {'multi_state': False, 'census': ''}


def test_B4_patch_saves_cleaned_answers_and_answers_the_form_state(api, deal):
    answered = _patch(api, deal, {'legal_name': ' Example Co. ', 'states_operating': 'fl ga', 'waiving_count': '3'})
    assert answered.status_code == 200
    body = answered.json()
    assert body['answers'] == {'legal_name': 'Example Co.', 'states_operating': ['FL', 'GA'], 'waiving_count': '3'}
    assert body['sources']['legal_name']['origin'] == 'typed'
    assert 'waive_reason' not in body['hidden'] and 'waive_reason' in body['needed']  # revealed and now needed
    assert body['status']['waive_reason'] == 'missing'
    assert body['notes']['multi_state'] is True
    assert body['activity_id'] == Activity.objects.get(deal=deal, area='intake', action='answers').id
    intake = Intake.objects.get(deal=deal)
    assert intake.answers == body['answers']
    assert api.get(f'/api/deals/{deal.id}/intake/').json()['answers'] == body['answers']


def test_B4_nothing_saves_when_any_answer_is_refused(api, deal):
    refused = _patch(api, deal, {'legal_name': 'Example Co.', 'fein': '12-345', 'union': 'maybe', 'shoe': '9'})
    assert refused.status_code == 400
    assert refused.json() == {
        'answers': {
            'fein': 'FEIN takes XX-XXXXXXX, not "12-345"',
            'union': 'Union Employees takes Yes or No, not "maybe"',
            'shoe': 'Not an intake question.',
        }
    }
    assert not Intake.objects.filter(deal=deal).exists()
    assert not Activity.objects.filter(deal=deal, area='intake', action='answers').exists()


@pytest.mark.parametrize(
    ('key', 'raw'),
    [
        ('fein', '12 3456789'),
        ('fein', '1234'),
        ('total_employees', '$1,200'),
        ('total_employees', 'about forty'),
        ('target_effective_date', '4/1/27'),
        ('target_effective_date', 'next spring'),
        ('ale_status', 'TRUE'),
        ('entity_type', 'llc'),
        ('entity_type', 'Trust'),
        ('states_operating', 'FL; ga'),
        ('states_operating', 'FL, Atlantis'),
    ],
)
def test_B3_the_producer_path_stores_what_the_one_cleaner_says(api, deal, key, raw):
    value, error = values.clean_value(key, raw)
    answered = _patch(api, deal, {key: raw})
    if error:
        assert answered.status_code == 400 and answered.json() == {'answers': {key: error}}
    else:
        assert answered.status_code == 200 and answered.json()['answers'] == {key: value}


def test_B4_an_unchanged_answer_writes_nothing(user, deal):
    first = services.update_answers(user, deal.id, {'legal_name': 'Example Co.'})
    intake = Intake.objects.get(deal=deal)
    again = services.update_answers(user, deal.id, {'legal_name': '  Example Co.'})
    assert first.changed and not again.changed and again.activity is None
    assert Intake.objects.get(deal=deal).updated_at == intake.updated_at
    assert Activity.objects.filter(deal=deal, area='intake', action='answers').count() == 1


def test_B4_a_blank_clears_and_a_first_blank_creates_no_row(user, deal):
    assert services.update_answers(user, deal.id, {'dba': ''}).changed == {}
    assert not Intake.objects.filter(deal=deal).exists()
    services.update_answers(user, deal.id, {'dba': 'Ex'})
    cleared = services.update_answers(user, deal.id, {'dba': '  '})
    assert cleared.changed == {'dba': ['Ex', None]} and cleared.sources == {'dba': None}
    assert 'dba' not in Intake.objects.get(deal=deal).sources


def test_B4_null_puts_back_what_was_read(user, deal):
    read = {'origin': 'ai', 'doc': 7, 'read_value': '64'}
    Intake.objects.create(deal=deal, answers={'employee_count': '64'}, sources={'employee_count': read})
    services.update_answers(user, deal.id, {'employee_count': '60'})
    typed = Intake.objects.get(deal=deal).sources['employee_count']
    assert typed['origin'] == 'typed' and typed['doc'] == 7  # still opens its file
    back = services.update_answers(user, deal.id, {'employee_count': None})
    intake = Intake.objects.get(deal=deal)
    assert back.changed == {'employee_count': ['60', '64']}
    assert intake.answers['employee_count'] == '64' and intake.sources['employee_count']['origin'] == 'ai'


def test_B1_the_target_effective_date_is_the_deals_one_date(api, user, deal):
    was = deal.effective_date.isoformat() if deal.effective_date else None
    answered = _patch(api, deal, {'target_effective_date': '7/1/2027'}).json()
    assert answered['answers'] == {'target_effective_date': '2027-07-01'}
    assert answered['effective_date'] == '2027-07-01'
    assert Deal.objects.get(pk=deal.id).effective_date == datetime.date(2027, 7, 1)
    intake = Intake.objects.get(deal=deal)
    assert form.EFFECTIVE_DATE not in intake.answers and intake.sources[form.EFFECTIVE_DATE]['origin'] == 'typed'
    row = Activity.objects.get(deal=deal, area='intake', action='answers')
    assert row.changes == [{'t': f'deal:{deal.id}', 'k': {'effective_date': [was, '2027-07-01']}}]
    api.patch(f'/api/deals/{deal.id}/', {'effective_date': '2027-09-01'}, format='json')  # the header's door
    assert api.get(f'/api/deals/{deal.id}/intake/').json()['answers'][form.EFFECTIVE_DATE] == '2027-09-01'
    with pytest.raises(activity.Refused):  # the header wrote the date since
        activity.revert(row.id, user)


def test_B1_revert_puts_the_effective_date_and_answers_back(user, deal):
    was = deal.effective_date
    answered = services.update_answers(user, deal.id, {'target_effective_date': '2027-03-01', 'union': 'No'})
    activity.revert(answered.activity.id, user)
    assert Deal.objects.get(pk=deal.id).effective_date == was
    intake = Intake.objects.get(deal=deal)
    assert intake.answers == {}
    assert (form.EFFECTIVE_DATE in intake.sources) is bool(was)


def test_B4_expect_refuses_a_write_over_a_newer_answer(api, user, deal):
    services.update_answers(user, deal.id, {'total_employees': '40', 'atne': '38'})
    stale = _patch(api, deal, {'total_employees': '45'}, expect={'total_employees': '39', 'atne': '38'})
    assert stale.status_code == 409
    assert stale.json()['detail'] == (
        'Total Employees changed since you last saw it, so nothing was saved. Reload to see the new answer.'
    )
    assert Intake.objects.get(deal=deal).answers['total_employees'] == '40'
    fresh = _patch(api, deal, {'total_employees': '45'}, expect={'total_employees': '40', 'dba': ''})
    assert fresh.status_code == 200
    multi = _patch(api, deal, {'states_operating': ['GA']}, expect={'states_operating': []})
    assert multi.status_code == 200


def test_B10_answers_entered_for_the_client_are_relayed(api, deal):
    body = _patch(api, deal, {'legal_name': 'Example Co.'}, relay=True).json()
    assert body['sources']['legal_name']['origin'] == 'relay'
    assert (
        Activity.objects.get(deal=deal, area='intake', action='answers').summary == "Entered 1 client's intake answer"
    )
    assert _patch(api, deal, {'dba': 'Ex'}, relay='yes').status_code == 400


def test_B4_a_burst_of_edits_is_one_activity_row(user, deal):
    services.update_answers(user, deal.id, {'legal_name': 'Example Co.'})
    services.update_answers(user, deal.id, {'dba': 'Ex', 'union': 'No'})
    row = Activity.objects.get(deal=deal, area='intake', action='answers')
    assert row.summary == 'Edited 3 intake answers'
    activity.revert(row.id, user)
    assert Intake.objects.get(deal=deal).answers == {}


def test_B4_bad_bodies_answer_400(api, deal):
    url = f'/api/deals/{deal.id}/intake/'
    assert api.patch(url, {'answers': ['legal_name']}, format='json').status_code == 400
    assert api.patch(url, {}, format='json').status_code == 400
    assert api.patch(url, {'answers': {'dba': 'x'}, 'expect': 'dba'}, format='json').status_code == 400
    assert api.patch(f'/api/deals/{2**64}/intake/', {'answers': {'dba': 'x'}}, format='json').status_code == 404


def test_Q3_flags_equal_a_fresh_rebuild_after_every_write(user, deal):
    from intake import flags

    Intake.objects.create(
        deal=deal,
        answers={'dba': 'Ex', 'atne': '9'},
        sources={'dba': {'origin': 'ai', 'low': 'blurred'}, 'atne': {'origin': 'ai', 'low': 'two figures'}},
        flags=2,
    )
    answered = services.update_answers(user, deal.id, {'atne': '10'})
    assert Intake.objects.get(deal=deal).flags == 1 and flags.rebuild([deal.id]) == []
    activity.revert(answered.activity.id, user)
    assert Intake.objects.get(deal=deal).flags == 1 and flags.rebuild([deal.id]) == []  # typed back, not read back
    Intake.objects.filter(deal=deal).update(flags=5)
    assert flags.rebuild([deal.id], write=True) == [(f'intake:{deal.id}', 5, 1)]
    assert Intake.objects.get(deal=deal).flags == 1
