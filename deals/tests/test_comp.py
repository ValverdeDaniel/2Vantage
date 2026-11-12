"""A commission's one parser and label (plan.md §4.6, §5.6; H1). Pure."""

import pytest

from deals import comp


@pytest.mark.parametrize(
    ('raw', 'stored'),
    [
        (5, {'type': 'pct', 'value': '5'}),
        ('5%', {'type': 'pct', 'value': '5'}),
        ('7.50', {'type': 'pct', 'value': '7.5'}),
        ({'type': 'flat', 'value': '$1,000,000'}, {'type': 'flat', 'value': '1000000'}),
        ({'type': 'FLAT', 'value': 12345.67}, {'type': 'flat', 'value': '12345.67'}),
        ({'type': 'pepm', 'value': '32'}, {'type': 'pepm', 'value': '32'}),
        ({'value': '4'}, {'type': 'pct', 'value': '4'}),
    ],
)
def test_H1_parse_comp_keeps_the_exact_decimal(raw, stored):
    assert comp.parse_comp(raw) == (stored, None)


@pytest.mark.parametrize(
    ('raw', 'error'),
    [
        ({'type': 'monthly', 'value': '5'}, 'Type must be percentage, flat, or PEPM'),
        ('five', 'Must be a number'),
        ('-1', 'Must not be negative'),
        ('120', 'Must be between 0 and 100'),
        ('NaN', 'Must be a number'),
        (True, 'Must be a number'),
    ],
)
def test_H1_parse_comp_refuses_in_words(raw, error):
    assert comp.parse_comp(raw) == (None, error)


def test_H1_a_blank_is_no_commission_unless_one_is_required():
    assert comp.parse_comp('') == (None, None)
    assert comp.parse_comp({'type': 'pct', 'value': ' '}) == (None, None)
    assert comp.parse_comp(None, allow_blank=False) == (None, 'Required')


@pytest.mark.parametrize(
    ('stored', 'label'),
    [
        ({'type': 'pct', 'value': '5'}, '5%'),
        ({'type': 'pct', 'value': '4.25'}, '4.25%'),
        ({'type': 'flat', 'value': '5000'}, '$5,000/yr'),
        ({'type': 'flat', 'value': '12345.6'}, '$12,345.60/yr'),
        ({'type': 'pepm', 'value': '32'}, '$32 PEPM'),
        ({'type': 'pepm', 'value': '32.5'}, '$32.50 PEPM'),
        ({}, ''),
        (None, ''),
    ],
)
def test_H1_comp_label(stored, label):
    assert comp.comp_label(stored) == label
