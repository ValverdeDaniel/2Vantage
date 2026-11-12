"""Where everything sits on a composite line's All Plans, Compare and Composite Rates tabs (plan.md §9.4; J148–J150;
old `presentation_bank.bank_map`, `compare_map` and `composite_pages` at 891f1b3). Pure geometry, 1-based like
Excel, plus `shared`: the counts every total on those tabs prices with.

The tests address a cell through these maps, as the writers do, never by guessing a row.
"""

from quotes.math import TIERS

from .. import layout
from ..model import column_letter
from .common import table_note_rows

FIRST_ROW = 5  # the All Plans tab's first entry row (title, subtitle, note, header above it)
FIRST_DESIGN_ROW = 8  # the Compare tab's first design row (rows 1–7: top, rule, status, Carrier, Plan Name)
FIRST_CARD_ROW = 5  # a Composite Rates tab's first page's status-word row (rows 1–4: its header)
CARDS_PER_PAGE = 4  # Composite Rates cards across a printed page
PER_PAGE = 5  # Compare columns a printed page holds
DEFAULT_SLOTS = 16
# The "% Difference Base Plans" box over slots 1 to 3: the title across E:J, then each base's word (E), "Based On ➡"
# (F) and its picker (G:J) on rows 2 and 3.
BOX = {'first': 5, 'word': 5, 'arrow': 6, 'pick': 7, 'last': 10}


def all_plans_map(line, bank, items):
    """The All Plans tab. Columns: A the plan label (the drop-downs' values), B the status, C the carrier, one column
    per design row (a band's name prefixes the labels under it), the SBC link when a listed plan has one, then with
    cost on the four rates, the stated premium when a plan has one, Monthly, Annual and, with exactly one current plan,
    % from current. Rows: the title, the subtitle, a note, the header, one row per entry from FIRST_ROW, then notes."""
    design, band, col = [], None, 4
    for item in items:
        if item['kind'] == 'band':
            band = item['label']
            continue
        header = f'{band}: {item["label"]}' if band else item['label']
        design.append({'item': item, 'header': header, 'col': col})
        col += 1
    cols = {'label': 1, 'status': 2, 'carrier': 3, 'design': design, 'sbc': None, 'rates': {}}
    cols.update(dict.fromkeys(('stated', 'monthly', 'annual', 'pct')))
    if bank['has_sbc']:
        cols['sbc'] = col
        col += 1
    if layout.part(line, 'cost'):
        for tier in TIERS:
            cols['rates'][tier] = col
            col += 1
        if bank['has_g']:
            cols['stated'] = col
            col += 1
        cols['monthly'], cols['annual'] = col, col + 1
        col += 2
        if len(bank['current_ids']) == 1:
            cols['pct'] = col
            col += 1
    first = FIRST_ROW
    last = first + len(bank['entries']) - 1
    row_of = {entry['id']: first + i for i, entry in enumerate(bank['entries']) if entry['kind'] == 'plan'}
    notes = sum(1 for count in bank['left_out'].values() if count)
    return {
        'cols': cols,
        'first': first,
        'last': last,
        'row_of': row_of,
        'last_col': col - 1,
        'last_row': last + (notes + 1 if notes else 0),
        'notes': (last + 2, last + 1 + notes) if notes else None,
    }


