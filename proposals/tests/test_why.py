"""`why_for` (plan.md §8.14; J57, J.5 B7; Q.9 row 26): one rule for the words under a line's recommendation. Pure."""

import pytest

from proposals.why import why_for


@pytest.mark.parametrize(
    ('config', 'line', 'words'),
    [
        (
            {'reasons': {'medical': 'Same doctors, lower premium.'}, 'recommendation': 'Deal-wide'},
            'medical',
            'Same doctors, lower premium.',
        ),
        ({'reasons': {'medical': 'Same doctors, lower premium.'}, 'recommendation': 'Deal-wide'}, 'dental', ''),
        ({'recommendation': '  Move everything to Cigna.  '}, 'dental', 'Move everything to Cigna.'),
        ({'reasons': {'medical': '   '}, 'recommendation': 'Deal-wide'}, 'medical', 'Deal-wide'),
        ({}, 'vision', ''),
    ],
)
def test_J57_a_lines_own_words_else_the_deal_wide_words_only_when_no_line_has_any(config, line, words):
    assert why_for(config, line) == words
