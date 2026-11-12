"""A client's answer waiting on its owner's row (plan.md §5.8, §6.5–§6.6; L.6 "the owner contract", O.3.1). Pure.

Intake, census and (from slice 58) the questionnaire keep a client's answers in a `client` JSON on their own row,
keyed by slot, until a person approves them (OQ84): `{"value": …, "confirm": false, "link": 41, "at": ISO, "status":
"pending" | "approved" | "rejected" | "replaced", "by": None, "decided_at": None}`; census adds `prior`, the value
stored when the client answered (its values never go into Activity). One shape, so review has one code path, and one
rule for the version a page holds (`base`), which census reads from here (it sits to intake's right).

- `base(source, entry, link_id, blank=…)`: a compare-and-set stamp, never the value (B13): when the stored value last
  changed and when the pending answer did. A blank link (L66) sees only its own answers, so only its own entry counts
  and the stored value's stamp does not, and a stamp never hints at what it does not show.
- `shown(stored, entry, link_id, blank=…)`: the value the page shows for a slot: a pending answer over the stored
  value; on a blank link only the link's own answer.
- `next_entry(...)`: what a save does to a slot: an answer equal to the stored value drops the pending one, a new one
  replaces it (plan.md §5.8: "a newer save replaces the pending one").
"""

import hashlib

PENDING, APPROVED, REJECTED, REPLACED = 'pending', 'approved', 'rejected', 'replaced'
STATUSES = (PENDING, APPROVED, REJECTED, REPLACED)


def pending(entry):
    return isinstance(entry, dict) and entry.get('status') == PENDING


def own(entry, link_id):
    return pending(entry) and entry.get('link') == link_id


def visible(entry, link_id, *, blank=False):
    """The pending answer this page sees: any on the slot, or on a blank link only its own."""
    return own(entry, link_id) if blank else pending(entry)


def base(source, entry, link_id, *, blank=False):
    stored_at = '' if blank else str((source or {}).get('at') or '')
    pending_at = str(entry.get('at') or '') if visible(entry, link_id, blank=blank) else ''
    return hashlib.sha256(f'{stored_at}|{pending_at}'.encode()).hexdigest()[:16]


def shown(stored, entry, link_id, *, blank=False):
    if visible(entry, link_id, blank=blank):
        return entry.get('value')
    return '' if blank else stored


def by_colleague(entry, link_id):
    """A pending answer another person on the same request gave (a flag, never a name; L82)."""
    return pending(entry) and entry.get('link') != link_id


def made(value, link_id, at, *, prior=None):
    """A new pending entry. `prior` (census) is the stored value it would replace."""
    entry = {'value': value, 'confirm': False, 'link': link_id, 'at': at, 'status': PENDING, 'by': None}
    entry['decided_at'] = None
    if prior is not None:
        entry['prior'] = prior
    return entry


def next_entry(stored, entry, value, link_id, at, *, prior=None):
    """(the slot's entry after a save — None to drop it —, whether anything changed)."""
    if value == stored:
        return None, pending(entry)
    if pending(entry) and entry.get('value') == value:
        return entry, False
    return made(value, link_id, at, prior=prior), True


def same(a, b):
    """Two answers are the same: blanks alike, lists by their items."""
    if a in (None, '', []) and b in (None, '', []):
        return True
    return a == b
