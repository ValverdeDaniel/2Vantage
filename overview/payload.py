"""`overview(deal, viewer)`: the deal Overview's one read, `GET deals/{id}/overview/` (plan.md §7.16, §8.6; M.6;
slices 62 and 63). Reads only: it gathers each app's facts once, inside one batch scope (`deals.batch`), then applies
the pure rules (`rules.py`, `gtm.py`, `outreach.py`). Nothing here writes, and a deal that has nothing yet answers every
block (M.6, O.2).

{deal_id,
 identity: {name, legal_name, legal_name_default, type, type_label, stage, open_days, renews, owner},
 client: {id, name, relationship, client_since, on_book, convert: {allowed, sentence} | null},
 renewal_offer: {premium_annual, pct_change, label} | null,
 facts: {fein, sic_code, situs_state, employee_count, carrier, funding, agent_of_record: {value, default}, deal_size,
         in_force: [{line, label, comp_label}], contact: {id, name, email, phone, …} | null},
 tiles: {plans_quoted, last_contact_at, expected_revenue},
 asks: {refusal, file_asks_ready},
 get_to_market: Card 1 (`gtm.card`), quote_to_close: [{key, detail, at}] (Card 2),
 enrollment_check: {intake, census, advisor, differ, warning},
 outreach: {last_contact_at, last_response_at, open, oldest_days, answered, waiting, expired, links, links_total,
            never_asked},
 commission: the commission card (`commission.summary.card`), coverage_notes: [{line, label, carrier, state_label,
 body}]}

`asks.file_asks_ready` is always true: a census or document ask goes out on a PIN link (review's `policy.floor`, the
second factor of slices 53–54), so M111's "disabled until the second factor exists" never disables one.

What the shell's `journey/` already reads is not read again (O.4): the Waiting banner, the next step, the stepper and
the Intake complete tile (the journey's Intake meter, intake's answered over needed, M35) come from that query. The lost
and archived banners read the deal header, which every tab shares.
"""

from django.db.models import Max

from commission import summary as commission_summary
from deals import batch, clock, comp, lines
from deals import contacts as contact_rules
from deals import rules as deal_rules
from deals.models import Note
from deals.selectors import contact_row, money, person, status_moves
from intake import selectors as intake_selectors
from proposals import summary_read
from proposals.issues import selectors as issue_selectors
from quotes import facts as quote_facts
from quotes import summary as quote_summary
from quotes.math import round_money
from quotes.selectors.state import scope_plans
from quotes.summary import QUOTE_ROLES
from review import summary as review_summary
from review import words as review_words

from . import market, rules
from .outreach import outreach as outreach_block

MEDICAL = 'medical'
# The intake answers the header's facts show and edit (M25), as intake's form keys; Legal name sits in `identity`.
ANSWERS = ('fein', 'sic_code', 'situs_state', 'employee_count')
ISSUED = 'issued'


def overview(deal, viewer, now=None):
    """The payload above for `deal` (its client and owners selected), as `viewer` may see it."""
    now = now or clock.now()
    with batch.scope([deal.id]):
        intake = intake_selectors.intake_row(deal.id)
        answers = intake_selectors.answers_of(deal, intake)
        found, requests = review_summary.collect([deal.id], now)
        review = found.get(deal.id) or {}
        commission = commission_summary.card(deal, viewer)
        issued_at = _last_issue(deal)
        tiles = _tiles(deal, review, commission, issued_at)
        return {
            'deal_id': deal.id,
            'identity': _identity(deal, answers, clock.today()),
            'client': _client(deal),
            'renewal_offer': rules.renewal_offer(summary_read.renewal_offer(deal)),
            'facts': _facts(deal, answers),
            'tiles': tiles,
            **_cards(deal, review, commission, issued_at),
            'outreach': outreach_block(
                review,
                requests.get(deal.id),
                batch.client_contacts(deal.id),
                tiles['last_contact_at'],
                now,
                dict(review_words.LINK_STATES),
            ),
            'commission': commission,
        }


