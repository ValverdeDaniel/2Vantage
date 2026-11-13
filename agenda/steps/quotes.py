"""The quotes track (I53–I55; plan.md §5.9): read what arrived, wait on the carriers, review flagged values. Pure.

- `read_quotes` is open while a quote file of the quote reader's kinds sits unread (quotes' facts: no finished read
  read it and no plan cites it), and opens Work with Claude on the Advisor (I53).
- "Waiting on carrier quotes", and its follow-up after 10 days, count from `marketed_at` whenever no quote file or
  quote plan has arrived since then, even when an example quote was read before (I54, I.5 bug 22).
- Before anything went to market and with no quotes, reading waits on the RFP (blocked), as the old app did at intake.
Words from old Vantage 891f1b3 `tasks/steps.py`.
"""

from datetime import timedelta

from .. import rules
from .base import Steps, as_datetime, days_since, local_day

READ = 'Read carrier quotes'


def _arrived_since(quotes, marketed_at):
    since = as_datetime(marketed_at)
    if since is None:
        return False
    moments = [as_datetime(doc.get('at')) for doc in quotes.get('quote_documents') or []]
    moments.append(as_datetime(quotes.get('last_quote_at')))
    return any(moment is not None and moment >= since for moment in moments)


def add(s: Steps, facts, sit):
    if sit.sold:
        return
    quotes = facts.get('quotes') or {}
    unread = quotes.get('unread') or []
    stage = (facts.get('deal') or {}).get('stage')
    if unread:
        s.add('read_quotes', READ, params={'claude': 1}, basis=unread)
    elif sit.marketed_at is not None and not _arrived_since(quotes, sit.marketed_at):
        _carriers(s, sit)
    elif not sit.quotes_in:
        if sit.marketed_at is None and stage == 'intake':
            s.add('read_quotes', READ, state='blocked', blocked_by='send_rfp', reason='After the RFP goes to market')
        else:  # quoting outside the app: the carriers owe us
            s.add('read_quotes', 'Waiting on carrier quotes', state='waiting', owner='carrier', since=sit.marketed_at)
    flagged = quotes.get('flagged') or 0
    if flagged:
        s.add('review_values', f'Review {rules.plural(flagged, "flagged value")}', severity='warn')


def _carriers(s, sit):
    s.add('read_quotes', 'Waiting on carrier quotes', state='waiting', owner='carrier', since=sit.marketed_at)
    wait = rules.FOLLOW_UP_DAYS['carriers']
    days = days_since(sit.marketed_at, sit.today) or 0
    if days >= wait:
        s.add('follow_up_carriers', f'Follow up with the carriers — at market {rules.days(days)}, no quotes back',
              severity='warn', since=sit.marketed_at, wait_days=wait,
              due=local_day(sit.marketed_at) + timedelta(days=wait))  # fmt: skip
