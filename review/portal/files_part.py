"""The files part of a link's page (plan.md §8.20; L93, L94; B22, B3). Allowlisted: each slot the link asks, its
words, the extensions it takes, the note a person left the client, and the files received through this request (a
blank link: through this link) by name and time, never a document id, a staff upload or another request's file (B22).
The census template it offers is always blank (`census-template/`, B3).
"""

from deals import lines
from documents import kinds
from documents.models import Document

from . import asked as asked_rules
from . import words

CENSUS_SLOT = 'census_file'  # the census file's `Document.slot` (and ReviewNote key)


def slot_kind(slot):
    """(document kind, its lines) for a slot: `invoice@medical` → ('invoice', ['medical'])."""
    kind, _, line = slot.partition('@')
    return kind, [line] if line else []


def label(slot):
    kind, line = slot_kind(slot)
    text = words.COMPLIANCE.get(kind) or kinds.label(kind)
    return f'{text} — {lines.label(line[0])}' if line else text


def received(link_ids, slots):
    """{slot: [{name, at}]} of the files received through `link_ids` for `slots`, oldest first."""
    found = (
        Document.objects.filter(link_id__in=link_ids, source='client', slot__in=slots)
        .order_by('uploaded_at', 'id')
        .values_list('slot', 'original_name', 'uploaded_at')
    )
    out = {slot: [] for slot in slots}
    for slot, name, at in found:
        out[slot].append({'name': name, 'at': at.isoformat()})
    return out


def shown_links(link, link_ids):
    return [link.id] if link.blank else list(link_ids)


def documents(found, link, link_ids):
    got = received(shown_links(link, link_ids), found.documents)
    out = []
    for slot in found.documents:
        kind, _line = slot_kind(slot)
        out.append(
            {
                'slot': slot,
                'label': label(slot),
                'detail': words.FILE_DETAIL,
                'accept': kinds.BY_KEY[kind]['accept'],
                'note': asked_rules.checklist_note(found.intake, kind),
                'received': got[slot],
            }
        )
    return out


def census_file(found, link, link_ids):
    if not found.census_file:
        return None
    got = received(shown_links(link, link_ids), [CENSUS_SLOT])[CENSUS_SLOT]
    return {'detail': words.CENSUS_FILE_DETAIL, 'accept': kinds.BY_KEY['census']['accept'], 'received': got}
