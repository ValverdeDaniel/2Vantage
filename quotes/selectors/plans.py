"""One plan as the API sends it (plan.md §7.8, F.6): its own fields, and its cells' compact flags.

The comparison is compact (F.6, C23): a cell carries only what it has to say, as `{s, o, d, m, p}`: its status
(`missing` or `to_check`; blank and ok are left out), its origin when not typed, the index of its document in the
payload's `documents` list (listed once), its review mark `m` (`mark_word`: ⚑ check always; ignored or approved
only where they change what the value shows, E92), and `p` when it is a potential error but not an open warning
(`look_again`; the station's Grid, E50). A value's full source comes on ↗ (`plans/{id}/source/`).
"""

from documents import review_rules
from documents.models import Document

from .. import facts
from .state import replaced_ids


class Documents:
    """The documents a payload's cells point at, each listed once."""

    def __init__(self):
        self.index = {}

    def at(self, document_id):
        return self.index.setdefault(document_id, len(self.index))

    def listed(self):
        # A removed (archived) file keeps its values' link and its name (E15).
        names = dict(Document.all_objects.filter(id__in=list(self.index)).values_list('id', 'original_name'))
        return [{'id': doc_id, 'name': names.get(doc_id, '')} for doc_id in self.index]


def mark_word(entry):
    """The review mark a cell shows (F64; the old reviewMarkClass): 'check' (⚑ Needs checking), 'ignored' or
    'approved' on a value whose doubt they settle (`review_rules.shows_approval`), else None."""
    state = review_rules.mark_state(entry)
    if state == review_rules.CHECKING:
        return state
    if not review_rules.shows_approval(entry):
        return None
    if state == review_rules.IGNORED:
        return state
    return 'approved' if review_rules.is_approved(entry) else None


def look_again(entry):
    """A potential error that is not an open warning (E50, D123): the locator could not find or pin the value down in
    its file and nobody dealt with it. The station's Grid filters and counts on it; the Advisor colours only `s`."""
    return review_rules.potential_error(entry) and not review_rules.open_warning(entry)


def cells(plan, status, documents):
    """{key: {s?, o?, d?, m?, p?}} for the keys with something to say."""
    out = {}
    for key, source in plan.sources.items():
        if key not in plan.values or not isinstance(source, dict):
            continue
        cell = {}
        if source.get('origin') not in (None, 'typed'):
            cell['o'] = source['origin']
        if source.get('doc'):
            cell['d'] = documents.at(source['doc'])
        mark = mark_word(source)
        if mark:
            cell['m'] = mark
        if look_again(source):
            cell['p'] = 1
        if cell:
            out[key] = cell
    for key, state in status.items():
        out.setdefault(key, {})['s'] = state
    return out


def star(plan):
    if not plan.starred:
        return None
    at = plan.starred_at.isoformat() if plan.starred_at else None
    return {'reason': plan.star_reason, 'by': plan.starred_by_id, 'at': at}


def base(plan):
    """The plan's own fields (no prices)."""
    return {
        'id': plan.id,
        'role': plan.role,
        'carrier': plan.carrier,
        'name': plan.name,
        'plan_number': plan.plan_number,
        'client_name': plan.client_name,
        'renews_id': plan.renews_id,
        'replaces_ids': list(plan.replaces_ids),
        'option_label': plan.option_label,
        'starred': plan.starred,
        'star': star(plan),
        'recommended': plan.recommended,
        'sold': plan.sold,
        'notes': plan.notes,
        'values': plan.values,
        'enrollment': plan.enrollment,  # its own typed counts; the line's switch is the comparison's `enrollment.on`
        # A copy or priced version names its original; the board's chips and arrows read both (F62, F43).
        'derived_from': plan.derived_from_id,
        'derived': plan.derived or None,
        'bundling': plan.bundling,  # the carrier's rates already include the bundle, or not (F78; slice 35)
    }


def plan_payload(plan):
    """One plan for a write's answer: its fields and its status (`replaces_ids` read when not set)."""
    if not hasattr(plan, 'replaces_ids'):
        plan.replaces_ids = sorted(replaced_ids(from_plan_id=plan.id).get(plan.id, []))
    return {**base(plan), 'line': plan.line, 'status': facts.statuses(plan.line, plan.values, plan.sources)}


def payloads(plans):
    """Several plans for a write's answer, their links in one query."""
    links = replaced_ids(from_plan_id__in=[plan.id for plan in plans])
    for plan in plans:
        plan.replaces_ids = sorted(links.get(plan.id, []))
    return [plan_payload(plan) for plan in plans]
