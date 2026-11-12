"""The vocabulary of priced versions (plan.md §5.4, §8.14; F76–F84; the old pricedKinds.js and concessions.py
constants), served on /api/meta/ as `board.priced`. A data module.

Three shapes of money back share one door (＋ on a plan): a **concession** (% or $ off or up, or set to, on all rates
or one rate at a time), a **bundling discount** (per placed line, naming the quote that has to sell) and a **premium
holiday** (a dollar credit a year, or free months). Only the premium moves: every kind reaches at most the line's rate
keys and the carrier's quoted group premium; a plan whose design changed is a new quote. The fourth member,
**Duplicate**, moves no money: it is a standalone copy (`copy_plan`, D-049), offered at the same door because that is
where people look (the old app's 2026-09-22 ask).
"""

from . import fields

CONCESSION, BUNDLE, HOLIDAY, DUPLICATE = 'concession', 'bundle', 'holiday', 'duplicate'
KINDS = (CONCESSION, BUNDLE, HOLIDAY)  # the priced kinds; a duplicate is a copy, not a priced version

FAMILIES = [
    {
        'key': CONCESSION,
        'label': 'Concession',
        'short': 'Concession',
        'glyph': '%',
        'hint': 'A negotiated change to the carrier’s rates — % or $, up or down, or set to the rep’s exact number, '
        'on all rates or one at a time',
    },
    {
        'key': BUNDLE,
        'label': 'Bundling discount',
        'short': 'Bundling',
        'glyph': '⊕',
        'hint': 'What the client buys — the carrier’s discount for placing ancillary lines, priced across all of that '
        'carrier’s quotes',
    },
    {
        'key': HOLIDAY,
        'label': 'Premium holiday',
        'short': 'Holiday',
        'glyph': '$',
        'hint': 'A credit against the year’s premium — the rates themselves never change',
    },
    {
        'key': DUPLICATE,
        'label': 'Duplicate',
        'short': 'Duplicate',
        'glyph': '⧉',
        'standalone': True,
        'hint': 'A copy of this plan as a separate column — for a carrier that reissued the same plan name with a '
        'different design, or to fix a quote the reader got wrong. Change its rows in the table afterwards',
    },
]

PCT_OPS = ('pct_off', 'pct_up')
OPS = [
    {'key': 'pct_off', 'label': '% off', 'short': '%↓'},
    {'key': 'pct_up', 'label': '% up', 'short': '%↑'},
    {'key': 'flat_off', 'label': '$ off', 'short': '$↓'},
    {'key': 'flat_up', 'label': '$ up', 'short': '$↑'},
    {'key': 'set', 'label': 'set to', 'short': '='},
]
OP_KEYS = tuple(op['key'] for op in OPS)
BUNDLE_OPS = ('pct_off', 'pct_up', 'flat_off', 'flat_up')  # a bundle adjusts the carrier's price, never restates it
KEEP = 'keep'  # a per-rate override that leaves one rate out of the all-rates change

# The ancillary lines carriers discount for, in cheat-sheet order, with the in-row editor's short names.
BUNDLE_LINES = [
    ('dental', 'Dental'),
    ('vision', 'Vision'),
    ('basic_life_add', 'Basic life'),
    ('voluntary_life', 'Vol. life'),
    ('std', 'STD'),
    ('ltd', 'LTD'),
]

# A quote's `Plan.bundling`, as the bundle's check-and-balance words it.
BUNDLING = [('', 'not confirmed'), ('unbundled', 'confirmed unbundled'), ('included', 'rates already include it')]

QUOTED = 'group_premium_monthly'  # the carrier's stated total: a % reaches it, a $ amount or a set-to does not
STOP_LOSS_RATES = ['sl_spec_rate', 'sl_agg_rate', 'sl_other_load']
RATE_BASES = ('composite', 'volume_1000', 'weekly_10', 'payroll_100', 'pepm', 'stop_loss')

WORDS = {
    'current_plan': 'The in-force plan is the baseline, not an offer — price the carrier’s renewal quote instead. A '
    'premium holiday is the one version the current plan can take.',
    'one_plan_credit': 'A dollar credit belongs to one plan — pick one, or use months to credit each plan its own '
    'month.',
    'credit_exceeds_year': 'The credit is larger than the annual premium.',
    'verify': 'Calculated — verify against the carrier. Every carrier computes concessions with its own formula; '
    'final rates are subject to final underwriting. “set to” is how you type the rep’s exact rate. Only the rates '
    'move — a plan whose deductible or copays changed is a new quote, not a priced version.',
    'holiday': 'A credit against the year’s premium — the rates themselves don’t change (which is why carriers like '
    'it: next year’s billed base stays high). The proposal shows the net annual premium after the credit.',
    'conditional': 'Rates require these lines to sell',
    'conditional_hint': '(uncheck when the carrier bakes the discount in regardless — the Florida Blue case)',
    'bundling_states': 'Do the quoted rates already include the bundle? The check-and-balance — confirm it with the '
    'carrier per quote:',
    'included': 'The carrier already baked the bundling discount into this quote — a bundled version would discount '
    'it twice',
}


def rate_keys(basis):
    """The rates a price change touches on a line of this basis (the old `rate_keys_for`)."""
    if basis == 'composite':
        return list(fields.TIER_RATE_KEYS)
    if basis == 'stop_loss':
        return list(STOP_LOSS_RATES)
    return ['unit_rate']


def premium_keys(basis):
    """Every key a priced version may change: the rates and the quoted group premium."""
    return [*rate_keys(basis), QUOTED]


def meta():
    return {
        'families': FAMILIES,
        'kinds': list(KINDS),
        'ops': OPS,
        'pct_ops': list(PCT_OPS),
        'bundle_ops': list(BUNDLE_OPS),
        'bundle_lines': [{'key': key, 'short': short} for key, short in BUNDLE_LINES],
        'keep': KEEP,
        'quoted': QUOTED,
        'rate_keys': {basis: rate_keys(basis) for basis in RATE_BASES},
        'bundling': [{'key': key, 'label': label} for key, label in BUNDLING],
        'words': WORDS,
    }
