"""Decisions on what the client sent (plan.md §5.8, §7.13 `review/approve/`, `reject/`; L.6 `decisions.py`; L16, L17,
L43, B38, C28, C32, C34; slice 55). Each is one transaction through the owners (rule 3): review never writes an
owner's row itself; `review.owners` names who decides each section.

- `approve(user, deal_id, refs=…)` approves the answers named; `approve(user, deal_id, surface=…, ready_only=True,
  include_idle=…)` is "Approve N ready ✓" (L43, C34): the section's answers whose link was submitted after its last
  save, and an idle link's only with the tick (D-153 C4), never an answer that blanks a value (a person looks at
  that); `ready_only=False` takes every answer waiting on the section ("Approve all").
- `reject(user, deal_id, refs)`: "Keep ours" (L17: a reject, so one writer).
- `undo(user, deal_id, refs)`: takes approvals back (C28 "undo approval"), through the owner's `revert_approval`.
Each returns Decided([ref], [Activity row]); the owners record their own rows (L.6: "the owners record approvals").
Lock order: the Deal first, then the owners in chain order (intake, then census), each locking its rows by id (O.3.7).
A ref with nothing to decide (decided meanwhile, by someone else) is skipped, so a repeated click changes nothing.
"""

from collections import namedtuple

from django.db import transaction
from rest_framework.exceptions import ValidationError

from deals import clock
from deals.models import Deal

from ..owners import OWNERS
from ..rules import refs as ref_rules
from ..rules import sections as section_rules
from ..selectors import entries as entry_rows

Decided = namedtuple('Decided', 'refs activity')

NO_SURFACE = 'Name the section: intake or census.'
BOTH = 'Send refs, or a section, not both.'
NOTHING = 'Name the answers to decide.'
TOO_MANY = f'Decide at most {ref_rules.LIMIT} answers at a time.'


def _split(refs):
    if not refs:
        raise ValidationError({'refs': [NOTHING]})
    if isinstance(refs, list) and len(refs) > ref_rules.LIMIT:
        raise ValidationError({'refs': [TOO_MANY]})
    try:
        return ref_rules.split(refs)
    except ref_rules.Bad as bad:
        raise ValidationError({'refs': bad.refs}) from bad


def _lock(deal_id):
    if not transaction.get_connection().in_atomic_block:
        raise RuntimeError('decisions lock inside transaction.atomic()')
    return Deal.objects.select_for_update(of=('self',)).get(pk=deal_id)


def _through(user, deal_id, by_surface, door):
    refs, rows = [], []
    for surface in ref_rules.SURFACES:
        slots = by_surface.get(surface) or []
        if not slots:
            continue
        decided = getattr(OWNERS[surface], door)(user, deal_id, slots)
        refs += [ref_rules.ref_of(surface, slot) for slot in decided[0]]
        rows += [row for row in decided[1] if row is not None]
    return Decided(refs, rows)


def section_refs(deal_id, surface, *, ready_only=True, include_idle=False, now=None):
    """The refs a section's "Approve N ready" (or, without `ready_only`, "Approve all") takes now."""
    found = entry_rows.waiting([deal_id], (surface,)).get(deal_id, [])
    if not ready_only:
        return [entry.ref for entry in found]
    links = entry_rows.links_of(found)
    return section_rules.ready_refs(found, links, now or clock.now(), include_idle=include_idle)


@transaction.atomic
def approve(user, deal_id, *, refs=None, surface=None, ready_only=False, include_idle=False):
    if surface is not None and refs is not None:
        raise ValidationError({'surface': [BOTH]})
    if surface is not None and surface not in ref_rules.SURFACES:
        raise ValidationError({'surface': [NO_SURFACE]})
    _lock(deal_id)
    if surface is not None:
        refs = section_refs(deal_id, surface, ready_only=ready_only, include_idle=include_idle)
        if not refs:
            return Decided([], [])
    return _through(user, deal_id, _split(refs), 'approve_client')


@transaction.atomic
def reject(user, deal_id, refs):
    by_surface = _split(refs)
    _lock(deal_id)
    return _through(user, deal_id, by_surface, 'reject_client')


@transaction.atomic
def undo(user, deal_id, refs):
    by_surface = _split(refs)
    _lock(deal_id)
    return _through(user, deal_id, by_surface, 'revert_approval')
