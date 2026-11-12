"""The one set of review rules for every value owner (plan.md §3.7, §10.7; O.3.1; E85–E92; the old
market/value_review.py and the browser's valueReview.js). Pure: each function reads one `sources` entry (O.3.1's shape:
`{origin, by, at, doc, page, cell, line, low, loc, mark, confirmed, ...}`), never the database.

- A **mark** is a person's review of a value: `mark: {state: 'check' | 'ignored', by, at}` (⚑ Needs checking, or the
  warning ignored on the record) or `confirmed: {by, at, via?}` (approved). `apply_mark` is the only rule that sets
  them; `deals.values.apply` drops both whenever the value changes, so a mark never outlives its value (O.6 #35).
  A blank value has no entry and takes no mark.
- **What needs review (OQ28, Daniel 2026-11-11: "only the values claude doubted need approval, but even unapproved
  values shouldn't stop the user from continuing").** A value Claude read (`origin: ai`) needs a person's look only
  when Claude doubted it (`low`) or the locator could not find it in its file (`loc` absent or weak), until a person
  approves or ignores it; a value a person flagged ⚑ needs checking whatever its origin. That is `open_warning`, the
  one rule: owners' statuses (`to_check`), stored `flags` and every count call it, so the Advisor, the station and the
  Overview agree; no SQL copy exists (E91, O.6 #29). Nothing is ever blocked by an open warning: it is a count and a
  colour. Claude never approves a value itself (D-119): `confirmed` is always a person's.
- A typed (or imported) value the locator cannot find in its file is not an open warning: only Claude's values need
  approval (OQ28), and the old app located only what was read. It is still a `potential_error`, so the station's List
  sorts it into "Not in the file" and its grid filter (slice 23) can show it.
"""

from .locate.query import ABSENT, DERIVED, FILE_REASONS, NOCHECK, WEAK

APPROVE, IGNORE, CHECK, CLEAR = 'approve', 'ignore', 'check', 'clear'
ACTIONS = (APPROVE, IGNORE, CHECK, CLEAR)
CHECKING, IGNORED = 'check', 'ignored'  # the two mark states
READ = 'ai'  # the origin of a value Claude read
LOOK_AGAIN = (ABSENT, WEAK)  # what the locator could not find, or could not pin down (D-122, D-123)
MARK_KEYS = ('mark', 'confirmed')

# The List's eight buckets, worst first (D122, E56; the old FileReviewList.BUCKETS, words kept).
BUCKETS = [
    {
        'key': 'absent',
        'label': 'Not in the file',
        'tone': 'rose',
        'help': 'Code looked for this value in the file and it is printed nowhere: the likeliest misread.',
    },
    {
        'key': 'eye',
        'label': 'Check by eye',
        'tone': 'amber',
        'help': 'The file cannot settle it in code: a common figure with no label beside it, an image, or a scanned '
        'page.',
    },
    {'key': 'review', 'label': 'AI flagged', 'tone': 'amber', 'help': 'The reader was unsure of this value.'},
    {
        'key': 'unchecked',
        'label': 'Not checked yet',
        'tone': 'grey',
        'help': 'Read before files were checked, or the check has not run. “Check this file” fills it in.',
    },
    {
        'key': 'derived',
        'label': 'Worked out',
        'tone': 'blue',
        'help': 'Not printed as read, but the reader’s own rule turns a printed figure into it (80% the plan pays '
        'records 20).',
    },
    {
        'key': 'moved',
        'label': 'Found on another page',
        'tone': 'blue',
        'help': 'Printed in the file, on a different page from the one the read recorded.',
    },
    {'key': 'found', 'label': 'Found', 'tone': 'green', 'help': 'Printed in the file where the read said.'},
    {
        'key': 'other',
        'label': 'Not a printed figure',
        'tone': 'grey',
        'help': 'A yes/no, a choice or a summary the reader wrote: nothing to find.',
    },
]
BUCKET_KEYS = tuple(bucket['key'] for bucket in BUCKETS)
BUCKET_ORDER = {key: index for index, key in enumerate(BUCKET_KEYS)}

# The quality headline (E34, M87; the old DocumentsTab.qualityHeadline): the share of a file's values that are clean.
CLEAN, MOSTLY = 0.9, 0.7


def _entry(entry):
    return entry if isinstance(entry, dict) else {}


def mark_state(entry):
    """'check' · 'ignored' · ''."""
    return (_entry(entry).get('mark') or {}).get('state') or ''


def loc_state(entry):
    loc = _entry(entry).get('loc')
    return loc.get('state') or '' if isinstance(loc, dict) else ''


def marks_of(entry):
    """The entry's marks alone, for Activity: {mark?, confirmed?}, or None. Never the value (E74)."""
    entry = _entry(entry)
    marks = {key: entry[key] for key in MARK_KEYS if entry.get(key)}
    return marks or None


def with_marks(entry, marks):
    """The entry with its marks replaced by `marks` (a `marks_of` answer or None)."""
    out = {key: value for key, value in _entry(entry).items() if key not in MARK_KEYS}
    out.update(marks or {})
    return out


