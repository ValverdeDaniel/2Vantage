"""The Overview's pure rules (overview/rules.py; M13–M37 of slice 62), table by table. Synthetic values only."""

from datetime import UTC, date, datetime

import pytest

from deals import lifecycle
from overview import rules


@pytest.mark.parametrize(
    ('created', 'today', 'days'),
    [
        (date(2026, 11, 1), date(2026, 11, 12), 11),
        (date(2026, 11, 12), date(2026, 11, 12), 0),
        (date(2026, 11, 13), date(2026, 11, 12), 0),  # a clock a step behind never reads "Open -1 days"
        (None, date(2026, 11, 12), None),
    ],
)
def test_M16_open_days_count_whole_days_never_below_zero(created, today, days):
    assert rules.open_days(created, today) == days


def test_M18_the_owner_is_the_deals_else_the_clients():
    assert rules.owner_of('deal owner', 'client owner') == 'deal owner'
    assert rules.owner_of(None, 'client owner') == 'client owner'
    assert rules.owner_of(None, None) is None


CLIENT = {'id': 7, 'name': 'Example Co. (synthetic)', 'client_since': None}


def moves(relationship, *, has_sold=False, lost=None):
    return lifecycle.moves(relationship, has_sold=has_sold, lost=lost)


def test_M23_CL4_a_prospects_box_offers_convert_to_client():
    box = rules.client_box({**CLIENT, 'relationship': lifecycle.PROSPECT}, moves(lifecycle.PROSPECT))
    assert box['on_book'] is False and box['convert'] == {'allowed': True, 'sentence': ''}
    assert box['name'] == CLIENT['name'] and box['id'] == CLIENT['id']


def test_M23_CL4_a_lost_deal_refuses_convert_with_the_status_doors_sentence():
    lost = 'This deal is marked lost — reopen it before converting the client.'
    box = rules.client_box({**CLIENT, 'relationship': lifecycle.PROSPECT}, moves(lifecycle.PROSPECT, lost=lost))
    assert box['convert'] == {'allowed': False, 'sentence': lost}


@pytest.mark.parametrize('relationship', [lifecycle.NEW_CLIENT, lifecycle.EXISTING_CLIENT])
def test_M21_a_client_is_on_the_book_and_offers_no_convert(relationship):
    box = rules.client_box({**CLIENT, 'relationship': relationship}, moves(relationship, has_sold=True))
    assert box['on_book'] is True and box['convert'] is None


@pytest.mark.parametrize(
    ('found', 'row_id', 'expected'),
    [
        (
            {'carrier': 'Example Health', 'funding': 'level_funded', 'source': 'plans'},
            None,
            {'value': 'Example Health', 'from': 'plans', 'coverage_id': None, 'editable': False},
        ),
        (
            {'carrier': 'Example Health', 'funding': '', 'source': 'coverage'},
            12,
            {'value': 'Example Health', 'from': 'coverage', 'coverage_id': 12, 'editable': True},
        ),
        (None, None, {'value': '', 'from': None, 'coverage_id': None, 'editable': True}),
    ],
)
def test_M26_the_carrier_is_read_only_while_the_current_plans_hold_it(found, row_id, expected):
    assert rules.incumbent(found, row_id, 'carrier') == expected


def test_M26_funding_reads_the_same_answer():
    found = {'carrier': 'Example Health', 'funding': 'level_funded', 'source': 'coverage'}
    assert rules.incumbent(found, 3, 'funding')['value'] == 'level_funded'


def test_M28_in_force_commission_takes_each_lines_first_in_force_row_with_a_rate():
    rows = [
        ('medical', 'Medical', True, '4%'),
        ('medical', 'Medical', True, '5%'),
        ('dental', 'Dental', False, '10%'),
        ('vision', 'Vision', True, ''),
        ('life', 'Basic Life', True, '$5,000/yr'),
    ]
    assert rules.in_force(rows) == [
        {'line': 'medical', 'label': 'Medical', 'comp_label': '4%'},
        {'line': 'life', 'label': 'Basic Life', 'comp_label': '$5,000/yr'},
    ]


@pytest.mark.parametrize(
    ('offer', 'label'),
    [
        ({'renewal_premium_annual': 13440, 'renewal_pct_change': 12}, 'Renewal offer $13,440/yr (+12.0%)'),
        ({'renewal_premium_annual': 13440.5, 'renewal_pct_change': None}, 'Renewal offer $13,441/yr'),
        ({'renewal_premium_annual': None, 'renewal_pct_change': -4.25}, 'Renewal offer (-4.3%)'),
        ({'renewal_premium_annual': None, 'renewal_pct_change': 0}, 'Renewal offer (+0.0%)'),  # flat is an answer
    ],
)
def test_M20_the_renewal_offer_chip_reads_the_letters_figures(offer, label):
    found = rules.renewal_offer({**offer, 'stated_current_premium_annual': None, 'group_number': ''})
    assert found['label'] == label
    assert (found['premium_annual'], found['pct_change']) == (
        offer['renewal_premium_annual'],
        offer['renewal_pct_change'],
    )


@pytest.mark.parametrize(
    'offer', [None, {}, {'renewal_premium_annual': None, 'renewal_pct_change': None, 'group_number': 'G-1'}]
)
def test_M20_no_letter_no_chip(offer):
    assert rules.renewal_offer(offer) is None


def at(hour):
    return datetime(2026, 11, 12, hour, tzinfo=UTC)


def test_M37_last_contact_is_the_newest_of_its_sources():
    assert rules.last_contact([at(9), None, at(14), at(11)]) == at(14)
    assert rules.last_contact([at(9).isoformat(), at(8)]) == at(9)  # review's facts carry ISO text
    assert rules.last_contact([None, None, '']) is None
