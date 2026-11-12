"""Booking at the sale (plan.md §5.6; H25–H32, H36, H124): `on_sold_changed`, `book_deal`, `rebook`.

- quotes sends `sold_changed` once the sale commits (`quotes.signals`, `send_robust`); `on_sold_changed`, connected in
  AppConfig.ready(), books in its own transaction, so a booking error is logged and never undoes the sale (H25). The
  tab then reads "Sold — not booked · Book now" (`selectors`).
- `book_deal` makes the deal's records equal what it books today (`to_book.targets`): one per line and carrier with
  sold plans, plus the Keep-as-is lines (H26). A record is found by its plans first, then by (line, carrier), so a
  carrier renamed on the plan updates the record instead of orphaning it (H28). Every `sale` key is refreshed, never a
  `typed` one; the terms are frozen again unless someone typed the shares (H29, H36). A record whose line has no sold
  plan now turns void, never deleted, and comes back if a plan is sold again (H32). A lost deal books nothing (H124).
- The year (H30): 1 + the client's distinct earlier effective years on records that are not void, else the typed year
  with us, else the first year unless the deal opened for an Existing client (`opened_as`, which the sale froze).
  Booking year N flips the client's earlier booked or active records on that line to renewed, with a term end (H31).
- `rebook` is Book now, the tab's Update (H120) and the drawer's Rebook: `book_deal` again, never a 409 (H36).
Each call locks the Deal, then the deal's records by id, then the client's earlier records it flips; it records one
Activity row (area `commission`, action `booked`) holding each record's before and after, which Revert refuses: a
booking follows the sale (un-sell, or Rebook, instead).
"""

import logging
from collections import namedtuple

from django.contrib.auth import get_user_model
from django.db import transaction

from deals import activity, lines, values
from deals.models import Deal
from deals.rules import refuses

from .. import book_rules, rules, terms, to_book, vocab
from ..models import Commission, Record
from .rates import AREA

log = logging.getLogger(__name__)
Booked = namedtuple('Booked', 'records changes activity')
FOLLOWS_SALE = 'A booking follows the sale: un-sell the plan, or Rebook, instead.'


def target(record_id):
    return f'record:{record_id}'


def _label(record):
    return f'{lines.label(record.line)} — {record.carrier or "no carrier"}'


def _earlier(deal, effective):
    dates = (
        Record.objects.filter(client_id=deal.client_id)
        .exclude(deal_id=deal.id)
        .exclude(status=vocab.VOID)
        .values_list('effective_date', flat=True)
    )
    return book_rules.earlier_years(list(dates), effective)


def _apply(record, by, wanted):
    """Refresh the record's sale keys from `wanted` (a Target; None voids it). Returns {key: [before, after]}."""
    merged = book_rules.facts(record)
    sources = record.sources
    if wanted is None:
        changes = {'status': vocab.VOID}  # the sale is undone, whatever status was typed
    else:
        changes = {key: wanted.facts.get(key, '') for key in book_rules.SALE_KEYS}
        changes = {key: value for key, value in changes.items() if not book_rules.typed(sources, key)}
        if record.status == vocab.VOID and book_rules.origin(sources, 'status') != book_rules.TYPED:
            changes['status'] = vocab.BOOKED
    origins = wanted.origins if wanted else {}
    diff = values.apply(merged, sources, changes, lambda key: values.source(origins.get(key, 'sale'), by))
    book_rules.split_facts(record, merged)
    return diff


def _summary(booked, voided):
    """ "Booked commission: Medical — Cigna" · "Voided commission: … (no plan is sold now)" · "Updated booked …"."""
    parts = []
    if booked:
        parts.append('Booked commission: ' + ', '.join(booked))
    if voided:
        parts.append('Voided commission: ' + ', '.join(voided) + ' (no plan is sold now)')
    return '; '.join(parts) or 'Updated the booked commission'


def _terms(record, frozen, year):
    """Freeze the terms and the year again, keeping typed shares and their reason (H36)."""
    diff = {}
    before = record.terms or {}
    after = {**frozen, 'shares': before.get('shares'), 'reason': before.get('reason', '')} if before else frozen
    if before != after:
        diff['terms'] = [before or None, after]
        record.terms = after
        record.party_ids = terms.party_ids(after)
    if record.year_number != year:
        diff['year_number'] = [record.year_number, year]
        record.year_number = year
    record.is_renewal = year != 1
    return diff


