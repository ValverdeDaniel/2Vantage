"""Set-up for the SBC and re-check tests (plan.md §10.4; slice 22): synthetic SBC files, the answer a perfect read of
one gives in the reader's schema, and plans whose values a quote read put on the deal.

Every carrier, plan and figure is invented. A one-page PDF is read as one range, `p1`, so the fake client's key for an
SBC read of it is ('sbc', the file's hash, 'p1'), and for a re-check of values recorded on its page 1
('recheck', the hash, 'p1#1').
"""

import hashlib

import synthetic_files
from ai import services as ai
from conftest import make_deal
from documents import services as documents
from quotes import services
from quotes.tests.review_world import read_into

LABELS = {
    'plan_type': 'Plan type',
    'network': 'Network',
    'deductible_single': 'What is the overall deductible? (individual)',
    'deductible_family': 'What is the overall deductible? (family)',
    'oop_max_single': 'What is the out-of-pocket limit? (individual)',
    'pcp_copay': 'Primary care visit',
    'specialist_copay': 'Specialist visit',
    'er_copay': 'Emergency room care',
    'rate_ee': 'Monthly premium (employee)',
}


def sbc_pdf(carrier, name, values):
    lines = [f'Summary of Benefits and Coverage: {carrier} {name}', 'Coverage period: 01/01/2027 - 12/31/2027']
    lines += [f'{LABELS.get(key, key)}: {value}' for key, value in values.items()]
    return synthetic_files.text_pdf(lines)


def answer(carrier, name, values, number=''):
    column = {
        'col': 1,
        'carrier': carrier,
        'plan_name': name,
        'plan_number': number,
        'codes': [],
        'side': 'quote',
        'renews_col': -1,
        'replaces': '',
        'unsure': False,
    }
    rows = [
        {
            'label': LABELS.get(key, key),
            'key': key,
            'cells': [{'col': 1, 'value': value, 'page': 1, 'cell': '', 'unsure': False}],
        }
        for key, value in values.items()
    ]
    return {'lines': [{'line': 'medical', 'columns': [column], 'rows': rows, 'counts': []}]}


def file_hash(document):
    with document.file.open('rb') as handle:
        return hashlib.sha256(handle.read()).hexdigest()[:16]


def add_sbc(user, deal, fake, carrier, name, values, number=''):
    """An SBC on the deal, with a perfect read recorded for it; returns the Document."""
    raw = sbc_pdf(carrier, name, values)
    document = documents.store_bytes(user, deal, f'{name} SBC (synthetic).pdf', raw, 'sbc', f'{name} SBC')
    fake.record(('sbc', file_hash(document), 'p1'), answer(carrier, name, values, number))
    return document


def read_sbc(person, deal, document, plan=None):
    job, _created = ai.start_read(person, deal, [document.id], target='sbc', plan=plan)
    job.refresh_from_db()
    return job


def quote_world(user):
    """A deal with a quote file and three medical plans: a current plan typed by hand, its renewal and a Cigna quote
    whose values a quote read put on the deal (origin `ai`)."""
    deal = make_deal(user)
    quote = documents.store_bytes(
        user, deal, 'quote.pdf', synthetic_files.text_pdf(['Example quote', 'Gold PPO']), 'quote', 'Quote'
    )
    current = services.create_plan(
        user,
        deal,
        line='medical',
        role='current',
        carrier='Seabreeze Health',
        name='Gold PPO 2000',
        values={'pcp_copay': '25', 'deductible_single': '2000'},
    )
    renewal = services.create_renewal(user, current.id)
    cigna = services.create_plan(
        user,
        deal,
        line='medical',
        role='alternate',
        carrier='Cigna',
        name='Open Access 2500',
        replaces_ids=[current.id],
    )
    cigna = read_into(cigna, {'pcp_copay': '30', 'deductible_single': '2500', 'rate_ee': '512.34'}, quote)
    return deal, current, renewal, cigna
