"""The quote reader's synthetic corpus (plan.md §12.8; Q.6): invented carriers, plans and rates, so every key is
known by construction. Two sets: `tuning` and `held_out`. Each case is a file (PDF or workbook) with its key (the plans
as printed, in order) and the answer a perfect read gives, which the fake client replays in tests; the Eval lane
(`manage.py reader_eval`) reads the same files live and scores Claude against the keys.

The corpus holds a two-current-plan renewal with printed per-plan counts and a plan printed under two numbers (the
Florida Blue pair, D116). `faults.faulty` bends a perfect answer the way a read goes wrong. Deterministic: the same
bytes every run.
"""

from dataclasses import dataclass, field

from . import printed

TUNING, HELD_OUT = 'tuning', 'held_out'
SETS = (TUNING, HELD_OUT)
MEDICAL_ROWS = [
    ('Plan type', 'plan_type'),
    ('Network', 'network'),
    ('Metal level', 'metal_level'),
    ('Deductible (single / family)', None),
    ('Out-of-pocket max (single)', 'oop_max_single'),
    ('Coinsurance (member)', 'coinsurance'),
    ('Primary care copay', 'pcp_copay'),
    ('Specialist copay', 'specialist_copay'),
    ('Chiropractic visits', ''),
    ('Employee only', 'rate_ee'),
    ('Employee + spouse', 'rate_es'),
    ('Employee + child(ren)', 'rate_ec'),
    ('Family', 'rate_fam'),
]


@dataclass
class Case:
    name: str
    set: str
    filename: str
    raw: bytes
    kind: str
    role: str
    carrier: str
    lines: list
    key: dict  # {'plans': [{line, side, carrier, name, plan_number, renews, values, counts}]}
    answer: dict  # the perfect read of the whole file, in the reader's schema
    range: str  # the range label that one read of the whole file covers
    extension: str = '.pdf'
    notes: list = field(default_factory=list)


def medical(name, side, design, rates, *, carrier, number='', codes=(), renews=None, replaces=''):
    deductible, family = design['deductible_single'], design.get('deductible_family', '')
    values = {**design, **dict(zip(('rate_ee', 'rate_es', 'rate_ec', 'rate_fam'), rates, strict=True))}
    return {
        'carrier': carrier,
        'name': name,
        'side': side,
        'plan_number': number,
        'codes': list(codes),
        'renews': renews,
        'replaces': replaces,
        'values': values,
        'deductible_text': f'${deductible} / ${family}' if family else f'${deductible}',
    }


def table(line, carrier, title, columns, counts=None):
    rows = []
    for label, key in MEDICAL_ROWS:
        if key is None:  # the money pair: single then family (D54)
            rows.append((label, '', [c['deductible_text'] for c in columns]))
            continue
        if key == '':
            rows.append((label, '', ['20 a year' for _ in columns]))
            continue
        cells = [c['values'].get(key, '') for c in columns]
        if any(cells):
            rows.append((label, key, cells))
    return {'line': line, 'carrier': carrier, 'title': title, 'columns': columns, 'rows': rows, 'counts': counts or {}}


def answer_of(tbl):
    """The perfect answer splits the money pair into its two fields (the reader's rule), not one unmapped row."""
    answer = printed.answer([tbl])
    block = answer['lines'][0]
    out = []
    for row in block['rows']:
        if row['label'].startswith('Deductible'):
            for key, part in (('deductible_single', 0), ('deductible_family', 1)):
                cells = []
                for cell in row['cells']:
                    pieces = cell['value'].replace('$', '').split('/')
                    if len(pieces) > part:
                        cells.append({**cell, 'value': pieces[part].strip()})
                if cells:
                    out.append({'label': row['label'], 'key': key, 'cells': cells})
        else:
            out.append(row)
    block['rows'] = out
    return answer


def key_of(tbl):
    plans = []
    for index, column in enumerate(tbl['columns']):
        renews = tbl['columns'][column['renews']]['name'] if column.get('renews') is not None else None
        plans.append(
            {
                'line': tbl['line'],
                'side': column['side'],
                'carrier': column['carrier'],
                'name': column['name'],
                'plan_number': column.get('plan_number', ''),
                'renews': renews,
                'replaces': column.get('replaces', ''),
                'values': dict(column['values']),
                'counts': dict(tbl.get('counts', {}).get(index, {})),
            }
        )
    return {'plans': plans}


