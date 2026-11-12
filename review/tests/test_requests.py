"""Making and closing requests (plan.md §5.8, §7.13; L40, L55–L57, L64, L70; OQ80–OQ82; B10): a link per person,
the floor, the PIN shown once and stored hashed, the token never stored, the refusals."""

from datetime import timedelta
from unittest import mock

import pytest
from django.contrib.auth.hashers import check_password
from rest_framework.exceptions import ValidationError

from conftest import make_deal
from deals import activity, clock
from deals.models import Activity, Contact
from deals.services import create_contact, mark_lost, set_archived
from review import services, tokens
from review.models import ClientLink, ClientRequest
from review.rules import policy

pytestmark = pytest.mark.django_db

MISSING_INTAKE = {'intake': {'scope': 'missing'}}
CENSUS_GAPS = {'census': {'scope': 'missing'}}


def ask(**extra):
    return {'asks': MISSING_INTAKE, **extra}


def test_L55_a_request_makes_one_link_per_person_with_their_snapshot(user, deal):
    dana = create_contact(user, deal.client_id, name='Dana Example', email='dana@example.com', role='hr_admin')
    made = services.create(
        user, deal.id, ask(people=[{'contact_id': dana.id}, {'name': 'Sam Typed'}], message='  Thanks!  ')
    )
    request = made.request
    assert (request.asks['intake']['scope'], request.message) == ('missing', 'Thanks!')
    links = list(request.links.order_by('id'))
    assert [(link.contact_id, link.name, link.email) for link in links] == [
        (dana.id, 'Dana Example', 'dana@example.com'),
        (None, 'Sam Typed', ''),  # a name is enough while copying is the send (Ch. 7)
    ]
    assert all(link.sent_at is None and link.security == 'link' for link in links)
    assert [path for _link, path, _pin in made.links] == [tokens.path_of(link.seed) for link in links]


def test_L57_nobody_named_is_one_private_link(user, deal):
    made = services.create(user, deal.id, ask(people=[]))
    ((link, path, pin),) = made.links
    assert (link.name, link.contact_id, pin) == ('', None, '')
    assert path.startswith('/portal/')


def test_L56_people_are_deduplicated_and_a_typed_address_becomes_the_contact(user, deal):
    dana = create_contact(user, deal.client_id, name='Dana Example', email='Dana@Example.com')
    made = services.create(
        user,
        deal.id,
        ask(
            people=[
                {'contact_id': dana.id},
                {'name': 'Dana again', 'email': 'dana@example.com'},
                {'contact_id': dana.id},
            ]
        ),
    )
    assert made.request.links.count() == 1


@pytest.mark.parametrize(
    ('people', 'words'),
    [
        ([{'contact_id': 999999}], 'is not a contact of this client'),
        ([{'name': ''}], 'Give each person you type a name.'),
        ([{'name': 'Pat', 'email': 'not-an-address'}], 'is not an email address'),
        ([{'name': f'Person {n}'} for n in range(21)], 'up to 20 people'),
        ('everyone', 'Send each person as'),
    ],
)
def test_L56_who_it_goes_to_is_checked(user, deal, people, words):
    with pytest.raises(ValidationError) as refused:
        services.create(user, deal.id, ask(people=people))
    assert words in str(refused.value.detail['people'])
    assert not ClientRequest.objects.exists()


def test_L56_a_contact_of_another_client_is_not_one_of_these(user, deal):
    other = make_deal(user, name='Other Co.')
    stranger = create_contact(user, other.client_id, name='Stranger', email='s@example.com')
    with pytest.raises(ValidationError):
        services.create(user, deal.id, ask(people=[{'contact_id': stranger.id}]))


def test_L64_OQ80_a_census_ask_rises_to_a_pin_shown_once_and_stored_hashed(user, deal):
    made = services.create(user, deal.id, {'asks': CENSUS_GAPS, 'people': [{'name': 'Dana'}], 'security': 'link'})
    ((link, _path, pin),) = made.links
    link.refresh_from_db()
    assert link.security == 'pin' and len(pin) == policy.PIN_DIGITS and pin.isdigit()
    assert link.pin_hash != pin and check_password(pin, link.pin_hash)
    assert (link.pin_tries, link.pin_version) == (0, 1)


def test_L57_Ch1_a_nameless_link_may_hold_a_pin_staff_keep(user, deal):
    made = services.create(user, deal.id, {'asks': MISSING_INTAKE, 'people': [], 'security': 'pin'})
    ((link, _path, pin),) = made.links
    assert link.security == 'pin' and pin


def test_L64_an_upload_only_ask_opens_with_the_link_alone(user, deal):
    made = services.create(user, deal.id, {'asks': {'census': {'file': True}, 'documents': {'missing': True}}})
    ((link, _path, pin),) = made.links
    assert (link.security, pin) == ('link', '')


def test_L77_the_token_is_never_stored_and_finds_its_link_by_hash(user, deal):
    made = services.create(user, deal.id, ask(people=[{'name': 'Dana'}]))
    ((link, path, _pin),) = made.links
    token = path.removeprefix('/portal/')
    assert len(token) == 43
    stored = ClientLink.objects.filter(pk=link.pk).values().get()
    assert token not in str(stored)
    assert ClientLink.objects.get(token_hash=tokens.digest(token)).pk == link.pk


