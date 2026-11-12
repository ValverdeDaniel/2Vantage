"""The proposal preview of golden deal 1 (plan.md §12.6). The deal comes from the root conftest's `gd1` fixture."""

import pytest

pytestmark = pytest.mark.django_db


def test_the_golden_proposal_preview(api, gd1):
    deal, refs = gd1.deal, gd1.refs
    body = api.get(f'/api/deals/{deal.id}/proposal/').json()
    assert body['issue_blockers'] == [] and body['can_issue'] is True
    medical = next(line for line in body['lines'] if line['line'] == 'medical')
    columns = [c['plan_id'] for c in medical['preview']['columns']]
    # The current plans first, then each one's quotes (F120); a starred line prints a renewal only when it is picked:
    # C2 is recommended, A2 and B2 are not (OQ11).
    assert columns[:4] == [refs['A'], refs['B'], refs['C'], refs['CG1']]
    assert refs['C2'] in columns and refs['A2'] not in columns and refs['B2'] not in columns
    labels = [row['label'] for row in medical['preview']['design_rows']]
    assert 'Meets minimum value (ACA) · Medicare Part D creditable' in labels
    assert not any('Mental Health' in label for label in labels)
    packages = {row['label'] for row in medical['preview']['packages']}
    assert {'Current', 'UHC consolidated', 'Cigna dual choice'} <= packages
    groups = {g['current']: g for g in medical['preview']['summary']['groups']}
    assert len(groups['Open Access HDHP 3300']['options']) == 2  # two options recommended for one plan
