"""Filing the signed copy (plan.md §6.8, §9.12; G135, G50).

The officer's signature files the filled PDF as a protected Document of the form's kind (`questionnaire` for a medical
form, `stop_loss` for the disclosure): what the officer attested, kept whatever happens to the form after. Archive and
purge refuse it (O.3.7), and a reopen leaves it in Documents. An agent's signature after the officer's files a fresh
copy, which becomes the one that downloads; every copy filed is listed on the row (`signed_copies`). Called inside the
signing transaction, after the row holds its new signature; the document's bytes go to storage at once, and a
rolled-back signature leaves them for `sweep_orphan_files` (E98).
"""

from deals import clock
from documents.services import store_bytes

from .. import forms
from ..forms import STOP_LOSS_KIND
from ..pdf import build

KINDS = {'medical': 'questionnaire', STOP_LOSS_KIND: 'stop_loss'}  # form kind → the document kind it files as


def file_copy(user, deal, row, facts, who):
    """Build the signed form from the row as it now stands, file it protected, and point the row at it. The caller
    saves `signed_document` and `signed_copies`."""
    form = forms.FORMS[row.form]
    data = build.build(deal, row.form, row=row, facts=facts)
    document = store_bytes(
        user,
        deal,
        build.file_name(deal, row.form),
        data,
        KINDS[form['kind']],
        f'{forms.label(row.form)} — signed copy',
        protected=True,
    )
    by = user.id if getattr(user, 'is_authenticated', False) else None
    row.signed_document = document
    row.signed_copies = [
        *row.signed_copies,
        {'document': document.id, 'who': who, 'at': clock.now().isoformat(), 'by': by},
    ]
    return document
