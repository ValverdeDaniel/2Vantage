"""The Overview's data confidence (plan.md §8.6, §7.13; Q.9 row 64; M83, M86, M87, M90, M91, M92): each origin lands
in one cell, the confirmed bar tells a person's approvals from those applied from Claude's re-check, each file has its
counts and quality, the marked lists never carry member data, and the read costs the same queries at any size."""

import json
from decimal import Decimal
from unittest import mock

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from ai import kinds
from ai.models import Job
from conftest import make_big_deal
from deals.values import apply, source
from intake.models import Intake
from quotes.models import Plan
from quotes.services import review as plan_marks
from review.selectors import confidence as reading
from review.services import marks

from .confidence_world import CANARY_ANSWER, CANARY_LASER, CANARY_NAME, world

pytestmark = pytest.mark.django_db


@pytest.fixture
def w(user):
    return world(user)


def read(api, deal):
    answer = api.get(f'/api/deals/{deal.id}/confidence/')
    assert answer.status_code == 200, answer.content
    return answer.json()


def test_M83_each_origin_lands_in_one_cell(api, user, w):
    plan = Plan.objects.get(pk=w.plan.id)
    apply(plan.values, plan.sources, {'deductible_single': '2000'}, source('typed', user))  # typed over a read
    plan.save()
    body = read(api, w.deal)
    cells = body['cells']
    assert cells['scanned'] == 12 and cells['corrected'] == 1  # read values, the corrected one among them
    assert cells['scanned'] + cells['typed'] + cells['from_client'] == body['filled']
    assert cells['typed'] > 0 and cells['from_client'] == 0 and cells['pending'] == 0
    assert body['warnings']['to_review'] == 4 and body['warnings']['low'] == 4  # rate, SIC code, two birth dates


def test_M86_the_bar_tells_a_persons_approvals_from_the_rechecks(api, user, w):
    marks.mark(user, w.deal.id, 'approve', document_id=w.other.id)
    plan_marks.mark_values(user, w.deal, 'approve', refs=[f'plan:{w.plan.id}:network'], via='recheck')
    body = read(api, w.deal)
    assert body['confirmed']['by_person'] == 2 and body['confirmed']['by_recheck'] == 1
    assert body['confirmed']['total'] == 3
    assert body['confirmed']['pct'] == int(Decimal(300) / body['filled'] + Decimal('0.5'))  # half up


def test_M87_each_file_has_its_counts_and_quality(api, user, w):
    marks.mark(user, w.deal.id, 'ignore', refs=['intake:sic_code'])
    body = read(api, w.deal)
    quote, other = body['documents']  # most values first
    assert (quote['id'], quote['values'], quote['confirmed'], quote['to_review']) == (w.quote.id, 10, 0, 3)
    assert quote['ignored'] == 1 and quote['name'] == w.quote.original_name
    assert quote['headline']['label'] == 'Mostly clean — review flags'  # 7 of 10 clean
    assert (other['id'], other['values'], other['headline']['label']) == (w.other.id, 2, 'Clean scan')


def test_M90_M91_the_marked_lists_never_carry_member_data(api, user, w):
    birth = [f'census:{person.id}:dob' for person in w.people]
    marks.mark(user, w.deal.id, 'ignore', refs=[*birth, f'plan:{w.stop.id}:sl_lasers', f'plan:{w.plan.id}:rate_ee'])
    named = f'census:{w.people[0].id}:last_name'
    marks.mark(user, w.deal.id, 'check', refs=['questionnaire:fl_blue_51:txtAdd2', named])
    body = read(api, w.deal)
    ignored = {row['ref']: row for row in body['ignored']['rows']}
    assert ignored[f'plan:{w.plan.id}:rate_ee']['value'] == '512.34'
    assert ignored[f'plan:{w.plan.id}:rate_ee']['where'] == 'Cigna — Open Access'
    laser = ignored[f'plan:{w.stop.id}:sl_lasers']
    assert laser['value'] is None and laser['label'].startswith('Lasers') and laser['doc']['id'] == w.other.id
    dob = ignored[birth[0]]
    assert dob['value'] is None and dob['where'] == 'Census · Employee row 1' and dob['label'] == 'Date of Birth'
    assert dob['by'] and dob['tab'] == 'census'
    check = {row['ref']: row for row in body['check']['rows']}
    form = check['questionnaire:fl_blue_51:txtAdd2']
    assert form['value'] is None and form['form'] == 'fl_blue_51' and form['label'] == 'Business Address Line 2'
    text = json.dumps(body)
    assert all(canary not in text for canary in (CANARY_NAME, CANARY_ANSWER, CANARY_LASER))


def test_M90_each_list_shows_its_first_rows_and_counts_the_rest(api, user, w):
    birth = [f'census:{person.id}:dob' for person in w.people]
    marks.mark(user, w.deal.id, 'ignore', refs=[*birth, f'plan:{w.plan.id}:rate_ee'])
    with mock.patch.object(reading, 'CAP', 2):
        body = read(api, w.deal)
    assert len(body['ignored']['rows']) == 2 and body['ignored']['more'] == 1
    assert body['check'] == {'rows': [], 'more': 0}


def test_M92_the_last_recheck_shows_its_result_and_first_differences(api, user, w):
    assert read(api, w.deal)['recheck'] == {'values': 5, 'last': None}  # the plan values read from files
    item = {
        'op': 'set_values', 'carrier': 'Cigna', 'name': 'Open Access',
        'values': [{'key': 'rate_ee', 'label': 'Rate — EE', 'old': '512.34', 'new': '521.34', 'doc': w.quote.id,
                    'page': 1}],
    }  # fmt: skip
    result = {'counts': {'approvals': 3, 'fixes': 7, 'unverified': 1}, 'items': [item] * 7, 'unverified': []}
    job = {'lane': kinds.WORK, 'kind': kinds.RECHECK, 'target': 'quotes', 'status': kinds.DONE, 'land': 'staged'}
    Job.objects.create(deal=w.deal, params={'refs': [], 'scanned': True}, result=result, **job)  # set-up: one ended
    last = read(api, w.deal)['recheck']['last']
    assert last['counts'] == {'checked': 11, 'agreed': 3, 'differ': 7, 'not_found': 1}
    assert last['scanned'] and last['waiting'] and len(last['differences']) == 6
    first = last['differences'][0]
    assert (first['label'], first['old'], first['new']) == ('Cigna Open Access — Rate — EE', '512.34', '521.34')
    assert first['doc']['name'] == w.quote.original_name


def test_Q3_2_the_read_writes_nothing_and_creates_no_row(api, deal):
    body = read(api, deal)  # a deal with no Intake row, no people and no form
    assert body['filled'] == 0 and body['documents'] == [] and body['confirmed']['pct'] == 0
    assert not Intake.objects.filter(deal=deal).exists()  # a read never makes an owner's row (§3.6)


def _queries(deal):
    with CaptureQueriesContext(connection) as captured:
        reading.confidence(deal)
    return len(captured.captured_queries)


def test_Q3_4_the_read_runs_the_same_queries_at_10_and_60_plans(user):
    small, big = make_big_deal(user, 10, name='Small (synthetic)'), make_big_deal(user, 60, name='Large (synthetic)')
    assert _queries(small) == _queries(big)
    assert reading.confidence(big)['filled'] > reading.confidence(small)['filled']
