"""What a PATCH of the RFP request may write, cleaned against what is stored (plan.md §7.11; K20–K27).

`stored(row)` is the request's settings as plain values (a deal with no row reads as the defaults); `apply(current,
changes, default_funding)` answers the new value of each key sent, or raises `Invalid` with an error per field
(K27: the screen says "That value was not accepted"). The carrier and funding chips send what a click changes,
`{add, remove}` (K21, K25: two quick clicks both land, where the old page sent the whole list from stale props); null
puts the funding back to its default and empties the carriers. The route takes 'warner', 'direct', or ''/null to
follow the band again (K20). The due date is a date (K26; the old one was raw text). Other carriers ≤ 300 characters,
notes ≤ 2,000, both trimmed. `done` and `sends` have their own doors (old `WRITER_OWNED`). The packet's ticks,
`include`, take `{key: true | false | null}` over the one key space (K.6: the census files, `form`, `cover`,
`proposal`, `questionnaire-<form>`, `disclosure-<form>`, `doc-<id>`), or 'reset'; this checks the key's shape, and the
service checks it names a row this deal's packet has and works out what is stored against the defaults the request
will have (`cards.include.merged`). The form chip (slice 46, K46) sends `form`: 'simplified' (or ''/null),
'small_group' or 'large_group'; blank is stored for the Simplified form, the standard at every size.
"""

import re
from datetime import date

from deals import carriers as identities

from . import request
from .cards import include as ticks
from .formats import scope
from .forms import maps

LIMITS = {'other_carriers': 300, 'notes': 2000}
SETTINGS = ('route', 'carriers', 'other_carriers', 'funding', 'form', 'due_date', 'notes', 'include')
EMPTY = {
    'route': '',
    'form': '',
    'carriers': [],
    'other_carriers': '',
    'funding': None,
    'due_date': None,
    'notes': '',
    'include': {},
}
WRITER_OWNED = {
    'done': 'Marked on each card with “Mark completed”, not here.',
    'sends': 'Recorded by marking an email draft sent, not here.',
}

UNKNOWN = 'This is not a setting of the RFP request.'
BAD_ROUTE = 'Send warner, direct, or null to follow the group size.'
BAD_PICKS = 'Send {"add": [...], "remove": [...]} with known keys.'
BAD_DATE = 'Enter a date like 2027-01-15, or leave it blank.'
BAD_TEXT = 'Send text.'
BAD_INCLUDE = 'Send {"<file key>": true, false or null}, or "reset".'
BAD_FORM = 'Send simplified, small_group or large_group.'
# The packet's keys beyond the census files (K.6's one key space): a document by id, a questionnaire by form.
FIXED_KEYS = ('form', 'cover', 'proposal')
PATTERNS = re.compile(r'^(?:doc-[1-9][0-9]{0,18}|questionnaire-[a-z0-9_]{1,40}|disclosure-[a-z0-9_]{1,40})$')
TOO_LONG = 'At most {limit:,} characters.'


class Invalid(Exception):
    """{field: [sentence]} for a 400."""

    def __init__(self, errors):
        super().__init__(errors)
        self.errors = errors


def stored(row):
    """The request's settings as plain values: lists, text, an ISO date or None."""
    if row is None:
        return {key: (type(value)(value) if isinstance(value, list | dict) else value) for key, value in EMPTY.items()}
    return {
        'route': row.route or '',
        'carriers': list(row.carriers or []),
        'other_carriers': row.other_carriers or '',
        'funding': None if row.funding is None else list(row.funding),
        'form': row.form or '',
        'due_date': row.due_date.isoformat() if row.due_date else None,
        'notes': row.notes or '',
        'include': dict(row.include or {}),
    }


def _picks(raw, current, known):
    """`current` plus `add` minus `remove`, in the vocabulary's order, or None when the shape or a key is wrong."""
    if not isinstance(raw, dict) or set(raw) - {'add', 'remove'}:
        return None
    add, remove = raw.get('add', []), raw.get('remove', [])
    if not isinstance(add, list) or not isinstance(remove, list):
        return None
    if any(not isinstance(key, str) or key not in known for key in [*add, *remove]):
        return None
    wanted = (set(current) | set(add)) - set(remove)
    return [key for key in known if key in wanted]


def _text(raw, key):
    if raw is None:
        return ''
    if not isinstance(raw, str):
        raise ValueError(BAD_TEXT)
    text = raw.strip()
    if len(text) > LIMITS[key]:
        raise ValueError(TOO_LONG.format(limit=LIMITS[key]))
    return text


def _date(raw):
    if raw in (None, ''):
        return None
    try:
        return date.fromisoformat(str(raw).strip()).isoformat()
    except ValueError:
        raise ValueError(BAD_DATE) from None


def is_file_key(key):
    """A key of the packet's one key space, by its shape (whether this deal has the row is the service's check)."""
    return isinstance(key, str) and (key in scope.keys() or key in FIXED_KEYS or bool(PATTERNS.match(key)))


def _include(raw):
    """The change asked for: 'reset', or {file key: bool | None}."""
    if raw == ticks.RESET:
        return ticks.RESET
    if not isinstance(raw, dict) or not raw:
        raise ValueError(BAD_INCLUDE)
    if any(not is_file_key(key) or not (value is None or isinstance(value, bool)) for key, value in raw.items()):
        raise ValueError(BAD_INCLUDE)
    return dict(raw)


def _form(raw):
    if raw in (None, ''):
        return ''
    if raw not in maps.VARIANTS:
        raise ValueError(BAD_FORM)
    return maps.STORED[raw]


def _one(key, raw, current, default_funding):
    if key == 'route':
        if raw in (None, ''):
            return ''
        if raw not in request.ROUTE_KEYS:
            raise ValueError(BAD_ROUTE)
        return raw
    if key == 'carriers':
        picked = [] if raw is None else _picks(raw, current['carriers'], identities.KEYS)
        if picked is None:
            raise ValueError(BAD_PICKS)
        return picked
    if key == 'funding':
        if raw is None:
            return None
        base = current['funding'] if current['funding'] is not None else default_funding()
        picked = _picks(raw, base, request.FUNDING_KEYS)
        if picked is None:
            raise ValueError(BAD_PICKS)
        return picked
    if key == 'due_date':
        return _date(raw)
    if key == 'include':
        return _include(raw)
    if key == 'form':
        return _form(raw)
    return _text(raw, key)


def apply(current, changes, default_funding):
    """{key: new value} for every key in `changes`. `default_funding()` is called only when a funding click lands on
    the default. Raises Invalid({field: [sentence]})."""
    if not isinstance(changes, dict):
        raise Invalid({'non_field_errors': ['Send the settings as an object.']})
    out, errors = {}, {}
    for key, raw in changes.items():
        if key in WRITER_OWNED:
            errors[key] = [WRITER_OWNED[key]]
        elif key not in SETTINGS:
            errors[key] = [UNKNOWN]
        else:
            try:
                out[key] = _one(key, raw, current, default_funding)
            except ValueError as exc:
                errors[key] = [str(exc)]
    if errors:
        raise Invalid(errors)
    return out
