"""The Review tab's Board (plan.md §7.13 `GET deals/{id}/review/board/`, §8.8; L1, L2, L7, L8, L28; O.6 #3).

{deal_id, asks_closed, counts {to_send, to_review, waiting, questions}, readiness {pct, state}, lanes {waiting
[request row]}, in_progress [{link_id, request_id, name, last_saved_at}]}.

- `counts` are the tab's own, from `rules.badges` over `summary.facts`, so the pills work before the shell's badges
  (slice 61) and agree with them after.
- `readiness` is the deal's intake readiness, the old board head's chip and bar (L2): the needed questions answered
  (`intake.summary.facts`) and the ready state (blocked, ready or submitted; words in /api/meta/ `review.readiness`).
- `lanes.waiting` holds the requests still out, soonest to run out first (L7); the Missing and To review lanes, Next
  and the client's questions join with slices 55–56.
- `asks_closed` is the sentence when the deal may no longer ask its client (lost, archived, a past year): the tab then
  only reads (L129).

A fixed number of queries however many requests and links the deal has (Q.3 #4). Writes nothing.
"""

from deals import clock, rules
from intake import summary as intake_summary

from .. import summary
from ..rules import badges
from ..rules import requests as request_rules


def readiness(deal_id):
    found = intake_summary.facts([deal_id]).get(deal_id) or {}
    needed, answered = found.get('needed', 0), found.get('answered', 0)
    return {'pct': round(answered / needed * 100) if needed else 100, 'state': found.get('ready_state') or 'blocked'}


def board(deal, now=None):
    now = now or clock.now()
    facts, rows = summary.collect([deal.id], now)
    found = facts[deal.id]
    waiting = [row for row in rows[deal.id] if row['state'] in request_rules.OPEN_STATES]
    return {
        'deal_id': deal.id,
        'asks_closed': rules.client_asks_open(deal),
        'counts': badges.counts(found),
        'readiness': readiness(deal.id),
        'lanes': {'waiting': request_rules.soonest_first(waiting)},
        'in_progress': found['in_progress'],
    }
