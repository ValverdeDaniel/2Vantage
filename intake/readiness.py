"""Ready to market (plan.md §5.2 Readiness; B13, B29, B33, B34). Pure: the deal's facts in, the state and its gaps
out.

- *Contacts OK*: at least one client contact with role HR admin or benefit administrator that has both a name and an
  email (old `contacts_ok`; B13).
- *BOR on file*: the BOR's typed signature, or a file of kind `bor` on the deal (§5.2; an earlier year's, B30, waits
  with renewals).
- **Ready to market**: every needed question answered with no open warning, contacts OK, census OK, BOR on file and
  the checklist clear. The badge reads **Sent to market** once the deal is marked as marketed, **Ready to market**
  when ready, else **Blocked** (B10, B33). Issues (B8) never block (OQ50).

`gaps` lists what stands between the deal and the market, in the banner's order (B9: the questions, then HR contact,
Signed BOR, Census) and then the checklist's missing items; Mark as marketed's 409 names them and "Market anyway"
records them (B34).
"""

from deals.contacts import ADMINS

from . import checklist

BLOCKED, READY, SUBMITTED = 'blocked', 'ready', 'submitted'
LABELS = {BLOCKED: 'Blocked — required items open', READY: 'Ready to market', SUBMITTED: 'Sent to market'}
QUESTION, TO_CHECK, CONTACTS, BOR, CENSUS, ITEM = 'question', 'to_check', 'contacts', 'bor', 'census', 'checklist'
HR_CONTACT, SIGNED_BOR, CENSUS_WORD = 'HR contact', 'Signed BOR', 'Census'


def contacts_ok(contacts):
    """`contacts`: objects or dicts with role, name and email."""

    def field(contact, key):
        value = contact.get(key) if isinstance(contact, dict) else getattr(contact, key, '')
        return str(value or '').strip()

    return any(field(c, 'role') in ADMINS and field(c, 'name') and field(c, 'email') for c in contacts)


def bor_on_file(signed_at, bor_files):
    return signed_at is not None or bool(bor_files)


def gap(kind, key, label):
    return {'kind': kind, 'key': key, 'label': label}


def gaps(*, missing, to_check, contacts_ok, bor_on_file, census_ok, items):
    """Every gap, once each. `missing` and `to_check` are [(key, label)] of the needed questions blank, and answered
    with an open warning; `items` the checklist's rows."""
    found = [gap(QUESTION, key, label) for key, label in missing]
    found += [gap(TO_CHECK, key, f'{label} (to check)') for key, label in to_check]
    if not contacts_ok:
        found.append(gap(CONTACTS, CONTACTS, HR_CONTACT))
    if not bor_on_file:
        found.append(gap(BOR, BOR, SIGNED_BOR))
    if not census_ok:
        found.append(gap(CENSUS, CENSUS, CENSUS_WORD))
    seen = {entry['key'] for entry in found if entry['kind'] in (CONTACTS, BOR, CENSUS)}
    found += [
        gap(ITEM, row['key'], row['label']) for row in items if row['status'] == 'missing' and row['key'] not in seen
    ]
    return found


def state(marketed_at, found_gaps):
    if marketed_at is not None:
        return SUBMITTED
    return BLOCKED if found_gaps else READY


def ready(*, marketed_at, contacts_ok, bor_on_file, census_ok, missing, to_check, items):
    """The ready block of the intake payload: {state, label, gaps, contacts_ok, bor_on_file, census_ok,
    checklist_clear}."""
    found = gaps(
        missing=missing,
        to_check=to_check,
        contacts_ok=contacts_ok,
        bor_on_file=bor_on_file,
        census_ok=census_ok,
        items=items,
    )
    now = state(marketed_at, found)
    return {
        'state': now,
        'label': LABELS[now],
        'gaps': found,
        'contacts_ok': contacts_ok,
        'bor_on_file': bor_on_file,
        'census_ok': census_ok,
        'checklist_clear': checklist.meter(items)['all_clear'],
    }
