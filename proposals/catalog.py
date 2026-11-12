"""The proposal builder's catalogue (plan.md §8.14; J.6.3; J16, J18, J38–J42, J59–J62). Data module.

Served as `/api/meta/` `proposal`, so the browser holds no copy (rule 1). Ported from old Vantage 891f1b3:
`pipeline/proposal_review.py` (the cards), `pipeline/composition.py` (parts, card stats, the stop-loss row set, the
limits) and `close/keyRows.js` (Key rows). Every key list is filtered against `quotes.fields` on the way out, so a
renamed field drops out rather than breaking, and nothing a client file may not print (§4.3 `client`; J.5 B3: the
laser roster) is ever offered.
"""

from deals import lines
from quotes import fields

from . import pages
from .summary_blocks import catalog as summary_catalog

# The builder's cards (D-113), in screen order. A deal card is marked once for the deal, a line card once per line.
# The optional cards take a mark but never count toward "the proposal is built": `pictures` (the old OPTIONAL_CARDS)
# and `pages`, the Presentation pages card, which the old app left unmarked so that adding it reopened no finished
# proposal (every page on it is optional, and a page with nothing to say does not print).
DEAL_CARDS = ('cover', 'output', 'coverage', 'summary', 'next_steps')
OPTIONAL_CARDS = ('pictures', 'pages')
LINE_CARDS = ('quotes', 'rows', 'markets')
CARDS = DEAL_CARDS + OPTIONAL_CARDS + LINE_CARDS
CARD_TITLES = {
    'cover': 'Cover',
    'pictures': 'Pictures',
    'output': 'How the documents look',
    'pages': 'Presentation pages',
    'coverage': 'Coverage & marketing intent',
    'summary': 'Executive summary',
    'next_steps': 'Next steps',
    'quotes': 'Plans on the proposal',
    'rows': 'What this section shows',
    'markets': 'Markets checked',
}
# The cards the builder draws so far; the cover and pictures join with slice 34. "n of N completed" counts these,
# the optional ones apart.
ON_SCREEN = ('output', 'pages', 'coverage', 'quotes', 'rows', 'summary', 'next_steps', 'markets')

# How the documents look (J38, J39, J41): the layout's words, the spreadsheet's Dynamic Compare columns, and the
# switches that default on. The Format (Presentation / Classic, J36, J37) and the share link's period (J40) wait (OQ8).
LAYOUT_LABELS = {
    'by_carrier': 'A page per carrier',
    'side_by_side': 'Every option side by side',
    'best_only': 'The recommendation only',
}
COMPARE_SLOTS = (5, 10, 16)
DEFAULT_COMPARE_SLOTS = 16
OUTPUT_SWITCHES = ('package_summary', 'compare_tabs', 'disclaimers')

# The Presentation format's switchable pages (J42), in the story's order. Renewal history waits with past plan years
# (J44, deferred).
PAGES = (
    ('agenda', 'Agenda and section pages'),
    ('about', 'About the firm'),
    ('team', 'Your team'),
    ('experience', 'Plan experience'),
    ('calendar', 'Meeting calendar'),
    ('bios', 'Team bios'),
)
PAGE_KEYS = tuple(key for key, _label in PAGES)

# The stock pictures the deck's dark pages wear (J35, D-190; old `stock_images.LIBRARY` at 891f1b3), cropped once to
# the boxes they fill (J.5 B12): `assets/images/stock_images/<key>.jpg` for a dark page's frame, `<key>-agenda.jpg` for
# the agenda's panel. A place the deal never touched reads its default; slice 34's Pictures card picks per place.
STOCK_PICTURES = (
    ('blue_light', 'Blue light'),
    ('at_the_table', 'At the table'),
    ('reaching_hands', 'Reaching hands'),
    ('hand_and_sun', 'Hand and sun'),
    ('light_bulb', 'Light bulb'),
    ('gold_lights', 'Gold lights'),
    ('circuit_brain', 'Circuit brain'),
)
PICTURE_PLACES = (
    ('cover', 'Cover'),
    ('agenda', 'Agenda'),
    ('sections', 'Section pages'),
    ('closing', 'Thank-you page'),
)
DEFAULT_PICTURES = {'cover': 'blue_light', 'closing': 'at_the_table'}

