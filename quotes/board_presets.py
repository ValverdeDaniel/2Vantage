"""The Advisor board's lists (plan.md §4.3, §7.1; F18, F20, F31, F32, F41, F62; D-051). A data module.

Served by `/api/meta/` under `board`, so the frontend never hard-codes them (rule 1), and read by the board export, so
the file prints the columns and words the screen shows (F93). Lists name plan fields from `quotes/fields.py` only; a
field a line does not have is dropped from that line's columns, as the old board's `activeColumns` did.

- `PRESETS`: the Columns tabs. Primary adapts to the line's field set; the others list fields, and All columns is
  every field of the line between Monthly total, Δ vs current and Flags (the old AdvisorTab's PRESET_TABS).
- `DERIVED`: the columns the board works out on the server (`premium`, `change`, `facts`; F41). `PINNED`: ★ and Plan.
- `SORTS`: the sort select (F32): the client's order (the default; values never move a plan), a column's own sort,
  and closeness to the nearest current plan (F121).
- `SLIDERS` and `BUDGET` (F18, F20) are slice 10's filters; their lists live here with the presets (§7.1).
- `COMPLIANCE`: the two tests a carrier can say a plan fails, with the chip's short words (F62, D-051).
"""

from deals import lines

from . import fields

PRESETS = [
    ('primary', 'Primary'),
    ('cost', 'Cost sharing'),
    ('rx', 'Rx'),
    ('rates', 'Rates & contributions'),
    ('all', 'All columns'),
]
DEFAULT_PRESET = 'primary'

# The Primary tab per field set (the old PRIMARY_BY_SET).
PRIMARY = {
    'medical': ['total', 'delta', 'deductible_single', 'oop_max_single', 'network_type', 'flags'],
    'dental': ['total', 'delta', 'den_annual_max', 'den_deductible', 'den_ortho', 'network_type', 'flags'],
    'vision': ['total', 'delta', 'vis_exam_copay', 'vis_frame_allowance', 'network_type', 'flags'],
    'life': ['total', 'delta', 'life_schedule', 'life_guarantee_issue', 'unit_rate', 'flags'],
    'disability': ['total', 'delta', 'dis_elimination', 'dis_benefit_pct', 'dis_max_benefit', 'unit_rate', 'flags'],
    'generic': ['total', 'delta', 'benefit_summary', 'plan_type', 'unit_rate', 'flags'],
    'stop_loss': ['total', 'delta', 'sl_spec_deductible', 'sl_spec_rate', 'sl_agg_factor', 'sl_lasers', 'flags'],
}

# The other tabs (the old PRESETS); medical-shaped ones resolve to nothing a dental line has, and that is fine.
COLUMNS = {
    'cost': [
        'deductible_single',
        'deductible_family',
        'oop_max_single',
        'oop_max_family',
        'coinsurance',
        'pcp_copay',
        'specialist_copay',
        'urgent_care_copay',
        'er_copay',
        'inpatient',
    ],
    'rx': ['rx_deductible', 'rx_t1', 'rx_t2', 'rx_t3', 'rx_t4'],
    'rates': [
        'total',
        'delta',
        'rate_ee',
        'rate_es',
        'rate_ec',
        'rate_fam',
        'contrib_ee',
        'contrib_es',
        'contrib_ec',
        'contrib_fam',
    ],
}

# Worked out on the server, never plan fields. `sort` False: the column takes no header sort. Transposed, each is a
# row in the line's groups (the old planGroups.EXTRA_ROWS): `start` rows open their group, the rest close it, and the
# cost group, which is no field group, closes the grid.
COST_GROUP = 'cost'
DERIVED = [
    {'key': 'flags', 'label': 'Flags', 'sort': False, 'group': 'info', 'at': 'start'},
    {'key': 'network_type', 'label': 'Network / type', 'sort': True, 'group': 'info', 'at': 'start'},
    {'key': 'total', 'label': 'Monthly total', 'sort': True, 'group': COST_GROUP, 'at': 'end'},
    {'key': 'delta', 'label': 'Δ vs current', 'sort': True, 'group': COST_GROUP, 'at': 'end'},
]
GROUP_LABELS = {COST_GROUP: 'Cost Summary'}
DERIVED_KEYS = [column['key'] for column in DERIVED]

