"""The Activity card's outreach strip and "Who we've asked" (plan.md §8.6; M68, M69; old Vantage 891f1b3
`outreach_payload`, `ActivityFeed.jsx`). Pure: review's facts and request rows for the deal, the client's contacts and
the Last contact tile's moment in; the block out.

- The strip: Last contact (the tile's rule, M37), Last response (the newest answer through any link) and Open asks:
  the requests sent and not answered, run-out ones included, counted per request (one ask to several people is one
  ask, D-062), with how many days the oldest has waited.
- "Who we've asked": every link, newest request first, capped at 50 rows (the counts are over every link): the
  person and their role, what the request asks, "shared request" when several people were asked the same thing, the
  link's state in review's one vocabulary, and the days left on a link still waiting. Then "Never asked": the client's
  contacts on its side whom no link went to.
"""

from datetime import datetime

from deals.contacts import CLIENT_SIDE

CAP = 50  # rows of "Who we've asked" (old `_MAX_LINK_ROWS`)
OUT = ('waiting', 'partly_sent')  # a request still out (sent, not answered, not run out, not closed)
EXPIRED, ANSWERED = 'expired', 'answered'
LIVE = ('waiting', 'opened')  # a link that can still be answered: its days left show


def _moment(value):
    if not value:
        return None
    return value if isinstance(value, datetime) else datetime.fromisoformat(str(value))


def _link(request, person, shared, labels):
    state = person['state']
    return {
        'link_id': person['link_id'],
        'request_id': request['id'],
        'name': person['name'] or person['email'] or '',
        'role': person['role'] or '',
        'asks': list(request['asks'] or []),
        'shared': shared,
        'state': state,
        'state_label': labels.get(state, state),
        'sent_at': person['sent_at'],
        'days_left': person['days_left'] if state in LIVE else None,
    }


def outreach(facts, requests, contacts, last_contact_at, now, labels):
    """{last_contact_at, last_response_at, open, oldest_days, answered, waiting, expired, links, links_total,
    never_asked}. `facts` is review's summary for the deal, `requests` its request rows (`review.summary.collect`),
    `contacts` the client's (role, name, id), `labels` the link states' words."""
    requests = list(requests or [])
    outstanding = [row for row in requests if row['state'] in (*OUT, EXPIRED)]
    sent = [_moment(row['first_sent_at']) for row in outstanding if row['first_sent_at']]
    oldest = min(sent, default=None)
    links = []
    for request in sorted(requests, key=lambda row: (row['created_at'] or '', row['id']), reverse=True):
        people = request['recipients'] or []
        links += [_link(request, person, len(people) > 1, labels) for person in people]
    asked = {person['contact_id'] for row in requests for person in row['recipients'] or [] if person['contact_id']}
    unasked = [contact for contact in contacts if contact.role in CLIENT_SIDE and contact.id not in asked]
    return {
        'last_contact_at': last_contact_at,
        'last_response_at': (facts or {}).get('last_response_at'),
        'open': len(outstanding),
        'oldest_days': max(0, (now - oldest).days) if oldest else None,
        'answered': sum(1 for row in requests if row['state'] == ANSWERED),
        'waiting': sum(1 for row in requests if row['state'] in OUT),
        'expired': sum(1 for row in requests if row['state'] == EXPIRED),
        'links': links[:CAP],
        'links_total': len(links),
        'never_asked': [contact.name for contact in unasked if contact.name],
    }