# A line section's parts, in print order (not configurable: a cost table before the plans it prices helps nobody).
PARTS = (('comparison', 'Plan comparison'), ('cost', 'Cost summary'), ('recommendation', 'Recommendation'))
PART_KEYS = tuple(key for key, _label in PARTS)

# "Key rows" on the builder's page tables (J16; old keyRows.js): display only, the files print every row. The Rx
# tiers read as one row, "$10 / $40 / $70 / 20%". Stop-loss leaves out the laser roster (B3).
RX_ROW = 'rx_tiers'
RX_TIER_KEYS = ('rx_t1', 'rx_t2', 'rx_t3', 'rx_t4')
RX_LABEL = 'Rx tiers'
KEY_ROWS = {
    'medical': ('deductible_single', 'coinsurance', 'oop_max_single', RX_ROW),
    'dental': ('den_deductible', 'den_annual_max', 'den_ortho'),
    'vision': ('vis_exam_copay', 'vis_frame_allowance'),
    'life': ('life_schedule', 'life_guarantee_issue', 'unit_rate'),
    'disability': ('dis_elimination', 'dis_benefit_pct', 'dis_max_benefit', 'unit_rate'),
    'stop_loss': ('sl_spec_deductible', 'sl_spec_rate', 'sl_agg_factor'),
    'generic': ('benefit_summary', 'plan_type', 'unit_rate'),
}
KEY_PRESET = 'key'  # the pages read's `preset` for Key rows; `all` is every row (the Advisor's All columns)

# "On the plan cards" (J61): a plan's headline stats, ≤6 a line; with no pick, the field set's standard list.
MAX_CARD_STATS = 6
CARD_STATS = {
    'medical': ('deductible_single', 'coinsurance', 'oop_max_single', 'pcp_copay'),
    'dental': ('den_annual_max', 'den_deductible', 'den_preventive', 'den_major', 'den_ortho'),
    'vision': ('vis_exam_copay', 'vis_frame_allowance', 'vis_exam_frequency'),
    'life': ('life_schedule', 'life_benefit_max', 'life_guarantee_issue', 'life_add_included'),
    'disability': ('dis_elimination', 'dis_benefit_pct', 'dis_max_benefit'),
    'stop_loss': (
        'sl_spec_deductible',
        'sl_contract_basis',
        'sl_spec_rate',
        'sl_agg_rate',
        'sl_agg_factor',
        'tpa_name',
    ),
    'generic': ('benefit_summary', 'plan_type', 'unit_rate'),
}
STAT_LABELS = {
    'deductible_single': 'Deductible',
    'coinsurance': 'Coinsurance',
    'oop_max_single': 'Out-of-pocket max',
    'pcp_copay': 'PCP copay',
    'den_annual_max': 'Annual maximum',
    'den_deductible': 'Deductible',
    'den_preventive': 'Preventive & diagnostic',
    'den_major': 'Major services',
    'den_ortho': 'Orthodontia',
    'vis_exam_copay': 'Exam copay',
    'vis_frame_allowance': 'Frame allowance',
    'vis_exam_frequency': 'Exam frequency',
    'life_schedule': 'Benefit schedule',
    'life_benefit_max': 'Benefit maximum',
    'life_guarantee_issue': 'Guarantee issue',
    'life_add_included': 'AD&D included',
    'dis_elimination': 'Elimination period',
    'dis_benefit_pct': 'Benefit percentage',
    'dis_max_benefit': 'Maximum benefit',
    'sl_spec_deductible': 'Specific deductible',
    'sl_contract_basis': 'Contract basis',
    'sl_spec_rate': 'Specific PEPM',
    'sl_agg_rate': 'Aggregate PEPM',
    'sl_agg_factor': 'Claims factor PEPM',
    'tpa_name': 'TPA',
    'benefit_summary': 'What it covers',
    'plan_type': 'Plan type',
    'unit_rate': 'Rate',
}