def test_OQ81_a_new_link_lives_seven_days_and_slides_until_a_day_is_picked(user, deal):
    now = clock.now()
    ((link, _p, _pin),) = services.create(user, deal.id, ask()).links
    assert link.slides and link.expires_at - link.created_at == timedelta(days=7)
    assert link.ceiling_at - link.created_at == timedelta(days=30)
    day = (now + timedelta(days=3)).astimezone(clock.agency_zone()).date()
    ((picked, _p, _pin),) = services.create(user, deal.id, ask(expires_on=day.isoformat())).links
    assert not picked.slides
    local = picked.expires_at.astimezone(clock.agency_zone())
    assert (local.date(), local.hour, local.minute) == (day, 23, 59)


@pytest.mark.parametrize(
    ('day', 'words'),
    [
        ('11/20/2026', 'YYYY-MM-DD'),
        ('2000-01-01', 'That date has passed'),
        ('2099-01-01', 'at most 30 days'),
    ],
)
def test_L61_a_picked_day_is_checked(user, deal, day, words):
    with pytest.raises(ValidationError) as refused:
        services.create(user, deal.id, ask(expires_on=day))
    assert words in str(refused.value.detail['expires_on'])


def test_L55_the_message_and_the_level_are_checked(user, deal):
    with pytest.raises(ValidationError) as refused:
        services.create(user, deal.id, ask(message='x' * 1001, security='verified'))
    assert set(refused.value.detail) == {'message', 'security'}


def test_L46_census_values_must_be_people_on_this_deal(user, deal):
    other = make_deal(user, name='Other Co.')
    from census.services import add_member

    stranger, _row = add_member(user, other.id, 'employee', employee_id=None, values={'first_name': 'Canary'})
    with pytest.raises(ValidationError) as refused:
        services.create(user, deal.id, {'asks': {'census': {'scope': 'selected', 'cells': [[stranger.id, 'dob']]}}})
    assert str(stranger.id) in str(refused.value.detail['census.cells'])


@pytest.mark.parametrize('closing', ['lost', 'archived', 'past'])
def test_B10_a_deal_that_may_no_longer_ask_its_client_refuses_a_request(user, deal, closing):
    if closing == 'lost':
        mark_lost(user, deal.id, reason='Went elsewhere')
    elif closing == 'archived':
        set_archived(user, deal.client_id, True)
    else:
        deal.effective_date = clock.today() - timedelta(days=400)
        deal.save(update_fields=['effective_date'])
    with pytest.raises(activity.Refused):
        services.create(user, deal.id, ask())
    assert not ClientRequest.objects.exists()


def test_L40_the_dry_run_answers_the_floor_and_writes_nothing(user, deal):
    activity_rows = Activity.objects.count()
    planned = services.create(user, deal.id, {'asks': CENSUS_GAPS, 'people': [{'name': 'Dana'}]}, dry_run=True)
    assert planned.floor == {'level': 'pin', 'because': ['Census']}
    assert planned.security == 'pin'
    assert not ClientRequest.objects.exists() and Activity.objects.count() == activity_rows


def test_L55_creating_records_one_activity_row_with_no_name_address_token_or_pin(user, deal):
    canary = create_contact(user, deal.client_id, name='Canary Person', email='canary@example.com')
    made = services.create(user, deal.id, {'asks': CENSUS_GAPS, 'people': [{'contact_id': canary.id}]})
    ((link, path, pin),) = made.links
    row = made.activity
    assert (row.area, row.action, row.revertible) == ('review', 'created', False)
    text = str(Activity.objects.filter(area='review').values())
    for secret in ('Canary', 'canary@example.com', path.removeprefix('/portal/'), pin, link.seed):
        assert secret not in text


def test_L70_closing_ends_every_link_and_closing_again_changes_nothing(user, deal):
    made = services.create(user, deal.id, ask(people=[{'name': 'A'}, {'name': 'B'}]))
    closed = services.close(user, made.request.id, 'superseded')
    assert closed.changed['close_reason'] == ['', 'superseded']
    request = ClientRequest.objects.get(pk=made.request.id)
    assert request.closed_at is not None and request.closed_by_id == user.id
    assert not any(policy.opens(link, clock.now(), closed=True) for link in request.links.all())
    again = services.close(user, made.request.id, 'cancelled')
    assert (again.changed, again.activity) == ({}, None)
    with pytest.raises(ValidationError):
        services.close(user, made.request.id, 'bored')


def test_L70_undo_of_a_close_reopens_the_request(user, deal):
    made = services.create(user, deal.id, ask())
    closed = services.close(user, made.request.id, 'cancelled')
    activity.revert(closed.activity.id, user)
    request = ClientRequest.objects.get(pk=made.request.id)
    assert (request.closed_at, request.closed_by_id, request.close_reason) == (None, None, '')


def test_L55_a_request_cannot_be_undone_but_its_links_can_be_turned_off(user, deal):
    made = services.create(user, deal.id, ask())
    with pytest.raises(activity.Refused):
        activity.revert(made.activity.id, user)


def test_Q3_7_a_picked_day_reads_the_agency_date_at_9pm_eastern(user, deal):
    late = clock.now().astimezone(clock.agency_zone()).replace(hour=21, minute=0)
    with mock.patch.object(clock, 'now', return_value=late):
        today = clock.today()
        ((link, _p, _pin),) = services.create(user, deal.id, ask(expires_on=today.isoformat())).links
    assert link.expires_at.astimezone(clock.agency_zone()).date() == today


def test_L56_contacts_without_email_can_be_asked(user, deal):
    nameless = Contact.objects.create(client_id=deal.client_id, name='No Mail', role='owner')
    ((link, _p, _pin),) = services.create(user, deal.id, ask(people=[{'contact_id': nameless.id}])).links
    assert (link.name, link.email) == ('No Mail', '')
