"""One plan as the API sends it (plan.md §7.8, F.6): its own fields, and its cells' compact flags.

The comparison is compact (F.6, C23): a cell carries only what it has to say, as `{s, o, d, m}`: its status
(`missing` or `to_check`; blank and ok are left out), its origin when not typed, the index of its document in the
payload's `documents` list (listed once), and its review mark. A value's full source comes on ↗ (`plans/{id}/source/`).
"""

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


def cells(plan, status, documents):
    """{key: {s?, o?, d?, m?}} for the keys with something to say."""
    out = {}
    for key, source in plan.sources.items():
        if key not in plan.values or not isinstance(source, dict):
            continue
        cell = {}
        if source.get('origin') not in (None, 'typed'):
            cell['o'] = source['origin']
        if source.get('doc'):
            cell['d'] = documents.at(source['doc'])
        mark = (source.get('mark') or {}).get('state')
        if mark:
            cell['m'] = mark
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
        'enrollment': plan.enrollment,
        'enrollment_on': plan.enrollment_on,
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
