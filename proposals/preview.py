"""The rows the client workbook will print, as JSON (plan.md §7.9, §9.4), so the screen and the file never disagree."""

from deals import lines
from quotes import fields
from quotes import math as m

from . import formatting as fmt

# §9.4 medical design rows: each part is a key, or a tuple of keys printed as a pair ("$3,300 / $6,600").
MEDICAL_ROWS = [
    ('Funding', ['funding']),
    ('Plan type · Network · Metal tier · Deductible type', ['plan_type', 'network', 'metal_level', 'deductible_type']),
    ('Meets minimum value (ACA) · Medicare Part D creditable', ['minimum_value', 'part_d_creditable']),
    ('Deductible (individual / family)', [('deductible_single', 'deductible_family')]),
    ('Deductible out of network', [('deductible_single_oon', 'deductible_family_oon')]),
    ('Coinsurance (in / out)', [('coinsurance', 'coinsurance_oon')]),
    ('Out-of-pocket max (individual / family)', [('oop_max_single', 'oop_max_family')]),
    ('Out-of-pocket max out of network', [('oop_max_single_oon', 'oop_max_family_oon')]),
    ('Primary care · Specialist · Telehealth', ['pcp_copay', 'specialist_copay', 'telehealth']),
    ('Lab & X-ray · Advanced imaging', ['diagnostic_test', 'advanced_imaging']),
    ('Urgent care · Emergency room', ['urgent_care_copay', 'er_copay']),
    ('Inpatient · Outpatient surgery', ['inpatient', 'outpatient_surgery']),
    (
        'Rx deductible · Rx tiers 1 / 2 / 3 · Specialty · Mail order',
        ['rx_deductible', ('rx_t1', 'rx_t2', 'rx_t3'), 'rx_t4', 'rx_mail_order'],
    ),
    ('Summary of Benefits', ['sbc_url']),
]
NOT_DESIGN = {'rates', 'contrib', 'lf'}


def _client(key):
    return fields.BY_KEY[key]['client']


def _part(plan, part):
    if isinstance(part, tuple):
        return fmt.joined([fmt.value(k, plan.values.get(k)) for k in part if _client(k)], ' / ')
    return fmt.value(part, plan.values.get(part)) if _client(part) else ''


def design_rows(line, columns):
    if line == 'medical':
        specs = MEDICAL_ROWS
    else:
        specs = [
            (fields.BY_KEY[k]['label'], [k])
            for g, _, keys in fields.groups_for(line)
            if g not in NOT_DESIGN
            for k in keys
            if _client(k)
        ]
    rows = []
    for label, parts in specs:
        cells = [fmt.joined([_part(plan, part) for part in parts], ' · ') for plan in columns]
        if any(cells):
            link = [plan.values.get('sbc_url', '') for plan in columns] if parts == ['sbc_url'] else None
            rows.append({'label': label, 'cells': cells, **({'links': link} if link else {})})
    return rows


def _change_cells(columns, results):
    dollars, percents = [], []
    for plan in columns:
        result = results[plan.id]
        if plan.role == 'current':
            dollars.append(''), percents.append('')
        elif result['change']:
            dollars.append(fmt.signed_money(result['change']['delta']))
            percents.append(fmt.pct(result['change']['pct']))
        elif result['part_of']:
            dollars.append(f"Part of {result['part_of']}'s enrollment"), percents.append('')
        else:
            dollars.append(''), percents.append('')
    return dollars, percents


