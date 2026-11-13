"""Review's facts for the tab's counts, Agenda and the Overview (plan.md §5.10, O.2; L118, L119; L.6 selectors):
`facts(deal_ids) -> {deal_id: dict}`, counts, dates and names only, the same for every viewer, in a fixed number of
queries however many deals, requests and links are asked (Q.3 #4): the deals, the requests, the links, the notes, the
waiting client entries (the intake rows, the people holding one), the census counts and the client's files.

Per deal:
- `requests`: {state: count} over every request; `open`: how many are still out (draft, partly sent, waiting);
- `waiting`: the open requests, soonest to run out first: {request_id, state, first_sent_at, asks, names,
  soonest_days, expiring};
- `in_progress`: links whose person saved and has not submitted since ("X is still answering"): {link_id,
  request_id, name, last_saved_at};
- `first_sent_at` (the oldest send on an open request), `last_sent_at`, `last_response_at`;
- `response`: the newest sent request's {state: waiting | answering | answered, at, link_id, name}, or None;
- `pending`: client answers waiting on the owners: {intake, census, people, documents, total} (Ch. 14b: census's
  come from its stored counts); `ready`: {intake, census}, those whose link is ready (submitted after its last save,
  or idle 24 h; census's counts the people a client added);
- `sections` (slice 55): per surface (intake, census) what came back — {to_review, in_progress, ready,
  ready_submitted, ready_idle, going_back, names} (`rules.sections`; `going_back`, answers sent back and not answered
  since, slice 56), plus `questions` and `in_tray` from the notes, and the census's `missing` (its required blanks,
  from its stored counts): the section bars and the To review lane;
- `questions`: {open, oldest_at}; `tray`: asks and send-backs not yet sent; `nudges`: reminders due today (L69).

Questionnaire answers join with slice 58, when the questionnaire's `client` entries are written.
"""

from collections import defaultdict

from django.db.models import Count, Min, Q

from census.models import CensusFacts
from deals import clock
from deals.models import Deal
from documents.models import Document

from .models import ASK_KINDS, ReviewNote
from .rules import policy
from .rules import requests as request_rules
from .rules import sections as section_rules
from .selectors import entries as entry_rows
from .selectors import going
from .selectors import requests as request_rows


def _iso(moment):
    return moment.isoformat() if moment else None


def _notes(ids):
    """{deal_id: {questions, oldest, tray, by_surface: {surface: {questions, in_tray}}}}: one grouped count."""
    counted = (
        ReviewNote.objects.filter(deal_id__in=ids, resolved_at__isnull=True)
        .values('deal_id', 'surface')
        .annotate(
            questions=Count('id', filter=Q(kind='question')),
            oldest=Min('at', filter=Q(kind='question')),
            tray=Count('id', filter=Q(kind__in=ASK_KINDS, sent_at__isnull=True)),
        )
    )
    out = {}
    for entry in counted:
        found = out.setdefault(entry['deal_id'], {'questions': 0, 'oldest': None, 'tray': 0, 'by_surface': {}})
        found['questions'] += entry['questions']
        found['tray'] += entry['tray']
        if entry['oldest'] and (found['oldest'] is None or entry['oldest'] < found['oldest']):
            found['oldest'] = entry['oldest']
        found['by_surface'][entry['surface']] = {'questions': entry['questions'], 'in_tray': entry['tray']}
    return out


def _pending(ids, waiting, links, now, gone):
    """{deal_id: (pending, ready, sections)} from the waiting entries, the census counts and the client's files."""
    out = {}
    for deal_id in ids:
        entries = waiting.get(deal_id, [])
        sections = section_rules.counts(entries, links, now, gone.get(deal_id, frozenset()))
        intake = sum(1 for entry in entries if entry.surface == 'intake')
        pending = {'intake': intake, 'census': 0, 'people': 0, 'documents': 0}
        ready = {surface: sections[surface]['to_review'] for surface in section_rules.SURFACES}
        out[deal_id] = (pending, ready, sections)
    for deal_id, answers, added, missing in CensusFacts.objects.filter(deal_id__in=ids).values_list(
        'deal_id', 'pending_answers', 'pending_people', 'missing'
    ):
        out[deal_id][0].update(census=answers, people=added)
        out[deal_id][2]['census']['missing'] = sum((missing or {}).values())
    files = Document.objects.filter(deal_id__in=ids, source='client', review_state='').values('deal_id')
    for entry in files.annotate(n=Count('id')):
        out[entry['deal_id']][0]['documents'] = entry['n']
    return out