def _cards(deal, review, commission, issued_at):
    """Card 1 and its asks, Card 2, the enrollment check and Coverage notes (M42–M67, M80, M108–M111)."""
    refusal = deal_rules.client_asks_open(deal)
    quotes = quote_summary.facts([deal.id]).get(deal.id) or {}
    card, check, intake = market.get_to_market(deal, review.get('pending'), refusal, quotes)
    return {
        'asks': {'refusal': refusal, 'file_asks_ready': True},
        'get_to_market': card,
        'quote_to_close': rules.quote_to_close(quotes, issued_at, commission.get('booking')),
        'enrollment_check': check,
        'coverage_notes': rules.coverage_notes((intake.get('intent') or {}).get('rows') or []),
    }


def _identity(deal, answers, today):
    """The header's identity and chips (M13–M18)."""
    client = deal.client
    return {
        'name': client.name,
        'legal_name': str(answers.get('legal_name') or '').strip(),
        'legal_name_default': client.name,  # what a blank legal name shows; never stored or counted (C9)
        'type': deal_rules.deal_type(deal),
        'type_label': deal_rules.deal_type_label(deal),
        'stage': deal.stage,
        'open_days': rules.open_days(clock.local(deal.created_at).date() if deal.created_at else None, today),
        'renews': deal.effective_date,
        'owner': person(rules.owner_of(deal.owner, client.owner)),
    }


def _client(deal):
    """The client box (M21, M23): the status door's moves decide whether Convert to client is offered (§5.1)."""
    client = deal.client
    moves = status_moves(client, list(client.deals.order_by('id')))
    found = {
        'id': client.id,
        'name': client.name,
        'relationship': client.relationship,
        'client_since': client.client_since,
    }
    return rules.client_box(found, moves)


def _facts(deal, answers):
    """The click-to-edit facts (M24–M30); each writes through its owner (intake, deals' contacts, `PATCH deals/`)."""
    rows = intake_selectors.coverage_rows(deal.id)
    medical = next((row for row in rows if row.line == MEDICAL and row.in_force), None)
    found = quote_facts.incumbent(deal, MEDICAL)
    main = contact_rules.primary(batch.client_contacts(deal.id))
    return {
        **{key: str(answers.get(key) if answers.get(key) is not None else '') for key in ANSWERS},
        'carrier': rules.incumbent(found, medical.id if medical else None, 'carrier'),
        'funding': rules.incumbent(found, medical.id if medical else None, 'funding'),
        'agent_of_record': {'value': deal.agent_of_record, 'default': deal_rules.agent_default(deal)},
        'deal_size': money(deal.deal_size),
        'in_force': rules.in_force(
            [(row.line, lines.label(row.line), row.in_force, comp.comp_label(row.commission)) for row in rows]
        ),
        'contact': contact_row(main) if main else None,
    }


def _last_note(deal):
    """When the newest call, email or meeting note was written (a logged follow-up is one), or None."""
    notes = Note.objects.filter(deal_id=deal.id, kind__in=rules.CONTACT_NOTES)
    return notes.aggregate(at=Max('created_at'))['at']


def _last_issue(deal):
    issued = [row['issued_at'] for row in issue_selectors.issues(deal) if row['state'] == ISSUED]
    return max(filter(None, issued), default=None)


def _tiles(deal, review, commission, issued_at):
    """Plans quoted (M36: renewal and alternate plans not removed), Last contact (M37) and Expected revenue (M38, the
    Commission tab's figure in whole dollars, half up). Intake complete is the journey's (M35)."""
    return {
        'plans_quoted': sum(1 for plan in scope_plans(deal.id) if plan.role in QUOTE_ROLES),
        'last_contact_at': rules.last_contact([review.get('last_sent_at'), issued_at, _last_note(deal)]),
        'expected_revenue': round_money(commission['expected']),
    }
