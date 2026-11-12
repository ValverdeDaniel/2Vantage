"""The station's List and the marks door over HTTP (plan.md §7.8, §10.7; E34, E48, E53, E56, E57, D122, F63):
`GET deals/{id}/plans/sources/` and `POST deals/{id}/plans/marks/`."""

import threading
from unittest import mock

import pytest
from django.db import connection

from conftest import make_deal
from quotes import services
from quotes.models import Plan
from quotes.selectors import review as selector
from quotes.services import review

from .review_world import add_file, read_into, world


@pytest.fixture
def w(user):
    return world(user)


def sources(api, w, **query):
    response = api.get(f'/api/deals/{w["deal"].id}/plans/sources/', query)
    assert response.status_code == 200, response.content
    return response.json()


def mark(api, w, body):
    return api.post(f'/api/deals/{w["deal"].id}/plans/marks/', body, format='json')


def test_D122_the_list_runs_worst_first_and_dealt_values_sink(api, w):
    body = sources(api, w, documents=str(w['doc'].id))
    assert [row['bucket'] for row in body['rows']] == ['absent', 'review', 'review', 'unchecked', 'unchecked', 'found']
    assert body['rows'][0]['ref'] == f'plan:{w["uhc"].id}:rate_ee' and body['rows'][0]['sub'] == 'UHC · Choice'
    assert body['warnings'] == {'open': 3, 'check': 0, 'unflagged': 3}
    first = body['rows'][1]['ref']
    assert mark(api, w, {'action': 'approve', 'refs': [first]}).status_code == 200
    rows = sources(api, w, documents=str(w['doc'].id))
    at = next(index for index, row in enumerate(rows['rows']) if row['ref'] == first)
    approved = rows['rows'][at]
    # No longer doubted, so out of "AI flagged" (the old bucketOf), and last in its bucket: a person dealt with it.
    assert approved['bucket'] == 'unchecked' and approved['dealt'] and approved['confirmed']['by_name']
    assert at == 4 and rows['rows'][5]['bucket'] == 'found'
    assert rows['counts']['unchecked'] == {'open': 2, 'done': 1} and rows['all']['done'] == 1


def test_E34_quality_counts_the_files_values_and_their_plans_blanks(api, w):
    body = sources(api, w, documents=str(w['doc'].id))
    assert body['quality']['high'] == 3 and body['quality']['low'] == 3 and body['quality']['missing'] > 0
    assert body['headline']['label'] == 'Needs review'


def test_E56_buckets_filter_and_pages_of_rows(api, w):
    only = sources(api, w, bucket='review')
    assert {row['bucket'] for row in only['rows']} == {'review'} and only['total'] == 2
    with mock.patch.object(selector, 'PAGE_SIZE', 4):
        first, second = sources(api, w, page=1), sources(api, w, page=2)
    assert first['pages'] == 2 and len(first['rows']) == 4 and len(second['rows']) == 2
    assert not {row['ref'] for row in first['rows']} & {row['ref'] for row in second['rows']}


def test_E56_a_typed_value_from_no_file_is_not_listed(api, w):
    refs = {row['ref'] for row in sources(api, w)['rows']}
    assert f'plan:{w["current"].id}:rate_ee' not in refs


@pytest.mark.parametrize('query', [{'documents': 'x'}, {'bucket': 'worst'}, {'page': '0'}, {'page': 'two'}])
def test_E56_bad_queries_answer_400(api, w, query):
    assert api.get(f'/api/deals/{w["deal"].id}/plans/sources/', query).status_code == 400


def test_F63_marks_answer_what_changed_for_both_screens(api, w):
    cigna = w['cigna']
    response = mark(api, w, {'action': 'ignore', 'plan_ids': [cigna.id]})
    assert response.status_code == 200
    body = response.json()
    assert body['changed'] == 2 and body['activity_id'] and not body['truncated']
    assert [(plan['id'], plan['flags']) for plan in body['plans']] == [(cigna.id, 0)]
    by_key = {value['key']: value for value in body['values']}
    assert by_key['rate_ee']['cell'] == {'m': 'ignored'} and not by_key['rate_ee']['open']
    comparison = api.get(f'/api/deals/{w["deal"].id}/plans/', {'line': 'medical'}).json()
    plan = next(p for p in comparison['plans'] if p['id'] == cigna.id)
    assert plan['facts']['flags'] == 0 == Plan.objects.get(pk=cigna.id).flags
    assert plan['cells']['rate_ee']['m'] == 'ignored' and 's' not in plan['cells']['rate_ee']


def test_F64_the_board_shows_check_and_approval_marks(api, w):
    uhc = w['uhc']
    mark(api, w, {'action': 'check', 'refs': [f'plan:{uhc.id}:deductible_single']})
    mark(api, w, {'action': 'approve', 'refs': [f'plan:{uhc.id}:rate_ee']})
    plans = api.get(f'/api/deals/{w["deal"].id}/plans/', {'line': 'medical'}).json()['plans']
    plan = next(p for p in plans if p['id'] == uhc.id)
    assert plan['cells']['deductible_single'] == {**plan['cells']['deductible_single'], 's': 'to_check', 'm': 'check'}
    assert plan['cells']['rate_ee']['m'] == 'approved' and 's' not in plan['cells']['rate_ee']
    assert plan['facts']['flags'] == 1


def test_E53_a_review_past_the_cap_lists_nothing_and_says_so(api, w):
    with mock.patch('quotes.review_views.VALUES_CAP', 1):
        body = mark(api, w, {'action': 'check'}).json()
    assert body['truncated'] and body['values'] == [] and body['changed'] == 3


@pytest.mark.parametrize(
    'body',
    [{'action': 'approve', 'refs': []}, {'action': 'nod', 'plan_ids': [1]}, {'action': 'approve', 'plan_ids': 'x'}],
)
def test_E86_bad_bodies_answer_400(api, w, body):
    assert mark(api, w, body).status_code == 400


def test_E54_undo_reverts_the_reviews_activity_row(api, w):
    body = mark(api, w, {'action': 'approve', 'document_ids': [w['doc'].id]}).json()
    assert body['changed'] == 3
    undone = api.post(f'/api/activity/{body["activity_id"]}/revert/')
    assert undone.status_code == 200 and len([key for c in undone.json()['changes'] for key in c['k']]) == 3
    assert sources(api, w)['warnings']['open'] == 3
    assert api.post(f'/api/activity/{body["activity_id"]}/revert/').status_code == 409


@pytest.mark.django_db(transaction=True)
def test_Q3_8_reviews_of_different_values_on_one_plan_both_survive(user):
    deal = make_deal(user)
    doc = add_file(user, deal)
    plan = services.create_plan(user, deal, line='medical', role='current', carrier='Aetna', name='HDHP')
    plan = read_into(plan, {'rate_ee': '500', 'rate_fam': '1500'}, doc, low=('rate_ee', 'rate_fam'))
    real = review.apply_mark

    def slow(*args):
        out = real(*args)
        threading.Event().wait(0.2)  # hold the locked row between read and write
        return out

    def write(key, action):
        try:
            review.mark_values(user, deal, action, refs=[f'plan:{plan.id}:{key}'])
        finally:
            connection.close()

    with mock.patch.object(review, 'apply_mark', slow):
        threads = [
            threading.Thread(target=write, args=('rate_ee', 'approve')),
            threading.Thread(target=write, args=('rate_fam', 'check')),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
    saved = Plan.objects.get(pk=plan.id)
    assert 'confirmed' in saved.sources['rate_ee'] and saved.sources['rate_fam']['mark']['state'] == 'check'
    assert saved.flags == 1
