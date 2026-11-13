"""The sections' own boards and their rules (plan.md §8.8; B37; C27, C28, C30; L6, L12, L45; OQ17): the Intake board
row per question with Auto / Required / Waived and a note the client reads; the Census board row per column with its
five-segment bar and origins, the drill and the by-person lens; the Missing lane (one rule: blank and no client answer
waiting) with "＋ Ask all" that skips what is asked; the Board's Next."""

import pytest

from census.models import CensusFacts, CensusSettings
from deals import activity, clock
from deals.models import Activity
from intake.models import Intake
from review.models import ClientLink
from review.services import tray

from .decision_world import census_answers, intake_answers, link_on
from .portal_world import client, field, make_request, page, person

pytestmark = pytest.mark.django_db


def section(api, deal, surface, **query):
    answer = api.get(f'/api/deals/{deal.id}/review/section/', {'surface': surface, **query})
    assert answer.status_code == 200, answer.content
    assert answer['Cache-Control'] == 'private, no-store'
    return answer.json()


def rules(api, deal, surface, body):
    return api.post(f'/api/deals/{deal.id}/review/rules/', {'surface': surface, 'rules': body}, format='json')


def row(board, key):
    return next(entry for entry in board['rows'] if entry['key'] == key)


def test_B37_a_question_required_on_this_deal_is_needed_and_its_note_reaches_the_client(api, user, deal):
    assert not row(section(api, deal, 'intake'), 'website')['needed']
    answer = rules(api, deal, 'intake', {'website': {'state': 'required', 'note': 'Your public site, please.'}})
    assert answer.status_code == 200, answer.content
    website = row(answer.json()['board'], 'website')
    assert (website['rule'], website['needed'], website['status'], website['note']) == (
        'required',
        True,
        'gap',
        'Your public site, please.',
    )
    _link, token, _pin = make_request(user, deal, {'intake': {'scope': 'required'}})
    assert field(page(client(), token).json(), 'website')['help'] == 'Your public site, please.'
    activity.revert(answer.json()['activity_id'], user)
    assert 'website' not in Intake.objects.get(deal=deal).rules


def test_B37_waived_lets_a_quote_blocking_question_go(api, user, deal):
    assert row(section(api, deal, 'intake'), 'fein')['needed']
    rules(api, deal, 'intake', {'fein': {'state': 'waived'}})
    fein = row(section(api, deal, 'intake'), 'fein')
    assert (fein['needed'], fein['status']) == (False, 'waived')
    assert rules(api, deal, 'intake', {'fein': {'state': 'sometimes'}}).status_code == 400
    assert rules(api, deal, 'intake', {'fein': {'note': 'x' * 301}}).status_code == 400


def test_B37_the_board_says_what_is_asked_and_what_the_client_sent_differently(api, user, deal):
    link = link_on(user, deal, {'intake': {'scope': 'all'}}, name='Dana')
    ClientLink.objects.filter(pk=link.pk).update(sent_at=clock.now())
    intake_answers(deal, link, {'dba': 'Example Trading'})
    board = section(api, deal, 'intake')
    dba = row(board, 'dba')
    assert dba['status'] == 'pending' and dba['asked_in'] == ['Dana'] and dba['theirs'] == 'Example Trading'


def test_C27_a_column_reads_its_segments_and_origins_and_takes_a_rule(api, user, deal):
    avery = person(user, deal, 'Avery', 'Synthetic', zip='32801')
    person(user, deal, 'Blake', 'Synthetic')
    link = link_on(user, deal)
    census_answers(deal, link, {(avery.id, 'dob'): '01/02/1980'})
    board = section(api, deal, 'census')
    columns = {column['key']: column for column in board['columns']}
    assert 'ssn' not in columns
    assert columns['zip']['filled'] == 1 and columns['zip']['origins'] == {'typed': 1}
    assert columns['dob']['counts']['client'] == 1 and columns['dob']['total'] == 2
    answer = rules(api, deal, 'census', {'zip': 'waived'})
    assert answer.status_code == 200, answer.content
    assert CensusSettings.objects.get(deal=deal).rules == {'zip': 'waived'}
    zip_ = next(column for column in answer.json()['board']['columns'] if column['key'] == 'zip')
    assert zip_['rule'] == 'waived' and not zip_['required']
    assert rules(api, deal, 'census', {'ssn': 'required'}).status_code == 400
    activity.revert(answer.json()['activity_id'], user)
    assert CensusSettings.objects.get(deal=deal).rules == {}


