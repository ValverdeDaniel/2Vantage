"""Writes to a booked record by hand (plan.md §5.6, §7.10; H54–H56, H58): `edit_record`, `set_shares`, `add_to_book`.

All three are the all tier's (the views check it). An edited fact gets a `typed` source, so booking never changes it
again (H28, H54); a move to an ended status adds a term end when there is none. Typed shares are stored on the record's
terms with their reason and override only that record (H55). Add to book books a client from outside the app, found
first among existing clients or created with no deal and a Status, Existing client by default (H58, review 22).
Each locks the record's Deal (when it has one), then the record; each records one Activity row in area `commission`:
on the deal, or a firm row about the record (`subject` `record:<id>`). An edit row carries each key's earlier origin
under `record_source:<id>`, so Revert puts the value back as the sale (or the agency) gave it.
"""

from collections import namedtuple

from django.db import IntegrityError, transaction
from rest_framework.exceptions import ValidationError

from deals import activity, clock, lifecycle, lines, values
from deals.models import Client, Deal
from deals.services import create_client

from .. import book_rules, math, rules, terms, vocab
from ..models import Party, Record
from . import clean
from .booking import target
from .rates import AREA

Edited = namedtuple('Edited', 'record changed activity')
TAKEN = 'Another record of this deal already books that carrier on this line.'
NO_REASON = 'Say why the frozen shares are changing (it goes in the history).'
BAD_TOTAL = 'The shares must total 100 % (now {total} %).'


def subject_of(record):
    return '' if record.deal_id else target(record.id)


def _locked(record_id):
    deal_id = Record.objects.values_list('deal_id', flat=True).get(pk=record_id)
    if deal_id:
        values.locked(Deal, deal_id)
    return values.locked(Record, record_id)


def _save(record):
    try:
        with transaction.atomic():
            record.save()
    except IntegrityError as exc:
        raise activity.Refused(TAKEN) from exc


def _label(record):
    return f'{lines.label(record.line)} — {record.carrier or "no carrier"}'


@transaction.atomic
def edit_record(by, record_id, changes):
    """Type any of the facts and the notes (H54, H56). Returns Edited(record, {key: [before, after]}, Activity|None)."""
    facts, notes = clean.record_changes(changes)
    record = _locked(record_id)
    merged = book_rules.facts(record)
    if facts.get('status') in vocab.ENDED and 'term_end' not in facts and not merged.get('term_end'):
        facts['term_end'] = clock.today().isoformat()
    origins = {key: book_rules.origin(record.sources, key) for key in facts}
    diff = values.apply(merged, record.sources, facts, values.source('typed', by))
    book_rules.split_facts(record, merged)
    if notes is not None and notes != record.notes:
        diff['notes'] = [record.notes, notes]
        record.notes = notes
    if not diff:
        return Edited(record, {}, None)
    record.updated_by = by
    _save(record)
    entries = [activity.change(target(record.id), diff)]
    moved = {key: [origins[key], book_rules.TYPED] for key in diff if origins.get(key, book_rules.TYPED) != 'typed'}
    if moved:
        entries.append(activity.change(f'record_source:{record.id}', moved))
    entry = activity.record(
        record.deal,
        by,
        AREA,
        'updated',
        f'Edited the booked {_label(record)} record',
        changes=entries,
        subject=subject_of(record),
    )
    return Edited(record, diff, entry)


def _clean_shares(rows, reason):
    if not isinstance(rows, list) or not rows:
        raise ValidationError({'shares': ['Send the shares as a list.']})
    asked = [row.get('party') for row in rows if isinstance(row, dict) and isinstance(row.get('party'), int)]
    known = set(Party.objects.filter(pk__in=asked).values_list('pk', flat=True))
    errors, out, seen, total = {}, [], set(), 0
    for i, row in enumerate(rows):
        row = row if isinstance(row, dict) else {}
        role = row.get('role')
        party = None if role == 'house' else row.get('party')
        if role not in ('house', *vocab.ROLE_KEYS):
            errors[f'shares.{i}.role'] = ['Unknown role.']
        elif role != 'house' and party not in known:
            errors[f'shares.{i}.party'] = ['Pick a person.']
        elif (party or 'house') in seen:
            errors[f'shares.{i}.party'] = ['Listed twice.']
        seen.add(party or 'house')
        pct, error = clean.percent(row.get('pct'))
        if error:
            errors[f'shares.{i}.pct'] = [error]
            continue
        share = math.millionths(pct)
        total += share
        out.append({'party': party, 'role': role, 'pct': math.pct_text(share)})
    if not errors and total != math.MILLION:
        errors['shares.total'] = [BAD_TOTAL.format(total=math.pct_text(total))]
    if not str(reason or '').strip():
        errors['reason'] = [NO_REASON]
    if errors:
        raise ValidationError(errors)
    return out, ' '.join(str(reason).split())[: vocab.LIMITS['reason']]


