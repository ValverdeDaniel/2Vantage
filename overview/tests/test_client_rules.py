"""The client page's pure rules (overview/client_rules.py; plan.md §8.5; CL14, CL18, G116): the deals' order, the deal
in flight, the Effective tile, a deal's sale and the History chips. No database."""

from datetime import date, datetime, timedelta
from types import SimpleNamespace

from overview import client_rules

TODAY = date(2026, 11, 12)


def deal(pk, effective=None, stage='intake', created=datetime(2026, 1, 5)):
    return SimpleNamespace(id=pk, effective_date=effective, stage=stage, created_at=created)


def test_CL14_deals_run_newest_first_by_effective_date_undated_last_then_by_id():
    rows = [deal(1, date(2025, 1, 1)), deal(2), deal(3, date(2027, 1, 1)), deal(4, date(2027, 1, 1))]
    assert [row.id for row in client_rules.newest_first(rows)] == [4, 3, 1, 2]


def test_CL19_the_deal_in_flight_is_the_newest_not_lost_and_not_a_year_past():
    lost = deal(5, date(2027, 1, 1), stage='lost')
    stale = deal(4, TODAY - timedelta(days=400))
    live = deal(3, TODAY - timedelta(days=30), stage='sold')
    assert client_rules.current_deal([lost, live, stale], TODAY) is live
    assert client_rules.current_deal([lost, stale], TODAY) is None


def test_CL18_the_effective_tile_counts_days_to_or_since():
    assert client_rules.effective(TODAY + timedelta(days=50), TODAY) == {'date': TODAY + timedelta(days=50), 'days': 50}
    assert client_rules.effective(TODAY - timedelta(days=3), TODAY)['days'] == -3
    assert client_rules.effective(None, TODAY) is None


def test_CL14_a_deals_year_is_its_effective_dates_else_the_year_it_was_made():
    assert client_rules.year_of(deal(1, date(2027, 4, 1))) == 2027
    assert client_rules.year_of(deal(1)) == 2026


def test_CL22_a_sale_names_each_carrier_once_and_its_newest_moment():
    early, late = datetime(2026, 11, 1, 9), datetime(2026, 11, 2, 9)
    plans = [
        SimpleNamespace(sold=True, carrier='Cigna', sold_at=early),
        SimpleNamespace(sold=False, carrier='Aetna', sold_at=None),
        SimpleNamespace(sold=True, carrier='Cigna', sold_at=late),
    ]
    assert client_rules.sold_of(plans) == {'carriers': ['Cigna'], 'at': late}
    assert client_rules.sold_of(plans[1:2]) is None


def test_G116_form_chips_list_armed_and_started_forms_with_their_kind_and_signature():
    found = client_rules.form_chips(
        {'fl_blue_51': True},
        {'siia_stop_loss', 'gone_form'},
        {'fl_blue_51': 'Florida Blue 51+', 'siia_stop_loss': 'SIIA'},
        {'fl_blue_51': 'medical', 'siia_stop_loss': 'stop_loss'},
    )
    assert [(row['key'], row['chip'], row['signed'], row['started']) for row in found] == [
        ('fl_blue_51', 'Questionnaire', True, False),
        ('siia_stop_loss', 'Stop-loss', False, True),
    ]


def test_G116_a_chip_shows_only_with_something_behind_it():
    empty = client_rules.chips({'answered': 0, 'needed': 9}, {'employees': 0}, [], 0)
    assert empty == {'intake': None, 'census': None, 'forms': [], 'documents': 0}
    full = client_rules.chips({'answered': 3, 'needed': 9}, {'employees': 60, 'dependents': 12}, [], 2)
    assert full['intake'] == {'answered': 3, 'needed': 9}
    assert full['census'] == {'employees': 60, 'dependents': 12} and full['documents'] == 2
