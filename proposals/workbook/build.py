"""The client spreadsheet, built (plan.md §9.4; J145–J154): the deal read once (`facts`), its tabs laid out (`layout`)
and drawn on the sheet model in order, then written (`write`). The file opens on the first Compare tab when there is
one (the tab the team presents from), else on the Cover; its author is the agency, never the user who pressed the
button (J152). Draft until issued: the Draft mark rides each tab's page header, never the Cover (J102; OQ35).

`workbook(deal) -> (bytes, file name)`; `book(deal) -> Book` (the model, for the tests and, from slice 28, the
Export viewer); both raise `NothingToPresent` with the producer's sentence when no line has a tab.
"""

from dataclasses import dataclass, field

from deals.downloads import safe_filename

from . import bank, facts, layout, write
from .model import Book
from .tabs import all_plans, compare, composite, cover, disclaimers, generic, in_force, markets, rates

AGENCY_FALLBACK = 'Vantage Risk Solutions'


class NothingToPresent(Exception):
    """The workbook cannot be built from this proposal; the message is the sentence the producer reads."""


@dataclass
class Context:
    facts: object
    layout: object
    banks: dict
    sheets: frozenset  # the file's tab titles: what a lookup formula may name
    draft: str
    maps: dict = field(default_factory=dict)  # {line: the rates tab's geometry}, for the Compare tab's counts


WRITERS = {
    'cover': lambda sheet, ctx, line: cover.write(sheet, ctx),
    'markets': lambda sheet, ctx, line: markets.write(sheet, ctx),
    'rates': lambda sheet, ctx, line: ctx.maps.__setitem__(line.key, rates.write(sheet, ctx, line)),
    'generic': lambda sheet, ctx, line: generic.write(sheet, ctx, line),
    'in_force': lambda sheet, ctx, line: in_force.write(sheet, ctx, line),
    'compare': lambda sheet, ctx, line: compare.write(sheet, ctx, line),
    'composite': lambda sheet, ctx, line: composite.write(sheet, ctx, line),
    'bank': lambda sheet, ctx, line: all_plans.write(sheet, ctx, line),
    'disclaimers': lambda sheet, ctx, line: disclaimers.write(sheet, ctx),
}


def from_facts(found, draft=None):
    """The `Book` for read facts (pure: no query)."""
    banks = bank.banks(found)
    tabs = layout.tabs(found, banks, bool(found.output.get('disclaimers', True)))
    message = layout.refusal(tabs)
    if message:
        raise NothingToPresent(message)
    titles = frozenset(tab.title for tab in tabs.tabs)
    ctx = Context(found, tabs, banks, titles, found.draft if draft is None else draft)
    lines = {line.key: line for line in found.lines}
    book = Book(author=found.agency['name'] or AGENCY_FALLBACK)
    for tab in tabs.tabs:
        sheet = book.sheet(tab.title)
        WRITERS[tab.kind](sheet, ctx, lines.get(tab.line))
    first_compare = next((i for i, tab in enumerate(tabs.tabs) if tab.kind == 'compare'), None)
    book.opens_on = first_compare if first_compare is not None else 0
    return book


def book(deal):
    return from_facts(facts.read_deal(deal))


def filename(deal, draft=True):
    """`<Client> - <year> Benefits Proposal[-DRAFT].xlsx` (J104): the effective date's year."""
    year = deal.effective_date.year if deal.effective_date else ''
    stem = f'{deal.client.name} - {year} Benefits Proposal'.replace('  ', ' ')
    return safe_filename(f'{stem}{"-DRAFT" if draft else ""}.xlsx')


def workbook(deal):
    """(.xlsx bytes, file name) of the draft client spreadsheet."""
    return write.to_bytes(book(deal)), filename(deal)