# Pinned on every tab, before the preset's columns.
PINNED = [
    {'key': 'star', 'label': '★', 'sort': True},
    {'key': 'carrier', 'label': 'Plan', 'sort': True},
]

# ⇄ Transpose draws every plan as a column; past this many plans on screen the board stays in rows (F34).
TRANSPOSE_MAX = 60

SORTS = [
    ('proposal', 'Proposal order'),
    ('', 'Sort by column'),
    ('closest', 'Closest to current'),
]
DEFAULT_SORT = 'proposal'

# Slice 10's sliders, steps of 50, bounded by the line's quotes. Annual maximum and frame allowance are "at least"
# sliders (F20, bug 16: the old ones worked backwards).
SLIDERS = {
    'medical': [
        {'key': 'deductible_single', 'label': 'Max deductible', 'op': '<='},
        {'key': 'oop_max_single', 'label': 'Max OOP', 'op': '<='},
    ],
    'dental': [
        {'key': 'den_deductible', 'label': 'Max deductible', 'op': '<='},
        {'key': 'den_annual_max', 'label': 'Min annual maximum', 'op': '>='},
    ],
    'vision': [
        {'key': 'vis_exam_copay', 'label': 'Max exam copay', 'op': '<='},
        {'key': 'vis_frame_allowance', 'label': 'Min frame allowance', 'op': '>='},
    ],
}
SLIDER_STEP = 50

# Slice 10's budget select (F18): "no more than N% above" what each plan replaces; negative rungs are "at least N%
# cheaper".
BUDGET = [
    {'value': None, 'label': 'Any budget'},
    {'value': 5, 'label': 'Within 5% of current'},
    {'value': 10, 'label': 'Within 10% of current'},
    {'value': 15, 'label': 'Within 15% of current'},
    {'value': -5, 'label': 'At least 5% cheaper'},
    {'value': -10, 'label': 'At least 10% cheaper'},
    {'value': -15, 'label': 'At least 15% cheaper'},
]

# The compliance tests a plan can fail (D-051): a carrier's "No" only; a blank is never a failure (`facts`).
COMPLIANCE = [
    {
        'key': 'minimum_value',
        'short': 'MV',
        'label': 'minimum value',
        'why': 'An employer offering only plans that fail minimum value has not met the ACA employer mandate.',
    },
    {
        'key': 'part_d_creditable',
        'short': 'Part D',
        'label': 'Medicare Part D creditable coverage',
        'why': 'A Medicare-eligible employee who takes a non-creditable plan can be charged a lifetime Part D '
        'late-enrolment penalty.',
    },
]


def columns(preset, line_key):
    """The column keys a preset shows on a line, in order: derived keys and the line's own fields only."""
    line = lines.get(line_key)
    if not line:
        return []
    own = fields.keys_for(line_key)
    if preset == 'all':
        return ['total', 'delta', *own, 'flags']
    wanted = PRIMARY.get(line['field_set'], PRIMARY['generic']) if preset == 'primary' else COLUMNS.get(preset)
    if wanted is None:
        return columns(DEFAULT_PRESET, line_key)
    has = set(own)
    return [key for key in wanted if key in DERIVED_KEYS or key in has]


def meta():
    return {
        'presets': [{'key': key, 'label': label} for key, label in PRESETS],
        'default_preset': DEFAULT_PRESET,
        'columns': {line['key']: {key: columns(key, line['key']) for key, _ in PRESETS} for line in lines.LINES},
        'derived': DERIVED,
        'group_labels': GROUP_LABELS,
        'pinned': PINNED,
        'sorts': [{'key': key, 'label': label} for key, label in SORTS],
        'default_sort': DEFAULT_SORT,
        'transpose_max': TRANSPOSE_MAX,
        'sliders': SLIDERS,
        'slider_step': SLIDER_STEP,
        'budget': BUDGET,
        'compliance': COMPLIANCE,
    }
