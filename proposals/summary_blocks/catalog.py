"""The executive summary's blocks: what each is called, whether it is worked out per line or for the whole deal, and
the standard sets (plan.md §8.14; J64–J66). Data module, served as `/api/meta/` `proposal.summary`.

Ported from old Vantage 891f1b3 `pipeline/exec_summary.py` (BLOCKS, LINE_ONLY, DEFAULT_BLOCKS, NEW_BUSINESS_BLOCKS,
RENEWAL_BLOCKS, MEDICARE_BLOCKS), words unchanged: the summary is picked, not written — a list of block keys, each
pinned to a line or not.
"""

LINE, DEAL = 'line', 'deal'

# key: (label, scope), in the picker's order: 13 line blocks, then 8 deal blocks.
BLOCKS = {
    'current_cost': ('What you pay today', LINE),
    'carriers_quoted': ('Who we went to', LINE),
    'best_option': ('Lowest quote', LINE),
    'recommended': ('Our recommendation', LINE),
    'spread': ('Range of quotes', LINE),
    'annual_delta': ('Annual impact', LINE),
    'ee_only': ('Employee-only rate', LINE),
    'deductible_move': ('Deductible', LINE),
    'oop_move': ('Out-of-pocket', LINE),
    'enrollment': ('Enrollment', LINE),
    'lf_claims_pct': ('Level-funded split', LINE),
    'stop_loss_mal': ('Maximum annual liability', LINE),
    'medicare_eligible': ('Medicare-eligible (65+)', LINE),
    'total_current': ('Total cost today', DEAL),
    'total_recommended': ('Total as recommended', DEAL),
    'total_annual_delta': ('Annual impact, all lines', DEAL),
    'lines_shopped': ('What we marketed', DEAL),
    'first_year_cost': ('First-year cost', DEAL),
    'lines_proposed': ('Proposed additions', DEAL),
    'renewal_offer': ('The carrier’s renewal', DEAL),
    'renewal_vs_recommended': ('Ours vs the renewal', DEAL),
}
KEYS = tuple(BLOCKS)

# Line blocks that belong to one line: unpinned, they resolve on that line only, and the picker offers no pin. The
# census is the medical census, and Medicare is a medical question (J66).
LINE_ONLY = {'medicare_eligible': 'medical'}

# The standard set (8): what am I paying, what did we find, what do you suggest, what does it cost me over a year.
DEFAULT_BLOCKS = (
    'total_current',
    'lines_shopped',
    'total_recommended',
    'total_annual_delta',
    'current_cost',
    'carriers_quoted',
    'recommended',
    'annual_delta',
)
# The new-business set (5): a deal with no current plan anywhere asks "what would this cost me".
NEW_BUSINESS_BLOCKS = ('lines_proposed', 'first_year_cost', 'recommended', 'ee_only', 'carriers_quoted')
# Appended only when the renewal letter's figures are on file (J65; OQ38), in the conversation's order.
RENEWAL_BLOCKS = ('renewal_offer', 'renewal_vs_recommended')
# Appended only when the census holds someone 65 or older (J66; the 2026-10-22 call).
MEDICARE_BLOCKS = ('medicare_eligible',)

MAX_BLOCKS = 24


def label(key):
    return BLOCKS[key][0]


def scope(key):
    return BLOCKS[key][1]


def meta():
    """The picker's menu: [{key, label, scope, line?}] and the cap."""
    return {
        'blocks': [
            {'key': key, 'label': name, 'scope': where, **({'line': LINE_ONLY[key]} if key in LINE_ONLY else {})}
            for key, (name, where) in BLOCKS.items()
        ],
        'max': MAX_BLOCKS,
    }