def _pdf_case(name, set_name, tbl, *, kind='renewal', role='renewal'):
    raw = printed.pdf([tbl])
    return Case(
        name,
        set_name,
        f'{name}.pdf',
        raw,
        kind,
        role,
        tbl['carrier'],
        [tbl['line']],
        key_of(tbl),
        answer_of(tbl),
        'p1-2',
    )


def renewal_two_current():
    carrier = 'Coastline Health (synthetic)'
    ppo = {
        'plan_type': 'PPO',
        'network': 'Coastal Choice',
        'metal_level': 'Gold',
        'deductible_single': '2000',
        'deductible_family': '4000',
        'oop_max_single': '6000',
        'coinsurance': '20',
        'pcp_copay': '25',
        'specialist_copay': '50',
    }
    hmo = {
        'plan_type': 'HMO',
        'network': 'Coastal Select',
        'metal_level': 'Silver',
        'deductible_single': '3000',
        'deductible_family': '6000',
        'oop_max_single': '7000',
        'coinsurance': '30',
        'pcp_copay': '30',
        'specialist_copay': '60',
    }
    columns = [
        medical(
            'Coastal PPO 2000',
            'current',
            ppo,
            ('688.40', '1445.60', '1273.55', '2065.20'),
            carrier=carrier,
            number='CP2000',
            codes=('CH-104455',),
        ),
        medical(
            'Coastal PPO 2000',
            'renewal',
            ppo,
            ('743.45', '1561.25', '1375.45', '2230.40'),
            carrier=carrier,
            number='CP2000',
            codes=('CH-104455',),
            renews=0,
        ),
        medical(
            'Coastal HMO 3000',
            'current',
            hmo,
            ('598.10', '1256.00', '1106.50', '1794.30'),
            carrier=carrier,
            number='CH3000',
            codes=('CH-104456',),
        ),
        medical(
            'Coastal HMO 3000',
            'renewal',
            hmo,
            ('640.00', '1343.90', '1183.95', '1919.90'),
            carrier=carrier,
            number='CH3000',
            codes=('CH-104456',),
            renews=2,
        ),
    ]
    counts = {0: {'EE': 14, 'ES': 4, 'EC': 3, 'FAM': 5}, 2: {'EE': 9, 'ES': 2, 'EC': 2, 'FAM': 1}}
    return _pdf_case('renewal-two-current', TUNING, table('medical', carrier, '2027 group renewal', columns, counts))


def quotes_three():
    carrier = 'Harbor Mutual (synthetic)'

    def design(kind, ded, oop, pcp):
        return {
            'plan_type': kind,
            'network': 'Harbor Open',
            'deductible_single': ded,
            'oop_max_single': oop,
            'coinsurance': '20',
            'pcp_copay': pcp,
        }

    columns = [
        medical(
            'Harbor Open PPO 1500',
            'quote',
            design('PPO', '1500', '5000', '20'),
            ('712.35', '1495.95', '1317.85', '2137.05'),
            carrier=carrier,
            number='HM-PPO-1500',
        ),
        medical(
            'Harbor Open EPO 2500',
            'quote',
            design('EPO', '2500', '6500', '30'),
            ('655.20', '1375.90', '1212.10', '1965.60'),
            carrier=carrier,
            number='HM-EPO-2500',
        ),
        medical(
            'Harbor HSA 3500',
            'quote',
            design('HDHP', '3500', '7000', '0'),
            ('512.34', '1075.90', '947.80', '1537.00'),
            carrier=carrier,
            number='HM-HSA-3500',
        ),
    ]
    return _pdf_case(
        'quotes-three',
        TUNING,
        table('medical', carrier, '2027 new business quote', columns),
        kind='quote',
        role='alternates',
    )


def pair_two_numbers():
    carrier = 'Gulfside Blue (synthetic)'
    design = {
        'plan_type': 'PPO',
        'network': 'Gulfside Options',
        'metal_level': 'Gold',
        'deductible_single': '2500',
        'deductible_family': '5000',
        'oop_max_single': '6350',
        'coinsurance': '20',
        'pcp_copay': '30',
    }
    columns = [
        medical(
            'Gulfside Options 2500',
            'current',
            design,
            ('702.40', '1474.95', '1299.45', '2107.20'),
            carrier=carrier,
            number='05182 / 05183',
        ),
    ]
    return _pdf_case(
        'pair-two-numbers',
        HELD_OUT,
        table('medical', carrier, '2027 renewal', columns, {0: {'EE': 11, 'ES': 3}}),
        kind='renewal',
        role='current',
    )


def cases():
    """Every case, tuning first."""
    return [renewal_two_current(), quotes_three(), pair_two_numbers()]
