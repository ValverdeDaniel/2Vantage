"""The roster grid's writes (plan.md §5.3.1, §7.7, §8.21; C4–C7, C24, O.6 #13, #33; Q.9 row 41): a PATCH answers only
the changed person and their issues; `expect` refuses a cell that changed since; an unchanged value writes nothing;
people are added under the roster and removed softly with their dependents; the stored counts follow every write."""

import pytest

from census import facts, services
from census.models import Member
from conftest import make_deal, write_path_contract
from deals import activity
from deals.models import Activity

from .helpers import family, imported, roster, xlsx

pytestmark = pytest.mark.django_db

SMITH = family('E1', 'Smith', tier='ES', deps=[('Spouse', 'Blake', '02/02/1981')])
LEE = family('E3', 'Lee', first='Robin', dob='03/04/1979')


@pytest.fixture
def world(user):
    deal = make_deal(user, requested_lines=('medical',))
    imported(user, deal, xlsx(roster(SMITH, LEE)))
    people = {m.values['first_name']: m for m in Member.objects.filter(deal=deal)}
    return {'deal': deal, **people}


def patch(api, member, values, **more):
    return api.patch(f'/api/census/members/{member.id}/', {'values': values, **more}, format='json')


def test_Q9_41_C6_a_patch_answers_only_the_changed_member_and_its_issues(api, world):
    answer = patch(api, world['Robin'], {'dob': '13/45/1979'})
    assert answer.status_code == 200
    body = answer.json()
    assert 'members' not in body and body['member']['id'] == world['Robin'].id
    assert body['changed'] == ['dob']
    assert body['member']['values']['dob'] == '13/45/1979'  # kept as typed, so validation can say why
    assert [issue['code'] for issue in body['member']['issues']['dob']] == ['dob_unparseable']
    assert body['summary']['errors'] == 1
    assert facts.differences(world['deal'].id) == {}


def test_C6_F69_an_unchanged_value_writes_nothing_and_a_date_is_stored_once_cleaned(user, api, world):
    robin = world['Robin']
    before = Activity.objects.count()
    answer = patch(api, robin, {'dob': '3/4/1979'}).json()  # the stored 1979-03-04, typed another way
    assert answer['changed'] == [] and answer['activity_id'] is None
    assert Activity.objects.count() == before
    robin.refresh_from_db()
    assert robin.sources['dob']['origin'] == 'import'  # not even its source moved (§3.7)


def test_Q3_1_a_hand_edit_is_keys_only_locks_the_person_and_refuses_revert(user, world):
    robin = world['Robin']
    row = write_path_contract(
        user,
        robin,
        lambda: services.edit_values(user, robin.id, {'zip': '02139', 'hours_per_week': '32'}),
        lambda member: member.values,
        lambda: services.edit_values(user, robin.id, {'zip': '02140'}),
        keys_only=True,
    )
    assert row.changes == [{'t': f'member:{robin.id}', 'k': ['hours_per_week', 'zip']}]
    assert row.summary == 'Edited 2 census values'


def test_O6_33_expect_refuses_a_cell_changed_since_and_names_it(user, api, world):
    robin = world['Robin']
    services.edit_values(user, robin.id, {'first_name': 'Robyn'})
    answer = patch(api, robin, {'first_name': 'Rob'}, expect={'first_name': 'Robin'})
    assert answer.status_code == 409
    assert answer.json() == {
        'detail': 'First Name changed since you last saw it, so nothing was saved. Reload to see the new value.',
        'keys': ['first_name'],
    }
    robin.refresh_from_db()
    assert robin.values['first_name'] == 'Robyn'
    shown_date = patch(api, robin, {'dob': '03/05/1979'}, expect={'dob': '03/04/1979'})  # as the grid shows it
    assert shown_date.status_code == 200 and shown_date.json()['changed'] == ['dob']


def test_C16_OQ16_a_masked_ssn_stands_for_the_number_on_file(user, api, world):
    robin = world['Robin']
    services.edit_values(user, robin.id, {'ssn': '123456789'})
    shown = api.get(f'/api/deals/{world["deal"].id}/census/').json()
    row = next(member for member in shown['members'] if member['id'] == robin.id)
    assert row['values']['ssn'] == '***-**-6789'
    assert patch(api, robin, {'ssn': '***-**-6789'}, expect={'ssn': '***-**-6789'}).json()['changed'] == []
    refused = patch(api, robin, {'ssn': '***-**-1111'})
    assert refused.status_code == 400
    assert refused.json() == {'values': {'ssn': 'Type the whole SSN, or leave the masked one as it is.'}}
    assert patch(api, robin, {'ssn': '987-65-4321'}).json()['member']['values']['ssn'] == '***-**-4321'


def test_C4_from_the_client_saves_as_relayed(user, api, world):
    robin = world['Robin']
    patch(api, robin, {'phone': '555-0100'}, relay=True)
    robin.refresh_from_db()
    assert robin.sources['phone']['origin'] == 'relay'
    assert Activity.objects.filter(deal=world['deal']).latest('id').summary == "Entered 1 client's census value"


