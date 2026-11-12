"""Commission's writes (plan.md §5.6, §7.10; H5, H11, H20, H22, H95–H100, H113; OQ70): what each service stores,
refuses and records, and what Revert puts back."""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.exceptions import PermissionDenied, ValidationError

from accounts.models import Profile
from commission import selectors, services
from commission.models import ClientSplit, Commission, Party, Settings
from conftest import make_deal
from deals import activity
from deals.models import Activity, AgencySettings

pytestmark = pytest.mark.django_db


def person(username, *, tier=None, staff=False):
    login = get_user_model().objects.create_user(username, f'{username}@example.com', 'pw-Example-1', is_staff=staff)
    if tier:
        Profile.objects.create(user=login, commissions_access=tier)
    return login


def partner(name='Riverside Partners (synthetic)', **fields):
    return Party.objects.create(kind='partner', name=name, **fields)


def test_H5_rates_merge_per_line_clear_with_a_blank_and_keep_their_source(user, deal):
    services.update(user, deal.id, {'rates': {'medical': '5'}})
    written = services.update(user, deal.id, {'rates': {'dental': {'type': 'flat', 'value': '1,000,000'}}})
    assert written.changed == {'rates.dental': [None, {'type': 'flat', 'value': '1000000'}]}
    row = Commission.objects.get(deal=deal)
    assert row.rates == {'medical': {'type': 'pct', 'value': '5'}, 'dental': {'type': 'flat', 'value': '1000000'}}
    assert row.sources['medical']['origin'] == 'typed' and row.sources['medical']['by'] == user.id
    services.update(user, deal.id, {'rates': {'medical': ''}})
    row.refresh_from_db()
    assert 'medical' not in row.rates and 'medical' not in row.sources
    assert services.update(user, deal.id, {'rates': {'medical': ''}}).changed == {}


def test_H1_rates_are_parsed_by_the_one_parser_and_bad_ones_answer_400(user, deal):
    with pytest.raises(ValidationError) as refused:
        services.update(user, deal.id, {'rates': {'medical': '-1', 'dental': 'abc', 'nope': '5'}, 'other': 1})
    assert refused.value.detail == {
        'rates.medical': ['Must not be negative'],
        'rates.dental': ['Must be a number'],
        'rates.nope': ['Not a line.'],
        'other': ['Not a commission field.'],
    }
    assert not Commission.objects.filter(deal=deal).exists()  # a refused write makes no row


def test_H30_the_typed_year_is_stored_and_read(user, deal):
    services.update(user, deal.id, {'year_number': 3})
    assert selectors.deal_payload(deal, user)['basis']['year'] == 3
    with pytest.raises(ValidationError):
        services.update(user, deal.id, {'year_number': 'two'})


def test_H20_a_deal_split_saves_and_a_client_split_takes_over_the_deal(user, deal):
    referral = partner()
    rows = [{'user': user.id, 'role': 'primary'}, {'party': referral.id, 'role': 'referral', 'amount': '20'}]
    saved = services.save_split(user, deal_id=deal.id, scope='deal', rows=rows)
    me = Party.objects.get(user=user)  # H11: the producer's Party is made on the first save
    stored = Commission.objects.get(deal=deal).split['rows']
    assert [(row['party'], row['role']) for row in stored] == [(me.id, 'primary'), (referral.id, 'referral')]
    assert saved.activity.summary == 'Saved the producers & splits for this deal'
    assert selectors.deal_payload(deal, user)['split']['source'] == 'deal'
    again = services.save_split(user, deal_id=deal.id, scope='client', rows=rows)
    assert ClientSplit.objects.get(client=deal.client).rows == stored
    assert Commission.objects.get(deal=deal).split is None  # the client's split applies to this deal again
    assert {entry['t'] for entry in again.activity.changes} == {
        f'commission:{deal.id}',
        f'client_split:{deal.client_id}',
    }
    other = make_deal(user, name='Sister Co.')
    other.client = deal.client
    other.save()
    assert selectors.deal_payload(other, user)['split']['source'] == 'client'  # every deal of the client


def test_H22_saving_a_primary_with_a_login_sets_the_owner(user, admin_user, deal):
    producer = person('pat')
    saved = services.save_split(admin_user, deal_id=deal.id, rows=[{'user': producer.id, 'role': 'primary'}])
    deal.refresh_from_db()
    assert deal.owner_id == producer.id and saved.owner == {'owner': [user.id, producer.id]}
    row = Activity.objects.filter(deal=deal, area='deal_facts').latest('id')
    assert row.summary == 'Changed the owner'
    services.save_split(admin_user, deal_id=deal.id, scope='client', rows=[{'user': admin_user.id, 'role': 'primary'}])
    deal.client.refresh_from_db()
    assert deal.client.owner_id == admin_user.id  # a client split sets the client's owner
    without_login = Party.objects.create(kind='producer', name='Nolan (synthetic)', appointed=True)
    saved = services.save_split(admin_user, deal_id=deal.id, rows=[{'party': without_login.id, 'role': 'primary'}])
    assert saved.owner == {}


