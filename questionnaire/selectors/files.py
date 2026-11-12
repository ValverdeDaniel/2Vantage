"""Which copy of a form downloads (plan.md §9.12; G56, G135). Reads; never writes.

Once the officer has signed and the copy is filed, "Download PDF" is that filed copy — what was attested, byte for
byte — rather than a fresh build; before, it is built from the form as it stands, DRAFT on it. A form signed before
filing existed (or whose file is gone) builds fresh: it is signed, so it prints the signatures.
"""

from collections import namedtuple

from ..models import Questionnaire
from ..pdf import build

Copy = namedtuple('Copy', 'data document name signed')


def filed(row):
    """The filed signed copy of a signed form, or None."""
    document = row.signed_document if row is not None and row.locked else None
    return document if document is not None and document.file else None


def download(deal, form_key):
    """Copy(bytes, the filed Document or None, file name, whether the officer has signed)."""
    row = Questionnaire.objects.select_related('signed_document').filter(deal_id=deal.id, form=form_key).first()
    document = filed(row)
    if document is not None:
        with document.file.open('rb') as handle:
            return Copy(handle.read(), document, build.file_name(deal, form_key), True)
    signed = bool(row and row.locked)
    return Copy(build.build(deal, form_key, row=row), None, build.file_name(deal, form_key), signed)
