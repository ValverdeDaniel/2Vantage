"""`GET work-queue/stats/` (plan.md §7.15; A10, I83, I84, I127; OQ94; slice 61): the Work queue's two graph cards.

{actions_week: {total, change_pct, series}, sales_month: {total, change_pct, series}}

- **Actions completed this week** (I83, OQ94): the milestone Activity rows of the last seven days, each counted by its
  `count` (a coalesced row holds several actions), plus the tasks ticked (their coalesced rows likewise). Milestones:
  sent to market, an RFP sent, a quote, intake or census read used, a proposal issued, a plan marked sold (the old
  card counted finished reads, marketed deals, sold plans and Hub submissions; the Hub is not built). A reverted row
  counts nothing; a row on an archived client's deal leaves the card with its deal (old `_LIVE_CASE`).
- **Total sales this month** (I84, OQ94): the Potential deal size of each live deal whose first sale (its earliest sold
  plan still sold) falls in the agency's month so far, compared with the same span of last month (I.5 bug 23).
- `change_pct`: the change on the prior span, a whole percent, or None when the prior span had nothing (the old card
  then hid it). `series`: ten real points (I127, I.5 bug 24), oldest first: the last ten seven-day spans ending now,
  and the last ten months, this one so far. Totals of money are exact text; a series is plain numbers to draw.
"""

from datetime import datetime, timedelta
from decimal import Decimal

from django.db.models import Min, Q

from deals import clock
from deals.models import Activity
from deals.selectors import money
from quotes.models import Plan

POINTS = 10
WEEK = timedelta(days=7)
# (area, action, the summary's first words or '' for any): the forward moves only — un-marketing and un-selling write
# the same action with other words.
MILESTONES = [
    ('intake', 'marketed', 'Marked as marketed'),
    ('rfp', 'sent', ''),
    ('quote_read', 'read', ''),
    ('intake', 'read', ''),
    ('census', 'imported', ''),
    ('proposal', 'issued', 'Issued proposal'),
    ('quotes', 'sold', 'Marked '),
]
TICKED = ('agenda', 'updated', 'agenda:tick')  # agenda's coalesced "Ticked N tasks" rows


def change_pct(total, prior):
    """The signed whole-percent change on the prior span, or None with nothing to compare (old `_pct_change`)."""
    if not prior:
        return None
    return int(round((Decimal(total) - Decimal(prior)) / Decimal(prior) * 100))


def _milestone(area, action, summary, coalesce_key):
    if (area, action, coalesce_key) == TICKED:
        return True
    return any(area == a and action == b and summary.startswith(words) for a, b, words in MILESTONES)


def actions(now):
    starts = [now - WEEK * (POINTS - index) for index in range(POINTS)]
    wanted = Q(area=TICKED[0], action=TICKED[1], coalesce_key=TICKED[2])
    for area, action, _words in MILESTONES:
        wanted |= Q(area=area, action=action)
    found = (
        Activity.objects.filter(wanted, created_at__gte=starts[0], created_at__lt=now, reverted_at__isnull=True)
        .filter(deal__isnull=False, deal__client__archived_at__isnull=True)
        .values_list('area', 'action', 'summary', 'coalesce_key', 'count', 'created_at')
    )
    series = [0] * POINTS
    for area, action, summary, coalesce_key, count, at in found:
        if _milestone(area, action, summary, coalesce_key):
            series[min(POINTS - 1, int((at - starts[0]) / WEEK))] += count
    return {'total': series[-1], 'change_pct': change_pct(series[-1], series[-2]), 'series': series}


def _month_start(day_or_moment):
    local = clock.local(day_or_moment) if isinstance(day_or_moment, datetime) else day_or_moment
    return datetime(local.year, local.month, 1, tzinfo=clock.agency_zone())


def _months_back(start, n):
    year, month = start.year, start.month - n
    while month < 1:
        year, month = year - 1, month + 12
    return datetime(year, month, 1, tzinfo=clock.agency_zone())


def _first_sales(since, now):
    """[(first sold moment, deal size)] of live deals whose earliest sold plan was sold in [since, now)."""
    sold = Plan.objects.filter(sold=True, sold_at__isnull=False, deal__client__archived_at__isnull=True)
    rows = sold.values('deal_id', 'deal__deal_size').annotate(first=Min('sold_at')).order_by()
    return [(row['first'], row['deal__deal_size']) for row in rows if since <= row['first'] < now]


def sales(now):
    month = _month_start(now)
    starts = [_months_back(month, POINTS - 1 - index) for index in range(POINTS)]
    prior_start = starts[-2]
    prior_end = min(prior_start + (now - month), month)  # the same days of last month (I.5 bug 23)
    totals, prior = [Decimal(0)] * POINTS, Decimal(0)
    for first, size in _first_sales(starts[0], now):
        index = max(i for i, start in enumerate(starts) if first >= start)
        totals[index] += size or 0
        if prior_start <= first < prior_end:
            prior += size or 0
    return {
        'total': money(totals[-1]),
        'change_pct': change_pct(totals[-1], prior),
        'series': [float(total) for total in totals],
    }


def stats(now=None):
    now = now or clock.now()
    return {'actions_week': actions(now), 'sales_month': sales(now)}
