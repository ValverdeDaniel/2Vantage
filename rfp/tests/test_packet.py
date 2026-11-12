"""The packet's census rows, their ticks and what the files require of the census (plan.md §5.3.3, §9.10; K10,
K34–K41, K56, K124; OQ64)."""

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.exceptions import ValidationError

from census import facts as census_facts
from census import providers as census_providers
from deals import activity
from deals.models import Activity
from rfp import cleaners, services
from rfp.cards import census as packet
from rfp.formats import required, scope
from rfp.models import RfpRequest

from .roster import family

pytestmark = pytest.mark.django_db


def request(**settings):
    return {**cleaners.stored(None), **settings}


def ticked(rows):
    return {row['key']: row['include'] for row in rows}


def test_K39_with_nothing_picked_every_carriers_format_is_ticked_and_angles_csv_is_off_on_purpose():
    rows = packet.rows(request(), 'warner', 5)
    assert ticked(rows) == {
        'census-warner': True,
        'census-aetna': True,
        'census-angle': True,
        'census-angle-csv': False,
        'census-uhc': True,
    }
    csv_row = next(row for row in rows if row['key'] == 'census-angle-csv')
    assert csv_row['alt_of'] == 'census-angle' and csv_row['deliberate'].startswith('The same census')


def test_K39_OQ64_the_universal_census_leaves_when_every_picked_carrier_has_its_own_format():
    direct = ticked(packet.rows(request(carriers=['aetna', 'unitedhealthcare']), 'direct', 5))
    assert direct == {**dict.fromkeys(scope.keys(), False), 'census-aetna': True, 'census-uhc': True}
    with_cigna = ticked(packet.rows(request(carriers=['aetna', 'cigna']), 'direct', 5))
    assert with_cigna['census-warner'] and with_cigna['census-aetna'] and not with_cigna['census-uhc']
    others = ticked(packet.rows(request(carriers=['aetna'], other_carriers='Oscar'), 'direct', 5))
    assert others['census-warner']
    through_warner = ticked(packet.rows(request(carriers=['aetna']), 'warner', 5))
    assert through_warner['census-warner']


def test_K36_each_row_says_who_it_is_for():
    rows = {row['key']: row for row in packet.rows(request(carriers=['aetna', 'cigna'], other_carriers='Oscar'), '', 5)}
    assert rows['census-aetna']['required_by'] == ['Aetna']
    assert rows['census-warner']['required_by'] == ['Cigna', 'Other carriers']
    assert rows['census-warner']['universal'] and rows['census-uhc']['required_by'] == []


def test_K41_with_nobody_on_the_census_no_row_can_be_ticked():
    rows = packet.rows(request(), 'warner', 0)
    assert not any(row['include'] or row['available'] for row in rows)
    assert {row['reason'] for row in rows} == {'No census yet'}


def test_K97_a_row_past_its_cap_says_so():
    rows = {row['key']: row for row in packet.rows(request(), 'warner', 300)}
    assert rows['census-angle']['capped'] and not rows['census-warner']['capped']
    assert not rows['census-angle-csv']['capped']


def test_K35_K56_only_ticks_that_differ_from_the_default_are_kept(user, deal):
    services.update(user, deal.id, {'carriers': {'add': ['aetna']}})
    services.update(user, deal.id, {'include': {'census-uhc': True, 'census-aetna': True}})
    assert RfpRequest.objects.get(deal=deal).include == {'census-uhc': True}
    services.update(user, deal.id, {'include': {'census-uhc': None, 'census-angle-csv': True}})
    assert RfpRequest.objects.get(deal=deal).include == {'census-angle-csv': True}
    RfpRequest.objects.filter(deal=deal).update(include={'census-angle-csv': True, 'doc-99': True})
    services.update(user, deal.id, {'include': {'census-warner': False}})
    assert RfpRequest.objects.get(deal=deal).include == {'census-angle-csv': True, 'census-warner': False}
    services.update(user, deal.id, {'include': 'reset'})
    assert RfpRequest.objects.get(deal=deal).include == {}


