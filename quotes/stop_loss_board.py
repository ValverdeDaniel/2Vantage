"""The stop-loss analysis's lists and words (plan.md §8.14; F98–F105, F29; the old StopLossAnalysis.jsx and
advisor_filters.RANK_KEYS at 891f1b3). A data module: served by `/api/meta/` under `stop_loss`, so the board never
hard-codes them (rule 1), and read by `board.clean_config` for the saved settings (F29).

- `RANK_KEYS`: what the verdict may be ranked on; every one is "lower is better", so there is no direction (F100).
- `TERMS`: the contract-term rows, read off the plan's own values (F99), in the old board's order and words.
- `SETTINGS`: the four saveable controls and their defaults (F102, F29): Rank by, PEPM or Annual only, Contract
  terms, Hide options we can't score. Reset lasers is not a setting: the what-if is never saved (F104).
- `BASIS_WORDS`: where the analysis's enrolled employees come from (F98): the basis names its source.
"""

from .math import enrollment
from .math.stop_loss import MONTHS

LINE = 'stop_loss'
VIEW = 'stop-loss'

RANK_KEYS = [
    ('max_annual_liability', 'Maximum annual liability'),
    ('annual_premium', 'Annual SL premium'),
    ('projected_cost', 'Projected cost'),
    ('laser_liability', 'Laser liability'),
    ('spec_deductible', 'Specific deductible'),
]
RANK_KEY_SET = tuple(key for key, _ in RANK_KEYS)

TERMS = [
    ('tpa_name', 'TPA'),
    ('tpa_rate_guarantee', 'TPA rate guarantee'),
    ('sl_contract_basis', 'Contract basis (incurred/paid)'),
    ('sl_run_in_months', 'Run-in period (months)'),
    ('sl_run_in_limit', 'Run-in dollar limit'),
    ('sl_run_out_months', 'Run-out / paid window (months)'),
    ('sl_tlo', 'TLO included / terms'),
    ('sl_collateral', 'Collateral / captive fees (annual)'),
]
TERM_KEYS = tuple(key for key, _ in TERMS)

SETTINGS = {
    'rank_by': 'max_annual_liability',
    'annual_mode': False,
    'show_terms': True,  # on by default, so a saved setting that leaves it out never collapses the table
    'hide_unscored': False,
}

BASIS_WORDS = {
    'typed': 'Typed on the in-force contract',
    enrollment.LINE: 'Typed for the whole Stop-Loss line',
    enrollment.MEDICAL: 'From medical enrollment',
    enrollment.CENSUS: 'From the census',
}
MIXED_BASIS = "Summed from the in-force contracts' own enrollment"


def basis_words(source):
    if source in BASIS_WORDS:
        return BASIS_WORDS[source]
    return enrollment.SOURCES.get(source, {}).get('label') or MIXED_BASIS


def meta():
    """/api/meta/ `stop_loss`: the rank keys, the term rows and the controls' defaults."""
    return {
        'line': LINE,
        'view': VIEW,
        'rank_keys': [{'key': key, 'label': label} for key, label in RANK_KEYS],
        'terms': [{'key': key, 'label': label} for key, label in TERMS],
        'settings': dict(SETTINGS),
        'months': MONTHS,
    }