@transaction.atomic
def set_shares(by, record_id, rows, reason=''):
    """Type the record's shares (H55): [{party (None for the house), role, pct}] totalling 100, with a reason. `rows`
    None puts the frozen terms' shares back. Returns Edited."""
    shares, why = (None, '') if rows is None else _clean_shares(rows, reason)
    record = _locked(record_id)
    before = record.terms or {}
    after = {**before, 'shares': shares, 'reason': why}
    diff = {key: [before.get(key), after[key]] for key in ('shares', 'reason') if before.get(key) != after[key]}
    if not diff:
        return Edited(record, {}, None)
    record.terms, record.party_ids, record.updated_by = after, terms.party_ids(after), by
    record.save()
    entry = activity.record(
        record.deal,
        by,
        AREA,
        'updated',
        f'Changed the shares on the booked {_label(record)} record',
        changes=[activity.change(target(record.id), diff)],
        subject=subject_of(record),
    )
    return Edited(record, diff, entry)


def _client(by, data):
    """The client a booking by hand is for: an existing one (archived ones too, H112), or a new one with no deal."""
    if data.get('client') not in (None, ''):
        pk = clean.record_id(data.get('client'), 'client')
        return values.locked(Client, pk)
    name = ' '.join(str(data.get('client_name') or '').split())
    if not name:
        raise ValidationError({'client': ['Pick a client, or type a new client name.']})
    status = data.get('relationship') or lifecycle.EXISTING_CLIENT
    client, _deal = create_client(by, name=name, relationship=status, first_deal=False)
    return client


@transaction.atomic
def add_to_book(by, data):
    """Book a line by hand (H58): {client | client_name + relationship, line, carrier, effective_date, premium_annual,
    rate, employees, plan_label, policy_number, year_number, notes}. Returns Edited(record, changes, Activity)."""
    if not isinstance(data, dict):
        raise ValidationError({'non_field_errors': ['Send the fields as an object.']})
    line = data.get('line')
    if line not in lines.BY_KEY:
        raise ValidationError({'line': ['Pick a line.']})
    facts, notes = clean.record_changes({k: v for k, v in data.items() if k in clean.FIELDS and k != 'status'})
    typed_year, error = rules.clean_years(data.get('year_number'))
    if error:
        raise ValidationError({'year_number': [error]})
    client = _client(by, data)
    effective = facts.get('effective_date')
    dates = Record.objects.filter(client_id=client.id).exclude(status=vocab.VOID).values_list('effective_date')
    earlier = book_rules.earlier_years([row[0] for row in dates], clean.day(effective)) if effective else 0
    year = rules.year_number(typed_year, client.relationship, earlier)
    record = Record(client=client, line=line, booked_by=by, updated_by=by, year_number=year, is_renewal=year != 1)
    merged = {'status': vocab.BOOKED}
    diff = values.apply(merged, record.sources, {k: v for k, v in facts.items() if v != ''}, values.source('typed', by))
    book_rules.split_facts(record, merged)
    record.terms = terms.for_client(by, client, year)
    record.party_ids = terms.party_ids(record.terms)
    record.notes = notes or ''
    record.save()
    entry = activity.record(
        None,
        by,
        AREA,
        'created',
        f'Added to the book by hand: {_label(record)}',
        changes=[activity.change(target(record.id), {**diff, 'year_number': [None, year]})],
        subject=target(record.id),
    )
    return Edited(record, diff, entry)
