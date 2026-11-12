"""A file's printed page numbers (plan.md §6.3; E94; the old ai/page_labels.py, D-149): `{"<pdf page>": "<printed>"}`
for the pages a carrier numbered differently from their place in the PDF, found by the quote reader in the bytes it
read (`documents.pages.printed_labels`) and kept when its read lands. Like `page_count` and `screen` at upload they come
from the file itself, so no Activity is recorded and Undo of the read leaves them.
"""

from ..models import Document


def set_page_labels(document_id, deal, labels):
    """Keep the file's labels; writes only when they differ. Returns whether it wrote."""
    clean = {str(page): str(printed)[:10] for page, printed in (labels or {}).items() if str(page).isdigit()}
    document = Document.all_objects.select_for_update().filter(pk=document_id, deal=deal).first()
    if document is None or document.page_labels == clean:
        return False
    document.page_labels = clean
    document.save(update_fields=['page_labels'])
    return True