def test_C6_bad_bodies_answer_400_naming_the_column_never_the_value(api, world):
    robin = world['Robin']
    assert patch(api, robin, {'not_a_column': 'x'}).json() == {'values': ['Some of those are not census columns.']}
    assert patch(api, robin, {'dob': ['1979']}).status_code == 400
    assert api.patch(f'/api/census/members/{robin.id}/', {'values': 'x'}, format='json').status_code == 400
    assert patch(api, robin, {'dob': '1979-03-04'}, relay='yes').status_code == 400
    assert api.patch(f'/api/census/members/{2**64}/', {'values': {}}, format='json').status_code == 404


def test_C7_add_an_employee_then_a_dependent_under_them(user, api, world):
    deal = world['deal']
    made = api.post(f'/api/deals/{deal.id}/census/members/', {'kind': 'employee'}, format='json')
    assert made.status_code == 201
    employee = made.json()['member']
    assert employee['kind'] == 'employee' and employee['values'] == {}
    assert 'first_name' in employee['missing']
    child = api.post(
        f'/api/deals/{deal.id}/census/members/',
        {'kind': 'dependent', 'employee_id': employee['id'], 'values': {'relationship': 'Child'}},
        format='json',
    ).json()['member']
    assert (child['employee_id'], child['values']) == (employee['id'], {'relationship': 'Child'})
    page = api.get(f'/api/deals/{deal.id}/census/').json()
    ids = [member['id'] for member in page['members']]
    assert ids[-2:] == [employee['id'], child['id']]  # a new employee sorts last, the dependent under them
    assert page['summary']['employees'] == 3
    assert facts.differences(deal.id) == {}
    row = Activity.objects.filter(deal=deal).latest('id')
    assert (row.summary, row.changes) == (
        'Added a dependent to the census',
        [{'t': f'member:{child["id"]}', 'k': ['kind', 'relationship']}],
    )


def test_C7_a_dependent_needs_an_employee_on_this_deal(user, api, world):
    deal, other = world['deal'], make_deal(user, name='Other Co (synthetic)')
    url = f'/api/deals/{deal.id}/census/members/'
    assert api.post(url, {'kind': 'dependent'}, format='json').status_code == 400
    assert api.post(url, {'kind': 'dependent', 'employee_id': world['Blake'].id}, format='json').status_code == 400
    foreign = api.post(
        f'/api/deals/{other.id}/census/members/',
        {'kind': 'dependent', 'employee_id': world['Avery'].id},
        format='json',
    )
    assert foreign.status_code == 400
    assert api.post(url, {'kind': 'boss'}, format='json').status_code == 400


def test_C7_O6_13_removing_an_employee_takes_their_dependents_softly(user, api, world):
    deal, avery = world['deal'], world['Avery']
    assert api.delete(f'/api/census/members/{avery.id}/').status_code == 204
    assert list(Member.objects.filter(deal=deal).values_list('values__first_name', flat=True)) == ['Robin']
    assert Member.all_objects.filter(deal=deal, removed_at__isnull=False).count() == 2
    row = Activity.objects.filter(deal=deal).latest('id')
    assert row.summary == 'Removed an employee (and 1 dependent) from the census'
    assert {entry['t'] for entry in row.changes} == {f'member:{avery.id}', f'member:{world["Blake"].id}'}
    assert api.delete(f'/api/census/members/{avery.id}/').status_code == 404
    assert facts.summary(facts.stored(deal.id))['employees'] == 1
    assert facts.differences(deal.id) == {}
    with pytest.raises(activity.Refused) as refused:
        activity.revert(row.id, user)
    assert refused.value.sentence == activity.KEYS_ONLY


def test_C7_a_removed_person_refuses_a_late_edit(user, world):
    robin = world['Robin']
    services.remove_member(user, robin.id)
    with pytest.raises(activity.Refused) as refused:
        services.edit_values(user, robin.id, {'first_name': 'Robyn'})
    assert refused.value.sentence == 'This person is no longer on the census. Reload the roster.'


def test_C9_clearing_the_roster_needs_confirming_and_removes_everyone(user, api, world):
    deal = world['deal']
    url = f'/api/deals/{deal.id}/census/clear/'
    assert api.post(url, {}, format='json').status_code == 400
    assert api.post(url, {'confirm': True}, format='json').status_code == 204
    assert not Member.objects.filter(deal=deal).exists()
    assert Activity.objects.filter(deal=deal).latest('id').summary == 'Cleared the census: 3 people'
    assert facts.differences(deal.id) == {}
    count = Activity.objects.count()
    assert api.post(url, {'confirm': True}, format='json').status_code == 204
    assert Activity.objects.count() == count  # an empty roster: nothing to clear, nothing recorded


def test_C24_select_all_missing_lists_every_required_blank_on_the_roster(user, api, world):
    deal = world['deal']
    services.edit_values(user, world['Robin'].id, {'medical_tier': ''})
    answer = api.get(f'/api/deals/{deal.id}/census/missing/').json()
    assert answer == {'refs': [f'census:{world["Robin"].id}:medical_tier'], 'count': 1}
    page = api.get(f'/api/deals/{deal.id}/census/', {'page_size': 1}).json()
    assert world['Robin'].id not in [member['id'] for member in page['members']]  # on page 2, still listed above
