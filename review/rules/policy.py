"""How a link is protected and how long it lives (plan.md §5.8, §3.8; L60–L64, L69; OQ80, OQ81, OQ83). Pure.

**The floor (OQ80, the narrowed rule; L64 Ch. 1).** A link needs a PIN, given by phone, when its page shows census
people (any census scope but `none`) or questionnaire answers (a form asked online), and for medical or claimant
send-backs. Upload-only asks (the census file, documents, a form in upload mode) and intake open with the private
link alone, the old default. A link is never below its floor. An emailed code ("verified recipient") waits for
outbound mail (L65), so there are two levels. The rule is fixed in code (OQ83: no admin switches).

**Life (OQ81, the old sliding rule; L61, L62).** A new link lives 7 days. A client's save gives it its life again
from then, at most once a day, never past its ceiling, 30 days from creation; submitting does not slide it. A date a
person picks ends the link at 23:59:59 that day in the agency's time zone, capped at the ceiling, and stops the
sliding. Extend and Restore give the link its life again from now, within the ceiling (L60).
"""

from datetime import datetime, time, timedelta

LINK, PIN = 'link', 'pin'
LEVELS = (LINK, PIN)  # weakest first
RANK = {LINK: 0, PIN: 1}

LIFE_DAYS = 7
CEILING_DAYS = 30
LIFE = timedelta(days=LIFE_DAYS)
CEILING = timedelta(days=CEILING_DAYS)
SLIDE_STEP = timedelta(days=1)  # a save slides the expiry at most once a day (L62, P2)
EXPIRING_DAYS = 2  # "Runs out in N days" on the Waiting lane (old board.EXPIRING_DAYS)
PIN_DIGITS = 6
PIN_TRIES = 5  # wrong PINs before the link locks, until a person makes a new one (L64, L77)
MESSAGE_LIMIT = 1000  # a request's message (L55)
MAX_PEOPLE = 20  # people on one request, a link each (L56)

# What sets the floor, in the builder's words ("Census needs a PIN").
CENSUS = 'Census'
QUESTIONNAIRE = 'Questionnaire answers'
SENSITIVE = 'Medical and claimant questions'


def floor(asks, *, sensitive=False):
    """{'level', 'because': [what set it]}: the lowest level a link asking `asks` may have. `sensitive` is a medical
    or claimant send-back on the link (slice 56 passes it)."""
    asks = asks or {}
    because = []
    if (asks.get('census') or {}).get('scope', 'none') not in ('none', ''):
        because.append(CENSUS)
    if any((form or {}).get('mode') == 'online' for form in asks.get('questionnaires') or []):
        because.append(QUESTIONNAIRE)
    if sensitive:
        because.append(SENSITIVE)
    return {'level': PIN if because else LINK, 'because': because}


def stricter(a, b):
    """The stricter of two levels: a new link rises to its floor by itself (L40)."""
    return a if RANK[a] >= RANK[b] else b


def first_life(now):
    """(expires_at, ceiling_at) of a link made at `now`."""
    return now + LIFE, now + CEILING


def picked_expiry(day, ceiling_at, zone):
    """The end of `day` (23:59:59) in the agency's zone, never past the ceiling (L61). Callers refuse a past day and a
    day after the ceiling's own day with a sentence."""
    return min(datetime.combine(day, time(23, 59, 59), tzinfo=zone), ceiling_at)


def latest_day(ceiling_at, zone):
    """The last day a person may pick: the ceiling's own day in the agency's zone."""
    return ceiling_at.astimezone(zone).date()


def renewed(expires_at, ceiling_at, now):
    """The expiry Extend and Restore give: its life again from now, never shorter than it is, never past the
    ceiling."""
    return max(expires_at, min(now + LIFE, ceiling_at))


def slid_on_save(link, now):
    """The expiry a client's save moves this link to, or None when it stays: a picked date stops the slide, a link
    turned off never slides, and it moves at most once a day (L62; slice 54 calls this)."""
    if not link.slides or link.revoked_at is not None:
        return None
    moved = renewed(link.expires_at, link.ceiling_at, now)
    return moved if moved - link.expires_at >= SLIDE_STEP else None


def opens(link, now, *, closed=False):
    """True while the link opens: not on a closed request, not turned off, not run out."""
    return not closed and link.revoked_at is None and link.expires_at > now


def can_renew(link, now):
    """True while Extend or Restore can give the link more life: it is still inside its ceiling."""
    return link.ceiling_at > now


def days_left(expires_at, now):
    return max(0, (expires_at - now).days)


def nudge_open(nudge, link, now, today, *, closed=False, lost=False):
    """True when a person asked to be reminded to nudge this link (`nudge.on`, a YYYY-MM-DD day) and the day has
    come, it is not done, the link still opens and the deal is not lost (L69; Agenda lists it from slice 60)."""
    on = (nudge or {}).get('on')
    if not on or (nudge or {}).get('done_at') or lost:
        return False
    return str(on) <= today.isoformat() and opens(link, now, closed=closed) and link.submitted_at is None
