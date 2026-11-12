"""Which enrollment prices a plan: every `enrollment_for` step, the census-arrival rule both ways, the switch, borrowing
and stop-loss lives, and §5.5's enrollment examples (plan.md §5.5, O.6 #24; F86–F92, F98; OQ18–OQ20; Q.9 row 13).
Pure: `PlanData` and `LineData` with their `People`, no database."""

from datetime import UTC, datetime
from decimal import Decimal as D

import pytest

from quotes import math as m
from quotes import packages as pk
from quotes.math import by_plan
from quotes.shapes import LineData, People, PlanData

NOV = {day: datetime(2026, 11, day, 12, tzinfo=UTC) for day in range(1, 30)}
FIGURE = {'EE': 20, 'ES': 5, 'EC': 3, 'FAM': 2}


def tiers(ee, es, ec, fam):
    return {'EE': D(ee), 'ES': D(es), 'EC': D(ec), 'FAM': D(fam)}


def plan(pid, role='alternate', counts=None, **kw):
    return PlanData(id=pid, role=role, enrollment=counts or {}, values={'rate_ee': '500'}, **kw)


def census(by_plan_counts=None, tiers_=(0, 0, 0, 0), source='census'):
    ee, es, ec, fam = tiers_
    out = {'EE': ee, 'ES': es, 'EC': ec, 'FAM': fam, 'enrolled': ee + es + ec + fam, 'source': source}
    if by_plan_counts is not None:
        out['by_plan'] = {
            text: {'EE': c[0], 'ES': c[1], 'EC': c[2], 'FAM': c[3], 'waived': 0, 'blank': 0}
            for text, c in by_plan_counts.items()
        }
    return out


def line(plans, key='medical', basis='composite', **people):
    return LineData(basis, plans, key=key, people=People(**people))


def got(p, data):
    return m.enrollment_for(p, data)


# ---- §5.5's enrollment examples (each MUST be a unit test) ----------------------------------------------------------


def test_5_5_quote_first_line_every_alternate_prices_the_line_figure():
    quotes = [plan(i) for i in range(1, 11)]
    data = line(quotes, figure=FIGURE)
    assert all(got(p, data) == (tiers(20, 5, 3, 2), 'line') for p in quotes)


def test_F88_a_current_plan_arriving_takes_no_price_away():
    d = plan(1, 'current')
    quotes = [plan(i) for i in range(2, 12)]
    data = line([d, *quotes], figure=FIGURE)
    assert got(d, data) == (tiers(20, 5, 3, 2), 'line')
    assert all(got(p, data) == (tiers(20, 5, 3, 2), 'line') for p in quotes)


def test_F88_OQ20_a_second_current_plan_stops_the_line_figure_and_unlinked_quotes_ask_what_they_replace():
    d, f = plan(1, 'current'), plan(2, 'current')
    linked, unlinked = plan(3, replaces=(1,)), plan(4)
    data = line([d, f, linked, unlinked], figure=FIGURE)
    assert {got(p, data) for p in (d, f, linked, unlinked)} == {(None, 'per_plan_counts_needed')}


def test_F88_the_split_prices_each_current_plan_and_the_quote_linked_to_one():
    d, f = (
        plan(1, 'current', {'EE': 12, 'ES': 3, 'EC': 2, 'FAM': 1}),
        plan(2, 'current', {'EE': 8, 'ES': 2, 'EC': 1, 'FAM': 1}),
    )
    e = plan(3, replaces=(1,))
    data = line([d, f, e], figure=FIGURE)
    assert got(d, data) == (tiers(12, 3, 2, 1), 'typed')
    assert got(f, data) == (tiers(8, 2, 1, 1), 'typed')
    assert got(e, data) == (tiers(12, 3, 2, 1), 'from replaced plan')


def test_F87_a_priced_version_prices_its_originals_people():
    d = plan(1, 'current', {'EE': 12, 'ES': 3, 'EC': 2, 'FAM': 1})
    e, version = plan(2, replaces=(1,)), plan(3, replaces=(1,), version_of=2)
    data = line([d, e, version])
    assert got(version, data) == (tiers(12, 3, 2, 1), 'from original plan')


# Typed before / after the deal's one census import: the count of applied imports decides (F91), the stamps only show.
BEFORE = {'typed_at': NOV[2], 'imported_at': NOV[5], 'census_seen': 0, 'imports': 1}
AFTER = {'typed_at': NOV[6], 'imported_at': NOV[5], 'census_seen': 1, 'imports': 1}