def _renew_earlier(by, record):
    """Booking year N renews the client's earlier live records on the line, with a term end (H31)."""
    if record.status == vocab.VOID or record.effective_date is None:
        return []
    earlier = (
        Record.objects.select_for_update()
        .filter(client_id=record.client_id, line=record.line, status__in=vocab.LIVE)
        .filter(effective_date__lt=record.effective_date)
        .exclude(deal_id=record.deal_id)
        .order_by('id')
    )
    changes = []
    for other in earlier:
        merged = book_rules.facts(other)
        wanted = {'status': vocab.RENEWED, 'term_end': record.effective_date.isoformat()}
        wanted = {key: value for key, value in wanted.items() if not book_rules.typed(other.sources, key)}
        diff = values.apply(merged, other.sources, wanted, values.source('sale', by))
        if diff:
            book_rules.split_facts(other, merged)
            other.updated_by = by
            other.save()
            changes.append(activity.change(target(other.id), diff))
    return changes


@transaction.atomic
def book_deal(by, deal_id):
    """Book the deal as it stands. Returns Booked([records], changes, Activity | None); a lost deal refuses (409)."""
    deal = values.locked(Deal, deal_id)
    refusal = refuses(deal, 'book')
    if refusal:
        raise activity.Refused(refusal)
    records = list(Record.objects.select_for_update().filter(deal_id=deal.id).order_by('id'))
    wanted = to_book.targets(deal)
    typed_year = Commission.objects.filter(deal_id=deal.id).values_list('year_number', flat=True).first()
    year = rules.year_number(typed_year, deal.opened_as, _earlier(deal, deal.effective_date))
    frozen = terms.for_deal(by, deal, year) if wanted else None
    pairs, left = book_rules.match(records, wanted)
    changes, booked, booked_words, void_words = [], [], [], []
    for target_, record in pairs:
        record = record or Record(client_id=deal.client_id, deal=deal, line=target_.line, booked_by=by)
        diff = _apply(record, by, target_)
        diff.update(_terms(record, frozen, year))
        if diff or record.pk is None:
            record.updated_by = by
            record.save()
            changes.append(activity.change(target(record.id), diff))
            booked_words.append(_label(record))
        booked.append(record)
    for record in left:
        if record.status != vocab.VOID:
            diff = _apply(record, by, None)
            if diff:
                record.updated_by = by
                record.save()
                changes.append(activity.change(target(record.id), diff))
                void_words.append(_label(record))
    for record in booked:
        changes += _renew_earlier(by, record)
    entry = None
    if changes:
        entry = activity.record(deal, by, AREA, 'booked', _summary(booked_words, void_words), changes=changes,
                                revertible=False)  # fmt: skip
    return Booked(booked, changes, entry)


def rebook(by, deal_id):
    """Book now, Update and Rebook (H36, H120): the deal booked again, refreshing every sale key."""
    return book_deal(by, deal_id)


@transaction.atomic
def rebook_record(by, record_id):
    """The drawer's Rebook (H36): a deal's record rebooks its deal; a record booked by hand has no sale, so only its
    terms are frozen again from the client's split (unless its shares were typed), in the year it was booked in."""
    deal_id = Record.objects.values_list('deal_id', flat=True).get(pk=record_id)
    if deal_id:
        return book_deal(by, deal_id)
    record = values.locked(Record, record_id)
    diff = _terms(record, terms.for_client(by, record.client, record.year_number), record.year_number)
    if not diff:
        return Booked([record], [], None)
    record.updated_by = by
    record.save()
    changes = [activity.change(target(record.id), diff)]
    summary = f'Rebooked {_label(record)}'
    subject = target(record.id)
    entry = activity.record(None, by, AREA, 'booked', summary, changes=changes, subject=subject, revertible=False)
    return Booked([record], changes, entry)


def on_sold_changed(sender, deal_id, lines, user_id, **kwargs):
    """`quotes.signals.sold_changed`'s receiver: book the deal in a transaction of its own (H25). An error propagates
    to `send_robust`, which logs it; the sale stays saved and the tab shows it not booked."""
    by = get_user_model().objects.filter(pk=user_id).first() if user_id else None
    try:
        book_deal(by, deal_id)
    except activity.Refused:
        log.info('commission: deal %s was not booked (refused)', deal_id)


@transaction.atomic
def forget_client(client_id):
    """Delete the client's records, for the seeders only (`seed_golden`, which deletes and rebuilds its deals): records
    are never deleted otherwise (H32, H112)."""
    Record.objects.filter(client_id=client_id).delete()
