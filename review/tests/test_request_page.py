"""The request page (plan.md §7.13 `review/request/`, §8.8; L24, L26–L29, L33; B12; slice 56): a tab at a time, each
item where it stands, census columns with their blanks, the who bar, threads, what is new since a person's last look,
and the tray read in a fixed number of queries."""

from datetime import timedelta

import pytest
from django.db import connection
from django.db.models import F
from django.test.utils import CaptureQueriesContext

from intake.services import update_answers
from review.models import ClientLink, ReviewNote, Seen
from review.services import questions, send, tray

from .decision_world import intake_answers, link_on, submitted
from .portal_world import person

pytestmark = pytest.mark.django_db


def _page(api, deal, pane='intake'):
    answer = api.get(f'/api/deals/{deal.id}/review/request/', {'pane': pane})
    assert answer.status_code == 200, answer.content
    return answer.json()


def _sent(link):
    ClientLink.objects.filter(pk=link.pk).update(sent_at=link.created_at)


def test_L29_each_intake_item_says_where_it_stands(api, user, deal):
    update_answers(user, deal.id, {'dba': 'Example'})
    link = link_on(user, deal, {'intake': {'scope': 'selected', 'keys': ['fein', 'sic_code']}})
    _sent(link)
    intake_answers(deal, link, {'sic_code': '1234'})
    submitted(link)
    questions.ask(link.id, [{'ref': 'intake:fein', 'text': 'Which one?'}])
    tray.ask(user, deal.id, ['intake:website'])
    found = _page(api, deal)
    status = {item['ref']: item['status'] for item in found['items']}
    assert status['intake:fein'] == 'question'
    assert status['intake:website'] == 'in_cart'
    assert status['intake:sic_code'] == 'answered'
    assert status['intake:dba'] == 'on_file'
    assert status['intake:years_in_business'] == 'missing'
    assert status['intake:block:bor'] == 'missing'
    assert found['counts']['question'] == 1 and found['counts']['in_cart'] == 1
    assert [pane['key'] for pane in found['panes']] == ['intake', 'census', 'documents']
    assert found['panes'][0]['waiting'] == 2 and found['panes'][0]['in_cart'] == 1
    assert found['threads']['intake:fein'][0]['from_client']
    assert found['people'][0]['name'] == 'Casey (synthetic)' and found['people'][0]['path'].startswith('/portal/')


def test_L29_asked_says_when_a_link_out_asks_it(api, user, deal):
    link = link_on(user, deal, {'intake': {'scope': 'selected', 'keys': ['fein']}})
    assert {i['ref']: i['status'] for i in _page(api, deal)['items']}['intake:fein'] == 'missing'  # never sent
    _sent(link)
    fein = next(item for item in _page(api, deal)['items'] if item['ref'] == 'intake:fein')
    assert fein['status'] == 'asked' and fein['asked_at']
    assert api.get(f'/api/deals/{deal.id}/review/tray/').json()['out']['intake:fein'] == fein['asked_at']


def test_L46_the_census_tab_counts_blanks_by_column(api, user, deal):
    person(user, deal, 'Avery', 'Synthetic')
    person(user, deal, 'Blake', 'Synthetic', dob='1980-01-02')
    tray.ask_census(user, deal.id, ['dob'])
    found = _page(api, deal, 'census')
    dob = next(column for column in found['columns'] if column['key'] == 'dob')
    assert (dob['blank'], dob['in_cart']) == (1, 1)
    assert found['census_file']['ref'] == 'census:file' and found['census_file']['status'] == 'on_file'
    assert api.get(f'/api/deals/{deal.id}/review/request/', {'pane': 'payroll'}).status_code == 400


def test_L33_new_since_a_person_last_looked(api, user, deal):
    link = link_on(user, deal, {'intake': {'scope': 'all'}})
    _sent(link)
    questions.ask(link.id, [{'ref': 'intake:fein', 'text': 'Which?'}])
    # a minute back: the dev container's clock can step back under load (P12), and a look is clamped to now
    ReviewNote.objects.filter(deal=deal).update(at=F('at') - timedelta(minutes=1))
    assert _page(api, deal)['new'] == ['intake:fein']
    seen = api.post(f'/api/deals/{deal.id}/review/seen/', {}, format='json')
    assert seen.status_code == 200 and Seen.objects.get(deal=deal, user=user)
    assert _page(api, deal)['new'] == []
    earlier = api.post(f'/api/deals/{deal.id}/review/seen/', {'at': '2020-01-01T00:00:00+00:00'}, format='json')
    assert earlier.json()['seen_at'] == seen.json()['seen_at']  # it only moves forward


def _queries(read):
    with CaptureQueriesContext(connection) as captured:
        read()
    return len(captured.captured_queries)


def test_Q3_4_the_tray_reads_in_the_same_queries_for_one_draft_and_many(api, user, deal):
    link = link_on(user, deal, {'intake': {'scope': 'required'}})
    _sent(link)
    tray.ask(user, deal.id, ['intake:fein'])
    one = _queries(lambda: api.get(f'/api/deals/{deal.id}/review/tray/'))
    tray.ask(user, deal.id, ['intake:dba', 'intake:website', 'doc:claims', 'census:file', 'intake:block:bor'])
    assert _queries(lambda: api.get(f'/api/deals/{deal.id}/review/tray/')) == one
    send.send(user, deal.id)