def split_line(when, **extra):
    d = plan(1, 'current', {'EE': 12, 'ES': 3, 'EC': 2, 'FAM': 1}, name='HMO 1500')
    f = plan(2, 'current', {'EE': 8, 'ES': 2, 'EC': 1, 'FAM': 1}, name='PPO 2500')
    e = plan(3, replaces=(1,))
    counts = census({'HMO 1500': (10, 3, 2, 2), 'PPO 2500': (9, 2, 2, 1), '': (0, 0, 0, 0)}, (19, 5, 4, 3))
    data = line([d, f, e], census=counts, **when, **extra)
    return d, f, e, data


def test_F91_counts_typed_before_the_latest_import_give_way_to_the_census():
    d, f, e, data = split_line(BEFORE)
    assert got(d, data) == (tiers(10, 3, 2, 2), 'census')
    assert got(f, data) == (tiers(9, 2, 2, 1), 'census')
    assert got(e, data) == (tiers(10, 3, 2, 2), 'census')  # the census counts of the plan it replaces
    assert [m.gave_way(p, data) for p in (d, f, e)] == [True, True, True]


def test_F91_counts_typed_after_the_import_win():
    d, f, e, data = split_line(AFTER)
    assert got(d, data) == (tiers(12, 3, 2, 1), 'typed')
    assert got(e, data) == (tiers(12, 3, 2, 1), 'from replaced plan')
    assert not any(m.gave_way(p, data) for p in (d, f, e))


def test_F91_typed_counts_stay_where_the_census_cannot_price_the_plan():
    d, f, e, _ = split_line(BEFORE)
    counts = census({'HMO 1500': (10, 3, 2, 2), 'Someone else': (9, 2, 2, 1)}, (19, 5, 4, 3))  # a text no plan has
    data = line([d, f, e], census=counts, **BEFORE)
    assert got(d, data) == (tiers(12, 3, 2, 1), 'typed')
    assert not m.gave_way(d, data)


def test_F91_a_line_figure_typed_before_the_import_gives_way_to_the_line_census():
    quotes = [plan(1), plan(2)]
    data = line(quotes, figure=FIGURE, census=census(tiers_=(18, 4, 4, 2)), **BEFORE)
    assert got(quotes[0], data) == (tiers(18, 4, 4, 2), 'census')
    assert m.gave_way(quotes[0], data)
    later = line(quotes, figure=FIGURE, census=census(tiers_=(18, 4, 4, 2)), **AFTER)
    assert got(quotes[0], later) == (tiers(20, 5, 3, 2), 'line')


@pytest.mark.parametrize(
    'typed_at, imported_at',
    [(NOV[5], NOV[5]), (NOV[6], NOV[5]), (NOV[2], NOV[5])],
    ids=['same instant', 'clock stepped back before the import', 'clock in order'],
)
def test_F91_the_count_of_imports_orders_a_save_and_an_import_whatever_the_clock_says(typed_at, imported_at):
    stamps = {'typed_at': typed_at, 'imported_at': imported_at}
    d, _f, _e, before = split_line({**stamps, 'census_seen': 1, 'imports': 2})  # an import came after the save
    assert got(d, before) == (tiers(10, 3, 2, 2), 'census') and m.gave_way(d, before)
    d, _f, _e, after = split_line({**stamps, 'census_seen': 2, 'imports': 2})  # saved after the latest import
    assert got(d, after) == (tiers(12, 3, 2, 1), 'typed') and not m.gave_way(d, after)


def test_F91_counts_never_saved_since_an_import_are_older_than_it_and_no_import_means_no_census_takeover():
    d, _f, _e, never = split_line({'imports': 1, 'census_seen': None})
    assert got(d, never)[1] == 'census'
    d, _f, _e, none = split_line({'imports': 0, 'census_seen': None})
    assert got(d, none)[1] == 'typed'


def test_F88_the_switch_off_prices_every_plan_from_the_census_and_keeps_the_counts():
    d, f, e, data = split_line(AFTER, on=False)
    assert got(d, data) == (tiers(10, 3, 2, 2), 'census')
    assert d.enrollment == {'EE': 12, 'ES': 3, 'EC': 2, 'FAM': 1}
    nothing = line([plan(1)], figure=FIGURE, on=False)
    assert got(nothing.plans[0], nothing) == (None, 'no_enrollment')


def test_F90_census_by_plan_waits_until_every_enrolled_text_is_matched_then_counts_hand_matches():
    d = plan(1, 'current', name='HMO 1500')
    f = plan(2, 'current', name='PPO 2500', plan_number='FB-77')
    counts = census({'HMO 1500': (10, 3, 2, 2), 'fb-77': (6, 1, 1, 0), 'PPO 2500 (old rates)': (3, 1, 1, 1)})
    data = line([d, f], census=counts)
    rows = {row['text']: (row['plan_id'], row['how']) for row in by_plan.matched(data)}
    assert rows == {'HMO 1500': (1, 'name'), 'fb-77': (2, 'number'), 'PPO 2500 (old rates)': (None, None)}
    assert got(d, data) == (None, 'per_plan_counts_needed')
    f.census_names = ('PPO 2500 (old rates)',)
    data = line([d, f], census=counts)
    assert got(f, data) == (tiers(9, 2, 2, 1), 'census')
    assert got(d, data) == (tiers(10, 3, 2, 2), 'census')


