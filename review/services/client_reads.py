"""The reads a client's upload starts (plan.md §7.14, §10.4; D44, L111, L94; OQ89; slice 59).

OQ89's default: once the PHI gate is passed, the census and intake files a client uploads through their link are read
automatically and staged for a person; a paper questionnaire is only filed (staff read it with "Read with Claude ▸",
L125, G101), and so is every other file (a renewal waits for the same door). So:
- `target_of(document)`: the reader a client's file starts — the census reader for the census file, the intake reader
  for a file of a kind it reads (an invoice, a plan document, a 5500, "Other") — or '' for none. A reader the PHI-gate
  switch leaves unregistered starts nothing: the file is only filed (§10.8).
- `after_upload(document)`: once the upload commits, `start` asks ai for the read (`ai.services.start_client_read`: no
  person, labelled "Client portal", in the work lane; files of one kind join the read still waiting to start). It never
  fails the upload: the client's answer stands whatever the read does (old `_autostart_reader`, "never let a
  convenience auto-start break the public submit response"). The client never sees the read (L109).
The upload door only takes files on Save or Submit (L97), so these are the reads Save and Submit start (D44).
"""

import logging

from django.db import transaction

from ai import registry
from ai.services import start_client_read
from documents.models import Document

from ..portal.asked import PAPER

logger = logging.getLogger(__name__)

READS = ('census', 'intake')  # the readers a client's upload starts (OQ89), in the order a send runs them (D17)


def target_of(document):
    if document.source != 'client' or document.slot.startswith(PAPER):
        return ''
    for target in READS:
        reader = registry.readers.get(target)
        if reader is not None and document.kind in reader.kinds:
            return target
    return ''


def start(document_id):
    """Start the read one committed client upload asks for; the job, or None."""
    try:
        document = Document.objects.select_related('deal').get(pk=document_id)
        target = target_of(document)
        if not target:
            return None
        started = start_client_read(document.deal, [document.id], target=target)
        return started[0] if started else None
    except Exception as exc:  # noqa: BLE001 - never the upload's failure; the class only, never a name (rule 10)
        logger.warning('A client upload could not start its read (%s).', exc.__class__.__name__)
        return None


def after_upload(document):
    transaction.on_commit(lambda: start(document.id))
