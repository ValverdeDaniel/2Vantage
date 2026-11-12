"""Saved parts of a proposal, Mine and Shared (plan.md §6.11, §7.12 `proposal/templates/`; J68, OQ7): the built-in
layout first, then a person's own and the team's shared ones; only the owner or an admin changes one; another
person's private template does not exist for anyone else; applying one is the deal's own PATCH."""

import pytest
from django.contrib.auth import get_user_model

from conftest import make_deal, write_path_contract
from proposals import template_services
from proposals.models import ProposalConfig, ProposalTemplate

pytestmark = pytest.mark.django_db


@pytest.fixture
def other(db):
    return get_user_model().objects.create_user('omar', 'omar@example.com', 'pw-Example-1')


def _names(api, kind, line=''):
    return [row['name'] for row in api.get('/api/proposal/templates/', {'kind': kind, 'line': line}).json()]


def test_J68_the_list_is_built_in_then_mine_then_shared_never_anothers_private(api, user, other):
    template_services.create(other, {'name': 'Their private', 'kind': 'layout'})
    template_services.create(other, {'name': 'Their shared', 'kind': 'layout', 'shared': True})
    made = api.post('/api/proposal/templates/', {'name': 'Mine', 'kind': 'layout', 'config': {}}, format='json')
    assert made.status_code == 201
    found = api.get('/api/proposal/templates/', {'kind': 'layout'}).json()
    assert [row['name'] for row in found] == ['Vantage default', 'Mine', 'Their shared']
    assert found[0]['built_in'] and not found[0]['can_edit']
    assert found[1]['is_mine'] and found[1]['can_edit']
    assert not found[2]['can_edit'] and found[2]['owner_name'] == 'omar'
    assert api.get('/api/proposal/templates/', {'kind': 'nope'}).status_code == 400


def test_J68_a_template_offered_on_one_line_shows_there_and_any_line_everywhere(api, user):
    template_services.create(user, {'name': 'Medical rows', 'kind': 'rows', 'line': 'medical'})
    template_services.create(user, {'name': 'Any rows', 'kind': 'rows'})
    assert _names(api, 'rows', 'medical') == ['Any rows', 'Medical rows']
    assert _names(api, 'rows', 'dental') == ['Any rows']


def test_J68_only_the_owner_or_an_admin_changes_a_shared_template(api, admin_api, other):
    shared = template_services.create(other, {'name': 'Theirs', 'kind': 'summary', 'shared': True})
    private = template_services.create(other, {'name': 'Hidden', 'kind': 'summary'})
    assert api.patch(f'/api/proposal/templates/{shared.id}/', {'name': 'Mine now'}, format='json').status_code == 403
    assert api.delete(f'/api/proposal/templates/{shared.id}/').status_code == 403
    assert api.patch(f'/api/proposal/templates/{private.id}/', {'name': 'x'}, format='json').status_code == 404
    renamed = admin_api.patch(f'/api/proposal/templates/{shared.id}/', {'name': 'Kept up'}, format='json')
    assert renamed.status_code == 200 and renamed.json()['name'] == 'Kept up'


def test_J68_names_are_one_per_person_and_kind_and_fields_answer_by_name(api, user):
    template_services.create(user, {'name': 'Ours', 'kind': 'summary'})
    taken = api.post('/api/proposal/templates/', {'name': 'Ours', 'kind': 'summary'}, format='json')
    assert taken.status_code == 400 and 'name' in taken.json()
    bad = api.post('/api/proposal/templates/', {'name': '', 'kind': 'cover', 'line': 'boats'}, format='json')
    assert bad.status_code == 400 and set(bad.json()) == {'name', 'kind', 'line'}
    assert api.post('/api/proposal/templates/', {'name': 'Ours', 'kind': 'layout'}, format='json').status_code == 201


def test_Q3_1_J68_an_update_reverts(user):
    row = template_services.create(user, {'name': 'Short', 'kind': 'summary', 'config': {'summary.on': False}})
    write_path_contract(
        user,
        row,
        lambda: template_services.update(user, row.id, {'description': 'For renewals'}),
        lambda found: found.description,
        lambda: template_services.update(user, row.id, {'description': 'For new groups'}),
    )


def test_J68_a_template_moved_to_another_kind_keeps_no_other_kinds_paths(user):
    row = template_services.create(user, {'name': 'Look', 'kind': 'layout', 'config': {'output.layout': 'best_only'}})
    assert row.config['output.layout'] == 'best_only'
    moved, _entry = template_services.update(user, row.id, {'kind': 'summary'})
    assert set(moved.config) == {'summary.on', 'summary.blocks'}


def test_J68_applying_a_layout_template_is_the_deals_own_patch(api, user):
    deal = make_deal(user)
    found = api.post(
        '/api/proposal/templates/',
        {
            'name': 'Side by side',
            'kind': 'layout',
            'config': {'output.layout': 'side_by_side', 'output.cover.on': False},
        },
        format='json',
    ).json()
    applied = api.patch(f'/api/deals/{deal.id}/proposal/', found['config'], format='json').json()
    assert applied['changed'] == {'output.layout': 'side_by_side', 'output.cover.on': False}  # the rest are defaults
    assert ProposalConfig.objects.get(deal=deal).config['output']['layout'] == 'side_by_side'
    (default,) = [row for row in api.get('/api/proposal/templates/', {'kind': 'layout'}).json() if row['built_in']]
    api.patch(f'/api/deals/{deal.id}/proposal/', default['config'], format='json')
    assert ProposalConfig.objects.get(deal=deal).config == {}  # Vantage default undoes every look choice
    assert not ProposalTemplate.objects.filter(name='Vantage default').exists()  # it lives in code