def apply_mark(entry, action, user_id, at):
    """The entry after a person's `action`, or None when nothing changes (E85; the old `_apply`):
    - approve: confirmed by this person, any mark off (unchanged when already approved and unmarked);
    - ignore / check: the mark set, any approval off (unchanged when already so and not approved);
    - clear (Undo, F67): the mark off; an approval stays (unchanged when there is no mark).
    A blank value has no entry and takes no mark. `at` is an ISO time."""
    if action not in ACTIONS:
        raise ValueError(f'Not a review action: {action}')
    if not isinstance(entry, dict) or not entry:
        return None
    mark, confirmed = entry.get('mark'), entry.get('confirmed')
    rest = {key: value for key, value in entry.items() if key not in MARK_KEYS}
    if action == CLEAR:
        if not mark:
            return None
        return {**rest, **({'confirmed': confirmed} if confirmed else {})}
    if action == APPROVE:
        if confirmed and not mark:
            return None
        return {**rest, 'confirmed': {'by': user_id, 'at': at}}
    state = IGNORED if action == IGNORE else CHECKING
    if mark_state(entry) == state and not confirmed:
        return None
    return {**rest, 'mark': {'state': state, 'by': user_id, 'at': at}}


def is_approved(entry):
    return bool(_entry(entry).get('confirmed'))


def is_ignored(entry):
    return mark_state(entry) == IGNORED


def is_dealt(entry):
    """A person dealt with it: approved or ignored. Such a value sinks within its bucket (E56)."""
    return is_approved(entry) or is_ignored(entry)


def doubted(entry):
    """Claude doubted this value, or the locator could not find it in its file: a value Claude read only (OQ28)."""
    entry = _entry(entry)
    return entry.get('origin') == READ and (bool(entry.get('low')) or loc_state(entry) in LOOK_AGAIN)


def open_warning(entry):
    """THE rule (OQ28): flagged ⚑ Needs checking by a person; or doubted (see `doubted`) and neither approved nor
    ignored. Counted in `flags`, shown amber, never blocking."""
    state = mark_state(entry)
    if state == CHECKING:
        return True
    return doubted(entry) and state != IGNORED and not is_approved(entry)


def potential_error(entry):
    """An open warning, or any value the locator could not find or pin down in its file, that nobody approved or
    ignored (D-123; the old potentialError). The station's filter and pick bar count these."""
    if open_warning(entry):
        return True
    return loc_state(entry) in LOOK_AGAIN and not is_dealt(entry)


def shows_approval(entry):
    """Whether an approval or an ignore changes what the value shows (E92, the old `shows_confirmation`): a value
    with a doubt, or one the locator could not find or pin down. A clean value's approval is kept but not drawn."""
    return bool(_entry(entry).get('low')) or loc_state(entry) in LOOK_AGAIN


def review_bucket(entry):
    """The List's bucket (D122, E56; the old `bucketOf`): where the locator's answer puts the value, else open
    warnings, else not checked; "moved" when the locator found it on another page than the one recorded."""
    entry = _entry(entry)
    loc = entry.get('loc') if isinstance(entry.get('loc'), dict) else None
    state = loc_state(entry)
    if state == ABSENT:
        return 'absent'
    if state == WEAK:
        return 'eye'
    if state == NOCHECK:
        return 'eye' if loc.get('why') in FILE_REASONS else 'other'
    if open_warning(entry):
        return 'review'
    if not loc:
        return 'unchecked'
    if state == DERIVED:
        return 'derived'
    if loc.get('page') and entry.get('page') and loc['page'] != entry['page']:
        return 'moved'
    return 'found'


def origin_bucket(entry):
    """Where a value came from, for the Overview's data confidence (M83): 'scanned' (Claude read it), 'corrected'
    (typed over a read value: it keeps its file), 'client' (the client's approved answer), 'typed' (everything a
    person entered or imported), or '' for no entry."""
    entry = _entry(entry)
    origin = entry.get('origin')
    if not origin:
        return ''
    if origin == READ:
        return 'scanned'
    if origin == 'client':
        return 'client'
    if origin in ('typed', 'relay') and entry.get('doc'):
        return 'corrected'
    return 'typed'


def quality_headline(high, low, missing):
    """{label, tone} for a file's values (E34, M87): high = read and clean, low = open warnings, missing = required
    blanks on the plans the file gave."""
    total = high + low + missing
    if total == 0:
        return {'label': 'Not scanned yet', 'tone': 'gray'}
    ratio = high / total
    if ratio >= CLEAN:
        return {'label': 'Clean scan', 'tone': 'green'}
    if ratio >= MOSTLY:
        return {'label': 'Mostly clean — review flags', 'tone': 'amber'}
    return {'label': 'Needs review', 'tone': 'rose'}


def warning_counts(entries):
    """{open, check, unflagged} over entries: the strip's "N AI values to review · M need checking" (E48)."""
    open_count = check = 0
    for entry in entries:
        if open_warning(entry):
            open_count += 1
            check += mark_state(entry) == CHECKING
    return {'open': open_count, 'check': check, 'unflagged': open_count - check}


def meta():
    """For /api/meta/: the List's buckets with their words (rule 1)."""
    return {'review_buckets': BUCKETS}