def test_F90_waived_and_blank_texts_never_need_a_match():
    d = plan(1, 'current', name='HMO 1500')
    counts = census({'HMO 1500': (10, 3, 2, 2)})
    counts['by_plan'][''] = {'EE': 0, 'ES': 0, 'EC': 0, 'FAM': 0, 'waived': 4, 'blank': 2}
    data = line([d, plan(2, 'current', name='Other')], census=counts)
    assert got(d, data) == (tiers(10, 3, 2, 2), 'census')


def test_F86_OQ19_a_worksite_line_borrows_medicals_typed_counts():
    accident = plan(1)
    data = line([accident], key='accident', medical=(tiers(20, 5, 3, 2), 'line'))
    assert got(accident, data) == (tiers(20, 5, 3, 2), 'proxy')
    assert m.SOURCES['proxy']['label'] == 'Borrowed from medical'


def test_F86_a_worksite_line_borrows_the_medical_census_first():
    accident = plan(1)
    data = line(
        [accident],
        key='accident',
        census=census(tiers_=(17, 4, 4, 2), source='borrowed'),
        medical=(tiers(20, 5, 3, 2), 'line'),
    )
    assert got(accident, data) == (tiers(17, 4, 4, 2), 'proxy')


def test_OQ19_dental_never_borrows():
    dental = plan(1)
    data = line([dental], key='dental', medical=(tiers(20, 5, 3, 2), 'line'))
    assert got(dental, data) == (None, 'no_enrollment')


def test_F98_stop_loss_lives_are_the_medical_enrolled_employees():
    contract = PlanData(id=1, role='alternate', values={'sl_spec_rate': '85.20'})
    data = line([contract], key='stop_loss', basis='stop_loss', medical=(tiers(20, 5, 3, 2), 'typed'))
    assert got(contract, data) == ({'lives': D(30)}, 'medical')
    assert m.SOURCES['medical']['label'] == 'From medical enrollment'
    typed = PlanData(id=2, role='alternate', enrollment={'lives': 41})
    data = line([typed], key='stop_loss', basis='stop_loss', medical=(tiers(20, 5, 3, 2), 'typed'))
    assert got(typed, data) == ({'lives': D(41)}, 'typed')


def test_F98_stop_loss_lives_come_from_the_census_without_medical_people():
    contract = PlanData(id=1, role='alternate')
    data = line([contract], key='stop_loss', basis='stop_loss', census={'lives': 37, 'source': 'census'})
    assert got(contract, data) == ({'lives': D(37)}, 'census')


def test_F92_a_pepm_line_prices_from_typed_lives_and_a_volume_line_from_typed_volume():
    telehealth = PlanData(id=1, role='alternate', values={'unit_rate': '4.50'})
    data = line([telehealth], key='telehealth', basis='pepm', figure={'lives': 52})
    figures, source = got(telehealth, data)
    assert (figures, source) == ({'lives': D(52)}, 'line')
    assert m.monthly_premium(telehealth, data, figures)[0] == 234
    life = PlanData(id=2, role='alternate', enrollment={'volume': 1_250_000}, values={'unit_rate': '0.12'})
    data = line([life], key='basic_life_add', basis='volume_1000')
    assert got(life, data) == ({'volume': D(1_250_000)}, 'typed')


def test_5_5_no_enrollment_at_all():
    data = line([plan(1)])
    assert got(data.plans[0], data) == (None, 'no_enrollment')


@pytest.mark.parametrize(
    'current, figure, census_, expected',
    [
        ((tiers(12, 3, 2, 1), tiers(8, 2, 1, 1)), FIGURE, None, (tiers(20, 5, 3, 2), 'typed')),
        ((None, None), FIGURE, None, (tiers(20, 5, 3, 2), 'line')),
        ((None, None), {}, (17, 4, 4, 2), (tiers(17, 4, 4, 2), 'census')),
        ((None, None), {}, None, None),
    ],
)
def test_5_7_medical_people_are_the_current_plans_then_the_figure_then_the_census(current, figure, census_, expected):
    plans = [
        plan(i + 1, 'current', {k: int(v) for k, v in counts.items()} if counts else None)
        for i, counts in enumerate(current)
    ]
    data = line(plans, figure=figure, census=census(tiers_=census_) if census_ else None)
    assert m.people(data, pk.evaluate(data)) == expected
