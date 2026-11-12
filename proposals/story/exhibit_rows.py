"""Which rows a plan set's table prints, and each plan's cell as the client reads it (plan.md §9.5; J133; old Vantage
891f1b3 `presentation_model.document_items`, `client_label` and `proposal_presentation._exhibit_entries`). Pure.

The design rows come from the house row maps (`workbook.rows`, J133, and `workbook.design.items`, shared with the
client spreadsheet so the two files print the same rows): Bryke's in/out map on a medical line, the field set's map
on the others, then the line's rates and its employer contribution in two bands of their own. Only client fields
(§4.3) are ever picked. A rate prints "count × rate" where anyone enrolls in its tier (a tier nobody is on prints
the rate alone: "0 × $2,746.03" reads as arithmetic, not a price). A value longer than `LONG_VALUE` moves to a
numbered note. A row no plan on THIS page has a value for says nothing and is left out, and a band over no row less.
"""

from quotes import fields

from .. import catalog, formatting
from ..layout import fit
from ..workbook import design
from ..workbook import rows as house

RATES_BAND = 'band:rates'
EMPLOYER_BAND = 'band:employer_contribution'  # what employees pay prints on a page of its own
QUOTED_TOTAL = 'group_premium_monthly'  # a quoted total says what the cost rows already say
RATE_KEYS = (*fields.TIER_RATE_KEYS, 'unit_rate', QUOTED_TOTAL)
TIER_OF_RATE = dict(zip(fields.TIER_RATE_KEYS, ('EE', 'ES', 'EC', 'FAM'), strict=True))
INOUT_TAG = ' (In/Out)'

# What a client document calls a row where the field's label is our own shorthand (D-175; the firm's wording to sign
# off). Only here: the spreadsheets and staff grids keep theirs.
CLIENT_ROW_LABELS = {
    'Rate — EE': 'Employee only',
    'Rate — EE + Spouse': 'Employee + spouse',
    'Rate — EE + Child(ren)': 'Employee + child(ren)',
    'Rate — Family': 'Family',
    'Employer Contrib — EE': 'Employee only',
    'Employer Contrib — ES': 'Employee + spouse',
    'Employer Contrib — EC': 'Employee + child(ren)',
    'Employer Contrib — FAM': 'Family',
    'Ind. Deductible': 'Individual deductible',
    'Fam. Deductible': 'Family deductible',
    'Ind. OOP Max': 'Individual out-of-pocket max',
    'Fam. OOP Max': 'Family out-of-pocket max',
    'Coinsurance — member pays': 'Coinsurance (you pay)',
    'PCP Copay': 'Primary care copay',
    'Rx Deductible': 'Prescription deductible',
    'Rx Drug Card (T1 / T2 / T3)': 'Prescriptions (tier 1 / 2 / 3)',
    'Specialty Rx': 'Specialty prescriptions',
    'Group Premium / mo (quoted)': 'Group monthly premium (as quoted)',
}


def client_label(label):
    if label.endswith(INOUT_TAG):
        base = label[: -len(INOUT_TAG)]
        return f'{CLIENT_ROW_LABELS.get(base, base)} (in / out of network)'
    return CLIENT_ROW_LABELS.get(label, label)


def _has_value(key, plans):
    return any(str(p['values'].get(key) if p['values'].get(key) is not None else '').strip() for p in plans)


def _band(keys, label, picked, plans):
    rows = [
        {'id': key, 'kind': 'row', 'label': fields.BY_KEY[key]['label'], 'keys': (key,), 'pair': False, 'indent': 1}
        for key in keys
        if key in picked and _has_value(key, plans)
    ]
    band = {'id': f'band:{label.lower().replace(" ", "_")}', 'kind': 'band', 'label': label, 'keys': ()}
    return [dict(band, pair=False, indent=0), *rows] if rows else []


def items(line):
    """The line's table rows on the client deck, as `workbook.design.items` gives them, labels in a client's words."""
    plans = list(line['plans'].values())
    picked = line['rows'] if line['rows'] is not None else catalog.client_keys(line['key'])
    allowed = set(catalog.client_keys(line['key']))
    picked = [key for key in picked if key in allowed]
    house_map = house.COMPARE_MEDICAL_ROWS if line['field_set'] == 'medical' else None
    found = design.items(line['field_set'], picked, [p['item'] for p in plans], house_map=house_map)
    found += _band(RATE_KEYS, 'Rates', set(picked), plans)
    found += _band(fields.CONTRIB_KEYS, 'Employer contribution', set(picked), plans)
    out = []
    for item in found:
        item = dict(item, keys=list(item['keys']))
        if item.get('inout') and len(item['keys']) == 1 and item['label'].endswith(INOUT_TAG):
            item['label'] = item['label'][: -len(INOUT_TAG)]
        item['label'] = client_label(item['label'])
        out.append(item)
    return out


def _count(number):
    return str(int(number)) if float(number).is_integer() else f'{number:g}'


def _cell(item, plan, offers, counts_on):
    keys = item['keys']
    value = design.text(item, plan['item']) or ''
    offer = (offers or {}).get(plan['id'])
    if offer is not None and len(keys) == 1 and keys[0] in offer['rates']:
        value = formatting.value(keys[0], offer['rates'][keys[0]]) or value
    tier = TIER_OF_RATE.get(keys[0]) if len(keys) == 1 else None
    count = (plan['counts'] or {}).get(tier) if value and tier and counts_on else None
    return f'{_count(count)} × {value}' if count else value


def entries(items_, page_plans, offers=None, with_cost=True, long_notes=True):
    """The page's benefit rows as text, so the page can be fitted before it is built: [(kind, item, cells)] with
    kind 'band' or 'row', and the long-value notes' lines."""
    out, shared, in_employer = [], {}, False
    money_lines = with_cost and any(p['monthly'] is not None for p in page_plans)
    for item in items_:
        if item['kind'] == 'band':
            in_employer = item['id'] == EMPLOYER_BAND
            if not in_employer:
                out.append(('band', item, [item['label']]))
            continue
        if in_employer or (money_lines and QUOTED_TOTAL in item['keys']):
            continue
        cells = [item['label']]
        for plan in page_plans:
            value = _cell(item, plan, offers, counts_on=True)
            if long_notes:
                value = fit.noted(value, item['label'], plan['carrier'], shared)
            cells.append(value or '—')
        out.append(('row', item, cells))
    out = [entry for entry in out if entry[0] != 'row' or any(value != '—' for value in entry[2][1:])]
    out = [
        entry
        for number, entry in enumerate(out)
        if entry[0] != 'band' or (number + 1 < len(out) and out[number + 1][0] == 'row')
    ]
    return out, fit.notes_of(shared)
