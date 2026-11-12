"""An approved block lands through its owner's own services (plan.md §5.8; L85, L.6 "the owner contract"; OQ84,
Ch. 6; slice 55). Called by `approvals.approve_client` inside its transaction, after the Deal and Intake locks.

A client's block answer is the list as they would have it (`client_view`), and approving it changes only what they
changed, as the old portal wrote it (891f1b3 `views/portal.py`, the contacts and coverage blocks):
- `block:contacts`: a row naming one of the client's contacts updates the fields that differ
  (`deals.services.update_contact`); a row with no id adds a contact (`create_contact`) unless the client already has
  one with that name and email. Nothing is removed, and the main contact stays the producer's call.
- `block:coverage`: a row naming one of the deal's coverage rows updates its line, carrier, funding and renewal date
  where they differ (`update_coverage`); a new row adds a line in force (`create_coverage`) unless one with that line
  and carrier is already in force. Carrier and funding are left alone on a line priced from current plans in the
  Advisor (they come from the plans there). Commission and the proposal's choices are never touched (L108).
- `block:lines`: "please shop" (Ch. 6): each ticked line not yet quoted is added through `intent.set_intent(shop=True)`,
  the one writer of the lines to quote, which lapses a confirmation that no longer holds (B20). Unticking never takes
  a line off.
Each owner records its own Activity row; `approvals` adds the key-only row that says the client's block was approved.
Returns a sentence fragment saying what landed, for that row.
"""

from deals import lines as line_vocab
from deals.models import Contact
from deals.services.contacts import create_contact, update_contact

from .. import client_view
from ..models import CurrentCoverage
from . import coverage, intent

CONTACT_TEXT = ('role', 'name', 'title', 'email', 'phone')
COVERAGE_TEXT = ('line', 'carrier', 'funding', 'renewal_date')
PRICED = ('carrier', 'funding')


def _counted(added, edited):
    parts = []
    if added:
        parts.append(f'{added} added')
    if edited:
        parts.append(f'{edited} edited')
    return ', '.join(parts) or 'nothing new'


def _contacts(user, deal, rows):
    known = {contact.id: contact for contact in Contact.objects.filter(client_id=deal.client_id)}
    added = edited = 0
    for row in rows:
        contact = known.get(row.get('id'))
        if contact is not None:
            wanted = {key: row.get(key, '') for key in CONTACT_TEXT}
            changed = {key: value for key, value in wanted.items() if (getattr(contact, key) or '') != value}
            if changed and update_contact(user, contact.id, **changed)[1]:
                edited += 1
            continue
        twin = any(
            (other.name or '').lower() == row.get('name', '').lower()
            and (other.email or '').lower() == row.get('email', '').lower()
            for other in known.values()
        )
        if not twin:
            made = create_contact(user, deal.client_id, **{key: row.get(key, '') for key in CONTACT_TEXT})
            known[made.id] = made
            added += 1
    return f'contacts ({_counted(added, edited)})'


def _row_text(row):
    return {
        'line': row.line,
        'carrier': row.carrier or '',
        'funding': row.funding or '',
        'renewal_date': row.renewal_date.isoformat() if row.renewal_date else '',
    }


def _coverage(user, deal, rows):
    known = {row.id: row for row in CurrentCoverage.objects.filter(deal_id=deal.id)}
    added = edited = 0
    for row in rows:
        wanted = {key: row.get(key, '') for key in COVERAGE_TEXT}
        if coverage.has_plans(deal.id, wanted['line']):
            wanted = {key: value for key, value in wanted.items() if key not in PRICED}
        current = known.get(row.get('id'))
        if current is not None:
            held = _row_text(current)
            changed = {key: value for key, value in wanted.items() if held[key] != value}
            if changed and coverage.update_coverage(user, current.id, changed).changed:
                edited += 1
            continue
        twin = any(
            other.in_force and other.line == row.get('line') and (other.carrier or '') == row.get('carrier', '')
            for other in known.values()
        )
        if not twin:
            written = coverage.create_coverage(user, deal.id, {**wanted, 'in_force': True})
            known[written.row.id] = written.row
            added += 1
    return f'current coverage ({_counted(added, edited)})'


def _lines(user, deal, keys):
    adding = [key for key in keys if key not in (deal.requested_lines or [])]
    if adding:
        intent.set_intent(user, deal.id, lines=adding, shop=True)
        deal.refresh_from_db(fields=['requested_lines'])
    names = ', '.join(line_vocab.label(key) for key in adding)
    return f'lines to quote ({names or "nothing new"})'


LANDERS = {client_view.CONTACTS: _contacts, client_view.COVERAGE: _coverage, client_view.LINES: _lines}


def land(user, deal, slot, value):
    """Write an approved block through its owner. Returns what landed, in words."""
    return LANDERS[slot](user, deal, value or [])
