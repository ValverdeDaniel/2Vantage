"""One line laid out as the client files print it, with its option numbers (plan.md §5.4, §7.12; F37, J49, J159;
J.5 B4).

`lay_out` is what the Pages read, the builder and Issue share, so a draft's "Option n" is the number Issue stamps:
the plans the line presents (quotes' `presented()`, in `order.layout`'s order), its pages (`pages.sequence`, the one
splitter, under the deal's chosen layout), and each plan's number in the order the client first reads it
(`quotes.labels.numbers`: a stored number stays, the others follow the highest stored on the line). `reading_ids`
gives Issue every presented plan in that order, line by line (slice 32 passes it to `stamp_option_numbers`).
"""

from collections import namedtuple

from django.db.models import Max

from intake.selectors import line_facts
from quotes import labels, presented
from quotes import selectors as quotes
from quotes.models import Plan

from . import config as settings
from . import page_columns as cols
from . import pages as splitter
from .models import ProposalConfig

Laid = namedtuple('Laid', 'rows shown numbers pages options')


def tops(deal, line_keys):
    """{line: the highest option number stored on it}, removed plans included (a number is never reused). One query."""
    rows = (
        Plan.all_objects.filter(deal=deal, line__in=list(line_keys))
        .order_by()
        .values_list('line')
        .annotate(top=Max('option_number'))
    )
    return {line: top or 0 for line, top in rows}


def stored_config(deal):
    return ProposalConfig.objects.filter(deal=deal).values_list('config', flat=True).first() or {}


def layout_of(config):
    return settings.get(config, 'output.layout')


def options(pages, data, rows, top):
    """{plan id: "Option n"} for the plans the pages show, as Issue will stamp them."""
    order = [data.by_id[pid] for pid in splitter.reading_order(pages)]
    stored = {pid: row.option_number for pid, row in rows.items() if row.option_number}
    return labels.numbers(order, stored, top)


def lay_out(state, off, layout, top):
    """The line's `Laid`: model rows by id, the presented plans, the current plans' slot numbers (Current 1, 2…), the
    pages and the option numbers. `off` is the intent's reason for keeping the line off (it presents nothing)."""
    data = state.data
    rows = {plan.id: plan for plan in state.plans}
    shown = presented.presented(data, off=bool(off))
    numbers = {plan.id: n for n, plan in enumerate(data.current, start=1)}
    captions = {plan.id: f'Replacing: {cols.words(rows[plan.id])}' for plan in data.current}
    picks = [plan.id for plan in shown if plan.recommended]
    columns = [cols.column(plan, data) for plan in shown]
    pages = splitter.sequence(columns, captions, layout=layout, picks=picks)
    return Laid(rows, shown, numbers, pages, options(pages, data, rows, top))


def reading_ids(deal):
    """Every plan the proposal presents, line by line, each line in the order its pages are read: what Issue stamps."""
    states = quotes.deal_state(deal)
    held = {line: {'sold': any(plan.sold for plan in state.plans)} for line, state in states.items()}
    _states, off = line_facts(deal, held)
    config = stored_config(deal)
    keys = settings.ordered(config, [line for line in states if line not in off])
    found = tops(deal, keys)
    out = []
    for line in keys:
        laid = lay_out(states[line], None, layout_of(config), found.get(line, 0))
        out.extend(splitter.reading_order(laid.pages))
    return out
