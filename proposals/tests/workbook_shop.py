"""The synthetic deal and the helpers the Compare, Composite Rates and All Plans tests share (test_workbook_compare)."""

from types import SimpleNamespace

import pytest

from conftest import make_deal
from proposals import services as proposals
from proposals.workbook import bank, facts, layout
from proposals.workbook.model import TEXT, Book
from proposals.workbook.tabs import all_plans, bank_map, compare, composite
from quotes import services as plans

RATES = ('rate_ee', 'rate_es', 'rate_ec', 'rate_fam')


def _rates(*figures):
    return dict(zip(RATES, figures, strict=True))


def _plan(user, deal, carrier, name, role='alternate', **extra):
    return plans.create_plan(user, deal, line='medical', role=role, carrier=carrier, name=name, **extra)


@pytest.fixture
def shop(user):
    """One medical line: today's plan (typed counts 10/2/1/3, the employer paying 80% and half the dependent cost),
    its renewal, two starred Cigna quotes (one recommended), and four quotes left off the proposal: UHC, Oscar (a
    quoted premium only), Humana (hidden on Markets checked) and Kaiser (no rate)."""
    deal = make_deal(user)
    current = _plan(
        user,
        deal,
        'Aetna',
        'HMO 1000',
        role='current',
        values={
            **_rates('500', '1000', '900', '1400'),
            'contrib_ee': '400',
            'contrib_es': '650',
            'contrib_ec': '600',
            'contrib_fam': '850',
            'deductible_single': '1000',
            'sbc_url': 'https://example.com/sbc/hmo-1000.pdf',
        },
    )
    plans.set_enrollment(
        user, deal, 'medical', plans=[{'id': current.id, 'enrollment': {'EE': 10, 'ES': 2, 'EC': 1, 'FAM': 3}}]
    )
    renewal = _plan(
        user,
        deal,
        'Aetna',
        'HMO 1000',
        role='renewal',
        renews_id=current.id,
        values=_rates('550', '1100', '990', '1540'),
    )
    c1 = _plan(
        user,
        deal,
        'Cigna',
        'LocalPlus 1000',
        replaces_ids=[current.id],
        values={**_rates('480.50', '961.10', '865.45', '1345.40'), 'deductible_single': '1500'},
    )
    c2 = _plan(
        user,
        deal,
        'Cigna',
        'Open Access 2000',
        replaces_ids=[current.id],
        values=_rates('470.12', '940', '850', '1300'),
    )
    others = {
        'uhc': _plan(user, deal, 'UnitedHealthcare', 'Choice Plus', values=_rates('490', '980', '880', '1380')),
        'oscar': _plan(user, deal, 'Oscar', 'Bronze', values={'rate_ee': '400', 'group_premium_monthly': '11000.4'}),
        'humana': _plan(user, deal, 'Humana', 'Gold', values=_rates('450', '900', '800', '1250')),
        'kaiser': _plan(user, deal, 'Kaiser', 'Silver'),
    }
    plans.star(user, deal, [c1.id, c2.id], True)
    plans.set_recommended(user, c1.id, True)
    proposals.set_config(user, deal, {'markets.lines.medical.hidden': ['humana']})
    return {'deal': deal, 'current': current, 'renewal': renewal, 'c1': c1, 'c2': c2, **others}


WRITERS = {'compare': compare.write, 'composite': composite.write, 'bank': all_plans.write}


def _book(deal, maps=None):
    """The deal's Compare, Composite Rates and All Plans tabs drawn as build.py draws them (`ctx` is its Context; the
    other tabs stay empty here). `maps`: the rates tabs' geometry, which the Compare counts link to."""
    found = facts.read_deal(deal)
    banks = bank.banks(found)
    tabs = layout.tabs(found, banks, True)
    ctx = SimpleNamespace(
        facts=found,
        layout=tabs,
        banks=banks,
        sheets=frozenset(tab.title for tab in tabs.tabs),
        draft='Draft for review',
        maps=maps or {},
    )
    lines = {line.key: line for line in found.lines}
    book = Book(author=found.agency['name'])
    for tab in tabs.tabs:
        sheet = book.sheet(tab.title)
        if tab.kind in WRITERS:
            WRITERS[tab.kind](sheet, ctx, lines[tab.line])
    return book


def _tab(book, kind_title):
    return next(sheet for sheet in book.sheets if sheet.title == kind_title)


def _compare(book):
    return next(sheet for sheet in book.sheets if sheet.title.startswith('Dynamic '))


def _all_plans(book):
    return next(sheet for sheet in book.sheets if sheet.title.endswith(' All Plans'))


def _column(sheet, col, first=bank_map.FIRST_ROW):
    rows = sorted(row for row, c in sheet.cells if c == col and row >= first)
    return [sheet.get(row, col).value for row in rows if sheet.get(row, col).kind == TEXT]


def _picks(sheet):
    return [sheet.get(7, 3 + 2 * k).value for k in range(16)]