# One-click row sets (J59): Stephanie's client rule for stop-loss, contract terms and costs, never plan design and
# never the laser roster.
ROW_PRESETS = (
    {
        'line': 'stop_loss',
        'key': 'client_safe',
        'label': 'Client-facing stop-loss',
        'description': 'Contract terms and costs — no lasers, no plan design.',
        'rows': (
            'sl_spec_deductible',
            'sl_contract_basis',
            'sl_run_in_months',
            'sl_run_in_limit',
            'sl_run_out_months',
            'sl_tlo',
            'sl_agg_corridor',
            'sl_agg_floor',
            'sl_agg_factor',
            'sl_spec_rate',
            'sl_agg_rate',
            'sl_other_load',
            'tpa_name',
            'tpa_admin_fee',
            'tpa_rate_guarantee',
            'sl_collateral',
            'group_premium_monthly',
        ),
    },
)

# Limits (J.6.2).
MAX_TITLE = 300
MAX_TEXT = 4000
MAX_ROWS = 80
TABLE_NOTE_MAX = 600
TABLE_NOTE_LINES = 4
MAX_NEXT_STEPS = 8
MAX_STEP_TEXT = 300
MAX_EXPERIENCE_ROWS = 6
MAX_PERIOD = 80
MAX_MARKET_NOTE = 120
MAX_HIDDEN = 40


def field_set(line):
    found = lines.BY_KEY[line]['field_set']
    return found if found in KEY_ROWS else 'generic'


def client_keys(line):
    """The line's fields a client file may print, in the line's order."""
    return [key for key in fields.keys_for(line) if fields.BY_KEY[key]['client']]


def _known(keys, line):
    allowed = set(client_keys(line))
    return [key for key in keys if key in allowed]


def key_rows(line):
    """Key rows for the line: field keys, with `RX_ROW` standing for the Rx tiers."""
    allowed = set(client_keys(line))
    return [key for key in KEY_ROWS[field_set(line)] if key == RX_ROW or key in allowed]


def card_stats(line):
    """The field set's standard card stats that this line has."""
    return _known(CARD_STATS[field_set(line)], line)


def stat_label(key):
    return STAT_LABELS.get(key) or fields.BY_KEY[key]['label']


def row_preset(line):
    for preset in ROW_PRESETS:
        if preset['line'] == line:
            return {**preset, 'rows': _known(preset['rows'], line)}
    return None


def default_pictures():
    """{place: stock key or None} for every place."""
    return {place: DEFAULT_PICTURES.get(place) for place, _label in PICTURE_PLACES}


def picture_sources(picks):
    """{place: the image src a page draws, or None}: the agenda's panel has its own crop."""
    keys = dict(STOCK_PICTURES)
    return {
        place: (f'stock:{key}-agenda' if place == 'agenda' else f'stock:{key}') if key in keys else None
        for place, key in picks.items()
    }


def meta():
    """/api/meta/ `proposal`."""
    return {
        'cards': [
            {'key': key, 'title': CARD_TITLES[key], 'line': key in LINE_CARDS, 'optional': key in OPTIONAL_CARDS}
            for key in CARDS
        ],
        'on_screen': list(ON_SCREEN),
        'parts': [{'key': key, 'label': label} for key, label in PARTS],
        'layouts': [{'key': key, 'label': LAYOUT_LABELS[key]} for key in pages.LAYOUTS],
        'compare_slots': list(COMPARE_SLOTS),
        'pages': [{'key': key, 'label': label} for key, label in PAGES],
        'summary': summary_catalog.meta(),
        'limits': {
            'title': MAX_TITLE,
            'text': MAX_TEXT,
            'card_stats': MAX_CARD_STATS,
            'table_note': TABLE_NOTE_MAX,
            'table_note_lines': TABLE_NOTE_LINES,
            'next_steps': MAX_NEXT_STEPS,
            'step_text': MAX_STEP_TEXT,
            'experience_rows': MAX_EXPERIENCE_ROWS,
            'period': MAX_PERIOD,
            'market_note': MAX_MARKET_NOTE,
        },
        'key_preset': KEY_PRESET,
    }
