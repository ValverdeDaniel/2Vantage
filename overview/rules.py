"""The Overview's own rules (plan.md §5.10, §8.6; M.6 `rules.py`; slice 62). Pure: no database; `payload.py` reads
what they take, once.

- `open_days(created_on, today)`: "Open N days" (M16), the creation day in the agency's time zone against today.
- `owner_of(deal_owner, client_owner)`: "Owner: …" (M18): the deal's owner, else the client's.
- `client_box(client, moves)`: the client box (M21, M23 as changed by OQ2): a New or Existing client is on the client
  book and its box links to the client; a prospect is "Not on the client book yet" with Convert to client, allowed or
  refused with the status door's own sentence (§5.1, OQ101 a; a lost deal refuses it).
- `incumbent(found, row_id, key)`: Current carrier and Funding (M26): `quotes.facts.incumbent`'s answer for medical,
  editable on intake's coverage row unless the current plans hold it.
- `in_force(rows)`: the in-force commission per line, read-only (M28).
- `renewal_offer(offer)`: the renewal-offer chip (M20; OQ38's default, yes): the letter's figures as the proposal's
  renewal blocks print them, one rule for both.
- `last_contact(moments)`: the newest contact (M37): a link sent, a proposal issued, a call, email or meeting note (a
  logged follow-up is one). A draft link is no contact; the browser says "just now", never "0h ago".
- `quote_to_close(quotes, issued_at, booking)`: Card 2's detail per Quote to Close milestone (M62, M65; slice 63); the
  rows' states are the journey's, so the card and the stepper agree.
- `coverage_notes(rows)`: the Coverage notes side card (M80): each intent row that carries a note, in the card's order.
"""

from datetime import datetime

from deals.lifecycle import NEW_CLIENT, PROSPECT
from proposals.summary_blocks import words

CONTACT_NOTES = ('call', 'email', 'meeting')  # the note kinds that are a contact (M37; a logged follow-up is one)
OFFER = 'Renewal offer'


def open_days(created_on, today):
    """Whole days since the deal was created, never below 0; None when undated."""
    if created_on is None:
        return None
    return max(0, (today - created_on).days)


def owner_of(deal_owner, client_owner):
    return deal_owner or client_owner


def client_box(client, moves):
    """The client's box: `client` (id, name, relationship, client_since) with `on_book` and `convert` ({allowed,
    sentence} for a prospect, else None). `moves` are `deals.lifecycle.moves`' answers for this client."""
    on_book = client['relationship'] != PROSPECT
    convert = None
    if not on_book:
        move = next((row for row in moves if row['to'] == NEW_CLIENT), None)
        if move is not None:
            convert = {'allowed': move['allowed'], 'sentence': move['sentence']}
    return {**client, 'on_book': on_book, 'convert': convert}


def incumbent(found, row_id, key):
    """{value, from, coverage_id, editable} for the medical line's `key` ('carrier' or 'funding'). `found` is
    `quotes.facts.incumbent(deal, 'medical')` ({carrier, funding, source} or None); `row_id` the first in-force medical
    coverage row, or None (a first edit adds one). The current plans' carrier and funding are read-only here (§6.5)."""
    source = found['source'] if found else None
    return {
        'value': str((found or {}).get(key) or ''),
        'from': source,
        'coverage_id': row_id,
        'editable': source != 'plans',
    }


def in_force(rows):
    """[{line, label, comp_label}]: each line's first in-force coverage row that carries a commission (M28). `rows`
    are (line, line label, in_force, comp_label) in the coverage card's order."""
    found, seen = [], set()
    for line, label, live, comp_label in rows:
        if live and comp_label and line not in seen:
            seen.add(line)
            found.append({'line': line, 'label': label, 'comp_label': comp_label})
    return found


def renewal_offer(offer):
    """{premium_annual, pct_change, label} from the renewal letter's facts, or None when the letter gives neither.
    The label is the old chip's ("Renewal offer $13,440/yr (+12.0%)"), its figures in the proposal blocks' words."""
    if not offer:
        return None
    annual, pct = offer.get('renewal_premium_annual'), offer.get('renewal_pct_change')
    if annual is None and pct is None:
        return None
    parts = [OFFER]
    if annual is not None:
        parts.append(words.per_year(annual))
    if pct is not None:
        parts.append(f'({words.pct(pct)})')
    return {'premium_annual': annual, 'pct_change': pct, 'label': ' '.join(parts)}


def _moment(value):
    if value is None or value == '':
        return None
    return value if isinstance(value, datetime) else datetime.fromisoformat(str(value))


def last_contact(moments):
    """The newest of `moments` (datetimes or ISO text; None for a source with nothing), or None."""
    found = [moment for moment in (_moment(value) for value in moments) if moment is not None]
    return max(found, default=None)


def _plural(count, word):
    return f'{count} {word}' if count == 1 else f'{count} {word}s'


def quote_to_close(quotes, issued_at, booking):
    """[{key, detail, at}] in the journey's Quote to Close order (quotes in, proposal built, issued, sold, commission
    entered), from quotes' facts (`quotes.summary.facts`), the newest issued proposal and the commission card's booking
    state. The old card's words (891f1b3 `PhaseCards.jsx`): "N plans · X to review · Y missing" or "Waiting on carrier
    responses"; "Secure link the client opens" became "Proposal issued <date>" (C22); the client-selected step and the
    hand-off wait (M63, M64), so the old hand-off's "Unlocks once a plan is sold" now heads the commission step."""
    count = quotes.get('quotes', 0) or 0
    if count:
        review, missing = quotes.get('to_review', 0), quotes.get('required_missing', 0)
        first = f'{_plural(count, "plan")} · {review} to review · {missing} missing'
    else:
        first = 'Waiting on carrier responses'
    sold = bool(quotes.get('sold_lines'))
    if not sold:
        commission = 'Unlocks once a plan is sold'
    elif (booking or {}).get('state') == 'booked':
        commission = 'Booked at sale'
    else:
        commission = 'Book it on the Commission tab'
    return [
        {'key': 'quotes_in', 'detail': first, 'at': None},
        {'key': 'built', 'detail': 'Advisor picks the best-fit plans', 'at': None},
        {'key': 'issued', 'detail': 'Proposal issued' if issued_at else '', 'at': issued_at},
        {'key': 'sold', 'detail': 'Confirm the winning plan', 'at': None},
        {'key': 'commission', 'detail': commission, 'at': None},
    ]


def coverage_notes(rows):
    """[{line, label, carrier, state_label, body}] for the intent rows (intake's coverage card) whose note is not
    blank; none at all hides the card (old `CoverageNotesCard`)."""
    return [
        {
            'line': row['line'],
            'label': row.get('label') or row['line'],
            'carrier': row.get('carrier') or '',
            'state_label': row.get('state_label') or '',
            'body': row['notes'].strip(),
        }
        for row in rows
        if (row.get('notes') or '').strip()
    ]