def _sections(found, notes):
    """The section counts with each surface's notes (questions, drafts in the tray)."""
    by_surface = notes.get('by_surface', {})
    for surface, counts in found.items():
        counts.setdefault('missing', 0)
        counts['questions'] = (by_surface.get(surface) or {}).get('questions', 0)
        counts['in_tray'] = (by_surface.get(surface) or {}).get('in_tray', 0)
    return found


def _response(rows):
    """The newest sent request's state, among those still out or answered, for the client response column (L118)."""
    sent = [row for row in rows if row['first_sent_at']]
    if not sent:
        return None
    newest = max(sent, key=lambda row: row['first_sent_at'])
    people = newest['recipients']
    answered = [person for person in people if person['submitted_at']]
    if answered:
        first = min(answered, key=lambda person: person['submitted_at'])
        return {'state': 'answered', 'at': first['submitted_at'], 'link_id': first['link_id'], 'name': first['name']}
    typing = [person for person in people if person['in_progress']]
    if typing:
        latest = max(typing, key=lambda person: person['last_saved_at'])
        return {
            'state': 'answering',
            'at': latest['last_saved_at'],
            'link_id': latest['link_id'],
            'name': latest['name'],
        }
    return {'state': 'waiting', 'at': newest['first_sent_at'], 'link_id': None, 'name': ''}


def _waiting(rows):
    open_rows = [row for row in rows if row['state'] in request_rules.OPEN_STATES]
    return request_rules.soonest_first(open_rows)


def _deal_facts(rows, links, pending, notes, now, today, lost):
    waiting = _waiting(rows)
    people = [person for row in rows for person in row['recipients']]
    sent = [person['sent_at'] for person in people if person['sent_at']]
    answered = [person['submitted_at'] for person in people if person['submitted_at']]
    states = {state: 0 for state in request_rules.REQUEST_STATES}
    for row in rows:
        states[row['state']] += 1
    closed = {person['link_id'] for row in rows if row['closed_at'] for person in row['recipients']}
    nudges = sum(
        1 for link in links if policy.nudge_open(link.nudge, link, now, today, closed=link.id in closed, lost=lost)
    )
    return {
        'requests': states,
        'open': len(waiting),
        'waiting': [
            {
                'request_id': row['id'],
                'state': row['state'],
                'first_sent_at': row['first_sent_at'],
                'asks': row['asks'],
                'names': [person['name'] for person in row['recipients'] if person['name']],
                'soonest_days': row['soonest_days'],
                'expiring': row['expiring'],
            }
            for row in waiting
        ],
        'in_progress': [
            {'link_id': p['link_id'], 'request_id': row['id'], 'name': p['name'], 'last_saved_at': p['last_saved_at']}
            for row in rows
            for p in row['recipients']
            if p['in_progress']
        ],
        'first_sent_at': min((row['first_sent_at'] for row in waiting if row['first_sent_at']), default=None),
        'last_sent_at': max(sent, default=None),
        'last_response_at': max(answered, default=None),
        'response': _response(waiting + [row for row in rows if row['state'] == request_rules.ANSWERED]),
        'pending': {**pending[0], 'total': sum(pending[0].values())},
        'ready': pending[1],
        'sections': _sections(pending[2], notes),
        'questions': {'open': notes.get('questions', 0), 'oldest_at': _iso(notes.get('oldest'))},
        'tray': notes.get('tray', 0),
        'nudges': nudges,
    }


def collect(deal_ids, now=None):
    """({deal_id: facts}, {deal_id: [request row]}) for the deals asked (unknown ids are left out)."""
    now = now or clock.now()
    today = clock.today()
    stages = dict(Deal.objects.filter(pk__in=list(deal_ids)).values_list('id', 'stage'))
    ids = list(stages)
    found, links = request_rows.load(ids)
    by_id = {link.id: link for group in links.values() for link in group}
    rows = {
        deal_id: [request_rows.row(request, links.get(request.id, []), now) for request in found.get(deal_id, [])]
        for deal_id in ids
    }
    waiting = entry_rows.waiting(ids)
    opened = going.opens([request for group in found.values() for request in group], links, now)
    pending = _pending(ids, waiting, by_id, now, going.refs(ids, waiting, opened))
    notes = _notes(ids)
    deal_links = defaultdict(list)
    for request_list in found.values():
        for request in request_list:
            deal_links[request.deal_id] += links.get(request.id, [])
    facts = {}
    for deal_id in ids:
        lost = stages[deal_id] == 'lost'
        facts[deal_id] = _deal_facts(
            rows[deal_id], deal_links[deal_id], pending[deal_id], notes.get(deal_id, {}), now, today, lost
        )
    return facts, rows


def facts(deal_ids, now=None):
    """{deal_id: facts} (above)."""
    return collect(deal_ids, now)[0]
