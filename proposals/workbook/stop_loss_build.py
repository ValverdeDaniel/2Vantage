"""The stop-loss analysis workbook, built (plan.md §9.13; J166, F106, G117, OQ43, OQ104): Stephanie's five-tab analysis
generated — In-Force Snapshot · Option Comparison · Binding Notes · Glossary · FIE Rates — with live formulas whose
stored results are quotes' exact figures (`quotes/math/stop_loss.py`), written through `xlsx_safe` like the client
spreadsheet (`write.to_bytes`).

It is the client document for self-funded and level-funded deals (OQ43's default), so it prints client fields only:
laser liability as amounts and lasers by position, never the claimant ids or initials of `sl_lasers` (OQ104's default;
the old sheet printed them). The Binding Notes read the SIIA disclosure through quotes' `disclosure_state` provider
(G117). It refuses a deal with no stop-loss plan, and one with two or more in-force contracts (F106), with the
producer's sentence.

`book(deal) -> Book` (the model, for the tests); `workbook(deal) -> (bytes, file name)`; both raise `Refused`.
"""

from django.utils.text import slugify

from deals.downloads import safe_filename
from deals.models import AgencySettings
from quotes.selectors import binding, stop_loss_file

from . import write
from .model import Book
from .tabs import stop_loss_look as look
from .tabs import stop_loss_notes, stop_loss_options, stop_loss_snapshot

AGENCY_FALLBACK = 'Vantage Risk Solutions'
TABS = (
    (look.SNAPSHOT, stop_loss_snapshot.write),
    (look.OPTIONS, stop_loss_options.write),
    (look.NOTES, stop_loss_notes.write_binding),
    (look.GLOSSARY, stop_loss_notes.write_glossary),
    (look.FIE, stop_loss_notes.write_fie),
)


class Refused(Exception):
    """The workbook cannot be built for this deal; the message is the sentence the producer reads."""


def facts(deal):
    """Everything the five tabs print, read once: quotes' client-safe stop-loss read, the binding notes, the client
    and the agency. Raises `Refused`."""
    found = stop_loss_file.read(deal)
    if found['refusal']:
        raise Refused(found['refusal'])
    plans = ([found['current']] if found['current'] else []) + found['options']
    shared = max((max(plan['shared'], default=0) for plan in plans), default=0)
    return {
        **found,
        'client': deal.client.name,
        'author': AgencySettings.get().name or AGENCY_FALLBACK,
        'binding': binding.binding_notes(deal),
        'shared_rows': shared,
        'snapshot_rows': look.snapshot_rows(found['laser_rows']),
        'option_rows': look.option_rows(found['laser_rows']),
    }


def from_facts(ctx):
    """The `Book` for read facts (pure: no query)."""
    book = Book(author=ctx['author'])
    for title, writer in TABS:
        writer(book.sheet(title), ctx)
    book.opens_on = 0
    return book


def book(deal):
    return from_facts(facts(deal))


def filename(deal):
    """`<client-slug>-stop-loss-analysis.xlsx`, the old app's name for this file."""
    return safe_filename(f'{slugify(deal.client.name) or "deal"}-stop-loss-analysis.xlsx')


def workbook(deal):
    """(.xlsx bytes, file name) of the stop-loss analysis workbook."""
    return write.to_bytes(book(deal)), filename(deal)
