"""Where a request and each of its links stand, and what a link asks (plan.md §5.8; L55, L7, L8, L70). Pure: each
function takes the rows' fields (model instances or anything with the same attributes) and `now`.

- `request_state(links, closed_at, now)`: draft, partly_sent, waiting, answered, expired or closed (old
  `reviewrequest.vocab.request_state`). Answered as soon as anyone on it submits (the answers land in one place); a
  link turned off counts as run out.
- `link_state(link, now, closed, covered)`: one link in one vocabulary (old `LinkStatus.linkState`), plus `closed`,
  since a closed request's links no longer open (L70).
- `carries(asks, ref, missing, blank)`: the one rule for what a link asks (§5.8). The portal's allowlist, the ask
  rail, the tray and the board read it (slices 54–57).
- `soonest_first(rows)`: the Waiting lane's order (L7): the request whose live link runs out soonest first (nothing
  live, last), then the newest.
"""

from datetime import timedelta

from . import policy

DRAFT, PARTLY_SENT, WAITING, ANSWERED, EXPIRED, CLOSED = (
    'draft',
    'partly_sent',
    'waiting',
    'answered',
    'expired',
    'closed',
)
REQUEST_STATES = (DRAFT, PARTLY_SENT, WAITING, ANSWERED, EXPIRED, CLOSED)
OPEN_STATES = (DRAFT, PARTLY_SENT, WAITING)  # the Waiting lane's (old board.OPEN_REQUEST_STATES)

LINK_STATES = ('answered', 'off', 'closed', 'covered', 'draft', 'lapsed_draft', 'expired', 'opened', 'waiting')


def request_state(links, closed_at, now):
    if closed_at:
        return CLOSED
    if any(link.submitted_at for link in links):
        return ANSWERED
    sent = [link for link in links if link.sent_at]
    if not sent:
        return DRAFT
    if not any(policy.opens(link, now) for link in sent):
        return EXPIRED
    if len(sent) < len(links):
        return PARTLY_SENT
    return WAITING


def link_state(link, now, *, closed=False, covered=False):
    """`covered`: a colleague on the same request has answered it, so nobody waits on this link."""
    if link.submitted_at:
        return 'answered'
    if link.revoked_at is not None:
        return 'off'
    if closed:
        return 'closed'
    if covered:
        return 'covered'
    expired = link.expires_at <= now
    if not link.sent_at:
        return 'lapsed_draft' if expired else 'draft'
    if expired:
        return 'expired'
    return 'opened' if link.opened_at else 'waiting'


IDLE = timedelta(hours=24)  # answers saved and left this long are ready for review (L.6 `ready_why`)


def ready(link, now):
    """True when what came through `link` is ready for review: submitted after its last save, or idle 24 h."""
    if link.submitted_at and (link.last_saved_at is None or link.submitted_at >= link.last_saved_at):
        return True
    return link.last_saved_at is not None and now - link.last_saved_at >= IDLE


def in_progress(link, now, *, closed=False):
    """A link whose person has saved, has not submitted since and is not idle (L7 "X is still answering")."""
    saved = link.last_saved_at
    return saved is not None and not ready(link, now) and policy.opens(link, now, closed=closed)


def soonest_first(rows):
    """Rows with `soonest_days` (int or None) and `created_at` (sortable): two stable sorts, so a tie stays newest
    first."""
    rows = sorted(rows, key=lambda row: row['created_at'] or '', reverse=True)
    return sorted(rows, key=lambda row: (row['soonest_days'] is None, row['soonest_days'] or 0))


# ---- what a link asks ------------------------------------------------------------------------------------------


def _intake(asks, key, ref, missing, blank):
    intake = asks.get('intake') or {}
    scope = intake.get('scope')
    if key.startswith('block:'):
        return key.removeprefix('block:') in (intake.get('blocks') or [])
    if scope == 'all' or key in (intake.get('keys') or []):
        return True  # keys named beside a scope are asked too (what the tray joined, slice 56)
    if scope == 'missing':
        return ref in blank
    return scope == 'required' and ref in missing


def _census(asks, rest, ref, missing, blank):
    census = asks.get('census') or {}
    if rest == 'file':
        return bool(census.get('file'))
    member, _, column = rest.partition(':')
    scope = census.get('scope', 'none')
    columns = census.get('columns') or []
    if any(str(cell[0]) == member and cell[1] == column for cell in census.get('cells') or []):
        return True  # cells named beside a scope are asked too (what the tray joined, slice 56)
    if scope in ('none', 'selected') or (columns and column not in columns):
        return False
    if scope == 'all':
        return True
    return ref in (blank if scope == 'blank' else missing)


def _questionnaire(asks, rest):
    form_key, _, slot = rest.partition(':')
    for form in asks.get('questionnaires') or []:
        if form['form'] != form_key:
            continue
        if slot == 'file':
            return form.get('mode') == 'upload'
        if form.get('mode') != 'online':
            return False
        picks = form.get('picks') or {}
        named = (picks.get('fields') or []) + (picks.get('blocks') or [])
        return not named or slot in named
    return False


def carries(asks, ref, *, missing=frozenset(), blank=frozenset()):
    """True when a link asking `asks` asks for `ref`.

    Refs: `intake:<key>`, `intake:block:<block>`, `census:file`, `census:<member id>:<column>`, `q:<form>:<slot>`,
    `q:<form>:file` (a form asked in upload mode), `doc:<slot>`. `blank` holds the refs blank now (intake's shown
    blanks, census's empty cells) and `missing` those also needed (intake's needed to market, census's required
    blanks, the checklist's missing files): the caller reads them from the owners, since what a scope asks follows
    what is still missing (L6 Ch. 2). Intake `missing` and census `blank` read `blank`; intake `required`, census
    `missing` and documents `missing` read `missing`."""
    asks = asks or {}
    area, _, rest = str(ref).partition(':')
    if area == 'intake':
        return _intake(asks, rest, ref, missing, blank)
    if area == 'census':
        return _census(asks, rest, ref, missing, blank)
    if area == 'q':
        return _questionnaire(asks, rest)
    if area == 'doc':
        documents = asks.get('documents') or {}
        return rest in (documents.get('slots') or []) or (bool(documents.get('missing')) and ref in missing)
    return False
