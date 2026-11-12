"""The Firm pages drawer's API (plan.md §6.11, §7.12 `proposal/firm-pages/`, `proposal/team/`; J155, OQ41): About,
figures and calendar, and the team with photos, open to every user; firm Activity rows with Revert."""

import io

import pytest
from PIL import Image

from conftest import write_path_contract
from deals import activity
from deals.models import Activity
from proposals import firm_services
from proposals.models import FirmPages, TeamMember
from proposals.tests import firm_shop

pytestmark = pytest.mark.django_db


def test_J155_firm_pages_read_blank_without_making_a_row(api):
    found = api.get('/api/proposal/firm-pages/').json()
    assert found == {'about_text': '', 'about_stats': [], 'service_calendar': []}
    assert not FirmPages.objects.exists()


def test_J155_firm_pages_save_cleaned_and_record_a_firm_row(api, user):
    body = {
        'about_text': '  Brokers for manufacturers.  ',
        'about_stats': [{'value': '20+', 'label': 'Years', 'extra': 'x'}, {'value': '', 'label': ''}],
        'service_calendar': [{'meeting': 'Kick-off', 'topics': ['Review', ''], 'when': 'January'}, {'meeting': ''}],
    }
    found = api.patch('/api/proposal/firm-pages/', body, format='json').json()
    assert found['about_text'] == 'Brokers for manufacturers.'
    assert found['about_stats'] == [{'value': '20+', 'label': 'Years', 'note': ''}]  # blank row dropped
    assert found['service_calendar'] == [{'meeting': 'Kick-off', 'topics': ['Review'], 'when': 'January'}]
    row = Activity.objects.get(pk=found['activity_id'])
    assert (row.deal_id, row.subject, row.area) == (None, 'firm_pages', 'firm')
    again = api.patch('/api/proposal/firm-pages/', body, format='json').json()
    assert again['activity_id'] is None  # nothing changed: nothing written


def test_J155_firm_pages_refuse_past_their_limits(api):
    long = api.patch('/api/proposal/firm-pages/', {'about_text': 'x' * 901}, format='json')
    assert long.status_code == 400 and 'about_text' in long.json()
    many = [{'value': str(n), 'label': 'x'} for n in range(FirmPages.MAX_STATS + 1)]
    assert api.patch('/api/proposal/firm-pages/', {'about_stats': many}, format='json').status_code == 400
    meetings = [{'meeting': f'M{n}'} for n in range(FirmPages.MAX_CALENDAR + 1)]
    assert api.patch('/api/proposal/firm-pages/', {'service_calendar': meetings}, format='json').status_code == 400


def test_Q3_1_J155_the_firm_pages_write_path(user):
    firm_services.save_pages(user, {'about_text': 'First words.'})
    row = FirmPages.objects.get(pk=1)
    write_path_contract(
        user,
        row,
        lambda: firm_services.save_pages(user, {'about_text': 'Second words.'}),
        lambda found: found.about_text,
        lambda: firm_services.save_pages(user, {'about_text': 'Third words.'}),
    )


def test_J155_the_team_is_added_edited_and_removed(api):
    made = api.post('/api/proposal/team/', {'name': ' Lee  Park ', 'group': 'Benefits advisor'}, format='json')
    assert made.status_code == 201
    person = made.json()
    assert (person['name'], person['group'], person['on_by_default'], person['has_photo']) == (
        'Lee Park',
        'Benefits advisor',
        True,
        False,
    )
    assert api.post('/api/proposal/team/', {'name': '  '}, format='json').status_code == 400
    url = f'/api/proposal/team/{person["id"]}/'
    edited = api.patch(url, {'on_by_default': False, 'bio': 'Ten years.'}, format='json')
    assert edited.json()['on_by_default'] is False and edited.json()['bio'] == 'Ten years.'
    bad = api.patch(f'/api/proposal/team/{person["id"]}/', {'email': 'not-an-email', 'bio': 'x' * 1401}, format='json')
    assert bad.status_code == 400 and set(bad.json()) == {'email', 'bio'}
    assert [p['name'] for p in api.get('/api/proposal/team/').json()] == ['Lee Park']
    assert api.delete(f'/api/proposal/team/{person["id"]}/').status_code == 204
    assert api.get('/api/proposal/team/').json() == []
    assert api.patch(f'/api/proposal/team/{person["id"]}/', {'title': 'x'}, format='json').status_code == 404


def test_Q3_1_J155_a_person_edit_reverts_and_adding_does_not(user):
    member = firm_shop.person(user, photo=False)
    added = Activity.objects.filter(subject=f'team:{member.id}', action='created').get()
    assert not added.revertible
    write_path_contract(
        user,
        member,
        lambda: firm_services.update_person(user, member.id, {'title': 'Account manager'}),
        lambda found: found.title,
        lambda: firm_services.update_person(user, member.id, {'title': 'Partner'}),
    )


def test_J155_the_team_holds_at_most_forty(user):
    TeamMember.objects.bulk_create(TeamMember(name=f'Person {n}') for n in range(TeamMember.MAX_MEMBERS))
    with pytest.raises(activity.Refused, match='at most 40'):
        firm_services.add_person(user, {'name': 'One more'})


def test_J155_a_photo_is_re_encoded_upright_small_and_without_metadata(api, user):
    member = firm_shop.person(user, photo=False)
    upload = firm_shop.upload('Lee Park portrait.jpg', size=(1600, 2400))
    found = api.post(f'/api/proposal/team/{member.id}/photo/', {'photo': upload}, format='multipart')
    assert found.status_code == 200 and found.json()['has_photo'] is True
    member.refresh_from_db()
    assert member.photo.name.startswith('proposals/team/photo')  # the name says nothing about the person
    data = api.get(f'/api/proposal/team/{member.id}/photo/').content
    assert firm_shop.MAKER.encode() not in data
    with Image.open(io.BytesIO(data)) as picture:
        assert picture.format == 'JPEG' and max(picture.size) == firm_services.PHOTO_STORE
    refused = api.post(f'/api/proposal/team/{member.id}/photo/', {'photo': firm_shop.upload('x.svg', b'<svg/>')})
    assert refused.status_code == 400 and 'PNG or JPEG' in refused.json()['photo']
    row = Activity.objects.filter(subject=f'team:{member.id}', summary='Changed a team photo').get()
    assert row.changes == [{'t': f'team:{member.id}', 'k': ['photo']}]  # key only: the bytes are never in Activity
    assert api.delete(f'/api/proposal/team/{member.id}/photo/').json()['has_photo'] is False
    assert api.get(f'/api/proposal/team/{member.id}/photo/').status_code == 404
