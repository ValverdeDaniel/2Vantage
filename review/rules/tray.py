"""The request tray's rules (plan.md §5.8; L49–L53; old 891f1b3 `review/notes.py` `target_for`, `_tray_target`,
`extend_candidates`, `sent_back_q`). Pure: the drafts' items, the deal's requests as `Candidate`s, and times.

**Where a draft goes** (`target`): every draft says where it goes, or why it cannot yet, before anything is sent (U1).
A draft named for a request goes there or nowhere ("one item, one draft": it never rides someone else's link). Else
the request its answer came through, then the newest open request already asking that section, then the newest open
request. A request can take an ask while it is not closed and one of its links is not turned off and is still inside
its 30-day ceiling: a link that ran out comes back when the ask joins it (L58). A census value shows people, so it goes
only on a request whose links ask for a PIN (OQ80, L64: a link is never silently tightened under its holder); with
none, it waits for a new link, which takes one (B18: "verified only" becomes "needs a PIN"). A draft about something
no longer on the deal is `GONE`, and sending drops it.

**Going back** (`going_back`): a client answer waiting for review that was sent back (or asked again) is out of
"to review" until they answer again: its send-back waits in the tray, or went out after the answer came on a request
that still opens. The queues list it under Going back and the section bar counts it (L14, L16; old `going_back_q`).

**When a sent ask is open** (`open_ask`): it went out, its request still opens, and nobody answered it since — the
client (a newer answer or file) or one of us (a newer decision on the value). Worked out on read, never stored: an
ask on a link that ran out asks nobody, and the item reads missing (or to review) again (L.6).
"""

from collections import namedtuple
from datetime import datetime

from . import policy

NEEDS_LINK = 'No open link to the client can take this yet: choose who to ask, and it goes on the new link.'
NEEDS_PIN = (
    'Census values show people, so they go only on a link that asks for a PIN, and no open link does: choose who to '
    'ask, and the new link takes one.'
)
GONE = (
    'This is no longer on the deal (the person left the census, or it is no longer asked): sending the tray drops it.'
)

CODES = {NEEDS_LINK: 'needs_link', NEEDS_PIN: 'needs_pin', GONE: 'gone'}  # each why's short name, for the screens

# One open request as the tray weighs it: its id, when it was made (newest first wins), the sections it already asks
# (`asks.sections`), the weakest security among its links that can still live, and its people's names.
Candidate = namedtuple('Candidate', 'request_id created_at sections security names')
# One draft's item: its ref, section, whether it is gone, the request its answer came through, the request a person
# named for it, and whether it shows people (a census value: PIN only).
Item = namedtuple('Item', 'ref section gone own named pin')


def live_links(links, now):
    """The links an ask joining their request reaches: not turned off, inside their ceiling (old
    `extend_candidates`)."""
    return [link for link in links if link.revoked_at is None and policy.can_renew(link, now)]


def can_take(closed_at, links, now):
    return closed_at is None and bool(live_links(links, now))


def weakest(links, now):
    """The security every live link of a request at least has."""
    levels = [link.security for link in live_links(links, now)] or [policy.LINK]
    return min(levels, key=lambda level: policy.RANK.get(level, 0))


def _newest(candidates):
    return sorted(candidates, key=lambda c: (c.created_at, c.request_id), reverse=True)


def target(item, candidates):
    """(Candidate or None, why). `candidates` are the deal's requests that can take an ask."""
    if item.gone:
        return None, GONE
    by_id = {c.request_id: c for c in candidates}
    if item.named is not None:
        found = by_id.get(item.named)
        if found is None:
            return None, NEEDS_LINK
        if item.pin and found.security != policy.PIN:
            return None, NEEDS_PIN
        return found, ''
    fits = [c for c in candidates if not item.pin or c.security == policy.PIN]
    if not fits:
        return None, (NEEDS_PIN if item.pin and candidates else NEEDS_LINK)
    if item.own in by_id and by_id[item.own] in fits:
        return by_id[item.own], ''
    carrying = [c for c in fits if item.section in c.sections]
    return _newest(carrying or fits)[0], ''


def moment(value):
    """A datetime from a datetime or an ISO text (entries and sources keep text), else None."""
    if isinstance(value, datetime) or value is None:
        return value
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def open_ask(sent_at, *, opens, answered_at=None, decided_at=None):
    """True while a sent ask waits on the client: its request still opens and nobody answered it since."""
    if sent_at is None or not opens:
        return False
    for later in (moment(answered_at), moment(decided_at)):
        if later is not None and later > sent_at:
            return False
    return True


def going_back(entries, drafted, sent):
    """The refs among `entries` (client answers waiting) that went back to the client. `drafted`: the refs a send-back
    or ask waits in the tray for; `sent`: {ref: the newest such that went out, on a request that still opens}."""
    out = set()
    for entry in entries:
        at = sent.get(entry.ref)
        answered = moment(entry.at)
        if entry.ref in drafted or (at is not None and (answered is None or answered <= at)):
            out.add(entry.ref)
    return out
