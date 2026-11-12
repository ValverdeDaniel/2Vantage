"""The executive summary's two quotes-math blocks on GD5 (plan.md §8.14; J64, F107; slice 36): a level-funded medical
plan's "% to claims" and a stop-loss contract's maximum annual liability with its change, from the facts
`summary_read` gives the summary (GD5's hand-worked key)."""

import pytest

from proposals import summary_read
from proposals.summary_blocks import design
from quotes import selectors

pytestmark = pytest.mark.django_db


def _line(key, entry):
    return {'key': key, 'label': key, 'state': 'shopped', 'picks': [entry], 'currents': [], 'options': [entry]}


def test_F107_J64_GD5_the_recommended_level_funded_plan_says_how_much_funds_claims(gd5, golden_keys):
    deal, refs, _ = gd5
    add = summary_read._verdicts('medical', selectors.line_state(deal, 'medical'))
    entry = add({'id': refs['LF-A'], 'words': 'Cigna · LocalPlus Level Funded 2500'})
    assert entry['lf_split'] == golden_keys['GD5']['lf_split']['LF-A'] and entry['stop_loss'] is None
    body = design.lf_claims_pct({'lines': [_line('medical', entry)]}, 'medical')
    assert body['value_label'] == '71.0% to claims'


def test_J64_GD5_the_recommended_stop_loss_contract_shows_its_maximum_annual_liability(gd5):
    deal, refs, _ = gd5
    add = summary_read._verdicts('stop_loss', selectors.line_state(deal, 'stop_loss'))
    entry = add({'id': refs['SL-B'], 'words': 'HM Insurance Group · Stop-Loss Select 50K'})
    assert entry['stop_loss'] == {'max_annual_liability': 736976, 'vs_current': -67957}  # 804,932.80 − 736,976
    assert add({'id': refs['SL-C'], 'words': 'Symetra'})['stop_loss']['vs_current'] is None
    body = design.stop_loss_mal({'lines': [_line('stop_loss', entry)]}, 'stop_loss')
    assert (body['value'], body['delta']) == (736976, -67957)
