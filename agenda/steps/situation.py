"""What every track reads first about one deal (pure): whether quotes are in, whether it is marketed, sold or lost,
and the client's asks that are out. Built once per deal from its facts dict (`agenda.facts.facts_for`)."""

from collections import namedtuple

Situation = namedtuple(
    'Situation', 'lost sold quotes_in marketed_at unpriced typed_drives asks_out drafts expired today now'
)

SENT = ('partly_sent', 'waiting')  # review's open request states once something went out


def situation(facts, today, now):
    deal = facts.get('deal') or {}
    quotes = facts.get('quotes') or {}
    review = facts.get('review') or {}
    raw = review.get('raw_asks') or {}
    waiting = review.get('waiting') or []
    sent = [row for row in waiting if row.get('state') in SENT]
    unpriced = quotes.get('unpriced') or 0
    quotes_in = (quotes.get('quotes') or 0) > 0
    return Situation(
        lost=bool(deal.get('lost')),
        sold=bool(deal.get('sold')),
        quotes_in=quotes_in,
        marketed_at=(facts.get('intake') or {}).get('marketed_at'),
        unpriced=unpriced,
        # Typed tier counts carry the Advisor: quotes are in and every plan on them is priced without a census (I50).
        typed_drives=quotes_in and not unpriced and (facts.get('census') or {}).get('employees', 0) == 0,
        asks_out=[{**row, 'raw': raw.get(row.get('request_id')) or {}} for row in sent],
        drafts=[{**row, 'raw': raw.get(row.get('request_id')) or {}} for row in waiting if row.get('state') == 'draft'],
        expired=(review.get('requests') or {}).get('expired', 0),
        today=today,
        now=now,
    )


def raw_out(sit):
    """The stored asks of every request that went out and is still open."""
    return [row['raw'] for row in sit.asks_out]
