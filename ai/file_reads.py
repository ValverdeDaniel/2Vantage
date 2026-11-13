"""What other apps read about ai's reads of a deal's files (plan.md §10.4, §10.5; D13, D44, L125, L135; slice 59). Reads
only, a fixed number of queries.

- `client_reads(deal_ids)`: the reads a client's upload started (no person, "Client portal") whose change sets wait
  for a person, oldest first: review's To review rows, "Their census file was read · Review and apply ▸" (L135).
- `where_reads_stand(deal_id)`: {document id: reading | waiting | used} by the newest read of each file (a file with no
  read, or whose newest read failed, was stopped or set aside, is left out): whether "Read with Claude ▸" on a
  client's file would start one (L125).
- `reader_for(kind)`: the reader that reads files of `kind` when a person asks for one file to be read, in the order a
  send runs them (D17): a renewal or a quote goes to the quote reader, an invoice to intake's (L125); '' for none.
"""

from django.db.models import BooleanField, Case, Value, When

from . import kinds, registry
from .models import Job
from .services.jobs import CLIENT_PORTAL
from .services.landing import APPLIED, DISCARDED, UNDONE
from .services.landing import waiting as is_waiting

READING, WAITING, USED = 'reading', 'waiting', 'used'
RESOLVED = (DISCARDED, APPLIED, UNDONE)


def client_reads(deal_ids):
    """{deal_id: [{job_id, target, documents, summary, counts, finished_at}]}."""
    staged = (
        Job.objects.filter(deal_id__in=list(deal_ids), kind=kinds.READ, created_by__isnull=True, land='staged')
        .filter(actor_label=CLIENT_PORTAL, status__in=(kinds.DONE, kinds.CANCELLED), result__has_key='items')
        .exclude(resolution__in=RESOLVED)
        .order_by('id')
    )
    out = {}
    for job in staged:
        if is_waiting(job):
            result = job.result or {}
            out.setdefault(job.deal_id, []).append(
                {
                    'job_id': job.id,
                    'target': job.target,
                    'documents': job.documents,
                    'summary': result.get('summary', ''),
                    'counts': result.get('counts') or {},
                    'finished_at': job.finished_at,
                }
            )
    return out


def _state(status, land, resolution, has_items):
    if status in kinds.ACTIVE:
        return READING
    if resolution.startswith(APPLIED):
        return USED
    waits = status in (kinds.DONE, kinds.CANCELLED) and land == 'staged' and has_items
    return WAITING if waits and not resolution.startswith(RESOLVED) else ''


def where_reads_stand(deal_id):
    rows = (
        Job.objects.filter(deal_id=deal_id, kind=kinds.READ)
        .annotate(
            has_items=Case(
                When(result__has_key='items', then=Value(True)), default=Value(False), output_field=BooleanField()
            )
        )
        .order_by('id')
        .values_list('documents', 'status', 'land', 'resolution', 'has_items')
    )
    out = {}
    for documents, status, land, resolution, has_items in rows:  # the newest read of a file decides
        state = _state(status, land, resolution, has_items)
        for document_id in documents or []:
            out[document_id] = state
    return {document_id: state for document_id, state in out.items() if state}


def reader_for(kind):
    for target in kinds.SEND_ORDER:
        reader = registry.readers.get(target)
        if reader is not None and kind in reader.kinds:
            return target
    return ''