def test_K35_a_bad_tick_answers_400_by_field(user, deal):
    for bad in ({'census-cigna': True}, {'census-uhc': 'yes'}, [], {}, 'all'):
        with pytest.raises(ValidationError) as refused:
            services.update(user, deal.id, {'include': bad})
        assert 'include' in refused.value.detail


def test_K10_a_tick_takes_the_packet_cards_mark_off_and_undo_restores_both(user, deal):
    services.set_done(user, deal.id, 'packet', True)
    written = services.update(user, deal.id, {'include': {'census-uhc': False}})
    assert written.cleared == ['packet']
    row = RfpRequest.objects.get(deal=deal)
    assert 'packet' not in row.done and row.include == {'census-uhc': False}
    activity.revert(written.activity.id, user)
    row.refresh_from_db()
    assert row.include == {} and 'packet' in row.done


def test_K124_required_columns_is_empty_on_an_untouched_deal_and_reads_no_census(deal):
    assert required.carrier_required(deal.id) == {}
    with CaptureQueriesContext(connection) as queries:
        found = required.required_columns(request(carriers=['unitedhealthcare']), ['medical'])
    assert queries.captured_queries == []
    assert found['employment_status'] == {'employee': ['UnitedHealthcare'], 'dependent': []}
    assert found['dob']['dependent'] == ['UnitedHealthcare']
    assert 'dental_tier' not in found  # UHC's dental column is not required


def test_K124_the_scope_follows_the_picks_the_other_carriers_and_the_ticks():
    found = required.required_columns(request(carriers=['cigna'], other_carriers='Oscar'), ['medical'])
    assert found['first_name']['employee'] == ['Cigna', 'Other carriers']
    assert required.required_columns(request(carriers=['aetna'], include={'census-aetna': False}), []) == {}
    by_hand = required.required_columns(request(include={'census-uhc': True}), ['medical'])
    assert by_hand['employment_status']['employee'] == ['UnitedHealthcare']
    not_quoted = required.required_columns(request(carriers=['aetna']), ['dental'])
    assert 'medical_tier' not in not_quoted


def test_K124_census_marks_a_picked_carriers_blanks_once_the_pick_commits(
    user, deal, django_capture_on_commit_callbacks
):
    family(user, deal)
    assert census_providers.carrier_required(deal.id) == {}
    before = census_facts.stored(deal.id)
    assert 'employment_status' not in before['missing']
    with django_capture_on_commit_callbacks(execute=True):
        services.update(user, deal.id, {'carriers': {'add': ['unitedhealthcare']}})
    assert census_providers.carrier_required(deal.id)['employment_status']['employee'] == ['UnitedHealthcare']
    after = census_facts.stored(deal.id)
    assert census_facts.differences(deal.id) == {}  # Q.3 #9: the stored counts equal a rebuild
    assert after['required_total'] > before['required_total']
    with django_capture_on_commit_callbacks(execute=True):
        activity.revert(Activity.objects.filter(deal=deal, area='rfp').latest('id').id, user)
    assert census_facts.differences(deal.id) == {}
    assert census_facts.stored(deal.id)['required_total'] == before['required_total']


def test_K34_the_page_and_a_tick_answer_the_packets_census_rows(api, user, deal):
    family(user, deal)
    page = api.get(f'/api/deals/{deal.id}/rfp/').json()

    def census_in(packet):  # the census section; the request form rides too since slice 46
        return sum(1 for row in packet['rows'] if row['section'] == 'census' and row['include'])

    assert census_in(page['packet']) == 4 and page['packet']['rows'][0]['rows'] == 4
    answer = api.patch(f'/api/deals/{deal.id}/rfp/', {'include': {'census-angle-csv': True}}, format='json').json()
    assert answer['changed'] == {'include': {'census-angle-csv': True}}
    assert census_in(answer['packet']) == 5 and answer['packet']['count'] == page['packet']['count'] + 1
    assert api.patch(f'/api/deals/{deal.id}/rfp/', {'include': {'x': 1}}, format='json').status_code == 400
