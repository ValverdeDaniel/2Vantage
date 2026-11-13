"""A facts dict for one deal, as `agenda.facts.facts_for` builds it, with every app's part at its empty default; a test
names only the parts it changes. Synthetic values only."""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

EASTERN = ZoneInfo('America/New_York')
TODAY = date(2026, 11, 12)
NOW = datetime(2026, 11, 12, 15, 0, tzinfo=EASTERN)


def at(days_ago, hour=10):
    """A moment `days_ago` agency days before TODAY, as the apps' facts carry it (ISO)."""
    day = TODAY - timedelta(days=days_ago)
    return datetime(day.year, day.month, day.day, hour, 0, tzinfo=EASTERN).isoformat()


def facts(**parts):
    found = {
        'deal': {'id': 1, 'stage': 'intake', 'lost': False, 'lost_reason': '', 'sold': False},
        'intake': {'ready_state': 'blocked', 'blockers': [], 'items': [], 'marketed_at': None},
        'census': {'employees': 0, 'dependents': 0, 'errors': 0, 'proposed_import': None, 'files': 0},
        'quotes': {
            'plans': 0,
            'quotes': 0,
            'last_quote_at': None,
            'quote_documents': [],
            'unread': [],
            'flagged': 0,
            'sold_lines': [],
            'unpriced': 0,
            'unpriced_lines': [],
        },
        'proposals': {'latest': None, 'needs': 0, 'picked': 0, 'ready': False},
        'rfp': {'cards_done': 0, 'cards_total': 5},
        'commission': {'unrated': []},
        'review': {
            'requests': {},
            'waiting': [],
            'pending': {'intake': 0, 'census': 0, 'people': 0, 'documents': 0},
            'questions': {'open': 0, 'oldest_at': None},
            'raw_asks': {},
        },
        'documents': {'questionnaire_files': []},
        'nudges': [],
    }
    for part, changes in parts.items():
        found[part] = {**found[part], **changes} if isinstance(changes, dict) else changes
    return found


def quotes_in(n=3, **more):
    return {'plans': n, 'quotes': n, 'last_quote_at': at(20), **more}


def ask(request_id, asks, *, state='waiting', sent_days_ago=1, names=('Riley Example',)):
    """(a waiting entry, its stored asks) for review's facts."""
    entry = {
        'request_id': request_id,
        'state': state,
        'first_sent_at': at(sent_days_ago) if state != 'draft' else None,
        'names': list(names),
    }
    return entry, asks


def review_with(*asks, expired=0):
    return {
        'requests': {'expired': expired},
        'waiting': [entry for entry, _raw in asks],
        'pending': {'intake': 0, 'census': 0, 'people': 0, 'documents': 0},
        'questions': {'open': 0, 'oldest_at': None},
        'raw_asks': {entry['request_id']: raw for entry, raw in asks},
    }


CENSUS_ASK = {'census': {'scope': 'none', 'file': True}}
BOR_ASK = {'intake': {'scope': None, 'blocks': ['bor']}}
FORM_ASK = {'questionnaires': [{'form': 'florida_blue_51', 'mode': 'online'}]}


def by_key(steps):
    return {step['key']: step for step in steps}
