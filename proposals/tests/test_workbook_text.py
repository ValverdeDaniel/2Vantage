"""What a cell of the client spreadsheet shows, as Excel shows it (plan.md §9.4; J116; old `workbook_text` at 891f1b3,
D-194): every number format the file may carry, drawn as Excel draws it. Pure table cases."""

import pytest

from proposals.workbook import styles as s
from proposals.workbook import text as t

RED, GREEN = '#FF0000', '#008000'


@pytest.mark.parametrize(
    ('value', 'fmt', 'shown', 'colour', 'pad'),
    [
        (1234.5, s.MONEY_WHOLE, '$1,235', None, ')'),
        (-1234.5, s.MONEY_WHOLE, '($1,235)', RED, ''),
        (0, s.MONEY_WHOLE, '$0', None, ')'),
        (612.5, s.MONEY_CENTS, '$612.50', None, ')'),
        (612.125, s.MONEY_CENTS, '$612.13', None, ')'),  # half up, as Excel rounds what it shows
        (14.105, s.RATE_3DP, '$14.105', None, ')'),
        (0.4512, s.RATE_4DP, '$0.4512', None, ')'),
        (612.5, s.RATE_FLEX, '$612.50', None, ')'),
        (612.1234, s.RATE_FLEX, '$612.1234', None, ')'),
        (0.25, s.PCT, '25%', None, ''),
        (0.0417, s.PCT_1DP, '4.2%', None, ''),
        (0.0417, s.CHANGE, '+4.2%', RED, ''),
        (-0.05, s.CHANGE, '-5.0%', GREEN, ''),
        (0, s.CHANGE, '0.0%', None, ''),
        (0.0417, s.CHANGE_EE_ONLY, 'EE Only: +4.2%', RED, ''),
        (-0.031, s.CHANGE_TOTAL, 'Total: -3.1%', GREEN, ''),
        (1500, s.CHANGE_MONEY, '+$1,500', RED, ''),
        (-508, s.CHANGE_MONEY, '-$508', GREEN, ''),
        (24, s.COUNT, '24', None, ''),
        (1234567.891, s.GENERAL, '1234567.891', None, ''),
        (0.1 + 0.2, s.GENERAL, '0.3', None, ''),
        ('=not a formula', s.TEXT, '=not a formula', None, ''),
        (None, s.MONEY_WHOLE, '', None, ''),
        ('', s.MONEY_WHOLE, '', None, ''),
    ],
)
def test_J116_a_value_reads_as_its_number_format_shows_it(value, fmt, shown, colour, pad):
    assert t.display(value, fmt) == (shown, colour, pad)


def test_J116_every_format_the_file_carries_is_one_the_viewer_draws():
    for fmt in s.NUMBER_FORMATS:
        assert t.display(1.5, fmt)[0]
        assert t.display(-1.5, fmt)[0]


def test_J116_general_gives_up_decimals_before_the_number():
    assert t.general(3.14159265358979, 11) == '3.141592654'
    assert t.general(3.14159265358979, 4) == '3.14'
    assert t.general(123456789012345.0) == '1.23457E+14'


def test_J118_a_wider_number_needs_more_pixels_and_hashes_fill_the_cell():
    assert t.text_px('$1,234,567') > t.text_px('$1,234')
    assert t.text_px('Total', bold=True) > t.text_px('Total')
    assert not t.number_fits('$1,234,567', ')', 40)
    assert t.number_fits('$1', ')', 40)
    assert set(t.hashes(40)) == {'#'}
    assert len(t.hashes(80)) > len(t.hashes(40))


def test_J118_wrapped_text_counts_its_lines():
    assert t.wrapped_lines('short', 200) == 1
    assert t.wrapped_lines('one\ntwo\nthree', 200) == 3
    assert t.wrapped_lines(' '.join(['word'] * 40), 100) > 3
    assert t.line_pt(11) == 14.25