def test_C27_requiring_a_column_moves_the_stored_counts(api, user, deal):
    person(user, deal, 'Avery', 'Synthetic')
    before = CensusFacts.objects.get(deal=deal).required_total
    rules(api, deal, 'census', {'hire_date': 'required'})
    assert CensusFacts.objects.get(deal=deal).required_total == before + 1


def test_C28_the_drill_names_people_and_values_for_staff(api, user, deal):
    person(user, deal, 'Avery', 'Synthetic', zip='32801')
    found = section(api, deal, 'census', column='zip')
    assert [(entry['title'], entry['value']) for entry in found['people']] == [('Avery Synthetic', '32801')]
    assert api.get(f'/api/deals/{deal.id}/review/section/', {'surface': 'census', 'column': 'ssn'}).status_code == 400


def test_C30_the_by_person_lens_and_the_file_hint(api, user, deal):
    person(user, deal, 'Avery', 'Synthetic')
    board = section(api, deal, 'census')
    assert board['people']['people'][0]['title'] == 'Avery Synthetic' and board['file_hint'] is False


def test_L6_missing_skips_waiting_answers_and_ask_all_skips_what_is_asked(api, user, deal):
    avery = person(user, deal, 'Avery', 'Synthetic')
    board = api.get(f'/api/deals/{deal.id}/review/board/').json()
    lane = {entry['key']: entry for entry in board['lanes']['missing']}
    intake = lane['intake']
    assert intake['ask'] and intake['left'] == intake['count']
    tray.ask(user, deal.id, intake['ask']['refs'][:1])
    lane = {e['key']: e for e in api.get(f'/api/deals/{deal.id}/review/board/').json()['lanes']['missing']}
    assert lane['intake']['left'] == intake['count'] - 1 and lane['intake']['count'] == intake['count']
    census = lane['census']
    assert census['ask']['census']['scope'] == 'missing'
    link = link_on(user, deal)
    census_answers(deal, link, {(avery.id, 'dob'): '01/02/1980'})
    lane = {e['key']: e for e in api.get(f'/api/deals/{deal.id}/review/board/').json()['lanes']['missing']}
    assert lane['census']['count'] == census['count'] - 1  # a waiting answer is not missing (Ch. 2)


def test_L45_a_sections_own_board_keeps_its_rows(api, user, deal):
    answer = api.get(f'/api/deals/{deal.id}/review/board/?scope=census')
    assert answer.status_code == 200
    found = answer.json()
    assert found['scope'] == 'census'
    assert [entry['key'] for entry in found['lanes']['missing']] == ['census_file']
    assert all(entry['surface'] in ('', 'census') for entry in found['next'])
    assert api.get(f'/api/deals/{deal.id}/review/board/?scope=everything').status_code == 400


def test_L3_the_board_names_what_comes_next(api, user, deal):
    board = api.get(f'/api/deals/{deal.id}/review/board/').json()
    assert board['next'][0]['kind'] == 'blocks_carrier' and 'required to market' in board['next'][0]['label']


def test_L30_their_form_writes_nothing_and_marks_what_is_new(api, user, deal):
    link, _token, _pin = make_request(user, deal, {'intake': {'scope': 'selected', 'keys': ['fein'], 'blocks': []}})
    rows = Activity.objects.count()
    body = {'request_id': link.request_id, 'on': {'census_file': True}, 'off': {'refs': ['intake:fein']}}
    answer = api.post(f'/api/deals/{deal.id}/review/preview/', body, format='json')
    assert answer.status_code == 200, answer.content
    found = answer.json()
    assert found['page']['preview'] and found['page']['census_file'] is not None
    assert found['new_refs'] == ['census:file'] and not field(found['page'], 'fein')
    fresh = api.post(f'/api/deals/{deal.id}/review/preview/', {'asks': {'intake': {'scope': 'all'}}}, format='json')
    assert field(fresh.json()['page'], 'fein') and Activity.objects.count() == rows
