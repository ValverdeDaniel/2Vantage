"""The golden deals against their answer keys (plan.md §12.6, Q.4), which were worked out apart from the app."""

import pytest

from quotes import selectors

pytestmark = pytest.mark.django_db

DEALS = ['GD1', 'GD2']


@pytest.mark.parametrize('key', DEALS)
def test_PAR1_every_plan_matches_the_key(golden, golden_keys, key):
    deal, refs, spec = golden[key]
    figures = golden_keys[key]
    for line in spec['lines']:
        _, _, results, _, _ = selectors.line_state(deal, line)
        for plan in (p for p in spec['plans'] if p['line'] == line):
            expected, got = figures['plans'][plan['ref']], results[refs[plan['ref']]]
            assert (got['monthly'], got['annual'], got['change']) == (
                expected['monthly'],
                expected['annual'],
                expected['change'],
            ), plan['ref']


@pytest.mark.parametrize('key', DEALS)
def test_PAR1_every_package_and_recommendation_matches_the_key(golden, golden_keys, key):
    deal, _, spec = golden[key]
    figures = golden_keys[key]
    for line in spec['lines']:
        _, _, _, packages, recommendation = selectors.line_state(deal, line)
        shown = {p['label']: p for p in packages}
        for label, expected in figures['packages'][line].items():
            assert label in shown, label
            got = shown[label]
            assert (got['annual'], got['same_people'], got['change']) == (
                expected['annual'],
                expected['same_people'],
                expected['change'],
            ), label
        offered_automatically = {p['label'] for p in packages if p['key'].startswith('carrier:')}
        member_built = {p['name'] for p in spec['packages']}
        expected_carriers = set(figures['packages'][line]) - {'Current', 'Renewal'} - member_built
        assert offered_automatically == expected_carriers
        assert recommendation['covered'] == figures['recommendation'][line]['covered']


@pytest.mark.parametrize('key', DEALS)
def test_PAR1_every_key_carries_its_signature_fields(golden_keys, key):
    figures = golden_keys[key]
    assert {'checked_by', 'checked_on', 'method'} <= set(figures)
    if figures['checked_by'] is not None:  # a signed key names who, when and how
        assert figures['checked_on'] and figures['method']
