"""One spec loads the same deal into 2Vantage, read back through the API; the fixtures build each deal once (Q.9 row 3).

The old app's half is the parity harness: tools/parity/old_loader.py reads the same spec file (plan.md §12.7).
"""

import pytest

from deals.models import Client
from quotes.services import clean_values

pytestmark = pytest.mark.django_db

DEALS = ['GD1', 'GD2', 'GD3', 'GD4']


def _links(row, names):
    if row['renews_id']:
        return [names[row['renews_id']]]
    return sorted(names[pid] for pid in row['replaces_ids'])


@pytest.mark.parametrize('key', DEALS)
def test_PAR1_one_spec_loads_the_deal_into_2vantage(golden, api, key):
    deal, refs, spec = golden[key]
    names = {plan_id: ref for ref, plan_id in refs.items()}
    header = api.get(f'/api/deals/{deal.id}/').json()
    assert header['client']['name'] == spec['client']
    assert header['effective_date'] == spec['effective_date']
    assert sorted(header['requested_lines']) == sorted(spec['lines'])
    for line in spec['lines']:
        body = api.get(f'/api/deals/{deal.id}/plans/', {'line': line}).json()
        got = {names[row['id']]: row for row in body['plans']}
        wanted = [plan for plan in spec['plans'] if plan['line'] == line]
        assert set(got) == {plan['ref'] for plan in wanted}
        for plan in wanted:
            row = got[plan['ref']]
            assert (row['role'], row['carrier'], row['name']) == (plan['role'], plan['carrier'], plan['name'])
            assert _links(row, names) == sorted(plan['links']), plan['ref']
            assert row['values'] == clean_values(line, plan['values']), plan['ref']
            assert (row['enrollment'] or None) == plan.get('enrollment'), plan['ref']
            assert row['starred'] == (plan['ref'] in spec['starred']), plan['ref']
            assert row['recommended'] == (plan['ref'] in spec['recommended']), plan['ref']
        assert body['enrollment']['figure'] == spec.get('line_enrollment', {}).get(line)  # the whole-line figure
        built = {p['name']: sorted(names[pid] for pid in p['plan_ids']) for p in body['member_packages']}
        assert built == {p['name']: sorted(p['plans']) for p in spec['packages'] if p['line'] == line}
    assert api.get(f'/api/deals/{deal.id}/proposal/').json()['config'].get('reasons', {}) == spec['reasons']


FIRST_SEEN = {}


@pytest.mark.parametrize('turn', ['first', 'second'])
def test_PAR1_the_fixtures_build_each_deal_once_per_module(golden, turn):
    for key, built in golden.items():
        assert Client.objects.filter(name=built.spec['client']).count() == 1, key
        seen = FIRST_SEEN.setdefault(key, (built.deal.id, built.deal.created_at))
        assert (built.deal.id, built.deal.created_at) == seen, key