def compare_map(bank, items, cost, *, table_notes=0, slots=None):
    """The Compare tab in Bryke's layout. Column A holds the labels and B the shared inputs (counts, contribution); each
    plan slot is two columns from C:D ('col' and 'right'), merged on every row but the two % rows (left half the
    employee-only change, right half the total's). Rows: the client, who prepared it and the line's date (1–3) beside
    the base box (its pickers rows 2 and 3, only with cost on), a navy rule (4), the status words (5), Carrier (6) and
    Plan Name (7); the design rows; the Summary of Benefits link when a listed plan has one; with cost on the rates
    block (its header, four tiers, the stated premium when a plan has one), the two totals, the two % rows (ce/ct one
    row, re/rt the other) and the contribution block (the two percents, whose rows carry the employer's cost under
    them, one dollars row a tier carrying that tier's cost, then the three totals); then the notes."""
    count = slots or bank.get('slots') or DEFAULT_SLOTS
    columns = [{'k': k, 'col': 3 + 2 * k, 'right': 4 + 2 * k} for k in range(count)]
    r = FIRST_DESIGN_ROW
    design = {}
    for item in items:
        design[item['id']] = r
        r += 1
    sbc = None
    if bank['has_sbc']:
        sbc, r = r, r + 1
    names = ('band', 'g', 'tm', 'ta', 'ce', 'ct', 're', 'rt', 'cband', 'ee_pct', 'dep_pct')
    at = dict.fromkeys((*names, 'er_ee', 'er_dep', 'er_total', 'ee_total', 'er_annual'))
    at['tiers'] = at['tier_pay'] = None
    if cost:
        at['band'] = r
        at['tiers'] = (r + 1, r + 2, r + 3, r + 4)
        r += 5
        if bank['has_g']:
            at['g'], r = r, r + 1
        at['tm'], at['ta'] = r, r + 1
        at['ce'] = at['ct'] = r + 2
        at['re'] = at['rt'] = r + 3
        r += 5  # the totals, the % rows, a spacer
        at['cband'] = r
        at['ee_pct'], at['dep_pct'] = r + 1, r + 2
        at['tier_pay'] = (r + 3, r + 4, r + 5, r + 6)
        r += 7
        for name in ('er_total', 'ee_total', 'er_annual'):
            at[name], r = r, r + 1
        at['er_ee'], at['er_dep'] = at['ee_pct'], at['dep_pct']
    notes = table_notes + (4 if cost else 2)
    r += 1  # spacer
    at['notes'] = (r, r + notes - 1)
    r += notes
    return {
        'slots': columns,
        'last_col': 2 + 2 * count,
        'last_row': r - 1,
        'box': dict(BOX) if cost else None,
        'rows': {
            'title': 1,
            'subtitle': 2,
            'note': 3,
            'rule': 4,
            'base_current': 2 if cost else None,
            'base_renewal': 3 if cost else None,
            'marker': 5,
            'carrier': 6,
            'plan': 7,
            'design': design,
            'sbc': sbc,
            **at,
        },
    }


def _shift(rows, delta, keep=('base_current', 'base_renewal')):
    """`compare_map`'s rows moved `delta` down, for one Composite Rates page. The base pickers keep their rows: they
    are the Compare tab's cells, which every card reads."""
    out = {}
    for name, value in rows.items():
        if name in keep or value is None or isinstance(value, bool):
            out[name] = value
        elif isinstance(value, int):
            out[name] = value + delta
        elif isinstance(value, tuple):
            out[name] = tuple(row + delta for row in value)
        elif isinstance(value, dict):
            out[name] = {key: row + delta for key, row in value.items()}
        else:
            out[name] = value
    return out


def card_page_last(page):
    """The last row a Composite Rates page draws: the row above its notes' spacer (a card page writes no notes)."""
    return page['rows']['notes'][0] - 2


def composite_pages(bank, items, cost):
    """[(first row, page map, entries)] for a Composite Rates tab: one page per CARDS_PER_PAGE listed plans, in the
    list's order (section rows are never cards), each `compare_map` with that many slots moved down the sheet under
    the one before and a spacer row."""
    cards = [entry for entry in bank['entries'] if entry['kind'] == 'plan']
    pages, top = [], FIRST_CARD_ROW
    for start in range(0, len(cards), CARDS_PER_PAGE):
        chunk = cards[start : start + CARDS_PER_PAGE]
        page = compare_map(bank, items, cost, slots=len(chunk))
        page = {**page, 'rows': _shift(page['rows'], top - page['rows']['marker']), 'box': None}
        pages.append((top, page, chunk))
        top = card_page_last(page) + 2
    return pages


def notes_count(line):
    return len(table_note_rows(line))


def shared(ctx, line):
    """The counts every total on the line's Compare, Composite Rates and All Plans tabs prices with: {'counts': {tier:
    number or None}, 'link': (rates tab title, count column letter, (four rows)) or None}. With exactly one current
    plan on a rates tab that shows its counts, they are that plan's counts there (linked, so one edit flows through);
    otherwise the line's people as quotes' math counts them (inputs), or nothing."""
    geometry = ctx.maps.get(line.key) if ctx.maps else None
    title = ctx.layout.line_tab.get(line.key)
    found = (geometry or {}).get('counts')
    if geometry and geometry.get('current') and (geometry.get('rows') or {}).get('tiers') and title and found:
        counts = {tier: found.get(tier) or 0 for tier in TIERS}
        letter = column_letter(geometry['current']['count'])
        return {'counts': counts, 'link': (title, letter, tuple(geometry['rows']['tiers']))}
    people = line.people or {}
    counts = {tier: people.get(tier) for tier in TIERS} if line.people else dict.fromkeys(TIERS)
    return {'counts': counts, 'link': None}


def enrollment(counts):
    """The shared counts as quotes' math reads an enrollment: a count with no number is 0."""
    return {tier: counts.get(tier) or 0 for tier in TIERS}
