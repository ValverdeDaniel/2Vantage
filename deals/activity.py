"""The Activity log (plan.md §3.7, §6.2).

Consecutive writes by the same actor with the same `coalesce_key` within 10 minutes update one row and its count,
so a burst of field-by-field saves reads "Edited 14 plan values", not fourteen rows. Imports, issues, sales and
stage changes pass no key and always get their own row.
"""

from datetime import timedelta

from . import clock
from .models import Activity

WINDOW = timedelta(minutes=10)


def _plural(count, noun):
    return noun if count == 1 else (noun[:-1] + 'ies' if noun.endswith('y') else noun + 's')


def record(deal, actor, area, action, summary, count=1, coalesce_key='', noun=''):
    """Append (or extend) an Activity row. With `coalesce_key`, `noun` builds the summary: "Edited 14 plan values"."""
    now = clock.now()
    if coalesce_key:
        latest = Activity.objects.filter(deal=deal).order_by('-updated_at', '-id').first()
        if (
            latest
            and latest.coalesce_key == coalesce_key
            and latest.actor_id == getattr(actor, 'id', None)
            and now - latest.updated_at <= WINDOW
        ):
            latest.count += count
            latest.updated_at = now
            latest.summary = f'{summary} {latest.count} {_plural(latest.count, noun)}'.strip()
            latest.save(update_fields=['count', 'updated_at', 'summary'])
            return latest
        summary = f'{summary} {count} {_plural(count, noun)}'.strip()
    return Activity.objects.create(
        deal=deal,
        actor=actor if getattr(actor, 'is_authenticated', False) else None,
        area=area,
        action=action,
        summary=summary[:300],
        count=count,
        coalesce_key=coalesce_key,
        created_at=now,
        updated_at=now,
    )
