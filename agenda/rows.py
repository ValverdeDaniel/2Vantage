"""What the marked steps say (I4, I67, I119, I121; I.6 `rows.py`). Pure: no database.

- `section(row)`: Up next, Waiting on, Later, Blocked or Done (I4; the old `partitionDeal`, now the server's).
- `finished(steps)`: nothing left before marks (D-097): decided on the unmarked steps, so Done anyway never makes a
  deal finished (I121, I.5 bug 12); a lost deal is decided by its stage.
- `next_step(steps)`: the first live lead step; else the first live step of any track; else the held row with its
  earliest Later day; else the first lead step, shown as done anyway (I67); a sold deal with nothing left reads "Sold".
  The Overview banner, the journey and the Work queue read this one answer (I42, I68).
- `waiting(steps)`: the first waiting lead step with its owner, since, days and severity; otherwise "with us" and the
  next step's words (I119).
"""

from . import catalogue
from .steps.base import days_since

LIVE = ('open', 'waiting')


def section(row):
    if row['kind'] != 'step':
        return 'done' if row.get('done') else 'up_next'
    if row['state'] == 'done':
        return 'done'
    if row.get('later_until'):
        return 'later'
    if row['state'] == 'blocked':
        return 'blocked'
    return 'waiting' if row['state'] == 'waiting' else 'up_next'


def live(step):
    return step['state'] in LIVE and not step.get('later_until')


def finished(unmarked_steps):
    return not any(step['state'] in (*LIVE, 'blocked') for step in unmarked_steps)


def _brief(step, **more):
    found = {
        'key': step['key'],
        'label': step['label'],
        'tab': step['tab'],
        'params': step.get('params') or {},
        'state': step['state'],
        'severity': step['severity'],
        'owner': step['owner'],
    }
    return {**found, **more}


def next_step(steps):
    """The deal's one next step (I67), or None when nothing is left."""
    leads = [step for step in steps if step['lead']]
    for pool in (leads, steps):
        found = next((step for step in pool if live(step)), None)
        if found:
            return _brief(found)
    held = [step for step in steps if step.get('later_until') and step['state'] in LIVE]
    if held:
        first = min(held, key=lambda step: (not step['lead'], step['later_until']))
        return _brief(first, later_until=min(step['later_until'] for step in held))
    marked = next((step for step in leads if step.get('done_anyway')), None)
    if marked:
        return _brief(marked, done_anyway=True)
    return None


def sold_step(steps):
    """A sold deal with nothing left reads "Sold" (§5.9; OQ91 as changed by OQ101 c)."""
    found = next((step for step in steps if step['key'] == 'mark_sold'), None)
    return _brief(found) if found else None


def lost_step(reason):
    """What a lost deal says instead of a next step (I66, M34)."""
    label = f'Deal lost — {reason}' if reason else 'Deal lost'
    return {'key': 'lost', 'label': label, 'tab': None, 'params': {}, 'state': 'lost', 'severity': 'done',
            'owner': 'us'}  # fmt: skip


def waiting(steps, today):
    """The Overview's "Waiting on" banner (I119): the first waiting lead step, or the ball in our court."""
    found = next((step for step in steps if step['lead'] and step['state'] == 'waiting' and live(step)), None)
    if found is None:
        found = next((step for step in steps if step['state'] == 'waiting' and live(step)), None)
    if found is None:
        upcoming = next_step(steps)
        return {'state': 'with_us', 'label': catalogue.WITH_US, 'next': upcoming['label'] if upcoming else ''}
    follow_ups = [step for step in steps if step['key'].startswith('follow_up_') and step['state'] == 'open']
    return {
        'state': 'waiting',
        'key': found['key'],
        'label': found['label'],
        'owner': found['owner'],
        'owner_words': catalogue.OWNER_WORDS.get(found['owner'], 'someone'),
        'since': found.get('since'),
        'days': days_since(found.get('since'), today),
        'severity': 'warn' if follow_ups else 'info',
    }
