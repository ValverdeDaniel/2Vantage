"""Documents as the API sends them (plan.md §7.4; E.6). Reads only: nothing here writes."""

from deals.selectors import person

from . import kinds
from .models import Document

# Files that read as their plan year when nobody named them: "2027 Renewal / rates" (E95; Rebecca's naming ask).
YEAR_LABELLED = ('renewal', 'invoice', 'claims')


def display_name(document):
    """The name a file shows: its label, else "<effective year> <kind>" for a year-labelled kind, else its file name."""
    if document.label:
        return document.label
    effective = document.deal.effective_date
    if document.kind in YEAR_LABELLED and effective:
        return f'{effective.year} {kinds.label(document.kind)}'
    return document.original_name


def document_payload(document):
    """`document` (§7.4): its details, how the viewer shows it (`shape`), its member-data screen in brief, and whether
    it is protected or removed. Never the stored path."""
    screen = document.screen or {}
    return {
        'id': document.id,
        'original_name': document.original_name,
        'label': document.label,
        'display_name': display_name(document),
        'kind': document.kind,
        'bucket': kinds.bucket(document.kind),
        'role': document.role,
        'carrier': document.carrier,
        'lines': document.lines,
        'size': document.size,
        'page_count': document.page_count,
        'shape': kinds.shape_of(document.original_name),
        'source': document.source,
        'review_state': document.review_state,
        'screen': {
            'left_out_pages': screen.get('left_out_pages', []),
            'image_pages': screen.get('image_pages', []),
            'lists_members': bool(screen.get('lists_members')),
        },
        'protected': document.protected,
        'archived_at': document.archived_at,
        'archived_by': person(document.archived_by),
        'uploaded_by': person(document.uploaded_by),
        'uploaded_at': document.uploaded_at,
    }


def deal_documents(deal, archived=False):
    """The deal's files, newest first; with `archived`, only the removed ones ("Show removed files", E16)."""
    rows = (
        Document.all_objects.filter(deal=deal, archived_at__isnull=False)
        if archived
        else Document.objects.filter(deal=deal)
    )
    return [document_payload(d) for d in rows.select_related('deal', 'uploaded_by', 'archived_by')]

