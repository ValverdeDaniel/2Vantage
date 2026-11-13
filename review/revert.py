"""Revert of a review Activity row (plan.md §3.7, rule 4; O.3.2). Registered as `activity.reverters['review']` in
ReviewConfig.ready().

`deals.activity.revert` has already locked the Deal; this locks the requests, then the links, each by id. It refuses
after a later write to one of the row's fields (naming it), refuses to put a link that was opened back to "not sent"
(L71), and refuses a new PIN (a PIN is never kept, so there is nothing to put back). Otherwise each field's "before"
goes back: Undo of Turn off turns the link back on, of a close reopens the request, of an extension restores the
earlier expiry. A request's creation is not revertible (`deals.activity.NOT_REVERTIBLE`): its links are turned off or
the request closed instead. Slice 57's link settings put back what they see, the date and whether saves slide it, and
the reminder to nudge them.
"""

from datetime import datetime

from deals import activity

from . import words
from .models import ClientLink, ClientRequest
from .services import marks

MODELS = {'link': ClientLink, 'request': ClientRequest}
TIMES = {'sent_at', 'expires_at', 'revoked_at', 'closed_at'}
USERS = {'revoked_by', 'closed_by'}
TEXTS = {'close_reason'}
FLAGS = {'blank', 'slides'}  # slice 57's link settings
JSONS = {'nudge'}
LABELS = {
    'blank': 'What they see',
    'slides': 'Whether their saves push the date out',
    'nudge': 'The reminder to nudge them',
    'sent_at': 'Sent',
    'expires_at': 'When the link runs out',
    'revoked_at': 'Turned off',
    'revoked_by': 'Turned off',
    'closed_at': 'Closed',
    'closed_by': 'Closed',
    'close_reason': 'Why it was closed',
}


def _locked(changes):
    """{target: row}, requests first, then links, each by id."""
    ids = {'request': set(), 'link': set()}
    for entry in changes:
        kind, _, pk = entry['t'].partition(':')
        ids[kind].add(int(pk))
    rows = {}
    for kind in ('request', 'link'):
        for row in MODELS[kind].objects.select_for_update().filter(pk__in=ids[kind]).order_by('pk'):
            rows[f'{kind}:{row.pk}'] = row
    return rows


def _put(row, key, before):
    if key in TIMES:
        setattr(row, key, datetime.fromisoformat(before) if before else None)
    elif key in USERS:
        setattr(row, f'{key}_id', before)
    elif key in TEXTS:
        setattr(row, key, before or '')
    elif key in FLAGS:
        setattr(row, key, bool(before))
    elif key in JSONS:
        setattr(row, key, before or {})
    else:
        raise activity.Refused(activity.NOTHING_TO_PUT_BACK)


def _now(row, key):
    value = getattr(row, f'{key}_id' if key in USERS else key)
    return value.isoformat() if hasattr(value, 'isoformat') else value


def revert(row, user):
    if row.action == marks.MARKED:  # the Overview's marks across owners (slice 64): each owner's own Revert
        return marks.revert(row, user)
    if row.action == 'pin':
        raise activity.Refused(words.PIN_KEPT)
    later = activity.later_keys(row)
    if later:
        keys = sorted(later)
        raise activity.changed_since([LABELS.get(key, key) for _target, key in keys], [key for _target, key in keys])
    rows = _locked(row.changes)
    written = []
    for entry in row.changes:
        stored = rows.get(entry['t'])
        if stored is None:
            raise activity.Refused(activity.NOTHING_TO_PUT_BACK)
        if 'sent_at' in entry['k'] and entry['k']['sent_at'][0] is None and (stored.opened_at or stored.submitted_at):
            raise activity.Refused(words.OPENED)
        diff = {}
        for key, (before, _after) in entry['k'].items():
            diff[key] = [_now(stored, key), before]
            _put(stored, key, before)
        stored.save(update_fields=list(entry['k']))
        written.append(activity.change(entry['t'], diff))
    return written
