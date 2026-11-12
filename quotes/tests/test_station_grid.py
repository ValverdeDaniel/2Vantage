"""What the Documents station's Grid reads from the Advisor's comparison (plan.md §7.8, §8.16; E36, E41, E50, D123):
each compact cell says whether its value is a potential error, so "⚠ Potential errors" and the pick bar count what
the server counts, and a review's answer moves the flag with the mark."""

import pytest

from deals.values import apply, source
from quotes.models import Plan

from .review_world import world


@pytest.fixture
def w(user):
    w = world(user)
    # A value typed over the file's (it keeps the file, E66) that the file does not print: a potential error that is
    # not an open warning, since only Claude's values wait for a person (OQ28).
    plan = Plan.objects.get(pk=w['cigna'].id)
    absent = {'state': 'absent', 'v': 1}
    apply(plan.values, plan.sources, {'pcp_copay': '35'}, source('typed', user, doc=w['doc'].id, loc=absent))
    plan.save()
    return w


def cell_of(api, w, plan, key):
    response = api.get(f'/api/deals/{w["deal"].id}/plans/', {'line': 'medical'})
    assert response.status_code == 200, response.content
    body = response.json()
    cell = next(row for row in body['plans'] if row['id'] == w[plan].id)['cells'].get(key, {})
    return cell, body['documents']


def test_E50_a_value_the_file_does_not_print_is_a_potential_error_on_the_comparison(api, w):
    typed, documents = cell_of(api, w, 'cigna', 'pcp_copay')
    assert typed == {'d': 0, 'p': 1} and documents[0]['id'] == w['doc'].id
    # Claude's value the file does not print is an open warning already: `s`, never both.
    read, _ = cell_of(api, w, 'uhc', 'rate_ee')
    assert read.get('s') == 'to_check' and 'p' not in read
    found, _ = cell_of(api, w, 'uhc', 'deductible_single')
    assert 'p' not in found and 's' not in found


def test_E50_a_review_moves_the_flag_with_its_mark(api, w):
    ref = f'plan:{w["cigna"].id}:pcp_copay'
    url = f'/api/deals/{w["deal"].id}/plans/marks/'
    approved = api.post(url, {'action': 'approve', 'refs': [ref]}, format='json').json()
    assert approved['values'][0]['cell'] == {'m': 'approved'} and approved['values'][0]['potential'] is False
    assert cell_of(api, w, 'cigna', 'pcp_copay')[0] == {'d': 0, 'm': 'approved'}
    # ⚑ Needs checking makes it an open warning (a person's flag); clearing the flag leaves it a potential error again.
    flagged = api.post(url, {'action': 'check', 'refs': [ref]}, format='json').json()
    assert flagged['values'][0]['cell'] == {'s': 'to_check', 'm': 'check'}
    cleared = api.post(url, {'action': 'clear', 'refs': [ref]}, format='json').json()
    assert cleared['values'][0]['cell'] == {'p': 1} and cleared['values'][0]['potential'] is True
