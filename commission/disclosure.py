"""The CAA / ERISA §408(b)(2) compensation disclosure: the data (plan.md §9.15; H108; OQ76's default: the back office
downloads it and sends it inside its own close-out email; the app sends no email, OQ82).

Ported from 891f1b3 `commissions/disclosure.py`. D-020: required whenever the agency earns commission on a client's
medical, dental or vision plans; it carries the rate per line (already every deal user's) and the carrier, never a
split or anyone's earnings. Built from the deal's live booked records, one per line (the first booked):
- pct → "Percentage of Premium"; pepm → "USD$ Per Employee Per Month"; flat → the additional-compensation sentence;
  the "Per Plan Member Per Month" column is always N/A; a line with no record or no rate reads N/A;
- the template's fourth row, Medical Stop Loss Insurance, is fixed at N/A.
The address is the intake's mailing address (else the physical one); the recipient the client's primary contact.
"""

from decimal import Decimal, InvalidOperation

from deals import comp as comps
from deals.models import AgencySettings, Contact
from intake.models import Intake

from . import vocab
from .models import Record

MDV_LINES = ('medical', 'dental', 'vision')
ROW_LABELS = {'medical': 'Medical Insurance', 'dental': 'Dental Insurance', 'vision': 'Vision Insurance'}
STOP_LOSS_ROW = 'Medical Stop Loss Insurance'
NOTHING_BOOKED = 'No medical, dental or vision commission is booked on this deal yet.'


def _money(value):
    try:
        return f'${Decimal(str(value)):,.2f}'
    except (InvalidOperation, ValueError, TypeError):
        return str(value)


def rows(records):
    """(the table's four rows of display text, the additional-compensation sentences)."""
    by_line = {}
    for record in records:
        by_line.setdefault(record.line, record)
    out, additional = [], []
    for line in MDV_LINES:
        label = ROW_LABELS[line]
        record = by_line.get(line)
        row = {'label': label, 'pmpm': 'N/A', 'pepm': 'N/A', 'pct': 'N/A', 'carrier': 'N/A'}
        if record is not None:
            comp = record.values.get('rate') or {}
            kind = comp.get('type')
            if kind == comps.PCT:
                row['pct'] = comps.comp_label(comp) or 'N/A'
            elif kind == comps.PEPM:
                row['pepm'] = _money(comp.get('value'))
            elif kind == comps.FLAT:
                additional.append(f'{_money(comp.get("value"))} per year with respect to {label}')
            if record.carrier:
                row['carrier'] = record.carrier
        out.append(row)
    out.append({'label': STOP_LOSS_ROW, 'pmpm': 'N/A', 'pepm': 'N/A', 'pct': 'N/A', 'carrier': 'N/A'})
    return out, additional


def _address(deal):
    answers = Intake.objects.filter(deal_id=deal.id).values_list('answers', flat=True).first() or {}
    address = str(answers.get('address_mailing') or answers.get('address_physical') or '').strip()
    return [line.strip() for line in address.splitlines() if line.strip()]


def _recipient(deal):
    contacts = Contact.objects.filter(client_id=deal.client_id)
    contact = contacts.filter(is_primary=True).first() or contacts.order_by('sort_order', 'id').first()
    return contact.name if contact and contact.name else ''


def data(deal):
    """Everything the PDF needs, as plain values; `has_records` is False when nothing is booked on these lines."""
    records = list(
        Record.objects.filter(deal_id=deal.id, line__in=MDV_LINES)
        .exclude(status=vocab.VOID)
        .order_by('line', 'booked_at', 'id')
    )
    table, additional = rows(records)
    name = deal.client.name
    return {
        'agency': AgencySettings.get().name,
        'client_name': name,
        'recipient': _recipient(deal) or name,
        'address_lines': _address(deal),
        'rows': table,
        'additional_comp': additional,
        'has_records': bool(records),
    }
