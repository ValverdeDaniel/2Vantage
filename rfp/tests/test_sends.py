"""Sends: a draft marked sent, taken back, and who was asked (plan.md §5.7 "Sent"; K64–K68, K111, K115, K117, K120;
G113; OQ52)."""

from datetime import UTC, date, datetime
from unittest import mock

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from conftest import write_path_contract
from deals import activity
from deals.models import Activity
from intake.models import Intake
from rfp import page, selectors, services
from rfp.context import Request
from rfp.models import RfpRequest

from .request import ask

pytestmark = pytest.mark.django_db


def sent(api, deal, key, value=True):
    return api.post(f'/api/deals/{deal.id}/rfp/drafts/{key}/sent/', {'sent': value}, format='json')


def test_K64_K68_the_first_send_moves_to_quoting_pins_the_route_and_records_who_was_asked(api, user, deal):
    ask(user, deal, 'aetna', 'guardian', other_carriers='Oscar Health')
    assert RfpRequest.objects.get(deal=deal).route == ''
    response = sent(api, deal, 'warner')
    assert response.status_code == 200
    data = response.json()
    assert data['stage'] == 'quoting' and data['drafts']['sent_count'] == 1
    deal.refresh_from_db()
    assert deal.stage == 'quoting'
    row = RfpRequest.objects.get(deal=deal)
    assert row.route == 'warner'
    send = row.sends['warner']
    assert send['route'] == 'warner' and send['by'] == user.id
    assert [entry['name'] for entry in send['asked']] == ['Aetna', 'Guardian', 'Oscar Health']
    asked = selectors.asked_by_line(deal)  # what the proposal's Markets checked reads (K117)
    assert {entry['name'] for entry in asked['medical']} == {'Aetna', 'Oscar Health'}
    assert {entry['name'] for entry in asked['dental']} == {'Aetna', 'Guardian', 'Oscar Health'}
    assert Activity.objects.filter(deal=deal, area='deal', summary__startswith='Moved to Quoting').count() == 1
    assert not Intake.objects.filter(deal=deal, marketed_at__isnull=False).exists()  # OQ52: no "Sent to market"


def test_K64_taking_a_send_back_keeps_the_stage_and_a_second_send_never_moves_it_again(api, user, deal):
    ask(user, deal, 'aetna', route='direct')
    assert sent(api, deal, 'aetna').json()['stage'] == 'quoting'
    assert sent(api, deal, 'aetna', False).json()['drafts']['sent_count'] == 0
    deal.refresh_from_db()
    assert deal.stage == 'quoting' and RfpRequest.objects.get(deal=deal).sends == {}


def test_K111_K112_a_lost_deal_and_a_past_year_refuse_a_send(api, user, deal):
    ask(user, deal, 'aetna', route='direct')
    deal.effective_date = date(2020, 1, 1)
    deal.save(update_fields=['effective_date'])
    assert sent(api, deal, 'aetna').status_code == 409
    deal.effective_date, deal.stage = None, 'lost'
    deal.save(update_fields=['effective_date', 'stage'])
    response = sent(api, deal, 'aetna')
    assert response.status_code == 409 and 'lost' in response.json()['detail']
    assert sent(api, deal, 'cigna').status_code == 409


def test_K64_an_unknown_draft_is_404_and_sent_must_be_a_bool(api, user, deal):
    ask(user, deal, 'aetna', route='direct')
    assert sent(api, deal, 'cigna').status_code == 404
    assert sent(api, deal, 'aetna', 'yes').status_code == 400


def test_K120_a_send_whose_draft_is_gone_stays_listed_and_can_be_taken_back(api, user, deal):
    ask(user, deal, 'aetna', 'cigna', route='direct')
    sent(api, deal, 'aetna')
    services.update(user, deal.id, {'carriers': {'remove': ['aetna']}})
    deal.refresh_from_db()
    block = page.request_parts(Request(deal))['drafts']
    assert [draft['key'] for draft in block['rows']] == ['cigna']
    assert block['sent_earlier'][0]['key'] == 'aetna' and block['sent_earlier'][0]['label'] == 'Aetna'
    assert sent(api, deal, 'aetna', False).json()['drafts']['sent_earlier'] == []
    assert selectors.asked_by_line(deal) == {}


def test_K115_a_send_is_its_own_row_never_merged_carries_no_notes_and_undo_takes_it_back(user, deal):
    ask(user, deal, 'aetna', route='direct', notes='Confidential: the incumbent offered 4%.')
    services.set_done(user, deal.id, 'emails', True)
    first = services.mark_sent(user, deal.id, 'aetna', True).activity
    assert first.action == 'sent' and 'Confidential' not in str(first.changes)
    row = RfpRequest.objects.get(deal=deal)
    assert 'emails' not in row.done  # the Emails card's mark comes off (K10)
    activity.revert(first.id, user)
    row.refresh_from_db()
    assert row.sends == {} and 'emails' in row.done


def test_Q3_send_write_path(user, deal):
    ask(user, deal, 'aetna', route='direct')
    deal.stage = 'quoting'  # the first send's stage move is `advance`'s own row (§5.1); here the deal is past it
    deal.save(update_fields=['stage'])
    row = RfpRequest.objects.get(deal=deal)
    write_path_contract(
        user,
        row,
        lambda: services.mark_sent(user, deal.id, 'aetna', True),
        lambda r: sorted(r.sends),
        lambda: services.mark_sent(user, deal.id, 'aetna', False),
    )


def test_Q3_7_a_send_at_9_pm_eastern_is_dated_today_in_agency_time(user, deal):
    ask(user, deal, 'aetna', route='direct')
    evening = datetime(2026, 11, 12, 2, 0, tzinfo=UTC)  # 21:00 on the 11th in New York
    with mock.patch('deals.clock.now', return_value=evening):
        services.mark_sent(user, deal.id, 'aetna', True)
    assert RfpRequest.objects.get(deal=deal).sends['aetna']['on'] == '2026-11-11'


def test_Q3_the_send_locks_the_deal_first_then_the_request(user, deal):
    ask(user, deal, 'aetna', route='direct')
    with CaptureQueriesContext(connection) as queries:
        services.mark_sent(user, deal.id, 'aetna', True)
    locks = [q['sql'] for q in queries.captured_queries if 'FOR UPDATE' in q['sql']]
    assert '"deals_deal"' in locks[0] and f'"{RfpRequest._meta.db_table}"' in locks[1]
