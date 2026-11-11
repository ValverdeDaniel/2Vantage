"""The golden deals against their answer keys (plan.md §12.6). The keys were computed independently of the app."""

import json
from pathlib import Path

import pytest

from proposals import golden, golden_data
from quotes import selectors

KEYS = json.loads((Path(__file__).parent / 'golden' / 'answer_keys.json').read_text(encoding='utf-8'))


@pytest.fixture
def built(user):
    return {deal.client.name: (deal, refs) for deal, refs in golden.build_all(user)}


@pytest.mark.parametrize('spec', golden_data.DEALS, ids=lambda s: s['client'])
def test_every_plan_matches_the_key(built, spec):
    deal, refs = built[spec['client']]
    key = KEYS[spec['client']]
    for line in spec['lines']:
        _, _, results, _, _ = selectors.line_state(deal, line)
        for ref, *_ in [p for p in spec['plans'] if p[1] == line]:
            expected, got = key['plans'][ref], results[refs[ref]]
            assert (got['monthly'], got['annual'], got['change']) == (
                expected['monthly'],
                expected['annual'],
                expected['change'],
            ), ref


@pytest.mark.parametrize('spec', golden_data.DEALS, ids=lambda s: s['client'])
def test_every_package_and_recommendation_matches_the_key(built, spec):
    deal, _ = built[spec['client']]
    key = KEYS[spec['client']]
    for line in spec['lines']:
        _, _, _, packages, recommendation = selectors.line_state(deal, line)
        shown = {p['label']: p for p in packages}
        for label, expected in key['packages'][line].items():
            assert label in shown, label
            got = shown[label]
            assert (got['annual'], got['same_people'], got['change']) == (
                expected['annual'],
                expected['same_people'],
                expected['change'],
            ), label
        offered_automatically = {p['label'] for p in packages if p['key'].startswith('carrier:')}
        expected_carriers = set(key['packages'][line]) - {'Current', 'Renewal'} - {p[1] for p in spec['packages']}
        assert offered_automatically == expected_carriers
        assert recommendation['covered'] == key['recommendation'][line]['covered']


def test_the_golden_proposal_preview(api, built):
    deal, refs = built['Golden Manufacturing (synthetic)']
    body = api.get(f'/api/deals/{deal.id}/proposal/').json()
    assert body['issue_blockers'] == [] and body['can_issue'] is True
    medical = next(line for line in body['lines'] if line['line'] == 'medical')
    columns = [c['plan_id'] for c in medical['preview']['columns']]
    # Each current plan then its renewal, before any alternate.
    assert columns[:6] == [refs['A'], refs['A2'], refs['B'], refs['B2'], refs['C'], refs['C2']]
    labels = [row['label'] for row in medical['preview']['design_rows']]
    assert 'Meets minimum value (ACA) · Medicare Part D creditable' in labels
    assert not any('Mental Health' in label for label in labels)
    packages = {row['label'] for row in medical['preview']['packages']}
    assert {'Current', 'Renewal — average increase', 'UHC consolidated', 'Cigna dual choice'} <= packages
    groups = {g['current']: g for g in medical['preview']['summary']['groups']}
    assert len(groups['Open Access HDHP 3300']['options']) == 2  # two options recommended for one plan
