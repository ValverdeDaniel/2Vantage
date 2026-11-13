"""The client's asks as two steps at most, never one per link (I64, I65; old Vantage 891f1b3 `tasks/steps.py`
`_ask_steps`), before the sale only (I66). Pure.

- `send_drafts`: requests made and never sent are ours to send.
- `follow_up_client`: while anything sent is unanswered, waiting until the oldest has waited 3 days, then a follow-up;
  at once when a request ran out unanswered. It names what was asked, to whom and how many.
Review's facts give the open requests (draft, partly sent, waiting) with when each first went out and to whom, and how
many ran out (`requests.expired`); what each asked comes from its stored asks (`asked.words`).
"""

from datetime import timedelta

from .. import rules
from . import asked
from .base import Steps, days_since, local_day


def add(s: Steps, _facts, sit):
    if sit.sold:
        return
    if sit.drafts:
        newest = max(sit.drafts, key=lambda row: row.get('request_id') or 0)
        label = (
            f'Send the {asked.words(newest["raw"])} you drafted'
            if len(sit.drafts) == 1
            else f'Send the {len(sit.drafts)} requests you drafted'
        )
        s.add('send_drafts', label, severity='warn')
    if sit.asks_out:
        _follow_up(s, sit)
    elif sit.expired:
        n = sit.expired
        label = (
            'Follow up: the request expired unanswered — send a fresh link'
            if n == 1
            else f'Follow up: {n} requests expired unanswered — send fresh links'
        )
        s.add('follow_up_client', label, severity='warn', wait_days=rules.FOLLOW_UP_DAYS['client_ask'])


def _follow_up(s, sit):
    wait = rules.FOLLOW_UP_DAYS['client_ask']
    out = sit.asks_out
    oldest = max(out, key=lambda row: days_since(row.get('first_sent_at'), sit.today) or 0)
    days = days_since(oldest.get('first_sent_at'), sit.today) or 0
    expired = sit.expired
    due_now = bool(expired) or days >= wait
    if len(out) == 1 and not expired:
        what = asked.words(oldest['raw'])
        names = oldest.get('names') or []
        to = f' to {", ".join(names)}' if names else ''
        if due_now:
            label = f'Follow up: {what} sent {rules.days(days)} ago{to}, not returned'
        else:
            label = f'Waiting on the client: {what} sent {rules.days(days)} ago{to}'
    else:
        lead_in = 'Follow up' if due_now else 'Waiting on the client'
        label = f'{lead_in}: {len(out)} requests out with the client, the oldest sent {rules.days(days)} ago'
        if expired:
            label += f' — {expired} expired, send fresh link{"s" if expired != 1 else ""}'
    sent_on = oldest.get('first_sent_at')
    if due_now:
        day = local_day(sent_on)
        s.add('follow_up_client', label, severity='warn', since=sent_on, wait_days=wait,
              due=day + timedelta(days=wait) if day else None)  # fmt: skip
    else:
        s.add('follow_up_client', label, state='waiting', owner='client', since=sent_on, wait_days=wait)