def cost_rows(line, columns, results, by_id):
    basis = lines.BY_KEY[line]['rate_basis']
    rows = []
    keys = m.enrollment_keys(basis)
    if basis == 'composite':
        for tier in m.TIERS:
            cells = [fmt.rate(m.cleaning.as_float(p.values.get(m.TIER_RATE[tier]))) for p in columns]
            rows.append({'label': f'Monthly rate — {tier}', 'cells': cells, 'kind': 'rate'})
    else:
        cells = [fmt.value('unit_rate', p.values.get('unit_rate')) for p in columns]
        rows.append({'label': 'Unit rate', 'cells': cells, 'kind': 'rate'})
    for key in keys:
        cells = [
            '' if not results[p.id]['enrollment_used'] else f'{results[p.id]["enrollment_used"][key]:g}'
            for p in columns
        ]
        label = f'Enrollment — {key}' if basis == 'composite' else key.capitalize()
        rows.append({'label': label, 'cells': cells, 'kind': 'input'})
    monthly = [
        (fmt.money(results[p.id]['monthly']) + (' †' if results[p.id]['quoted'] else ''))
        if results[p.id]['monthly'] is not None
        else m.REASON_WORDS.get(results[p.id]['reason'], '')
        for p in columns
    ]
    rows.append({'label': 'Total monthly premium', 'cells': monthly, 'kind': 'total'})
    rows.append(
        {
            'label': 'Total annual premium',
            'cells': [fmt.money(results[p.id]['annual']) for p in columns],
            'kind': 'total',
        }
    )
    dollars, percents = _change_cells(columns, results)
    rows.append({'label': 'Change vs current ($)', 'cells': dollars, 'kind': 'change'})
    rows.append({'label': 'Change vs current (%)', 'cells': percents, 'kind': 'change'})
    if basis == 'composite' and any(p.role == 'renewal' for p in columns):
        for tier in m.TIERS:
            cells = []
            for p in columns:
                change = None
                if p.role == 'renewal' and p.renews_id in by_id:
                    change = m.tier_rate_change(by_id[p.id], by_id[p.renews_id])[tier]
                cells.append(fmt.pct(change['pct']) if change else '')
            rows.append({'label': f'Rate change — {tier} (%)', 'cells': cells, 'kind': 'change'})
    return rows


def package_rows(packages, columns, labels):
    presented = {p.id for p in columns}
    rows = []
    for package in packages:
        if package['key'] == 'sold' or package['annual'] is None or not set(package['plan_ids']) <= presented:
            continue
        label = 'Renewal — average increase' if package['key'] == 'renewal' else package['label']
        rows.append(
            {
                'key': package['key'],
                'label': label,
                'plans': ', '.join(labels[pid] for pid in package['plan_ids']),
                'monthly': fmt.money(package['monthly']),
                'annual': fmt.money(package['annual']),
                'change': fmt.signed_money(package['change']['delta']) if package['change'] else '',
                'change_pct': fmt.pct(package['change']['pct']) if package['change'] else '',
                'note': '' if package['same_people'] or not package['reason'] else 'Enrollment differs from today',
            }
        )
    return rows


def summary(plans, results, packages, recommendation, labels, reason_text):
    current = next((p for p in packages if p['key'] == 'current'), None)
    recommended = [p for p in plans if p.recommended]

    def option(plan):
        result = results[plan.id]
        return {
            'plan_id': plan.id,
            'label': plan.option_label,  # blank until the proposal is issued; carrier and name follow it
            'carrier': plan.carrier,
            'name': plan.name,
            'annual': fmt.money(result['annual']),
            'change': fmt.signed_money(result['change']['delta']) if result['change'] else '',
            'change_pct': fmt.pct(result['change']['pct']) if result['change'] else '',
            'note': f"Part of {result['part_of']}'s enrollment" if result['part_of'] else '',
        }

    groups = [
        {'current': p.name, 'options': [option(r) for r in recommended if p.id in results[r.id]['base_ids']]}
        for p in plans
        if p.role == 'current'
    ]
    if not groups:
        groups = [{'current': '', 'options': [option(r) for r in recommended]}]
    return {
        'today_annual': fmt.money(current['annual']) if current else '',
        'groups': groups,
        'packages': package_rows(recommendation['packages'], recommended, labels),
        'reasons': reason_text,
        'covered': recommendation['covered'],
        'missing': recommendation['missing'],
    }
