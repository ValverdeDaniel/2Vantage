"""Set-up for the review tests (plan.md §10.7): plans whose values a quote read put on the deal, from a synthetic file.

`read_into` lands values the way a read does (origin `ai`, the file and page, Claude's doubt, the locator's answer)
straight onto the row: test set-up standing in for slice 19's read apply, which these tests do not exercise. A save
of the row rewrites `flags` (Plan.save), so the stored count is right from the start.
"""

import synthetic_files
from conftest import make_deal
from deals.values import apply, source
from documents import services as documents
from quotes import services
from quotes.models import Plan

QUOTE_PDF = synthetic_files.text_pdf(['Example Health quote', 'Gold PPO 1500', 'Deductible $1,500', 'Employee $512.34'])


def add_file(user, deal, name='example-quote.pdf'):
    return documents.store_bytes(user, deal, name, QUOTE_PDF, 'quote', 'Example quote')


def read_into(plan, values, doc, *, page=1, low=(), loc=None):
    """Values as a read lands them: `low` names the keys Claude doubted, `loc` maps keys to the locator's answer."""
    loc = loc or {}

    def entry(key):
        doubt = 'two figures for one tier' if key in low else None
        return source('ai', None, doc=doc.id, page=page, low=doubt, loc=loc.get(key))

    plan = Plan.objects.get(pk=plan.id)
    apply(plan.values, plan.sources, values, entry)
    plan.save()
    return plan


def world(user):
    """A deal with one quote file and three medical plans: Aetna current (typed), Cigna and UHC read from the file,
    with two doubted values on Cigna and one not found in the file on UHC."""
    deal = make_deal(user)
    doc = add_file(user, deal)
    current = services.create_plan(
        user, deal, line='medical', role='current', carrier='Aetna', name='HMO 1500', values={'rate_ee': '480'}
    )
    cigna = services.create_plan(
        user, deal, line='medical', role='alternate', carrier='Cigna', name='Open Access', replaces_ids=[current.id]
    )
    uhc = services.create_plan(
        user, deal, line='medical', role='alternate', carrier='UHC', name='Choice', replaces_ids=[current.id]
    )
    cigna = read_into(
        cigna,
        {'deductible_single': '1500', 'rate_ee': '512.34', 'rate_fam': '1580.47', 'network': 'Open Access'},
        doc,
        low=('rate_ee', 'rate_fam'),
    )
    uhc = read_into(
        uhc,
        {'deductible_single': '2000', 'rate_ee': '530'},
        doc,
        loc={'rate_ee': {'state': 'absent', 'v': 1}, 'deductible_single': {'state': 'found', 'page': 1, 'v': 1}},
    )
    return {'deal': deal, 'doc': doc, 'current': current, 'cigna': cigna, 'uhc': uhc}