def test_OQ70_only_the_all_tier_or_the_deals_owner_saves_a_split(user, deal):
    rows = [{'user': user.id, 'role': 'primary'}]
    for outsider in (person('own-tier'), person('no-tier', tier='none')):
        with pytest.raises(PermissionDenied):
            services.save_split(outsider, deal_id=deal.id, rows=rows)
    services.save_split(person('all-tier', tier='all'), deal_id=deal.id, rows=rows)
    services.save_split(user, deal_id=deal.id, rows=rows)  # the deal's owner, at the own tier
    with pytest.raises(PermissionDenied):
        services.save_split(person('stranger'), client_id=deal.client_id, rows=rows)


def test_H19_a_bad_split_answers_400_and_writes_nothing(user, deal):
    with pytest.raises(ValidationError) as refused:
        services.save_split(user, deal_id=deal.id, rows=[{'party': partner().id, 'role': 'split', 'amount': '5'}])
    assert refused.value.detail == {'rows.primary': ['Pick a primary producer']}
    with pytest.raises(ValidationError):
        services.save_split(user, deal_id=deal.id, scope='firm', rows=[{'user': user.id, 'role': 'primary'}])
    assert not Commission.objects.filter(deal=deal).exists() and not Party.objects.filter(user=user).exists()


def test_H113_revert_puts_a_split_and_a_rate_back(user, deal):
    services.update(user, deal.id, {'rates': {'medical': '5'}})
    first = services.save_split(user, deal_id=deal.id, scope='client', rows=[{'user': user.id, 'role': 'primary'}])
    activity.revert(first.activity.id, user)
    assert not ClientSplit.objects.filter(client=deal.client).exists()
    rate = Activity.objects.filter(deal=deal, area='commission', summary__startswith='Edited').latest('id')
    activity.revert(rate.id, user)
    assert Commission.objects.get(deal=deal).rates == {}


def test_H96_H97_parties_are_added_edited_and_deactivated(admin_user):
    added = services.create_party(admin_user, {'kind': 'partner', 'name': '  Riverside  Life ', 'default_split': '15'})
    party = added.row
    assert (party.name, party.default_split) == ('Riverside Life', {'type': 'pct', 'value': '15'})
    assert added.activity.subject == f'party:{party.id}' and added.activity.deal is None
    assert 'Riverside' not in added.activity.summary  # summaries never carry a person's name
    written = services.save_party(admin_user, party.id, {'first_year_pct': '55', 'active': False})
    assert written.changed['active'] == [True, False]
    party.refresh_from_db()
    assert str(party.first_year_pct.normalize()) == '55' and party.active is False
    activity.revert(written.activity.id, admin_user)
    party.refresh_from_db()
    assert party.active is True and party.first_year_pct is None
    with pytest.raises(ValidationError):
        services.save_party(admin_user, party.id, {'renewal_pct': '101', 'email': 'not-an-email', 'active': 'yes'})


def test_H95_a_producer_login_gets_its_party_from_the_roster(admin_user, user):
    created = services.create_party(admin_user, {'user': user.id, 'appointed': True}).row
    assert (created.user_id, created.kind, created.name, created.appointed) == (user.id, 'producer', 'Dana', True)
    with pytest.raises(ValidationError):
        services.create_party(admin_user, {'user': user.id})  # already on the list


def test_H100_settings_and_the_agency_rate_on_one_screen_and_saving_confirms(admin_user):
    assert selectors.settings_payload()['confirmed'] is False
    written = services.save_settings(admin_user, {'first_year_pct': '45', 'default_commission': '6'})
    assert {entry['t'] for entry in written.changed} == {'settings:1', 'agency:1'}
    payload = selectors.settings_payload()
    assert (payload['first_year_pct'], payload['first_year_house_pct'], payload['confirmed']) == ('45', '55', True)
    assert AgencySettings.get().default_commission == {'type': 'pct', 'value': '6'}
    activity.revert(written.activity.id, admin_user)
    assert Settings.get().confirmed_at is None and Settings.get().first_year_pct == 40
    assert AgencySettings.get().default_commission == {}
    assert services.save_settings(admin_user, {'confirm': True}).changed == [
        {'t': 'settings:1', 'k': {'confirmed': [False, True]}}
    ]
    with pytest.raises(ValidationError):
        services.save_settings(admin_user, {'renewal_pct': '', 'gap_grace_days': 45})
