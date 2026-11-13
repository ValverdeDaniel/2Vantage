"""Marks across every value owner, in one transaction (plan.md §10.7, §8.6, §7.13; M88–M91; M.6 `mark_document`; O.6
#30; slice 64): the Overview's data confidence approves, ignores, flags and unmarks values through here.

`mark(user, deal_id, action, document_id=…|refs=…)` is `POST deals/{id}/review/marks/`:
- `document_id`: one file's values on every owner — Confirm all (approve) takes every value read from it, census
  included; Ignore N warnings and ⚑ Needs checking its open warnings; clear its marked values (`review_rules.takes`).
  A file of another deal is a 404.
- `refs`: exactly those values, each in its owner's form ("intake:fein", "census:<id>:<key>", "plan:<id>:<key>",
  "questionnaire:<form>:<slot>"): the marked lists' Undo, ✓ Approve and Undo all.
Lock order (O.3.7): the Deal first, then the owners in chain order — intake, census, quotes, the questionnaires — each
locking its own rows by id and writing them through its own `services.file_marks` (rule 3: review never writes an
owner's row). One Activity row (area `review`, action `marked`, never merged) holds every owner's marks before and
after under `mark.<key>`, never a value (§3.8), with the file when one was named. Marks are bookkeeping: no
`updated_at` moves. Returns Marked(action, {owner: values changed}, the row or None).

`revert(row, user)` is that row's Undo, through `reverters['review']`: each owner's entries go back through the
owner's own Revert (`reverters[owner]`, action `marked`), in chain order, on the values still as the row left them; a
value changed or marked since stays as it is. When none can go back the Revert is refused, and a sold plan or a signed
form refuses it outright (rule 4).
"""

from collections import namedtuple
from types import SimpleNamespace

from django.db import transaction
from django.http import Http404
from rest_framework.exceptions import ValidationError

from census.services import file_marks as census_marks
from deals import activity, clock
from deals.models import Deal
from documents.models import Document
from documents.review_rules import ACTIONS, CHECK
from intake.services import file_marks as intake_marks
from questionnaire.services import file_marks as questionnaire_marks
from quotes.services import file_marks as quote_marks

from .common import AREA

Marked = namedtuple('Marked', 'action changed row')

MARKED = 'marked'
# Chain order: the order a mark locks and writes the owners in (O.3.7). Each owner's area is its reverter's key.
OWNERS = (
    ('intake', intake_marks),
    ('census', census_marks),
    ('quotes', quote_marks),
    ('questionnaire', questionnaire_marks),
)
REF_OWNER = {'intake': 'intake', 'census': 'census', 'plan': 'quotes', 'questionnaire': 'questionnaire'}
TARGET_OWNER = {'intake': 'intake', 'member': 'census', 'plan': 'quotes', 'questionnaire': 'questionnaire'}
DONE = {'approve': 'Approved', 'ignore': 'Ignored', 'check': 'Flagged', 'clear': 'Unmarked'}
LIMIT = 500  # refs in one request: the marked lists send at most 50 of each

ONE_TARGET = 'Name one file, or the values to review — not both.'
BAD_ACTION = 'The action is approve, ignore, check or clear.'
BAD_REFS = 'Name the values to review.'
NOT_A_VALUE = 'Some of those are not values a review can mark.'
ALL_CHANGED = 'Every value this review marked was changed or reviewed again after it, so it cannot be reverted.'


def _ids(raw):
    """A file id from the body: an int (a bool or anything else is a 400; past bigint, no file: 404)."""
    if isinstance(raw, bool):
        raise ValidationError({'document_id': ['Give the file’s id.']})
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise ValidationError({'document_id': ['Give the file’s id.']}) from exc
    if value < 1 or value > 2**63 - 1:
        raise Http404
    return value


def _split(refs):
    """{owner: [refs]} in the owners' own forms; 400 for anything else."""
    if not isinstance(refs, list) or not refs or len(refs) > LIMIT:
        raise ValidationError({'refs': [BAD_REFS]})
    out = {}
    for ref in refs:
        owner = REF_OWNER.get(str(ref).partition(':')[0])
        if owner is None:
            raise ValidationError({'refs': [NOT_A_VALUE]})
        out.setdefault(owner, []).append(str(ref))
    return out


def _summary(action, count, document_id):
    what = 'value' if count == 1 else 'values'
    tail = ' as needing checking' if action == CHECK else ''
    return f'{DONE[action]} {count} {what}{tail}' + (' from one file' if document_id else '')


@transaction.atomic
def mark(user, deal_id, action, *, document_id=None, refs=None):
    if action not in ACTIONS:
        raise ValidationError({'action': [BAD_ACTION]})
    if (document_id is None) == (refs is None):
        raise ValidationError({'non_field_errors': [ONE_TARGET]})
    by_owner = _split(refs) if refs is not None else None
    if document_id is not None:
        document_id = _ids(document_id)
        if not Document.all_objects.filter(deal_id=deal_id, pk=document_id).exists():
            raise Http404
    deal = Deal.objects.select_for_update(of=('self',)).get(pk=deal_id)  # the Deal first (O.3.7)
    at = clock.now().isoformat()
    changes, changed = [], {}
    for owner, module in OWNERS:
        if by_owner is not None and owner not in by_owner:
            continue
        found = module.mark(user, deal, action, document_id=document_id, refs=(by_owner or {}).get(owner), at=at)
        count = sum(len(entry['k']) for entry in found)
        if count:
            changed[owner] = count
            changes += found
    if not changes:
        return Marked(action, {}, None)
    total = sum(changed.values())
    row = activity.record(
        deal,
        user,
        AREA,
        MARKED,
        _summary(action, total, document_id),
        count=total,
        changes=changes,
        document_id=document_id,
    )
    return Marked(action, changed, row)


def _batches(changes):
    """[(owner, [entries])] in chain order; a questionnaire's entries one form at a time (its Revert takes one)."""
    by_owner = {}
    for entry in changes:
        owner = TARGET_OWNER.get(str(entry['t']).partition(':')[0])
        if owner is None or not isinstance(entry['k'], dict):
            raise activity.Refused(activity.NO_REVERTER)
        by_owner.setdefault(owner, []).append(entry)
    out = []
    for owner, _module in OWNERS:
        entries = by_owner.get(owner, [])
        if owner == 'questionnaire':
            out += [(owner, [entry]) for entry in entries]
        elif entries:
            out.append((owner, entries))
    return out


def revert(row, user):
    """Put back one `marked` row's marks through each owner's own Revert. Runs inside `deals.activity.revert`'s
    transaction, after the Deal lock; returns the changes written."""
    written, missed = [], []
    for owner, entries in _batches(row.changes):
        part = SimpleNamespace(
            pk=row.pk, id=row.id, deal_id=row.deal_id, deal=row.deal, subject=row.subject, area=owner,
            action=MARKED, changes=entries, document_id=row.document_id,
        )  # fmt: skip
        try:
            written += activity.reverters[owner](part, user)
        except activity.Refused as refused:
            if not refused.keys:
                raise  # a sold plan, a signed form: refused outright (rule 4)
            missed.append(refused)
    if not written:
        if len(missed) == 1:
            raise missed[0]
        raise activity.Refused(ALL_CHANGED, [key for refused in missed for key in refused.keys])
    return written
