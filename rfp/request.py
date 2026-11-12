"""The request in rules (plan.md §5.7; K17–K29): the size band, the route, the funding asked for, which carriers fit,
the commission text and the band's words. Pure: the facts come in as arguments (the selectors read them).

- Band (K18): `large` at 51 or more enrolled, else `small` (OQ53 default: at exactly 50 the band is small; a hand
  override waits, K30). The count is the one headcount, `quotes.facts.enrolled_headcount` (K17, OQ21).
- Route (K20): blank follows the band — through Warner Pacific under 51, direct to the carriers from 51 — until the
  first send pins it (slice 46); a pick overrides it, and picking the band's own route again sends null.
- Funding (K21, K22): the stored list, `[]` kept (bug 4: an empty pick says "Pick at least one funding type"); null
  means the default, the medical incumbent's funding (`quotes.facts.incumbent`: the current medical plans, else the
  medical current-coverage row), else fully insured and level-funded both, as UHC's own template defaults to "Both".
- Eligibility (K24): advice, never a block: a carrier fits when its Warner columns at the band cover a requested line.
- Commission text (K29, K106): one label when every line agrees ("5%"), else the lines grouped by label, larger groups
  first ("5% Med · 15% Den/Vis"). Per-line rates come from commission once it is built (slice 48); until then every
  line takes `AgencySettings.default_commission`. Ported from old Vantage 891f1b3 `market/rfp.py`.
"""

from deals import comp, lines

from . import carriers

SMALL, LARGE = 'small', 'large'
LARGE_FLOOR = 51
BANDS = ((SMALL, 'Small group (2–50)'), (LARGE, 'Large group (51+)'))
FORM_SIZE = {SMALL: '2–50', LARGE: '51+'}

WARNER, DIRECT = 'warner', 'direct'
# (key, chip label, long label, chip tooltip, the default's tag): old CarriersTab.jsx's words.
ROUTES = (
    (
        WARNER,
        'Warner Pacific',
        'Through Warner Pacific',
        'Warner’s form leads the packet, and one email goes to Warner’s quoting inbox',
        'standard under 51',
    ),
    (
        DIRECT,
        'Direct to carriers',
        'Direct to carriers',
        'Our own cover page leads the packet, and each carrier gets its own email',
        'standard at 51+',
    ),
)
ROUTE_KEYS = tuple(route[0] for route in ROUTES)

FUNDING = (('fully_insured', 'Fully insured'), ('level_funded', 'Level funded'), ('aso', 'ASO / self-funded'))
FUNDING_KEYS = tuple(key for key, _ in FUNDING)
FUNDING_LABELS = dict(FUNDING)
# What Warner's forms call our current-coverage funding (§4.6).
FUNDING_FROM_COVERAGE = {'fully_insured': 'fully_insured', 'level_funded': 'level_funded', 'self_funded': 'aso'}
UNKNOWN_FUNDING = ('fully_insured', 'level_funded')
NO_FUNDING = 'Pick at least one funding type'

NOT_ON_FORM = 'Not on the {size} form'
NO_LINES = 'None of the lines you picked'


def band(count):
    """'large' at 51 or more enrolled, else 'small' (an unknown count is small)."""
    return LARGE if (count or 0) >= LARGE_FLOOR else SMALL


def band_label(key):
    return dict(BANDS)[key]


def route(stored, band_key):
    """(route, default): the stored pick wins; otherwise the band decides."""
    default = DIRECT if band_key == LARGE else WARNER
    return (stored if stored in ROUTE_KEYS else default), default


def default_funding(incumbent_funding):
    """The funding asked for by default, in the forms' words: the medical incumbent's, else both."""
    found = FUNDING_FROM_COVERAGE.get(incumbent_funding or '')
    return [found] if found else list(UNKNOWN_FUNDING)


def funding(stored, default):
    """The funding asked for: the stored list (an empty one is a real pick), or the default when none is stored."""
    return list(default) if stored is None else [key for key in FUNDING_KEYS if key in set(stored)]


def eligibility(key, band_key, requested):
    """(eligible, reason, the requested lines it can quote at the band)."""
    overlap = [line for line in carriers.lines_for(key, band_key) if line in set(requested)]
    if not carriers.columns_for(key, band_key):
        return False, NOT_ON_FORM.format(size=FORM_SIZE[band_key]), overlap
    if not overlap:
        return False, NO_LINES, overlap
    return True, '', overlap


def chips(picked, band_key, requested, identities):
    """The carrier chips in registry order (K23): `identities` is deals' list ({key, name, group})."""
    rows = []
    for carrier in identities:
        key = carrier['key']
        eligible, reason, overlap = eligibility(key, band_key, requested)
        found = carriers.ATTRIBUTES[key]
        rows.append(
            {
                'key': key,
                'name': carrier['name'],
                'group': carrier['group'],
                'selected': key in picked,
                'eligible': eligible,
                'reason': reason,
                'lines': overlap,
                'line_labels': [lines.label(line) for line in overlap],
                'census_format': found['census_format'],
                'on_form': found['on_form'],
                'note': found['note'],
            }
        )
    return rows


def _comp(raw):
    found, error = comp.parse_comp(raw, allow_blank=True)
    return None if error else found


def commission_text(requested, rates, default):
    """(the text the form prints, ['Medical: 5%', …]). `rates` is {line: comp} (empty until commission is built);
    a line with no rate takes `default`. Blank when no line has one."""
    fallback = _comp(default)
    pairs = []
    for line in requested:
        found = _comp((rates or {}).get(line)) or fallback
        if found:
            pairs.append((line, comp.comp_label(found)))
    if not pairs:
        return '', []
    breakdown = [f'{lines.label(line)}: {label}' for line, label in pairs]
    groups = {}
    for line, label in pairs:
        groups.setdefault(label, []).append(line)
    if len(groups) == 1:
        return pairs[0][1], breakdown
    ordered = sorted(groups.items(), key=lambda item: -len(item[1]))  # stable: ties keep the order they first came
    parts = [f'{label} {"/".join(lines.BY_KEY[line]["short"] for line in shared)}' for label, shared in ordered]
    return ' · '.join(parts), breakdown
